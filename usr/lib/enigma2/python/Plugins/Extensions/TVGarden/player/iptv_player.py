#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - IPTV Player
Advanced player with channel zapping
Based on TV Garden Project
"""
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
from ..helpers import log
from ..utils.config import get_config
from .. import _


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
        try:
            self.hideTimer.timeout.connect(self.doTimerHide)
        except BaseException:
            self.hideTimer.callback.append(self.doTimerHide)

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
            try:
                self.help_timer_conn = self.help_timer.timeout.connect(
                    self.hide_help_overlay)
            except BaseException:
                self.help_timer.callback.append(self.hide_help_overlay)

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
        self.current_index = current_index
        self.itemscount = len(self.channel_list)
        self.stream_running = False
        self.eof_count = 0
        self.last_eof_time = 0
        self.current_service = None

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
        try:
            self.eof_recovery_timer.timeout.connect(self.restartAfterEOF)
        except BaseException:
            self.eof_recovery_timer.callback.append(self.restartAfterEOF)

        self.stream_check_timer = eTimer()
        try:
            self.stream_check_timer.timeout.connect(self.check_stream_status)
        except BaseException:
            self.stream_check_timer.callback.append(self.check_stream_status)

        self.audio_reset_timer = eTimer()
        try:
            self.audio_reset_timer.timeout.connect(self.reset_audio_tracks)
        except BaseException:
            self.audio_reset_timer.callback.append(self.reset_audio_tracks)
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

            # Add performance info
            use_hw_accel = self.config.get("use_hardware_acceleration", True)
            hw_accel = "HW" if use_hw_accel else "SW"
            buffer_size = self.config.get("buffer_size", 2048)
            player_type = self.config.get("player", "auto")

            return "{} [{}/{}]{} | {} | {}KB | {}".format(
                name, index, total, extra_str, hw_accel, buffer_size, player_type)
        return "TV Garden Player"

    def should_use_hardware_acceleration(self, stream_url):
        """Decide whether to use hardware acceleration for this stream"""
        if not self.config.get("use_hardware_acceleration", True):
            return False

        # Check stream type
        url_lower = stream_url.lower()

        # Formats that usually support hardware acceleration
        hw_accel_formats = [
            '.mp4', '.m4v', '.mov',        # MP4 container
            '.ts', '.m2ts', '.mts',        # MPEG-TS
            '.mkv',                        # Matroska
            '.avi',                        # AVI
            '.flv',                        # Flash Video
        ]

        # Codecs that support hardware acceleration
        hw_accel_codecs = [
            'h264', 'h.264', 'avc',        # H.264
            'h265', 'h.265', 'hevc',       # H.265/HEVC
            'mpeg2', 'mpeg-2',             # MPEG-2
            'mpeg4', 'mpeg-4',             # MPEG-4
        ]

        # Check file format
        for fmt in hw_accel_formats:
            if fmt in url_lower:
                return True

        # Check codec in URL (if specified)
        for codec in hw_accel_codecs:
            if codec in url_lower:
                return True

        # For HTTP streams, try hardware acceleration
        if url_lower.startswith(('http://', 'https://')):
            return True

        return False

    def build_standard_service_ref(self, url_encoded, name_encoded):
        """Build standard service reference"""
        return "4097:0:1:0:0:0:0:0:0:0:%s:%s" % (url_encoded, name_encoded)

    def build_service_ref_with_hw_accel(self, url_encoded, name_encoded):
        """Build service reference with hardware acceleration support"""
        # Format for hardware acceleration (depends on player)
        player = self.config.get("player", "auto")

        if player == "exteplayer3":
            # exteplayer3 with hardware acceleration
            return "4097:0:1:0:0:0:0:0:0:0:%s:%s" % (url_encoded, name_encoded)
        elif player == "gstplayer":
            # gstreamer with hardware acceleration
            return "4097:0:1:0:0:0:0:0:0:0:%s:%s" % (url_encoded, name_encoded)
        else:
            # Standard format
            return "4097:0:1:0:0:0:0:0:0:0:%s:%s" % (url_encoded, name_encoded)

    def add_buffer_size_param(self, ref_str, buffer_size_kb):
        """Add buffer size parameter if supported"""
        player = self.config.get("player", "auto")
        if player == "exteplayer3" and buffer_size_kb > 0:
            buffer_size_bytes = buffer_size_kb * 1024
            ref_str += "?buffersize=%d" % buffer_size_bytes
            log.debug("Added buffer size: %sKB (%s bytes)" %
                      (buffer_size_kb, buffer_size_bytes), module="Player")
        return ref_str

    def is_problematic_stream(self, url):
        """Check whether a stream URL may cause playback issues."""
        url_lower = url.lower()

        # Warning signs that usually indicate problematic streams
        warning_signs = [
            "moveonjoy.com",   # Site known to cause crashes
            "akamaihd.net",    # Often uses DRM
            "drm",
            "widevine",
            "playready",
            ".mpd",
            "/dash/",
            "encryption",
            "key",
            "license"
        ]

        return any(sign in url_lower for sign in warning_signs)

    def show_stream_warning(self, channel_name):
        """Show warning about potentially problematic stream"""
        message = (
            "Warning: %s\n\n"
            "This stream might use encryption or DRM that is not supported by your receiver.\n\n"
            "Try another channel.") % channel_name
        self.session.open(MessageBox, message, MessageBox.TYPE_WARNING)

    def start_stream(self):
        """Start playing the current channel with error handling"""
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
            return

        log.info(
            "Playing channel %d: %s" %
            (self.current_index,
             channel_name),
            module="Player")
        log.debug("URL: %s..." % stream_url[:80], module="Player")

        use_hw_accel = self.config.get("use_hardware_acceleration", True)
        buffer_size = self.config.get("buffer_size", 2048)
        player_type = self.config.get("player", "auto")

        log.info("=== PERFORMANCE SETTINGS ===", module="Player")
        log.info("Player: %s" % player_type, module="Player")
        log.info(
            "Hardware Acceleration: %s" %
            ("ENABLED" if use_hw_accel else "DISABLED"),
            module="Player")
        log.info("Buffer Size: %s KB" % buffer_size, module="Player")

        # Decisione HW acceleration
        if self.should_use_hardware_acceleration(stream_url):
            log.info(
                "HW Acceleration decision: WILL USE for this stream",
                module="Player")
        else:
            log.info(
                "HW Acceleration decision: WILL NOT USE for this stream",
                module="Player")

        # Buffer size application
        if player_type == "exteplayer3" and buffer_size > 0:
            log.info(
                "Buffer size will be applied: %s bytes" %
                (buffer_size * 1024), module="Player")
        else:
            log.info(
                "Buffer size setting may not apply to player: %s" %
                player_type, module="Player")

        # Check if the URL may be problematic
        if self.is_problematic_stream(stream_url):
            log.warning("Stream might be problematic", module="Player")
            self.show_stream_warning(channel_name)

        self.stream_running = True
        self.eof_count = 0

        try:
            # Create service reference with performance parameters
            url_encoded = stream_url.replace(":", "%3a")
            name_encoded = channel_name.replace(":", "%3a")

            # Add User-Agent if needed
            if "#User-Agent=" not in stream_url:
                stream_url_with_ua = stream_url + "#User-Agent=TVGarden/1.0"
                url_encoded = stream_url_with_ua.replace(":", "%3a")

            # Build service reference string with additional parameters
            if self.should_use_hardware_acceleration(stream_url):

                ref_str = self.build_service_ref_with_hw_accel(
                    url_encoded, name_encoded)
                log.debug("Using hardware acceleration", module="Player")
            else:
                # Use standard format
                ref_str = self.build_standard_service_ref(
                    url_encoded, name_encoded)
                log.debug("Using standard playback", module="Player")

            # Add buffer size if supported
            ref_str = self.add_buffer_size_param(ref_str, buffer_size)

            log.debug("ServiceRef string: " +
                      ref_str[:100] + "...", module="Player")

            sref = eServiceReference(ref_str)
            sref.setName(channel_name)

            # Start service with timeout
            self.session.nav.playService(sref)
            self.current_service = sref

            # Show overlays briefly
            self.show_overlays()
            # Start a timer to check whether the stream plays correctly
            self.start_stream_check_timer()

        except Exception as error:
            log.error("ERROR starting stream: " + str(error), module="Player")
            self.stream_running = False
            self.show_error_message("Cannot play: " + channel_name)

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
            time.sleep(0.5)
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
            # Add performance settings info
            use_hw_accel = self.config.get("use_hardware_acceleration", True)
            buffer_size = self.config.get("buffer_size", 2048)
            player_type = self.config.get("player", "auto")
            info += "Player: %s\n" % player_type
            info += "HW Accel: %s\n" % ("On" if use_hw_accel else "Off")
            info += "Buffer: %sKB\n" % buffer_size

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
        """Service stopped"""
        log.info("Playback stopped", module="Player")
        self.stream_running = False
        self.close()

    def cleanup(self):
        """Clean up resources"""
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
        self.cleanup()
        self.close()
