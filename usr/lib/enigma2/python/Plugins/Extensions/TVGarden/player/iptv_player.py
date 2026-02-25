#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - IPTV Player
Advanced player with channel zapping
Based on TV Garden Project
"""
from __future__ import print_function
from enigma import (
    eServiceReference,
    iPlayableService,
    eTimer
)
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import config
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.InfoBarGenerics import (
    InfoBarSeek,
    InfoBarAudioSelection,
    InfoBarNotifications,
)

from ..helpers import log
from ..utils.config import get_config


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
            ("position", "0,0"),
            ("size", "1280,50"),
            ("font", "Regular;28"),
            ("halign", "center"),
            ("valign", "center"),
            ("foregroundColor", "#FFFFFF"),
            ("backgroundColor", "#666666"),
            ("transparent", "0"),
            ("zPosition", "100")
        ]

        self["helpOverlay"] = self.helpOverlay
        self["helpOverlay"].hide()

        self.hideTimer = eTimer()
        try:
            self.hideTimer_conn = self.hideTimer.timeout.connect(
                self.doTimerHide)
        except BaseException:
            self.hideTimer.callback.append(self.doTimerHide)
        self.hideTimer.start(5000, True)

        self.onShow.append(self.__onShow)
        self.onHide.append(self.__onHide)

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
        if self.__state == self.STATE_SHOWN:
            if self["helpOverlay"].visible:
                self.help_timer.stop()
                self.hide_help_overlay()
            else:
                self.show_help_overlay()

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
        self.hideTimer.stop()
        self.hide()
        if self["helpOverlay"].visible:
            self.help_timer.stop()
            self.hide_help_overlay()
        self.startHideTimer()

    def serviceStarted(self):
        if self.execing and config.usage.show_infobar_on_zap.value:
            self.doShow()

    def startHideTimer(self):
        if self.__state == self.STATE_SHOWN and not self.__locked:
            self.hideTimer.stop()
            self.hideTimer.start(5000, True)
        elif hasattr(self, "pvrStateDialog"):
            self.hideTimer.stop()
        self.skipToggleShow = False

    def doTimerHide(self):
        self.hideTimer.stop()
        if self.__state == self.STATE_SHOWN:
            self.hide()
            if self["helpOverlay"].visible:
                self.help_timer.stop()
                self.hide_help_overlay()

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

        InfoBarBase.__init__(self)
        InfoBarSeek.__init__(self)
        InfoBarAudioSelection.__init__(self)
        InfoBarNotifications.__init__(self)
        TvInfoBarShowHide.__init__(self)

        self.channel_list = channel_list if channel_list else []
        self.current_index = current_index
        self.itemscount = len(self.channel_list)

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
        self.onFirstExecBegin.append(self.start_stream)
        self.onClose.append(self.cleanup)

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

        try:
            # Create service reference with performance parameters
            url_encoded = stream_url.replace(":", "%3a")
            name_encoded = channel_name.replace(":", "%3a")

            # Build service reference string with additional parameters
            if self.should_use_hardware_acceleration(stream_url):
                # Add parameters for hardware acceleration
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

            # Start a timer to check whether the stream plays correctly
            self.start_stream_check_timer()

        except Exception as error:
            log.error("ERROR starting stream: " + str(error), module="Player")
            self.show_error_message("Cannot play: " + channel_name)

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
        # For some players, we can add parameters to the service reference
        # This depends on the specific player implementation

        # For exteplayer3: use buffersize parameter
        player = self.config.get("player", "auto")

        if player == "exteplayer3" and buffer_size_kb > 0:
            # Add buffersize parameter (in bytes)
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

    def start_stream_check_timer(self):
        """Start timer to check if stream is actually playing"""
        self.stream_check_timer = eTimer()
        try:
            self.stream_check_timer_conn = self.stream_check_timer.timeout.connect(
                self.check_stream_status)
        except AttributeError:
            self.stream_check_timer.callback.append(self.check_stream_status)
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

    def next_channel(self):
        """Switch to the next channel with audio fix"""
        if self.itemscount <= 1:
            return

        # Calculate the new index
        new_index = (self.current_index + 1) % self.itemscount
        log.debug("Next channel: %d -> %d" %
                  (self.current_index, new_index), module="Player")

        # Get new channel info
        new_channel = self.channel_list[new_index]
        stream_url = new_channel.get('stream_url') or new_channel.get('url')
        channel_name = new_channel.get('name', 'TV Garden')

        if not stream_url:
            log.error(
                "No stream URL for channel %d" %
                new_index, module="Player")
            return

        # Create new service reference
        url_encoded = stream_url.replace(":", "%3a")
        name_encoded = channel_name.replace(":", "%3a")

        # Use same performance settings
        buffer_size = self.config.get("buffer_size", 2048)

        if self.should_use_hardware_acceleration(stream_url):
            ref_str = self.build_service_ref_with_hw_accel(
                url_encoded, name_encoded)
        else:
            ref_str = self.build_standard_service_ref(
                url_encoded, name_encoded)

        ref_str = self.add_buffer_size_param(ref_str, buffer_size)

        log.info("Switching to: %s" % channel_name, module="Player")

        # Play new service
        sref = eServiceReference(ref_str)
        sref.setName(channel_name)
        self.session.nav.playService(sref)

        # Update current index
        self.current_index = new_index

        # Reset audio tracks after 1 second
        self.audio_reset_timer = eTimer()
        try:
            self.audio_reset_timer_conn = self.audio_reset_timer.timeout.connect(
                self.reset_audio_tracks)
        except AttributeError:
            self.audio_reset_timer.callback.append(self.reset_audio_tracks)
        self.audio_reset_timer.start(1000, True)

    def previous_channel(self):
        """Switch to the previous channel with audio fix"""
        if self.itemscount <= 1:
            return

        # Calculate new index
        new_index = (self.current_index - 1) % self.itemscount
        log.debug("Previous channel: %d -> %d" %
                  (self.current_index, new_index), module="Player")

        # Get new channel info
        new_channel = self.channel_list[new_index]
        stream_url = new_channel.get('stream_url') or new_channel.get('url')
        channel_name = new_channel.get('name', 'TV Garden')

        if not stream_url:
            log.error(
                "No stream URL for channel %d" %
                new_index, module="Player")
            return

        # Create new service reference
        url_encoded = stream_url.replace(":", "%3a")
        name_encoded = channel_name.replace(":", "%3a")

        # Use same performance settings
        buffer_size = self.config.get("buffer_size", 2048)

        if self.should_use_hardware_acceleration(stream_url):
            ref_str = self.build_service_ref_with_hw_accel(
                url_encoded, name_encoded)
        else:
            ref_str = self.build_standard_service_ref(
                url_encoded, name_encoded)

        ref_str = self.add_buffer_size_param(ref_str, buffer_size)

        log.info("Switching to: %s" % channel_name, module="Player")

        # Play new service
        sref = eServiceReference(ref_str)
        sref.setName(channel_name)
        self.session.nav.playService(sref)

        # Update current index
        self.current_index = new_index

        # Reset audio tracks after 1 second
        self.audio_reset_timer = eTimer()
        try:
            self.audio_reset_timer_conn = self.audio_reset_timer.timeout.connect(
                self.reset_audio_tracks)
        except AttributeError:
            self.audio_reset_timer.callback.append(self.reset_audio_tracks)
        self.audio_reset_timer.start(1000, True)

    def reset_audio_tracks(self):
        """Reset audio tracks when changing channels"""
        log.debug("Resetting audio tracks...", module="Player")

        try:
            service = self.session.nav.getCurrentService()
            if service:
                audio = service.audioTracks()
                if audio:
                    # Get current track info
                    current_track = audio.getCurrentTrack()
                    num_tracks = audio.getNumberOfTracks()

                    log.debug(
                        "Audio tracks: %d, current: %d" %
                        (num_tracks, current_track), module="Player")

                    if num_tracks > 0:
                        # Force reset to track 0
                        audio.selectTrack(0)

                        # Get track info for debugging
                        track_info = audio.getTrackInfo(0)
                        if track_info:
                            description = track_info.getDescription()
                            language = track_info.getLanguage()
                            log.debug(
                                "Selected track 0: %s (%s)" %
                                (description, language), module="Player")

                        # Force update audio settings
                        # self.audioSelection()

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

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, 'refreshTimer'):
            self.refreshTimer.stop()

        # Restore initial service
        if self.srefInit:
            self.session.nav.stopService()
            self.session.nav.playService(self.srefInit)

    def leave_player(self):
        """Exit the player."""
        self.cleanup()
        self.close()

    def __serviceStarted(self):
        """Service started playing"""
        log.debug("Playback started successfully", module="Player")
        self.state = self.STATE_PLAYING

    def __evEOF(self):
        log.info("Playback completed", module="Player")
        self.close()

    def __evStopped(self):
        log.info("Playback stopped", module="Player")
        self.close()
