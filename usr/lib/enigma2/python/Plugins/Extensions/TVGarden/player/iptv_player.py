#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - IPTV Player
Advanced player with channel zapping
Based on TV Garden Project
"""
import re
from enigma import (
    eServiceReference,
    iPlayableService,
    eTimer,
    getDesktop
)
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.ActionMap import ActionMap
from Components.Label import Label
# from Components.config import config
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.InfoBarGenerics import (
    InfoBarSeek,
    InfoBarAudioSelection,
    InfoBarNotifications,
)
import time
from os.path import isdir
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from ..helpers import log, timer_connect, is_youtube_url
from ..utils.config import get_config
from ..utils.youtube_helper import resolve_youtube
from .. import _


# Service types: 4097 = servicemp3 (always available),
# 5001 = gstplayer and 5002 = exteplayer3 (provided by ServiceApp)
SERVICE_MP3 = 4097
SERVICE_GSTPLAYER = 5001
SERVICE_EXTEPLAYER3 = 5002


def has_serviceapp():
    """Check if the ServiceApp system plugin is installed"""
    try:
        return isdir(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/ServiceApp"))
    except Exception:
        return False


def get_service_type(player):
    """Map the 'player' setting to an Enigma2 service type"""
    if player in ("exteplayer3", "gstplayer"):
        if has_serviceapp():
            if player == "exteplayer3":
                return SERVICE_EXTEPLAYER3
            return SERVICE_GSTPLAYER
        log.warning(
            "Player '%s' requires ServiceApp, falling back to 4097" %
            player, module="Player")
    return SERVICE_MP3


# ============ DETECT SCREEN RESOLUTION ============
def get_screen_resolution():
    """Get current screen resolution"""
    desktop = getDesktop(0)
    return desktop.size().width(), desktop.size().height()


screen_width, screen_height = get_screen_resolution()

# Set overlay dimensions based on screen resolution
if screen_width >= 2560:  # WQHD
    OVERLAY_WIDTH = 2560
    OVERLAY_HEIGHT_TOP = 70
    OVERLAY_HEIGHT_INFO = 80
    FONT_SIZE_TOP = 42
    FONT_SIZE_INFO = 36
    OVERLAY_Y_INFO = screen_height - 100  # 1340
    OVERLAY_Y_TOP = 10
    IMAGES_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/wqhd"
    SKIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/skins/wqhd"

elif screen_width >= 1920:  # FHD
    OVERLAY_WIDTH = 1920
    OVERLAY_HEIGHT_TOP = 60
    OVERLAY_HEIGHT_INFO = 70
    FONT_SIZE_TOP = 36
    FONT_SIZE_INFO = 32
    OVERLAY_Y_INFO = screen_height - 80  # 1000
    OVERLAY_Y_TOP = 5
    IMAGES_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/fhd"
    SKIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/skins/fhd"

else:  # HD (1280x720)
    OVERLAY_WIDTH = 1280
    OVERLAY_HEIGHT_TOP = 50
    OVERLAY_HEIGHT_INFO = 60
    FONT_SIZE_TOP = 28
    FONT_SIZE_INFO = 24
    OVERLAY_Y_INFO = screen_height - 70  # 650
    OVERLAY_Y_TOP = 0
    IMAGES_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/hd"
    SKIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/skins/hd"


def convert_youtube_embed_to_watch(url):
    """
    [TVGarden patch] Converte URL embed YouTube in URL watch.
    Così ytdlpwrapper (Enigma2) lo riconosce e lo risolve.

    https://www.youtube-nocookie.com/embed/VIDEO_ID  →  https://www.youtube.com/watch?v=VIDEO_ID
    https://www.youtube.com/embed/VIDEO_ID            →  https://www.youtube.com/watch?v=VIDEO_ID
    https://youtu.be/VIDEO_ID                         →  https://www.youtube.com/watch?v=VIDEO_ID
    """
    try:
        # youtube-nocookie.com/embed/XXX o youtube.com/embed/XXX
        m = re.search(
            r'(?:youtube-nocookie\.com|youtube\.com)/embed/([^/?#&]+)', url)
        if m:
            return "https://www.youtube.com/watch?v=%s" % m.group(1)

        # youtube.com/live/XXX (live diretti)
        m = re.search(r'youtube\.com/live/([^/?#&]+)', url)
        if m:
            return "https://www.youtube.com/watch?v=%s" % m.group(1)

        # youtu.be/XXX (short)
        m = re.search(r'youtu\.be/([^/?#&]+)', url)
        if m:
            return "https://www.youtube.com/watch?v=%s" % m.group(1)

        # youtube.com/shorts/XXX
        m = re.search(r'youtube\.com/shorts/([^/?#&]+)', url)
        if m:
            return "https://www.youtube.com/watch?v=%s" % m.group(1)

        # youtube.com/v/XXX
        m = re.search(r'youtube\.com/v/([^/?#&]+)', url)
        if m:
            return "https://www.youtube.com/watch?v=%s" % m.group(1)
    except Exception:
        pass
    return url


class TvInfoBarShowHide():
    """ InfoBar show/hide control, accepts toggleShow and hide actions, might start
    fancy animations. """
    STATE_HIDDEN = 0
    STATE_HIDING = 1
    STATE_SHOWING = 2
    STATE_SHOWN = 3
    FLAG_CENTER_DVB_SUBS = 2048
    skipToggleShow = False

    def __init__(self):
        self["ShowHideActions"] = ActionMap(
            ["InfobarShowHideActions"],
            {
                "toggleShow": self.OkPressed,
                "hide": self.hide
            },
            0
        )
        self.__event_tracker = ServiceEventTracker(
            screen=self, eventmap={
                iPlayableService.evStart: self.serviceStarted})
        self.__state = self.STATE_SHOWN
        self.__locked = 0

        self.helpOverlay = Label("")
        self.helpOverlay.skinAttributes = [
            ("position", "0,{}".format(OVERLAY_Y_TOP)),
            ("size", "{},{}".format(OVERLAY_WIDTH, OVERLAY_HEIGHT_TOP)),
            ("font", "Regular;{}".format(FONT_SIZE_TOP)),
            ("halign", "center"),
            ("valign", "center"),
            ("foregroundColor", "#00ffffff"),
            ("backgroundColor", "#80000000"),
            ("transparent", "0"),
            ("zPosition", "99")
        ]

        self["helpOverlay"] = self.helpOverlay
        self["helpOverlay"].hide()

        # Bottom overlay (channel info)
        self.infoOverlay = Label("")
        self.infoOverlay.skinAttributes = [
            ("position", "0,{}".format(OVERLAY_Y_INFO)),
            ("size", "{},{}".format(OVERLAY_WIDTH, OVERLAY_HEIGHT_INFO)),
            ("font", "Regular;{}".format(FONT_SIZE_INFO)),
            ("halign", "center"),
            ("valign", "center"),
            ("foregroundColor", "#00ffffff"),
            ("backgroundColor", "#80000000"),
            ("transparent", "0"),
            ("zPosition", "99")
        ]
        self["infoOverlay"] = self.infoOverlay
        self["infoOverlay"].hide()

        # Timer to hide the overlay after a while
        self.hideTimer = eTimer()
        self.hideTimer_conn = timer_connect(self.hideTimer, self.doTimerHide)

        self.onShow.append(self.__onShow)
        self.onHide.append(self.__onHide)

    def get_current_channel_info(self):
        """Method to be overridden by the child class (TVGardenPlayer)"""
        if hasattr(self, 'channel_list') and hasattr(self, 'current_index'):
            if self.channel_list and 0 <= self.current_index < len(
                    self.channel_list):
                channel = self.channel_list[self.current_index]
                name = channel.get('name', 'N/A')
                index = self.current_index + 1
                total = len(self.channel_list)

                # Add country/language if available
                extra = []
                if channel.get('country'):
                    extra.append(channel.get('country'))
                if channel.get('language'):
                    extra.append(channel.get('language'))

                extra_str = " [{}]".format(', '.join(extra)) if extra else ""

                return "{} [{}/{}]{}".format(name, index, total, extra_str)
        return "TV Garden Player"

    def show_overlays(self):
        """Show both overlays with controls and channel info."""
        try:
            # Controls text
            controls = _(
                "CH+/CH- = Change | OK = Toggle | STOP = Exit | by Lululla")

            # Get channel info
            channel_info = self.get_current_channel_info()

            self["helpOverlay"].setText(controls)
            self["helpOverlay"].show()

            self["infoOverlay"].setText(channel_info)
            self["infoOverlay"].show()

            # Start hide timer (5 seconds)
            self.hideTimer.start(5000, True)

        except Exception as e:
            print("[TvInfoBar] Error showing overlays: {}".format(e))

    def hide_overlays(self):
        """Hide both overlays."""
        if self["helpOverlay"].visible:
            self.hideTimer.stop()
            self["helpOverlay"].hide()
            self["infoOverlay"].hide()

    def show_help_overlay(self):
        help_text = (
            "OK = Info | CH-/CH+ = Prev/Next | PLAY/PAUSE = Toggle | STOP = Stop | EXIT = Exit | by Lululla"
        )
        self["helpOverlay"].setText(help_text)
        self["helpOverlay"].show()

        if not hasattr(self, 'help_timer'):
            self.help_timer = eTimer()
            self.help_timer_conn = timer_connect(
                self.help_timer, self.hide_help_overlay)

        self.help_timer.start(5000, True)

    def hide_help_overlay(self):
        if self["helpOverlay"].visible:
            self["helpOverlay"].hide()

    def OkPressed(self):
        """Toggle overlays on OK press."""
        if self["helpOverlay"].visible:
            self.hide_overlays()
        else:
            self.show_overlays()
        self.toggleShow()

    def __onShow(self):
        self.__state = self.STATE_SHOWN
        self.startHideTimer()

    def __onHide(self):
        self.__state = self.STATE_HIDDEN

    def doShow(self):
        self.hideTimer.stop()
        self.show()
        self.startHideTimer()

    def doHide(self):
        self.hide()
        if self["helpOverlay"].visible:
            self.hide_overlays()

    def serviceStarted(self):
        if self.execing:
            self.doShow()
            self.show_overlays()

    def startHideTimer(self):
        if self.__state == self.STATE_SHOWN and not self.__locked:
            self.hideTimer.stop()
            self.hideTimer.start(5000, True)
        elif hasattr(self, "pvrStateDialog"):
            self.hideTimer.stop()
        self.skipToggleShow = False

    def doTimerHide(self):
        if self["helpOverlay"].visible:
            self.hide_overlays()
            self.toggleShow()

    def toggleShow(self):
        if not self.skipToggleShow:
            if self.__state == self.STATE_HIDDEN:
                self.doShow()
                self.show_help_overlay()
            else:
                self.doHide()
                if self["helpOverlay"].visible:
                    if hasattr(self, 'help_timer'):
                        self.help_timer.stop()
                    self.hide_help_overlay()
        else:
            self.skipToggleShow = False

    def lockShow(self):
        try:
            self.__locked += 1
        except BaseException:
            self.__locked = 0
        if self.execing:
            self.show()
            self.hideTimer.stop()
            self.skipToggleShow = False

    def unlockShow(self):
        try:
            self.__locked -= 1
        except BaseException:
            self.__locked = 0
        if self.__locked < 0:
            self.__locked = 0
        if self.execing:
            self.startHideTimer()


class TVGardenPlayer(
        InfoBarBase,
        InfoBarSeek,
        InfoBarAudioSelection,
        InfoBarNotifications,
        TvInfoBarShowHide,
        Screen):
    STATE_IDLE = 0
    STATE_PLAYING = 1
    STATE_PAUSED = 2
    ENABLE_RESUME_SUPPORT = True
    ALLOW_SUSPEND = True

    def __init__(self, session, service, channel_list=None, current_index=0):
        Screen.__init__(self, session)
        self.session = session
        self.skinName = 'MoviePlayer'

        self.config = get_config()
        self.channel_list = channel_list if channel_list else []
        self.itemscount = len(self.channel_list)
        if not (0 <= current_index < self.itemscount):
            current_index = 0
        self.current_index = current_index
        self.stream_running = False
        self.eof_count = 0
        self.last_eof_time = 0
        self.current_service = None
        self.play_request = 0
        self.closing = False
        self._cleaned_up = False

        InfoBarBase.__init__(self)
        InfoBarSeek.__init__(self)
        InfoBarAudioSelection.__init__(self)
        InfoBarNotifications.__init__(self)
        TvInfoBarShowHide.__init__(self)

        log.debug("INIT: Got %d channels, starting at index %d" %
                  (self.itemscount, self.current_index), module="Player")
        if self.channel_list:
            current_ch = self.channel_list[self.current_index]
            log.debug(
                "Current channel: %s" %
                current_ch.get('name'),
                module="Player")
            log.debug(
                "Current URL: %s" %
                (current_ch.get('stream_url') or current_ch.get('url')),
                module="Player")

        self['actions'] = ActionMap(
            [
                'MoviePlayerActions',
                'MovieSelectionActions',
                'MediaPlayerActions',
                'EPGSelectActions',
                'OkCancelActions',
                'InfobarShowHideActions',
                'InfobarActions',
                'DirectionActions',
                'InfobarSeekActions'
            ],
            {
                "stop": self.leave_player,
                "cancel": self.leave_player,
                "channelDown": self.previous_channel,
                "channelUp": self.next_channel,
                "down": self.previous_channel,
                "up": self.next_channel,
                "back": self.leave_player,
                "info": self.show_channel_info,
            },
            -1
        )

        self.__event_tracker = ServiceEventTracker(
            screen=self,
            eventmap={
                iPlayableService.evStart: self.__serviceStarted,
                iPlayableService.evEOF: self.__evEOF,
                iPlayableService.evStopped: self.__evStopped,
            }
        )
        self.srefInit = self.session.nav.getCurrentlyPlayingServiceReference()
        self.eof_recovery_timer = eTimer()
        self.eof_recovery_timer_conn = timer_connect(
            self.eof_recovery_timer, self.restartAfterEOF)

        self.stream_check_timer = eTimer()
        self.stream_check_timer_conn = timer_connect(
            self.stream_check_timer, self.check_stream_status)

        self.audio_reset_timer = eTimer()
        self.audio_reset_timer_conn = timer_connect(
            self.audio_reset_timer, self.reset_audio_tracks)
        self.onFirstExecBegin.append(self.start_stream)
        self.onClose.append(self.cleanup)

    def get_current_channel_info(self):
        """Override for TvInfoBarShowHide"""
        if self.channel_list and 0 <= self.current_index < len(
                self.channel_list):
            channel = self.channel_list[self.current_index]
            name = channel.get('name', 'N/A')
            index = self.current_index + 1
            total = self.itemscount

            # Add country/language if available
            extra = []
            if channel.get('country'):
                extra.append(channel.get('country'))
            if channel.get('language'):
                extra.append(channel.get('language'))

            extra_str = " [{}]".format(', '.join(extra)) if extra else ""
            player_type = self.config.get("player", "auto")

            return "{} [{}/{}]{} | {}".format(
                name, index, total, extra_str, player_type)
        return "TV Garden Player"

    def start_stream(self):
        """Start playing the current channel with error handling"""
        if not self.channel_list or self.closing:
            if not self.channel_list:
                log.error("No channel list!", module="Player")
            return

        current_channel = self.channel_list[self.current_index]
        stream_url = current_channel.get(
            'stream_url') or current_channel.get('url')
        channel_name = current_channel.get('name', 'TV Garden')

        if not stream_url:
            log.error(
                "No stream URL for channel %d" %
                self.current_index, module="Player")
            self.show_error_message(_("No stream URL for: %s") % channel_name)
            return

        log.info(
            "Playing channel %d: %s" %
            (self.current_index, channel_name), module="Player")
        log.debug("URL: %s..." % stream_url[:80], module="Player")

        self.play_request += 1
        request_id = self.play_request

        if is_youtube_url(stream_url):
            # yt-dlp can take a long time: resolve it off the GUI thread
            log.info(
                "YouTube channel detected: %s" %
                channel_name, module="Player")
            self.show_overlays_text(_("Resolving YouTube stream..."))
            try:
                from twisted.internet import threads
                d = threads.deferToThread(resolve_youtube, stream_url)
                d.addCallback(self._youtube_resolved, request_id, channel_name)
                d.addErrback(self._youtube_failed, request_id)
            except Exception as e:
                log.error("Cannot start YouTube resolver: %s" %
                          e, module="Player")
                self._youtube_resolved(
                    resolve_youtube(stream_url), request_id, channel_name)
            return

        self._play_url(stream_url, channel_name)

    def _youtube_resolved(self, result, request_id, channel_name):
        """Called on the GUI thread when yt-dlp has finished"""
        if self.closing or request_id != self.play_request:
            return
        resolved, error = result
        if resolved:
            log.info("YouTube resolved: %s..." %
                     resolved[:80], module="Player")
            self._play_url(resolved, channel_name)
        else:
            log.error("Failed to resolve YouTube stream: %s" %
                      error, module="Player")
            message = _("YouTube stream not available")
            if error:
                message += "\n\n%s" % error
            if error == "yt-dlp is not installed":
                message += "\n" + _("Install it with: opkg install python3-yt-dlp")
            self.show_error_message(message)

    def _youtube_failed(self, failure, request_id):
        log.error("YouTube resolver error: %s" % failure, module="Player")
        self._youtube_resolved(
            (None, failure.getErrorMessage()), request_id, "")

    def show_overlays_text(self, text):
        try:
            self["infoOverlay"].setText(text)
            self["infoOverlay"].show()
        except Exception:
            pass

    def _play_url(self, stream_url, channel_name):
        """Play a resolved URL"""
        self.eof_count = 0
        try:
            if isinstance(stream_url, (tuple, list)):
                stream_url = str(stream_url[0])
            else:
                stream_url = str(stream_url)

            player_type = self.config.get("player", "auto")
            service_type = get_service_type(player_type)
            log.info("Player: %s, service_type=%d" %
                     (player_type, service_type), module="Player")

            sref = eServiceReference(service_type, 0, stream_url)
            sref.setName(channel_name)

            self.session.nav.playService(sref)
            self.current_service = sref
            self.stream_running = True
            log.info("Playback started", module="Player")

            self.show_overlays()
            self.start_stream_check_timer()

        except Exception as error:
            log.error("ERROR starting stream: " + str(error), module="Player")
            self.stream_running = False
            self.show_error_message(_("Cannot play: %s") % channel_name)

    def start_stream_check_timer(self):
        """Start timer to check if stream is actually playing"""
        self.stream_check_timer.start(3000, True)

    def check_stream_status(self):
        """Check whether the stream is actually playing."""
        try:
            service = self.session.nav.getCurrentService()
            if service:
                info = service.info()
                if info:
                    # If we can retrieve info, the stream is likely working
                    log.info(
                        "Stream appears to be playing correctly",
                        module="Player")
                    return
        except Exception:
            pass

        log.warning("Stream might have failed to start", module="Player")

    def stop_stream(self):
        """Stop the current stream"""
        if self.stream_running:
            self.stream_running = False
            try:
                self.session.nav.stopService()
            except BaseException:
                pass

    def restartAfterEOF(self):
        """Restart stream after EOF"""
        try:
            log.info("Restarting stream after EOF", module="Player")
            self.stop_stream()
            self.start_stream()
        except Exception as e:
            log.error("Error restarting after EOF: %s" % e, module="Player")

    def next_channel(self):
        """Switch to the next channel with audio fix"""
        if self.itemscount <= 1:
            return

        self.stop_stream()
        self.current_index = (self.current_index + 1) % self.itemscount
        self.start_stream()
        # Reset audio tracks after 1 second
        self.audio_reset_timer.start(1000, True)

    def previous_channel(self):
        """Switch to the previous channel with audio fix"""
        if self.itemscount <= 1:
            return

        self.stop_stream()
        self.current_index = (self.current_index - 1) % self.itemscount
        self.start_stream()
        # Reset audio tracks after 1 second
        self.audio_reset_timer.start(1000, True)

    def reset_audio_tracks(self):
        """Reset audio tracks when changing channels"""
        log.debug("Resetting audio tracks...", module="Player")

        try:
            service = self.session.nav.getCurrentService()
            if service:
                audio = service.audioTracks()
                if audio:
                    num_tracks = audio.getNumberOfTracks()
                    log.debug("Audio tracks: %d" % num_tracks, module="Player")
                    if num_tracks > 0:
                        audio.selectTrack(0)
                        log.debug(
                            "Audio tracks reset successfully",
                            module="Player")
                    else:
                        log.debug("No audio tracks available", module="Player")
        except Exception as e:
            log.error("Error resetting audio: %s" % e, module="Player")

    def show_channel_info(self):
        """Display information for the current channel."""
        if self.channel_list and 0 <= self.current_index < len(
                self.channel_list):
            channel = self.channel_list[self.current_index]
            info = "Channel: %s\n" % channel.get('name', 'N/A')
            info += "Index: %d/%d\n" % (self.current_index +
                                        1, self.itemscount)
            info += "Player: %s\n" % self.config.get("player", "auto")

            if channel.get('country'):
                info += "Country: %s\n" % channel.get('country')
            if channel.get('language'):
                info += "Language: %s\n" % channel.get('language')

            url = channel.get('stream_url') or channel.get('url', 'N/A')
            if len(url) > 60:
                info += "URL: %s..." % url[:60]
            else:
                info += "URL: %s" % url

            self.session.open(MessageBox, info, MessageBox.TYPE_INFO)

    def show_error_message(self, message):
        """Show error message"""
        self.session.open(MessageBox, message, MessageBox.TYPE_ERROR)

    def __serviceStarted(self):
        """Service started playing"""
        log.debug("Playback started successfully", module="Player")
        self.state = self.STATE_PLAYING

    def __evEOF(self):
        """End of file reached"""
        log.info("End of stream (EOF)", module="Player")

        current_time = time.time()
        if current_time - self.last_eof_time < 10:
            self.eof_count += 1
        else:
            self.eof_count = 1

        self.last_eof_time = current_time

        if self.eof_count <= 3:
            delay = 2 + (self.eof_count * 2)  # 2, 4, 6 seconds
            log.info("Restarting in %d seconds (attempt %d/3)" %
                     (delay, self.eof_count), module="Player")
            self.eof_recovery_timer.start(delay * 1000, True)
        else:
            log.warning("Too many EOFs, stopping", module="Player")
            self.leave_player()

    def __evStopped(self):
        """Service stopped (also fired while zapping, so do not close)"""
        log.info("Playback stopped", module="Player")
        self.stream_running = False

    def cleanup(self):
        """Clean up resources (runs once, from onClose)"""
        if self._cleaned_up:
            return
        self._cleaned_up = True
        self.closing = True
        # Stop all timers
        self.eof_recovery_timer.stop()
        self.stream_check_timer.stop()
        self.audio_reset_timer.stop()
        self.stop_stream()

        # Restore initial service
        if self.srefInit:
            try:
                self.session.nav.playService(self.srefInit)
            except BaseException:
                pass

    def leave_player(self):
        """Exit the player"""
        if self.closing:
            return
        self.closing = True
        self.close()
