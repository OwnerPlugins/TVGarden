#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Categories Browser
Browse 29 categories of IPTV channels
Based on TV Garden Project
"""
from __future__ import print_function
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap

from .base import BaseBrowser
from .channels import ChannelsBrowser
from ..helpers import log
from ..utils.cache import CacheManager
from ..utils.config import PluginConfig, get_config
from .. import _, PLUGIN_VERSION


try:
    from ..helpers import CATEGORIES
except ImportError:
    # Fallback
    CATEGORIES = [
        {'id': 'animation', 'name': _('Animation'), 'icon': 'film'},
        {'id': 'auto', 'name': _('Auto'), 'icon': 'car'},
        {'id': 'business', 'name': _('Business'), 'icon': 'briefcase'},
        {'id': 'classic', 'name': _('Classic'), 'icon': 'landmark'},
        {'id': 'comedy', 'name': _('Comedy'), 'icon': 'masks-theater'},
        {'id': 'cooking', 'name': _('Cooking'), 'icon': 'utensils'},
        {'id': 'culture', 'name': _('Culture'), 'icon': 'palette'},
        {'id': 'documentary', 'name': _('Documentary'), 'icon': 'camera-retro'},
        {'id': 'education', 'name': _('Education'), 'icon': 'graduation-cap'},
        {'id': 'entertainment', 'name': _('Entertainment'), 'icon': 'gamepad'},
        {'id': 'family', 'name': _('Family'), 'icon': 'users'},
        {'id': 'general', 'name': _('General'), 'icon': 'tv'},
        {'id': 'history', 'name': _('History'), 'icon': 'scroll'},
        {'id': 'hobby', 'name': _('Hobby'), 'icon': 'puzzle-piece'},
        {'id': 'kids', 'name': _('Kids'), 'icon': 'child-reaching'},
        {'id': 'legislative', 'name': _('Legislative'), 'icon': 'gavel'},
        {'id': 'lifestyle', 'name': _('Lifestyle'), 'icon': 'person-walking'},
        {'id': 'local', 'name': _('Local'), 'icon': 'map-marker-alt'},
        {'id': 'movies', 'name': _('Movies'), 'icon': 'clapperboard'},
        {'id': 'music', 'name': _('Music'), 'icon': 'music'},
        {'id': 'news', 'name': _('News'), 'icon': 'newspaper'},
        {'id': 'politics', 'name': _('Politics'), 'icon': 'landmark-dome'},
        {'id': 'religious', 'name': _('Religious'), 'icon': 'place-of-worship'},
        {'id': 'series', 'name': _('Series'), 'icon': 'photo-film'},
        {'id': 'science', 'name': _('Science'), 'icon': 'flask'},
        {'id': 'shop', 'name': _('Shop'), 'icon': 'shopping-cart'},
        {'id': 'sports', 'name': _('Sports'), 'icon': 'futbol'},
        {'id': 'travel', 'name': _('Travel'), 'icon': 'plane-departure'},
        {'id': 'weather', 'name': _('Weather'), 'icon': 'cloud-sun'}
    ]


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

    def __init__(self, session):

        self.config = PluginConfig()
        dynamic_skin = self.config.load_skin("CategoriesBrowser", self.skin)
        self.skin = dynamic_skin

        BaseBrowser.__init__(self, session)
        self.session = session

        self.cache = CacheManager()
        self.selected_category = None

        self["menu"] = MenuList([])
        self['title'] = StaticText(
            "TV Garden %s | by Lululla" %
            PLUGIN_VERSION)
        self["status"] = StaticText(_("Loading categories..."))
        # self["icon"] = Pixmap()
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
        """Load categories list"""
        menu_items = []
        for category in CATEGORIES:
            # Show name only - we'll get count when selected
            menu_items.append((category['name'], category['id']))

        self["menu"].setList(menu_items)
        self["status"].setText(_("Select a category"))

    def select_category(self):
        """Select category"""
        selection = self["menu"].getCurrent()
        if selection:
            category_id = selection[1]
            category_name = selection[0]

            log.debug(
                "Selected: %s (%s)" %
                (category_id,
                 category_name),
                module="Categories")

            try:
                # Get cache configuration
                config = get_config()
                # cache_enabled = config.get("cache_enabled", True)
                force_refresh_browsing = config.get(
                    "force_refresh_browsing", False)

                # Load data with cache config
                log.debug(
                    "Calling cache.get_category_channels('%s')" %
                    category_id, module="Categories")

                if hasattr(
                        self.cache, 'get_category_channels') and callable(
                        self.cache.get_category_channels):
                    # If the method supports force_refresh
                    try:
                        data = self.cache.get_category_channels(
                            category_id, force_refresh=force_refresh_browsing)
                    except TypeError:
                        # If it doesn't support the parameter, use default
                        data = self.cache.get_category_channels(category_id)
                else:
                    # Fallback
                    data = []

                log.debug(
                    "Data received, type: %s" %
                    type(data), module="Categories")

                # Full log for the first 500 characters
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
                        # Search for other keys
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
                    self.session.open(
                        ChannelsBrowser,
                        category_id=category_id,
                        category_name="%s (%d channels)" %
                        (category_name,
                         len(channels)))
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
            # "clear_cache" o "force_refresh"
            refresh_method = config.get("refresh_method", "clear_cache")

            if refresh_method == "clear_cache":
                self.cache.clear_all()
                self["status"].setText(_("Cache cleared"))
                log.info("Cache cleared manually", module="Categories")
            else:
                # Set force_refresh for next navigation
                # You may want to set a temporary flag
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
