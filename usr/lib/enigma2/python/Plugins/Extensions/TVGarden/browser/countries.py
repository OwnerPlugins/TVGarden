#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Countries Browser
Browse 150+ countries with flags
Based on TV Garden Project

[TVGarden patch] Supporto multi-sorgente (tv / webcams).
Il browser accetta `media_type` e lo propaga a:
- cache.get_countries_metadata()
- ChannelsBrowser
"""
import os
import tempfile
from os import unlink
from Components.Sources.StaticText import StaticText
from enigma import eTimer, loadPNG
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap

from .. import _, PLUGIN_VERSION
from .base import BaseBrowser
from .channels import ChannelsBrowser
from ..helpers import log, get_flag_url, timer_connect
from ..utils.cache import CacheManager, open_url
from ..utils.config import PluginConfig, get_config


class CountriesBrowser(BaseBrowser):

    skin = """
        <screen name="CountriesBrowser" position="center,center" size="1920,1080" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <!-- Button pixmaps -->
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/redbutton.png" position="47,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/greenbutton.png" position="261,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/yellowbutton.png" position="474,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/bluebutton.png" position="688,1038" size="210,6" alphatest="blend" transparent="1" />

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
            <widget source="title" position="44,57" size="1770,60" font="Regular;48" foregroundColor="#ffff00" zPosition="5" render="Label" backgroundColor="#ff000000" />

            <!-- Status -->
            <widget source="status" render="Label" position="921,976" size="976,61" font="Regular;32" halign="center" foregroundColor="#3333ff" transparent="1" alphatest="blend" />

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

    def __init__(self, session, media_type="tv"):
        # [TVGarden patch] media_type: "tv" (default) oppure "webcams"
        self.media_type = media_type

        self.config = PluginConfig()
        dynamic_skin = self.config.load_skin("CountriesBrowser", self.skin)
        self.skin = dynamic_skin

        BaseBrowser.__init__(self, session)
        self.session = session
        self.cache = CacheManager()

        self.countries = []
        self.selected_country = None
        self.show_flags = get_config().get("show_flags", True)
        self.flag_request = 0
        self.pending_flag = None

        # Debounce timer: flags are fetched only when the cursor stops
        self.flag_timer = eTimer()
        self.flag_timer_conn = timer_connect(
            self.flag_timer, self._start_flag_download)

        log.info("Flags enabled using loadPNG method", module="Countries")
        log.info("CountriesBrowser opened with media_type=%s" %
                 self.media_type, module="Countries")

        # [TVGarden patch] Titolo dinamico in base al media_type
        title_label = "Webcams" if self.media_type == "webcams" else "TV Garden"

        self["menu"] = MenuList([], enableWrapAround=True)
        self["menu"].onSelectionChanged.append(self.onSelectionChanged)
        self['title'] = StaticText(
            "%s %s | by Lululla" % (title_label, PLUGIN_VERSION))
        self["status"] = StaticText(_("Loading countries..."))
        self["flag"] = Pixmap()
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Select"))
        self["key_yellow"] = StaticText(_("Refresh"))
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "cancel": self.exit,
            "ok": self.select_country,
            "red": self.exit,
            "green": self.select_country,
            "yellow": self.refresh,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
        }, -2)

        self.onFirstExecBegin.append(self.load_countries)
        self.onClose.append(self.cleanup)

    def cleanup(self):
        """Cleanup resources on close"""
        if getattr(self, '_cleaned_up', False):
            return
        self._cleaned_up = True
        log.debug("Cleaning up", module="Countries")

        for name in ('timer', 'flag_timer'):
            timer = getattr(self, name, None)
            if timer:
                try:
                    timer.stop()
                except Exception as e:
                    log.debug("Error stopping %s: %s" %
                              (name, e), module="Countries")
                setattr(self, name, None)

        try:
            self["menu"].onSelectionChanged = []
        except Exception:
            pass

    def load_countries(self, force_refresh=False):
        """Load countries list from TV Garden repository"""
        try:
            config = get_config()
            cache_enabled = config.get("cache_enabled", True)
            force_refresh_browsing = force_refresh or config.get(
                "force_refresh_browsing", False)

            # [TVGarden patch] Passiamo media_type al cache
            if hasattr(self.cache, 'get_countries_metadata'):
                try:
                    metadata = self.cache.get_countries_metadata(
                        media_type=self.media_type,
                        force_refresh=force_refresh_browsing)
                except TypeError:
                    # Retrocompatibilità con versioni vecchie del cache
                    metadata = self.cache.get_countries_metadata(
                        force_refresh=force_refresh_browsing)
            else:
                metadata = {}

            log.debug(
                "Metadata received for %s: %d countries" %
                (self.media_type, len(metadata)), module="Countries")

            self.countries = []
            for code, info in metadata.items():
                if info.get('hasChannels', False):
                    self.countries.append({
                        'code': code,
                        'name': info.get('country', code),
                        'channels': info.get('channelCount', 0)
                    })

            self.countries.sort(key=lambda x: x['name'])

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

                self.timer = eTimer()
                self.timer_conn = timer_connect(
                    self.timer, self.load_initial_flag)
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
            refresh_method = config.get("refresh_method", "clear_cache")

            if refresh_method == "clear_cache":
                self.cache.clear_all()
                log.info("Cache cleared manually", module="Countries")
                self.load_countries()
            else:
                # Keep the cache, just download this list again
                self.load_countries(force_refresh=True)

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

            self["flag"].hide()
            if not self.show_flags:
                return

            flag_code = self.selected_country['code'].lower()
            self.pending_flag = (get_flag_url(flag_code), flag_code)
            if self.flag_timer:
                self.flag_timer.stop()
                self.flag_timer.start(300, True)

    def _start_flag_download(self):
        """Download the flag in a worker thread (never block the GUI)"""
        if not self.pending_flag:
            return
        url, country_code = self.pending_flag
        self.flag_request += 1
        request_id = self.flag_request
        log.debug("Loading flag for: %s" % country_code, module="Countries")
        try:
            from twisted.internet import threads
            d = threads.deferToThread(open_url, url, 5)
            d.addCallback(self._flag_downloaded, request_id, country_code)
            d.addErrback(self._flag_failed, country_code)
        except Exception as e:
            log.error("Flag download error: %s" % e, module="Countries")

    def _flag_failed(self, failure, country_code):
        log.debug(
            "Flag %s not available: %s" %
            (country_code,
             failure.getErrorMessage()),
            module="Countries")

    def _flag_downloaded(self, flag_data, request_id, country_code):
        """Runs on the GUI thread once the flag has been downloaded"""
        # Ignore late answers (cursor moved or screen closed)
        if request_id != self.flag_request or getattr(
                self, '_cleaned_up', False):
            return
        if not flag_data:
            return

        temp_path = None
        try:
            temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(flag_data)

            pixmap = loadPNG(temp_path)
            if pixmap and self["flag"].instance:
                self["flag"].instance.setPixmap(pixmap)
                self["flag"].instance.setScale(1)
                self["flag"].instance.invalidate()
                self["flag"].show()
                log.debug("Flag displayed for %s" %
                          country_code, module="Countries")
        except Exception as e:
            log.error("Flag error %s: %s" %
                      (country_code, e), module="Countries")
            self["flag"].hide()
        finally:
            if temp_path:
                try:
                    unlink(temp_path)
                except OSError:
                    pass

    def select_country(self):
        """Select a country and show its channels"""
        if not self.selected_country:
            self["status"].setText(_("No country selected"))
            return

        log.info(
            "Opening channels for: {} (media_type={})".format(
                self.selected_country['code'], self.media_type),
            module="Countries")

        if self.flag_timer:
            try:
                self.flag_timer.stop()
            except BaseException:
                pass

        # [TVGarden patch] Passiamo media_type a ChannelsBrowser
        self.session.open(
            ChannelsBrowser,
            country_code=str(self.selected_country.get('code', '')),
            country_name=str(self.selected_country.get('name', '')),
            media_type=self.media_type
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
        """Exit browser (cleanup runs from onClose)"""
        self.close()
