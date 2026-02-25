#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - About Screen
Shows plugin information, credits and version
"""
from __future__ import print_function
from os import listdir
from os.path import exists, join, getsize
from enigma import eTimer
from Screens.Screen import Screen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel

from .. import _, PLUGIN_VERSION
from ..helpers import log
from ..utils.cache import CacheManager
from ..utils.config import PluginConfig, get_config


class TVGardenAbout(Screen):
    skin = """
        <screen name="TVGardenAbout" position="center,center" size="1280,720" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/redbutton.png" position="32,688" size="140,6" zPosition="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/kofi.png" position="740,460" size="130,130" scale="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/paypal.png" position="877,460" size="130,130" scale="1" transparent="1" alphatest="blend"/>
            <!--
            <ePixmap name="" position="0,0" size="1280,720" alphatest="blend" zPosition="-1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/hd/background.png" scale="1" />
            -->
            <widget name="background" position="0,0" size="1280,720" backgroundColor="#1a1a2e" />
            <ePixmap name="" position="1039,531" size="200,80" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/logo.png" scale="1" transparent="1" alphatest="blend"/>
            <widget name="key_red" position="33,649" zPosition="1" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>
            <widget name="scrolltext" position="28,116" size="680,474" font="Regular;22" halign="left" valign="top" foregroundColor="#e0e0e0" transparent="1"/>
            <widget name="version" position="603,643" size="648,50" font="Regular; 22" halign="center" foregroundColor="#3333ff" transparent="1" alphatest="blend"/>
            <eLabel backgroundColor="#001a2336" size="1270,60" zPosition="-80"/>
            <eLabel name="" position="24,101" size="694,502" zPosition="-1" backgroundColor="#00171a1c" foregroundColor="#00171a1c"/>
            <widget source="session.VideoPicture" render="Pig" position="739,140" zPosition="19" size="520,308" backgroundColor="transparent" transparent="0" />
        </screen>
    """

    def __init__(self, session):
        self.config = PluginConfig()
        dynamic_skin = self.config.load_skin("TVGardenAbout", self.skin)
        self.skin = dynamic_skin

        Screen.__init__(self, session)
        self["title"] = StaticText(_("TV Garden Plugin"))
        self["scrolltext"] = ScrollLabel()
        self["version"] = StaticText("")
        self["key_red"] = StaticText(_("Close"))
        self["actions"] = ActionMap(["TVGardenActions", "DirectionActions", "ColorActions", "OkCancelActions"], {
            "cancel": self.close,
            "exit": self.close,
            "back": self.close,
            "red": self.close,
            "ok": self.close,
            "up": self.pageUp,
            "down": self.pageDown,
            "left": self.pageUp,
            "right": self.pageDown,
            "channelUp": self.pageUp,
            "channelDown": self.pageDown,
        }, -2)

        self.setTitle(_("About TV Garden"))
        self.onLayoutFinish.append(self.load_content)

    def load_content(self):
        """Load about content with dynamic stats"""
        try:
            # Get stats
            cache = CacheManager()

            # Try to get countries count
            countries_count = "Loading..."
            try:
                metadata = cache.get_countries_metadata()
                countries_count = str(
                    len([c for c in metadata.values() if c.get('hasChannels', False)]))
            except BaseException:
                countries_count = "150+"

            # Get cache info
            cache_info = "Active"
            # cache_size = 0
            cache_files = 0

            try:
                # cache_size = cache.get_size()  # Numbers of file
                cache_dir = cache.cache_dir

                # Calculate total size
                total_size = 0
                if exists(cache_dir):
                    for file in listdir(cache_dir):
                        if file.endswith('.gz'):
                            cache_files += 1
                            file_path = join(cache_dir, file)
                            if exists(file_path):
                                total_size += getsize(file_path)

                # Format the size
                if total_size > 0:
                    if total_size < 1024 * 1024:  # Less than 1MB
                        cache_size_str = "%d KB" % (total_size // 1024)
                    else:
                        cache_size_str = "%.1f MB" % (
                            total_size / (1024 * 1024))
                    cache_info = "%d files, %s" % (cache_files, cache_size_str)
                else:
                    cache_info = "Empty"

            except Exception as e:
                log.debug("Could not get cache size: %s" % e, module="About")
                cache_info = "Active"

            # Get config for cache settings
            config = get_config()
            cache_enabled = config.get("cache_enabled", True)

            # Build about text with cache details
            about_text = self.generate_about_text(
                countries_count=countries_count,
                cache_info=cache_info,
                cache_enabled=cache_enabled,
                # cache_ttl=ttl_str
            )

            self["scrolltext"].setText(about_text)
            self["version"].setText("Version: %s" % PLUGIN_VERSION)

            # Auto-scroll after 5 seconds
            self.scroll_timer = eTimer()
            try:
                self.scroll_timer_conn = self.scroll_timer.timeout.connect(
                    self.auto_scroll)
            except AttributeError:
                self.scroll_timer.callback.append(self.auto_scroll)
            self.scroll_timer.start(5000, False)

        except Exception as e:
            log.error("Error loading content: %s" % e, module="About")
            self["scrolltext"].setText(_("Error loading information"))

    def generate_about_text(self, countries_count="150+", cache_info="Active",
                            cache_enabled=True):
        """Generate formatted about text"""
        return """
            ═══════════════════════════════════════════════
                         TV GARDEN PLUGIN
                    Complete IPTV Solution for Enigma2
            ═══════════════════════════════════════════════

            VERSION: %s
            STATUS: ● FULLY OPERATIONAL WITH PERFORMANCE OPTIMIZATION

            ━━━━━━━━━━━━━━━━━━ CORE FEATURES ━━━━━━━━━━━━━━━━━━
            • Global Coverage: %s Countries
            • Content Variety: 29 Categories
            • Channel Library: 50,000+ Streams
            • Real-time Search with Virtual Keyboard (Case-insensitive)
            • Smart Caching System: %s
            • Auto-Skin Detection (HD/FHD/WQHD)
            • Favorites Management with Bouquet Export
            • DRM/Problematic Stream Filtering
            • Configurable Channel Limits
            • Hardware Acceleration Support
            • Configurable Buffer Size (512KB - 8MB)

            ━━━━━━━━━━━━━━━━━━ NEW: HIERARCHICAL BOUQUET EXPORT ━━━━━━━━━━━━━━━━━━
            • SINGLE-FILE EXPORT: All channels in one bouquet (traditional)
            • MULTI-FILE EXPORT: Hierarchical structure for better performance
            • SMART SPLITTING: Configurable max channels per sub-bouquet
            • CONTAINER SYSTEM: Parent bouquet with sub-bouquet references
            • ENHANCED PERFORMANCE: Faster loading, no Enigma2 slowdown
            • COMPATIBLE: Works with all Enigma2 receivers

            ━━━━━━━━━━━━━━━━━━ CACHE SYSTEM ━━━━━━━━━━━━━━━━━━
            • CONFIGURABLE CACHE: Enable/Disable via Settings
            • FORCE REFRESH OPTIONS:
              - Force refresh on browsing
              - Force refresh on export
            • MEMORY + DISK CACHE: Dual-layer for performance
            • CACHE SIZE: Configurable limit (10-5000 items)

            ━━━━━━━━━━━━━━━━━ PERFORMANCE SETTINGS ━━━━━━━━━━━━━━━━━━
            • Hardware Acceleration Toggle (On/Off)
            • Buffer Size Control: 512KB, 1MB, 2MB, 4MB, 8MB
            • Smart HW Accel Detection (H.264, H.265)
            • Player Selection: Auto, ExtePlayer3, GStreamer
            • Memory Optimization Option

            ━━━━━━━━━━━━━━━━━ KEY CONTROLS ━━━━━━━━━━━━━━━━━━
            [ BROWSER ]
              OK/GREEN      > Play Selected Channel
              EXIT/RED      < Back / Exit
              YELLOW        [ ] Context Menu (Remove/Export)
              BLUE          [X] Export Favorites to Bouquet

            [ FAVORITES BROWSER ]
              OK/GREEN      > Play Selected Channel
              EXIT/RED      < Back / Exit
              YELLOW        [ ] Options (Remove/Info/Export)
              BLUE          [X] Export ALL to Enigma2 Bouquet

            [ PLAYER ]
              CHANNEL +/-   ^/v Zap Between Channels
              OK            [i] Show Channel Info + Performance Stats
              EXIT          [X] Close Player

            ━━━━━━━━━━━━━━━━━ CONFIGURATION SYSTEM ━━━━━━━━━━━━━━━━━━
            • 20+ Configurable Parameters
            • Player Settings: Player engine selection
            • Display Settings: Show flags, Show logos
            • Browser Settings: Max channels, Default view, Sort by
            • Cache Settings: Enable, Size, Force Refresh options
            • Export Settings: Enable, Max channels, Name prefix, List position
            • Network Settings: User agent, Connection & Download timeout
            • Logging Settings: Level, File logging
            • Performance Settings: HW acceleration, Buffer size, Memory opt.
            • Search Settings: Max results
            • Bouquet Management: Auto-reload after export

            ━━━━━━━━━━━━━━━━━ TECHNICAL SPECS ━━━━━━━━━━━━━━━━━━
            • Python 2.7+ Compatible (Enigma2 Optimized)
            • Memory Efficient (~50MB RAM)
            • Player Engines: GStreamer / ExtePlayer3 / Auto
            • Smart Cache Management with configurable refresh
            • Advanced Logging System (DEBUG to CRITICAL)
            • Skin System with Resolution Detection
            • Bouquet Integration with Enigma2 EPG

            ━━━━━━━━━━━━━━━━━ STATISTICS ━━━━━━━━━━━━━━━━━━
            • 50,000+ channels available
            • ~70%% stream compatibility rate
            • <5 sec loading time (cached)
            • 150+ countries supported
            • 29 content categories

            ━━━━━━━━━━━━━━━━━ DATA SOURCE ━━━━━━━━━━━━━━━━━━
            TV Garden Channel List Project
            Maintained by Belfagor2005

            ━━━━━━━━━━━━━━━━━ CREDITS ━━━━━━━━━━━━━━━━━━━━━━━━
            • Original Concept: Lululla
            • Data Source: Belfagor2005
            • Plugin Development: TV Garden Team
            • Enigma2 Community for Testing & Feedback

            ━━━━━━━━━━━━━━━━━ TIPS ━━━━━━━━━━━━━━━━━━━━
            RECOMMENDED SETTINGS:
            1. Buffer Size: 2MB-4MB for stable connections
            2. HW Acceleration: ON for H.264/H.265 streams
            3. Max Channels per Country: 250-500 for faster loading
            4. Cache: ON for normal use, OFF for testing

            BOUQUET EXPORT:
            • Single-File: Best for <1000 channels
            • Multi-File: Recommended for complete database
            • Files: /etc/enigma2/*.tvgarden_*

            For support, bug reports or feature requests,
            please visit the GitHub repository.

            Enjoy optimized streaming with TV Garden!
            """ % (PLUGIN_VERSION, countries_count, cache_info)

    def pageUp(self):
        """Scroll page up"""
        self["scrolltext"].pageUp()

    def pageDown(self):
        """Scroll page down"""
        self["scrolltext"].pageDown()

    def auto_scroll(self):
        """Auto-scroll text slowly"""
        self["scrolltext"].pageDown()
        # Continue scrolling every 5 seconds
        self.scroll_timer.start(5000, False)

    def close(self):
        """Close screen"""
        if hasattr(self, 'scroll_timer'):
            self.scroll_timer.stop()
        Screen.close(self)
