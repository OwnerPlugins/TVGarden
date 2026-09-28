#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Categories Browser
Browse categories of IPTV channels / webcams
Based on TV Garden Project

[TVGarden patch] Supporto multi-sorgente (tv / webcams).
- Le categorie NON sono più hardcoded: vengono lette dalla GitHub API
  tramite CacheManager.get_available_categories(media_type).
- Il browser accetta `media_type` e lo propaga a ChannelsBrowser.
"""
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap

from .base import BaseBrowser
from .channels import ChannelsBrowser
from ..helpers import log
from ..utils.cache import CacheManager
from ..utils.config import PluginConfig, get_config
from .. import _, PLUGIN_VERSION


class CategoriesBrowser(BaseBrowser):
    """Browse channels by category"""

    skin = """
        <screen name="CategoriesBrowser" position="center,center" size="1920,1080" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <!-- Button pixmaps -->
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/redbutton.png" position="47,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/greenbutton.png" position="261,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/yellowbutton.png" position="474,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/bluebutton.png" position="688,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/kofi.png" position="1134,730" size="150,150" scale="1" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/paypal.png" position="1300,730" size="150,150" scale="1" alphatest="blend" transparent="1" />
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
        </screen>
    """

    def __init__(self, session, media_type="tv"):
        # [TVGarden patch] media_type: "tv" (default) oppure "webcams"
        self.media_type = media_type

        self.config = PluginConfig()
        dynamic_skin = self.config.load_skin("CategoriesBrowser", self.skin)
        self.skin = dynamic_skin

        BaseBrowser.__init__(self, session)
        self.session = session

        self.cache = CacheManager()
        self.selected_category = None
        self.categories = []  # [TVGarden patch] popolata dinamicamente

        # [TVGarden patch] Titolo dinamico in base al media_type
        title_label = "Webcams" if self.media_type == "webcams" else "TV Garden"

        self["menu"] = MenuList([])
        self['title'] = StaticText(
            "%s %s | by Lululla" % (title_label, PLUGIN_VERSION))
        self["status"] = StaticText(_("Loading categories..."))
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Select"))
        self["actions"] = ActionMap(["TVGardenActions", "OkCancelActions", "ColorActions"], {
            "cancel": self.exit,
            "ok": self.select_category,
            "red": self.exit,
            "green": self.select_category,
            "up": self.up,
            "down": self.down,
        }, -2)
        self.onFirstExecBegin.append(self.load_categories)

    def load_categories(self):
        """
        [TVGarden patch] Load categories dynamically from GitHub API.
        Non usa più la lista hardcoded CATEGORIES di helpers.py.
        """
        try:
            config = get_config()
            force_refresh_browsing = config.get(
                "force_refresh_browsing", False)

            # Legge le categorie dal cache (che le scarica dalla GitHub API)
            if hasattr(self.cache, 'get_available_categories'):
                try:
                    self.categories = self.cache.get_available_categories(
                        media_type=self.media_type,
                        force_refresh=force_refresh_browsing)
                except TypeError:
                    # Retrocompatibilità con versioni vecchie
                    self.categories = self.cache.get_available_categories()
            else:
                # Fallback estremo
                self.categories = [{'id': 'all', 'name': 'All'}]

            log.info(
                "Loaded %d categories for %s" %
                (len(self.categories), self.media_type), module="Categories")

            # Costruisci i menu items
            menu_items = []
            for category in self.categories:
                menu_items.append((category['name'], category['id']))

            # Sort alfabetico (tranne "all" che va prima)
            menu_items = sorted(
                menu_items,
                key=lambda x: (x[1] != 'all', x[0].lower())
            )

            self["menu"].setList(menu_items)
            self["status"].setText(_("Select a category"))

        except Exception as e:
            log.error(
                "Error loading categories for %s: %s" %
                (self.media_type, e), module="Categories")
            import traceback
            traceback.print_exc()
            self["status"].setText(_("Error loading categories"))
            self["menu"].setList([])

    def select_category(self):
        """Select category"""
        selection = self["menu"].getCurrent()
        if selection:
            category_id = selection[1]
            category_name = selection[0]

            log.debug(
                "Selected: %s (%s) for media_type=%s" %
                (category_id, category_name, self.media_type),
                module="Categories")

            try:
                config = get_config()
                force_refresh_browsing = config.get(
                    "force_refresh_browsing", False)

                log.debug(
                    "Calling cache.get_category_channels('%s', media_type='%s')" %
                    (category_id, self.media_type), module="Categories")

                # [TVGarden patch] Passiamo media_type
                if hasattr(
                        self.cache, 'get_category_channels') and callable(
                        self.cache.get_category_channels):
                    try:
                        data = self.cache.get_category_channels(
                            category_id,
                            media_type=self.media_type,
                            force_refresh=force_refresh_browsing)
                    except TypeError:
                        # Retrocompatibilità
                        try:
                            data = self.cache.get_category_channels(
                                category_id, force_refresh=force_refresh_browsing)
                        except TypeError:
                            data = self.cache.get_category_channels(category_id)
                else:
                    data = []

                log.debug(
                    "Data received, type: %s" %
                    type(data), module="Categories")

                data_str = str(data)
                log.debug("Data sample: %s..." % data_str[:300] if len(
                    data_str) > 300 else data_str, module="Categories")

                # Extract channels
                channels = []
                if isinstance(data, list):
                    channels = data
                    log.debug(
                        "Data is list with %d items" %
                        len(channels), module="Categories")
                elif isinstance(data, dict):
                    log.debug(
                        "Data is dict with keys: %s" %
                        list(
                            data.keys()),
                        module="Categories")
                    if 'channels' in data:
                        channels = data['channels']
                        log.debug(
                            "Found 'channels' key with %d items" %
                            len(channels), module="Categories")
                    else:
                        for key in ['items', 'streams', 'list']:
                            if key in data:
                                channels = data[key]
                                log.debug(
                                    "Found '%s' key with %d items" %
                                    (key, len(channels)), module="Categories")
                                break

                log.debug(
                    "Total channels extracted: %d" %
                    len(channels), module="Categories")

                if len(channels) > 0:
                    log.debug(
                        "Opening ChannelsBrowser with %d channels" %
                        len(channels), module="Categories")
                    # [TVGarden patch] Passiamo media_type
                    self.session.open(
                        ChannelsBrowser,
                        category_id=category_id,
                        category_name="%s (%d channels)" %
                        (category_name,
                         len(channels)),
                        media_type=self.media_type)
                else:
                    self["status"].setText(_("No channels in this category"))
                    log.warning("Empty channel list!", module="Categories")

            except Exception as e:
                self["status"].setText(_("Error loading category"))
                log.error(
                    "ERROR: %s: %s" %
                    (type(e).__name__, e), module="Categories")
                import traceback
                traceback.print_exc()

    def refresh(self):
        """Refresh categories - clear cache or force refresh"""
        self["status"].setText(_("Refreshing..."))
        try:
            config = get_config()
            refresh_method = config.get("refresh_method", "clear_cache")

            if refresh_method == "clear_cache":
                self.cache.clear_all()
                self["status"].setText(_("Cache cleared"))
                log.info("Cache cleared manually", module="Categories")
            else:
                self["status"].setText(_("Next load will use fresh data"))
                log.info(
                    "Force refresh enabled for next load",
                    module="Categories")

        except Exception as e:
            self["status"].setText(_("Refresh failed"))
            log.error("Error in refresh: %s" % e, module="Categories")

    def exit(self):
        """Exit browser"""
        self.close()

    def up(self):
        """Handle up key"""
        self["menu"].up()

    def down(self):
        """Handle down key"""
        self["menu"].down()
