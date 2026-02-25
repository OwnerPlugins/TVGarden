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
# from Components.Sources.StaticText import StaticText
from Components.Label import Label
from enigma import eTimer, loadPNG  # ,ePicLoad
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from sys import version_info

from .. import _
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
        <screen name="CountriesBrowser" position="center,center" size="1280,720" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/redbutton.png" position="32,688" size="140,6" zPosition="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/greenbutton.png" position="176,688" size="140,6" zPosition="1" transparent="1" alphatest="blend"/>
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/yellowbutton.png" position="314,688" size="140,6" zPosition="1" transparent="1" alphatest="blend"/>
            <!--
            <ePixmap name="" position="0,0" size="1280,720" alphatest="blend" zPosition="-1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/hd/background.png" scale="1" />
            -->
            <widget name="background" position="0,0" size="1280,720" backgroundColor="#1a1a2e" />
            <ePixmap name="" position="1039,531" size="200,80" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/logo.png" scale="1" transparent="1" alphatest="blend"/>
            <widget name="key_red" position="33,649" zPosition="1" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>
            <widget name="key_green" position="174,650" zPosition="1" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>
            <widget name="key_yellow" position="315,650" zPosition="1" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>
            <widget name="menu" position="28,116" size="680,474" scrollbarMode="showOnDemand" backgroundColor="#16213e"/>
            <widget name="status" position="603,643" size="648,50" font="Regular; 22" halign="center" foregroundColor="#3333ff" transparent="1" alphatest="blend"/>
            <widget name="flag" position="751,468" size="190,120" alphatest="blend" scale="1"/>
            <eLabel backgroundColor="#001a2336" position="5,639" size="1270,60" zPosition="-80"/>
            <eLabel name="" position="24,101" size="694,502" zPosition="-1" backgroundColor="#00171a1c" foregroundColor="#00171a1c"/>
            <widget source="session.VideoPicture" render="Pig" position="739,140" zPosition="19" size="520,308" backgroundColor="transparent" transparent="0" />
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
        self["status"] = Label(_("Loading countries..."))
        self["flag"] = Pixmap()
        self["key_red"] = Label(_("Back"))
        self["key_green"] = Label(_("Select"))
        self["key_yellow"] = Label(_("Refresh"))
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
                        # Set to widget - CORRECT pattern
                        self["flag"].instance.setPixmap(pixmap)
                        self["flag"].instance.setScale(1)
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

    # def download_flag_safe(self, url, country_code):
        # """Load flag using loadPNG (ACTIVE VERSION)"""
        # try:
        # self["flag"].hide()

        # log.debug("Loading flag for: %s" % country_code, module="Countries")

        # # Download flag
        # req = Request(url, headers={'User-Agent': 'TVGarden-Enigma2/1.0'})
        # response = None
        # flag_data = None
        # try:
        # response = urlopen(req, timeout=5)
        # if response.getcode() == 200:
        # flag_data = response.read()
        # log.debug("Downloaded %d bytes" % len(flag_data), module="Countries")
        # else:
        # log.warning("HTTP %d for %s" % (response.getcode(), country_code), module="Countries")
        # return
        # finally:
        # if response:
        # response.close()

        # if not flag_data:
        # log.warning("No data for flag %s" % country_code, module="Countries")
        # return

        # # Save to temp file
        # from os import close
        # temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
        # close(temp_fd)

        # with open(temp_path, 'wb') as f:
        # f.write(flag_data)

        # log.debug("Saved to: %s" % temp_path, module="Countries")

        # try:
        # log.debug("Attempting loadPNG...", module="Countries")

        # ptr = loadPNG(temp_path)

        # if ptr:
        # log.debug("loadPNG SUCCESS for %s" % country_code, module="Countries")

        # # Scala a dimensioni ragionevoli
        # try:
        # # Dimensione dal widget
        # flag_widget = self["flag"]
        # widget_size = flag_widget.instance.size()

        # # Usa dimensioni dello skin o default
        # if widget_size.width() > 0 and widget_size.height() > 0:
        # width = widget_size.width()
        # height = widget_size.height()
        # else:
        # # Default per HD skin
        # width, height = 190, 120

        # # Scala se possibile
        # if hasattr(ptr, 'scale'):
        # try:
        # ptr.scale(width, height)
        # log.debug("Scaled to %dx%d" % (width, height), module="Countries")
        # except:
        # pass

        # except Exception as size_error:
        # log.debug("Size error: %s" % size_error, module="Countries")
        # # Continua comunque

        # # Mostra la bandiera
        # self["flag"].instance.setPixmap(ptr)
        # self["flag"].show()

        # log.info("✓ Flag displayed for %s" % country_code, module="Countries")
        # return True

        # else:
        # log.warning("loadPNG returned None for %s" % country_code, module="Countries")

        # except ImportError as e:
        # log.error("loadPNG not available: %s" % e, module="Countries")
        # except Exception as e:
        # log.error("loadPNG error: %s" % e, module="Countries")

        # # Se loadPNG fallisce, prova loadJPG
        # try:
        # from enigma import loadJPG
        # log.debug("Trying loadJPG as fallback...", module="Countries")

        # ptr = loadJPG(temp_path)
        # if ptr:
        # self["flag"].instance.setPixmap(ptr)
        # self["flag"].show()
        # log.info("✓ Flag via loadJPG for %s" % country_code, module="Countries")
        # return True
        # except:
        # pass

        # # Pulizia
        # try:
        # unlink(temp_path)
        # except:
        # pass

        # except Exception as e:
        # log.error("Flag error %s: %s" % (country_code, e), module="Countries")
        # import traceback
        # traceback.print_exc()

        # # Se tutto fallisce, nascondi
        # self["flag"].hide()
        # return False

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
