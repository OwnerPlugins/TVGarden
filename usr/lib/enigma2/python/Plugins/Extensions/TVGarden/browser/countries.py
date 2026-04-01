#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Countries Browser
Browse 150+ countries with flags
Based on TV Garden Project
"""
from __future__ import print_function
import tempfile
from os import unlink
from os.path import exists
from Components.Sources.StaticText import StaticText
# from Components.Label import Label
from enigma import eTimer, loadPNG  # ,ePicLoad
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from sys import version_info

from .. import _, PLUGIN_VERSION
from .base import BaseBrowser
from .channels import ChannelsBrowser
from ..helpers import log
from ..utils.cache import CacheManager
from ..utils.config import PluginConfig, get_config


if version_info[0] == 3:
    from urllib.request import urlopen, Request
else:
    from urllib2 import urlopen, Request


class CountriesBrowser(BaseBrowser):

    skin = """
        <screen name="CountriesBrowser" position="center,center" size="1920,1080" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <!-- Button pixmaps -->
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/redbutton.png" position="47,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/greenbutton.png" position="261,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/yellowbutton.png" position="474,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/bluebutton.png" position="688,1038" size="210,6" alphatest="blend" transparent="1" />

            <!--
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/kofi.png" position="1134,730" size="150,150" scale="1" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/paypal.png" position="1300,730" size="150,150" scale="1" alphatest="blend" transparent="1" />
            -->

            <!-- Background -->
            <ePixmap name="" position="0,0" size="1920,1080" alphatest="blend" zPosition="-1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/fhd/background.png" scale="1" />

            <!-- Logo -->
            <ePixmap name="" position="1676,812" size="200,80" alphatest="blend" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/logo.png" scale="1" transparent="1" />

            <!-- Button texts -->
            <widget source="key_red" render="Label" position="50,975" zPosition="1" size="210,60" font="Regular;32" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend" />
            <widget source="key_green" render="Label" position="260,975" zPosition="1" size="210,60" font="Regular;32" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend" />
            <widget source="key_yellow" render="Label" position="470,975" zPosition="1" size="210,60" font="Regular;32" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend" />
            <widget source="key_blue" render="Label" position="680,975" zPosition="1" size="210,60" font="Regular;32" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend" />

            <!-- Menu -->
            <widget name="menu" position="48,160" size="1020,750" font="Regular;32" itemHeight="50" scrollbarMode="showOnDemand" backgroundColor="#16213e" />

            <!-- Title -->
            <widget name="title" position="44,57" size="1770,60" font="Regular;48" foregroundColor="#ffff00" zPosition="5" render="Label" backgroundColor="#ff000000" />

            <!-- Status -->
            <widget name="status" position="921,976" size="976,61" font="Regular;32" halign="center" foregroundColor="#3333ff" transparent="1" alphatest="blend" />

            <!-- Bottom bar -->
            <eLabel backgroundColor="#001a2336" cornerRadius="30" position="8,959" size="1905,90" zPosition="-80" />

            <!-- Menu background -->
            <eLabel name="" position="36,152" size="1040,767" zPosition="-1" cornerRadius="18" backgroundColor="#00171a1c" foregroundColor="#00171a1c" />

            <!-- Video Picture -->
            <widget source="session.VideoPicture" render="Pig" position="1109,210" zPosition="19" size="780,462" backgroundColor="transparent" transparent="0" cornerRadius="14" />

            <!-- Flag (specifico per CountriesBrowser) -->
            <widget name="flag" position="1149,719" size="285,180" alphatest="blend" scale="1" zPosition="4" />
        </screen>
    """

    def __init__(self, session):
        self.config = PluginConfig()
        dynamic_skin = self.config.load_skin("CountriesBrowser", self.skin)
        self.skin = dynamic_skin

        BaseBrowser.__init__(self, session)
        self.session = session
        self.cache = CacheManager()

        self.countries = []
        self.selected_country = None
        self.current_flag_path = None

        log.info("Flags enabled using loadPNG method", module="Countries")
        self["menu"] = MenuList([], enableWrapAround=True)
        self["menu"].onSelectionChanged.append(self.onSelectionChanged)
        self['title'] = StaticText(
            "TV Garden %s | by Lululla" %
            PLUGIN_VERSION)
        self["status"] = StaticText(_("Loading countries..."))
        self["flag"] = Pixmap()
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Select"))
        self["key_yellow"] = StaticText(_("Refresh"))
        self["actions"] = ActionMap(["TVGardenActions", "OkCancelActions", "ColorActions", "DirectionActions"], {
            "cancel": self.exit,
            "ok": self.select_country,
            "red": self.exit,
            "green": self.select_country,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
        }, -2)

        self.onFirstExecBegin.append(self.load_countries)
        self.onClose.append(self.cleanup)

    def cleanup(self):
        """Cleanup resources on close"""
        log.debug("Cleaning up", module="Countries")

        # Flag to prevent double cleanup
        if getattr(self, '_cleaned_up', False):
            return
        self._cleaned_up = True

        # Remove timer callbacks
        if hasattr(self, 'timer') and self.timer:
            try:
                self.timer.callback = []
                self.timer.stop()
            except Exception as e:
                log.debug(
                    "Error stopping timer: {}".format(e),
                    module="Countries")
            finally:
                self.timer = None

        if hasattr(self, 'flag_timer') and self.flag_timer:
            try:
                self.flag_timer.callback = []
                self.flag_timer.stop()
            except Exception as e:
                log.debug(
                    "Error stopping flag_timer: {}".format(e),
                    module="Countries")
            finally:
                self.flag_timer = None

        # Remove temporary flag file
        if hasattr(self, 'current_flag_path') and self.current_flag_path:
            if exists(self.current_flag_path):
                try:
                    unlink(self.current_flag_path)
                except Exception as e:
                    log.debug(
                        "Error deleting temp file: {}".format(e),
                        module="Countries")
            self.current_flag_path = None

        # Remove picload callback
        if hasattr(self, 'picload_conn') and self.picload_conn:
            try:
                if self.picload and hasattr(self.picload, 'PictureData'):
                    if exists('/var/lib/dpkg/info'):
                        # DreamOS
                        self.picload.PictureData.disconnect(self.picload_conn)
                    else:
                        # Python3 images
                        if self.picload.PictureData and self.picload.PictureData.get():
                            self.picload.PictureData.get().remove(self.picload_conn)
            except Exception as e:
                log.debug(
                    "Error removing picload callback: {}".format(e),
                    module="Countries"
                )
            finally:
                self.picload_conn = None

        # Cleanup picload
        if hasattr(self, 'picload') and self.picload:
            try:
                pass
            except BaseException:
                pass
            finally:
                self.picload = None

        # Remove menu callback
        try:
            if hasattr(self["menu"], 'onSelectionChanged'):
                self["menu"].onSelectionChanged = []
        except BaseException:
            pass

    def load_countries(self):
        """Load countries list from TV Garden repository"""
        try:
            # Get cache configuration
            config = get_config()
            cache_enabled = config.get("cache_enabled", True)
            force_refresh_browsing = config.get(
                "force_refresh_browsing", False)

            # Load metadata with cache config
            if hasattr(self.cache, 'get_countries_metadata'):
                try:
                    metadata = self.cache.get_countries_metadata(
                        force_refresh=force_refresh_browsing)
                except TypeError:
                    # If the method does not support force_refresh
                    metadata = self.cache.get_countries_metadata()
            else:
                # Fallback
                metadata = {}

            log.debug(
                "Metadata received: %d countries" %
                len(metadata), module="Countries")

            self.countries = []
            for code, info in metadata.items():
                if info.get('hasChannels', False):
                    self.countries.append({
                        'code': code,
                        'name': info.get('country', code),
                        'channels': info.get('channelCount', 0)
                    })

            self.countries.sort(key=lambda x: x['name'])

            # Create menu items
            menu_items = []
            for idx, country in enumerate(self.countries):
                display_text = "%s" % country['name']
                if country['channels'] > 0:
                    display_text += " (%d ch)" % country['channels']
                menu_items.append((display_text, idx))

            self["menu"].setList(menu_items)

            if menu_items:
                cache_info = ""
                if force_refresh_browsing:
                    cache_info = _(" [Fresh data]")
                elif not cache_enabled:
                    cache_info = _(" [Cache disabled]")

                self["status"].setText(_("Select a country") + cache_info)

                # Load initial flag with delay
                self.timer = eTimer()
                try:
                    self.timer_conn = self.timer.timeout.connect(
                        self.load_initial_flag)
                except AttributeError:
                    self.timer.callback.append(self.load_initial_flag)
                self.timer.start(100, True)
            else:
                self["status"].setText(_("No countries with channels found"))

        except Exception as e:
            self["status"].setText(_("Error loading countries"))
            log.error("Error: %s" % e, module="Countries")
            import traceback
            traceback.print_exc()

    def refresh(self):
        """Refresh countries list"""
        self["status"].setText(_("Refreshing..."))
        try:
            config = get_config()
            # "clear_cache" o "force_refresh"
            refresh_method = config.get("refresh_method", "clear_cache")

            if refresh_method == "clear_cache":
                # Clean all cache
                self.cache.clear_all()
                log.info("Cache cleared manually", module="Countries")
                self["status"].setText(_("Cache cleared"))
            else:
                # Set force refresh for next call
                # Here you may want to set a temporary flag
                # For now, force refresh
                if hasattr(self.cache, 'clear_all'):
                    self.cache.clear_all()  # Clear come fallback
                self["status"].setText(_("Will load fresh data next time"))

            self.load_countries()

        except Exception as e:
            self["status"].setText(_("Refresh failed"))
            log.error("Refresh error: %s" % e, module="Countries")

    def load_initial_flag(self):
        """Load first flag after a short delay"""
        if self.countries:
            self.update_country_selection(0)

    def onSelectionChanged(self):
        """Called when menu selection changes"""
        current_index = self["menu"].getSelectedIndex()
        if current_index is not None:
            self.update_country_selection(current_index)

    def update_country_selection(self, index):
        """Update selection and load flag"""
        if 0 <= index < len(self.countries):
            self.selected_country = self.countries[index]

            # Load new flag with proper error handling
            self["flag"].hide()
            flag_code = self.selected_country['code'].lower()

            # DEBUG: mostra info
            log.debug("=" * 50, module="Countries")
            log.debug(
                "SELECTED COUNTRY: %s (%s)" %
                (self.selected_country['name'],
                 flag_code),
                module="Countries")
            log.debug(
                "Channels: %d" %
                self.selected_country['channels'],
                module="Countries")

            flag_url = "https://flagcdn.com/w80/%s.png" % flag_code
            log.debug("Flag URL: %s" % flag_url, module="Countries")

            # Use a timer to prevent rapid consecutive loads
            if hasattr(self, 'flag_timer'):
                self.flag_timer.stop()

            self.flag_timer = eTimer()
            try:
                self.flag_timer.timeout.connect(
                    lambda: self.download_flag_safe(flag_url, flag_code)
                )
            except AttributeError:
                self.flag_timer.callback.append(
                    lambda: self.download_flag_safe(flag_url, flag_code)
                )

            self.flag_timer.start(100, True)

    def download_flag_safe(self, url, country_code):
        """Load flag using PROPER loadPNG pattern"""
        try:
            # Hide first
            self["flag"].hide()

            log.debug(
                "Loading flag for: %s" %
                country_code, module="Countries")

            # Download flag
            req = Request(url, headers={'User-Agent': 'TVGarden-Enigma2/1.0'})
            response = None
            flag_data = None
            try:
                response = urlopen(req, timeout=5)
                if response.getcode() == 200:
                    flag_data = response.read()
                    log.debug(
                        "Downloaded %d bytes" %
                        len(flag_data), module="Countries")
                else:
                    log.warning(
                        "HTTP %d for flag %s" %
                        (response.getcode(), country_code), module="Countries")
                    return
            finally:
                if response:
                    response.close()

            if not flag_data:
                log.warning(
                    "No data for flag %s" %
                    country_code, module="Countries")
                return

            # Save temporarily
            import os
            temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
            os.close(temp_fd)

            with open(temp_path, 'wb') as f:
                f.write(flag_data)

            log.debug("Saved to temp file: %s" % temp_path, module="Countries")

            # 1. Check if file exists
            # 2. Encode for Python 2 if needed
            # 3. Load with loadPNG
            # 4. Set pixmap
            # 5. Set scale
            # 6. Show

            if exists(temp_path):
                # Handle Python 2/3 encoding
                if exists('/var/lib/dpkg/info'):
                    png_path = temp_path.encode('utf-8')
                else:
                    png_path = temp_path

                try:
                    pixmap = loadPNG(png_path)
                    if pixmap:
                        # Set to widget
                        self["flag"].instance.setPixmap(pixmap)
                        self["flag"].instance.setScale(1)
                        self["flag"].instance.invalidate()
                        self["flag"].instance.show()
                        log.info(
                            "✓ Flag displayed for %s" %
                            country_code, module="Countries")
                    else:
                        log.warning(
                            "loadPNG returned None for %s" %
                            country_code, module="Countries")

                except ImportError as e:
                    log.error(
                        "loadPNG not available: %s" %
                        e, module="Countries")
                except Exception as e:
                    log.error("loadPNG error: %s" % e, module="Countries")
                    import traceback
                    traceback.print_exc()

            # Cleanup
            try:
                os.unlink(temp_path)
            except BaseException:
                pass

        except Exception as e:
            log.error(
                "Flag error %s: %s" %
                (country_code, e), module="Countries")
            import traceback
            traceback.print_exc()
            # Hide if all failed
            self["flag"].hide()

    def load_default_flag(self):
        """Load a default/placeholder flag"""
        try:
            self["flag"].hide()
        except BaseException:
            pass

    def update_flag(self, picInfo=None):
        """Callback for async picload - use with caution"""
        # This is called when picload finishes async decode
        # We're using sync decode mainly, but keep this for compatibility
        if picInfo:
            log.debug(
                "Async decode finished: %s" %
                picInfo, module="Countries")

    def select_country(self):
        """Select a country and show its channels"""
        if not self.selected_country:
            self["status"].setText(_("No country selected"))
            return

        log.info(
            "Opening channels for: {}".format(
                self.selected_country['code']),
            module="Countries")

        # Cleanup before opening new screen
        if self.current_flag_path and exists(self.current_flag_path):
            try:
                unlink(self.current_flag_path)
            except BaseException:
                pass

        # Additional minor cleanup
        if hasattr(self, 'flag_timer') and self.flag_timer:
            try:
                self.flag_timer.stop()
            except BaseException:
                pass

        self.session.open(
            ChannelsBrowser,
            country_code=str(self.selected_country.get('code', '')),
            country_name=str(self.selected_country.get('name', ''))
        )

    def up(self):
        self["menu"].up()

    def down(self):
        self["menu"].down()

    def left(self):
        self["menu"].pageUp()

    def right(self):
        self["menu"].pageDown()

    def exit(self):
        """Exit browser"""
        self.cleanup()
        self.close()
