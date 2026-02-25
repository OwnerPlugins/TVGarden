#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
###########################################################
#                                                         #
#  TV Garden Plugin for Enigma2                           #
#  Created by Enigma2 Developer Lulualla                  #
#  Based on TV Garden Project by Lululla                  #
#  Data Source: Belfagor2005 fork                         #
#                                                         #
#  Repository:                                            #
#  https://github.com/Belfagor2005/tv-garden-channel-list #
#                                                         #
#  PLUGIN FEATURES:                                       #
#  • Global: 150+ countries with flags                    #
#  • Content: 29 categories, 50,000+ channels             #
#  • Caching: Smart TTL + gzip compression                #
#  • Player: Advanced with channel zapping                #
#  • Favorites: Export to Enigma2 bouquets                #
#  • Search: Fast virtual keyboard search                 #
#  • Skins: Auto-detection (HD/FHD/WQHD)                  #
#  • Safety: DRM/crash stream filtering                   #
#  • Performance: HW acceleration + buffer control        #
#  • Logging: File logging with rotation                  #
#  • Updates: Auto-check with notifications               #
#                                                         #
#  PERFORMANCE OPTIMIZATION:                              #
#  • Hardware acceleration for H.264/H.265                #
#  • Configurable buffer size (512KB-8MB)                 #
#  • Smart player selection (Auto/ExtePlayer3/GStreamer)  #
#  • Memory efficient (~50MB RAM usage)                   #
#                                                         #
#  BOUQUET EXPORT SYSTEM:                                 #
#  • Export favorites to native Enigma2 bouquets          #
#  • Configurable bouquet name prefix                     #
#  • Max channels for bouquet limit                       #
#  • Max channels per sub-bouquet limit (Hierarchical)    #
#  • Auto-refresh bouquet option                          #
#  • Confirm before export option                         #
#  • Single / Multi-file (Hierarchical) export            #
#  • Requires Enigma2 restart after export                #
#                                                         #
#  CONFIGURATION SYSTEM:                                  #
#  • 20+ configurable parameters                          #
#  • Organized settings categories:                       #
#    - Player: Player engine selection                    #
#    - Display: Show flags, Show logos                    #
#    - Browser: Max channels, Default view                #
#    - Cache: Enable/Disable, Size, Refresh method        #
#    - Export: Enable/Disable, Max channels, Prefix       #
#    - Network: User agent, Connection & Download timeout #
#    - Logging: Level, File logging                       #
#    - Performance: HW acceleration, Buffer size, Memory  #
#    - Search: Max results                                #
#    - Bouquet Management: Auto-reload after export       #
#                                                         #
#  KEY CONTROLS:                                          #
#  [ BROWSER ]                                            #
#    OK/GREEN    - Play selected channel                  #
#    EXIT/RED    - Back / Exit                            #
#    YELLOW      - Context menu (Remove/Export)           #
#    BLUE        - Export favorites to bouquet            #
#    MENU        - Context menu                           #
#                                                         #
#  [ FAVORITES BROWSER ]                                  #
#    OK/GREEN    - Play selected channel                  #
#    EXIT/RED    - Back / Exit                            #
#    YELLOW      - Options (Remove/Info/Export)           #
#    BLUE        - Export ALL to Enigma2 bouquet          #
#    ARROWS      - Navigate channels                      #
#                                                         #
#  [ PLAYER ]                                             #
#    CHANNEL +/- - Zap between channels                   #
#    OK          - Show channel info + performance stats  #
#    RED         - Toggle favorite                        #
#    GREEN       - Show channel list                      #
#    EXIT        - Close player                           #
#                                                         #
#  TECHNICAL DETAILS:                                     #
#  • Python 2.7+ compatible (Enigma2 optimized)           #
#  • Player engines: GStreamer / ExtePlayer3 / Auto       #
#  • HLS stream support with adaptive bitrate             #
#  • Smart cache management with force refresh options    #
#  • Configuration backup & restore                       #
#  • Skin system with resolution detection                #
#  • Bouquet integration with Enigma2 EPG                 #
#                                                         #
#  STATISTICS:                                            #
#  • 50,000+ channels available                           #
#  • ~70% stream compatibility rate                       #
#  • <5 sec loading time (cached)                         #
#  • 20+ configuration parameters                         #
#  • 150+ countries supported                             #
#  • 29 content categories                                #
#                                                         #
#  CREDITS & THANKS:                                      #
#  • Original TV Garden concept: Lululla                  #
#  • Repository fork & maintenance: Belfagor2005          #
#  • Plugin development: TV Garden Team                   #
#  • Performance optimization: Recent updates             #
#  • Enigma2 community for testing & feedback             #
#  • All open-source contributors                         #
#                                                         #
#  NOTE: This plugin is for educational purposes only.    #
#  Please respect content rights and usage policies.      #
#                                                         #
#  Last Updated: 2025-12-17                               #
#  Code Review & Cleanup: Configurations consolidated     #
###########################################################
"""

from __future__ import absolute_import, print_function
from os.path import dirname
from sys import path
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from . import _, PLUGIN_VERSION, PLUGIN_ICON
# , PLUGIN_NAME, PLUGIN_PATH
from .helpers import log, simple_log, get_metadata_url
from .browser.about import TVGardenAbout
from .browser.countries import CountriesBrowser
from .browser.categories import CategoriesBrowser
from .browser.favorites import FavoritesBrowser
from .browser.search import SearchBrowser
from .utils.cache import CacheManager
from .utils.config import PluginConfig
from .utils.update_manager import UpdateManager
from .utils.updater import PluginUpdater


# Add plugin path to sys.path for imports
plugin_path = dirname(__file__)
if plugin_path not in path:
    path.insert(0, plugin_path)


simple_log("START PLUGIN TVGARDEN BY LULULLA - TEST")

MODULES_LOADED = False
MODULES_LOADED = all([
    CountriesBrowser is not None,
    CategoriesBrowser is not None,
    FavoritesBrowser is not None,
    PluginConfig is not None,
    CacheManager is not None
])


if MODULES_LOADED:
    simple_log("✓ All modules loaded successfully")
else:
    simple_log("✗ Some modules failed to load", "WARNING")
    simple_log("  CountriesBrowser: %s" % (CountriesBrowser is not None))
    simple_log("  CategoriesBrowser: %s" % (CategoriesBrowser is not None))
    simple_log("  FavoritesBrowser: %s" % (FavoritesBrowser is not None))
    simple_log("  PluginConfig: %s" % (PluginConfig is not None))
    simple_log("  CacheManager: %s" % (CacheManager is not None))


class TVGardenMain(Screen):
    """Main menu screen"""

    skin = """
        <screen name="TVGardenMain" position="center,center" size="1280,720" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/redbutton.png" position="32,688" size="140,6" zPosition="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/greenbutton.png" position="176,688" size="140,6" zPosition="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/yellowbutton.png" position="314,688" size="140,6" zPosition="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/bluebutton.png" position="458,688" size="140,6" zPosition="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/kofi.png" position="740,460" size="130,130" scale="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/paypal.png" position="877,460" size="130,130" scale="1" transparent="1" alphatest="blend"/>
            <ePixmap name="" position="0,0" size="1280,720" zPosition="-1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/hd/background.png" scale="1" alphatest="blend"/>
            <ePixmap name="" position="1039,531" size="200,80" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/logo.png" scale="1" transparent="1" alphatest="blend"/>

            <widget name="key_red" position="33,649" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>
            <widget name="key_green" position="174,650" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>
            <widget name="key_yellow" position="315,650" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>
            <widget name="key_blue" position="455,650" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>

            <widget name="menu" position="28,116" size="680,474" scrollbarMode="showOnDemand" backgroundColor="#16213e"/>
            <widget name="status" position="603,643" size="648,50" font="Regular; 22" halign="center" foregroundColor="#3333ff" transparent="1" alphatest="blend"/>
            <eLabel backgroundColor="#001a2336" position="5,639" size="1270,60" zPosition="-80"/>
            <eLabel name="" position="24,101" size="694,502" zPosition="-1" backgroundColor="#00171a1c" foregroundColor="#00171a1c"/>
            <widget source="session.VideoPicture" render="Pig" position="739,140" zPosition="19" size="520,308" backgroundColor="transparent" transparent="0"/>
        </screen>
        """

    def __init__(self, session):

        self.config = PluginConfig()
        dynamic_skin = self.config.load_skin("TVGardenMain", self.skin)
        self.skin = dynamic_skin

        Screen.__init__(self, session)
        self.session = session
        self["status"] = StaticText("TV Garden %s | Ready" % PLUGIN_VERSION)

        self.cache = CacheManager()
        self.menu_items = [
            (_("Browse by Country"), "countries", _("Browse channels by country")),
            (_("Browse by Category"), "categories", _("Browse channels by category")),
            (_("Favorites"), "favorites", _("Your favorite channels")),
            (_("Search"), "search", _("Search channels by name")),
            (_("Settings"), "settings", _("Plugin settings and configuration")),
            (_("Check for Updates"), "updates", _("Check for plugin updates")),
            (_("About"), "about", _("About TV Garden plugin"))
        ]

        self["menu"] = MenuList(self.menu_items)
        self["key_red"] = StaticText(_("Exit"))
        self["key_green"] = StaticText(_("Select"))
        self["key_yellow"] = StaticText(_("Refresh"))
        self["key_blue"] = StaticText(_("Settings"))

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "cancel": self.exit,
            "ok": self.select_item,
            "red": self.exit,
            "green": self.select_item,
            "yellow": self.refresh_data,
            "blue": self.open_settings,
        }, -2)

        test_url = get_metadata_url()
        try:
            data = self.cache.fetch_url(test_url, force_refresh=False)
            log.info("✓ Cache test OK: %s, %d items" %
                     (type(data), len(data) if data else 0), module="Test")
            self.update_cache_status()
        except Exception as e:
            log.error("✗ Cache test failed: %s" % str(e), module="Test")
            self["status"].setText(
                "TV Garden v.%s | Cache error" %
                PLUGIN_VERSION)

    def select_item(self):
        """Handle menu item selection"""
        selection = self["menu"].getCurrent()
        if selection:
            action = selection[1]

            if action == "countries":
                self.session.open(CountriesBrowser)
            elif action == "categories":
                self.session.open(CategoriesBrowser)
            elif action == "favorites":
                self.session.open(FavoritesBrowser)
            elif action == "search":
                self.open_search()
            elif action == "settings":
                self.open_settings()
            elif action == "updates":
                self.check_for_updates()
            elif action == "about":
                self.show_about()

    def open_search(self):
        """Open search screen"""
        self.session.open(SearchBrowser)

    def open_settings(self):
        """Open settings screen"""
        from .utils.settings import TVGardenSettings
        self.session.open(TVGardenSettings)

    def update_cache_status(self):
        """Update widget status with current cache info"""
        try:
            cache_info = self.cache.get_cache_info()

            if 'error' not in cache_info:
                cache_count = cache_info.get('total_files', 0)
                cache_size_kb = cache_info.get('total_size_kb', 0)

                if cache_count > 0:
                    new_status = "TV Garden v.%s | Cache: %d files (%.1fKB)" % (
                        PLUGIN_VERSION, cache_count, cache_size_kb)
                else:
                    new_status = "TV Garden v.%s | Cache: empty" % PLUGIN_VERSION
            else:
                new_status = "TV Garden v.%s | Cache error" % PLUGIN_VERSION

            self["status"].setText(new_status)
            log.debug("Cache status updated: %s" % new_status, module="Main")

        except Exception as e:
            log.error(
                "Error updating cache status: %s" %
                str(e), module="Main")
            self["status"].setText(
                "TV Garden v.%s | Status error" %
                PLUGIN_VERSION)

    def refresh_data(self):
        """Refresh cache and metadata"""
        self["status"].setText(_("Refreshing data..."))

        try:
            # Clear cache
            self.cache.clear_all()

            # Force refresh countries metadata
            countries_data = self.cache.get_countries_metadata(
                force_refresh=True)

            # Update status using the same method
            self.update_cache_status()

            # Show completion message
            self.session.open(
                MessageBox,
                _("Refresh completed!\nLoaded %d countries") %
                len(countries_data),
                MessageBox.TYPE_INFO)

        except Exception as e:
            error_msg = _("Refresh failed: %s") % str(e)
            self["status"].setText(error_msg)
            log.error("Refresh error: %s" % str(e), module="Main")

    def check_for_updates(self):
        """Check for plugin updates"""
        log.debug("check_for_updates called from main menu", module="Main")
        try:
            log.debug("Creating UpdateManager instance...", module="Main")
            updater = PluginUpdater()
            log.debug("PluginUpdater created successfully", module="Main")

            latest = updater.get_latest_version()
            log.debug(
                "Direct test - Latest version: %s" %
                latest, module="Main")

            # UpdateManager
            UpdateManager.check_for_updates(self.session, self["status"])

            self.update_cache_status()
        except Exception as e:
            log.error("Direct test error: %s" % e, module="Main")
            self["status"].setText(_("Update check error"))

    def show_about_fallback(self):
        about_text = """
            TV GARDEN v%s
            Cache: %d items | Countries: 150+ | Streams: 50K+

            CONTROLS:
            • Browser: OK=Play, Yellow=Options, Blue=Export
            • Favorites: Blue=Export all, Yellow=Single/Multi export
            • Player: CH+/−=Zap, OK=Info, Red=Favorite

            NEW EXPORT SYSTEM:
            • Single File: All in one bouquet
            • Multi-File: Smart split (>500 ch)
            • Parent: userbouquet.tvgarden_container.tv
            • Children: subbouquet.tvgarden_[country].tv

            PERFORMANCE:
            • HW Acceleration for H.264/H.265
            • Buffer: 512KB-8MB configurable
            • Max 500 channels for file

            STATUS: OPERATIONAL | EXPORT: Dual Mode
            """ % (PLUGIN_VERSION, self.cache.get_size())

        self.session.open(MessageBox, about_text.strip(), MessageBox.TYPE_INFO)

    def show_about(self):
        """Show about screen"""
        try:
            self.session.open(TVGardenAbout)
        except ImportError:
            # Fallback to MessageBox
            self.show_about_fallback()

    def exit(self):
        """Exit plugin"""
        self.cache.clear_all()
        self.update_cache_status()
        self.close()


def menu(menuid, **kwargs):
    """Plugin menu integration"""
    if menuid == "mainmenu":
        return [(_("TV Garden"), main, "tv_garden", 46)]
    return []


def main(session, **kwargs):
    try:
        return session.open(TVGardenMain)
    except Exception as e:
        import traceback
        import time

        try:
            from .helpers import log
            log.error("TVGarden Crash: %s" % str(e), module="Main")
            log.error(traceback.format_exc(), module="Main")
        except ImportError:
            # Fallback se log non è disponibile
            print("[TVGarden CRASH]: %s" % str(e))
            traceback.print_exc()

        # Scrivi sempre il crash log
        log_path = "/tmp/tvgarden_crash.log"
        try:
            with open(log_path, "a") as f:
                f.write("=" * 50 + "\n")
                f.write(time.ctime() + "\n")
                f.write("CRASH on init TVGardenMain\n")
                f.write(str(e) + "\n")
                f.write(traceback.format_exc())
                f.write("\n" + "=" * 50 + "\n")
        except BaseException:
            pass

        return None


def Plugins(**kwargs):
    """Plugin descriptor list"""
    from Plugins.Plugin import PluginDescriptor
    try:
        from .utils.config import get_config
        config = get_config()
        log_level = config.get("log_level", "INFO")
        log_to_file = config.get("log_to_file", True)

        from .helpers import log
        log.set_level(log_level)
        log.enable_file_logging(log_to_file)
        log.info("TV Garden Plugin started", "Main")

    except Exception as e:
        print("[TVGarden] Plugin loading - log init failed: %s" % str(e))

    description = _("Access free IPTV channels from around the world")
    plugin_descriptor = PluginDescriptor(
        name="TV Garden",
        description=description,
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon=PLUGIN_ICON,
        fnc=main
    )

    extensions_descriptor = PluginDescriptor(
        name="TV Garden",
        description=description,
        where=PluginDescriptor.WHERE_EXTENSIONSMENU,
        fnc=main
    )

    return [plugin_descriptor, extensions_descriptor]
