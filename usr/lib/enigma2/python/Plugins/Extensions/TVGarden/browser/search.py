#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - SearchBrowser
Live search
Data Source: TV Garden Project

[TVGarden patch] Ricerca unificata su TV + Webcams.
I risultati mostrano un prefisso [TV] o [WEB] per distinguere la sorgente.
"""
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from enigma import eServiceReference, eTimer

from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.NumericalTextInput import NumericalTextInput
import time
import threading

from .base import BaseBrowser
from ..utils.cache import CacheManager
from ..helpers import (
    log,
    timer_connect,
    extract_stream_url,
    is_valid_stream_url,
    get_channel_language,
    get_all_channels_url
)
from ..utils.favorites import FavoritesManager
from ..player.iptv_player import TVGardenPlayer
from ..utils.config import PluginConfig, get_config

from .. import _, PLUGIN_VERSION


# [TVGarden patch] Sorgenti da cercare in un'unica ricerca
SEARCH_MEDIA_TYPES = ("tv", "webcams")

# [TVGarden patch] Etichette brevi per distinguere i risultati
MEDIA_LABELS = {
    "tv": "TV",
    "webcams": "WEB",
}


class SearchBrowser(BaseBrowser):
    skin = """
        <screen name="SearchBrowser" position="center,center" size="1920,1080" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <!-- Button pixmaps -->
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/redbutton.png" position="47,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/greenbutton.png" position="261,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/yellowbutton.png" position="474,1038" size="210,6" alphatest="blend" transparent="1" />
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/bluebutton.png" position="688,1038" size="210,6" alphatest="blend" transparent="1" />

            <!-- Donation icons -->
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

            <!-- Menu (risultati ricerca) -->
            <widget name="menu" position="48,160" size="1020,750" font="Regular;32" itemHeight="50" scrollbarMode="showOnDemand" backgroundColor="#16213e" />

            <!-- Title -->
            <widget source="title" position="49,-8" size="1770,60" font="Regular;48" foregroundColor="#ffff00" zPosition="5" render="Label" backgroundColor="#ff000000" />

            <!-- Search label and text -->
            <widget source="search_label" position="48,55" size="610,90" zPosition="10" font="Regular;34" halign="right" valign="center" foregroundColor="#ffffff" render="Label" />
            <widget source="search_text" position="671,55" size="1220,90" zPosition="10" font="Regular;34" halign="left" valign="center" backgroundColor="#2d3047" foregroundColor="#ffffff" render="Label" />

            <!-- Status -->
            <widget source="status" render="Label" position="921,976" size="976,61" font="Regular;32" halign="center" foregroundColor="#3333ff" transparent="1" alphatest="blend" />

            <!-- Bottom bar -->
            <eLabel backgroundColor="#001a2336" cornerRadius="30" position="8,959" size="1905,90" zPosition="-80" />

            <!-- Menu background -->
            <eLabel name="" position="36,152" size="1040,767" zPosition="0" cornerRadius="18" backgroundColor="#00171a1c" foregroundColor="#00171a1c" />

            <!-- Video Picture -->
            <widget source="session.VideoPicture" render="Pig" position="1109,210" zPosition="19" size="780,462" backgroundColor="#ff000000" transparent="0" cornerRadius="14" />
        </screen>
    """

    def __init__(self, session):

        self.config = PluginConfig()
        dynamic_skin = self.config.load_skin("SearchBrowser", self.skin)
        self.skin = dynamic_skin

        BaseBrowser.__init__(self, session)
        self.session = session
        self.cache = CacheManager()
        self.fav_manager = FavoritesManager()

        self.search_query = ""
        self.all_channels = []
        self.filtered_channels = []
        self.menu_channels = []
        self.selectedIndex = 0
        self.last_key = None
        self.last_key_time = 0
        self.key_timer = eTimer()
        self.key_timer_conn = timer_connect(
            self.key_timer, self.finishKeyInput)
        self.load_check_timer = None
        self._cancel_loading = False
        self['title'] = StaticText(
            "TV Garden %s | by Lululla" % PLUGIN_VERSION)
        self["search_label"] = StaticText(_("Search:"))
        self["search_text"] = StaticText("")
        self["menu"] = MenuList([])
        self["status"] = StaticText(_("Press GREEN for keyboard..."))
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Keyboard"))
        self["key_yellow"] = StaticText(_("Favorite"))
        self["key_blue"] = StaticText(_("Clear"))

        self["actions"] = ActionMap(["OkCancelActions",
                                     "ColorActions",
                                     "DirectionActions",
                                     "NumberActions"],
                                    {"cancel": self.exit,
                                     "ok": self.play_channel,
                                     "red": self.exit,
                                     "green": self.open_keyboard,
                                     "yellow": self.toggle_favorite,
                                     "blue": self.clear_search,
                                     "up": self.up,
                                     "down": self.down,
                                     "left": self.left,
                                     "right": self.right,
                                     "1": lambda: self.key_number(1),
                                     "2": lambda: self.key_number(2),
                                     "3": lambda: self.key_number(3),
                                     "4": lambda: self.key_number(4),
                                     "5": lambda: self.key_number(5),
                                     "6": lambda: self.key_number(6),
                                     "7": lambda: self.key_number(7),
                                     "8": lambda: self.key_number(8),
                                     "9": lambda: self.key_number(9),
                                     "0": lambda: self.key_number(0),
                                     },
                                    -2)

        self.search_timer = eTimer()
        self.search_timer_conn = timer_connect(
            self.search_timer, self.perform_search)

        self.numerical_input = NumericalTextInput(self.search_with_string)
        self.onFirstExecBegin.append(self.load_all_channels)

    def _update_status(self, text):
        """Thread-safe status update (called from the loader thread)"""
        try:
            from twisted.internet import reactor
            reactor.callFromThread(self._set_status_text, text)
        except Exception:
            pass

    def _set_status_text(self, text):
        if not self._cancel_loading:
            self["status"].setText(text)

    def _check_loading_complete(self):
        if hasattr(self, '_loading_complete') and self._loading_complete:
            self.load_check_timer.stop()
            self._loading_in_progress = False

            if hasattr(self, '_loading_error'):
                self["status"].setText(
                    _("Error loading channels: %s") %
                    self._loading_error)
                self.all_channels = []
            elif hasattr(self, '_loaded_channels'):
                self.all_channels = self._loaded_channels
                log.info("Total channels loaded: %d" %
                         len(self.all_channels), module="Search")
                self["status"].setText(
                    _("Ready - %d channels") % len(self.all_channels))
                self.search_results = self.all_channels[:]
                self.display_search_results()
            else:
                self["status"].setText(_("No channels loaded"))
                log.error("No _loaded_channels found", module="Search")

            for attr in [
                '_loading_complete',
                '_loaded_channels',
                    '_loading_error']:
                if hasattr(self, attr):
                    delattr(self, attr)

    def _load_media_channels(self, media_type, force_refresh):
        """Load every channel of one media type"""
        try:
            countries = self.cache.get_countries_metadata(
                media_type=media_type, force_refresh=force_refresh) or {}
        except Exception as e:
            log.warning("No metadata for %s: %s" %
                        (media_type, e), module="Search")
            countries = {}

        # Country code -> display name
        names = {}
        for code, info in countries.items():
            if isinstance(info, dict):
                names[code.lower()] = info.get('country', code)

        # 1. One single download: <media>/raw/categories/all.json
        try:
            self._update_status(_("Loading %s channels...") % media_type)
            channels = self.cache.fetch_url(
                get_all_channels_url(media_type), force_refresh=force_refresh)
            if isinstance(channels, list) and channels:
                for ch in channels:
                    code = str(ch.get('country', '')).lower()
                    ch['country'] = names.get(code, code.upper())
                    ch['media_type'] = media_type
                return channels
        except Exception as e:
            log.warning("all.json not available for %s: %s" %
                        (media_type, e), module="Search")

        # 2. Fallback: country by country
        result = []
        total_countries = len(countries)
        for processed, (code, info) in enumerate(countries.items(), 1):
            if self._cancel_loading:
                break
            if isinstance(info, dict) and not info.get('hasChannels', True):
                continue
            self._update_status(
                _("Loading %s: %s (%d/%d)") %
                (media_type, code.upper(), processed, total_countries))
            try:
                channels = self.cache.get_country_channels(
                    code, media_type=media_type, force_refresh=force_refresh)
                for ch in channels or []:
                    ch['country'] = names.get(code.lower(), code)
                    ch['media_type'] = media_type
                result.extend(channels or [])
            except Exception as e:
                log.debug("Skipped %s/%s: %s" %
                          (media_type, code, str(e)[:50]), module="Search")
        return result

    def _load_all_channels_thread(self):
        """
        [TVGarden patch] Carica canali da TV + Webcams in un unico thread.
        Ogni channel viene taggato con `media_type` per distinguerlo.
        """
        force_refresh = get_config().get("force_refresh_browsing", False)
        temp_channels = []
        try:
            for media_type in SEARCH_MEDIA_TYPES:
                if self._cancel_loading:
                    break
                temp_channels.extend(
                    self._load_media_channels(media_type, force_refresh))

            self._loaded_channels = temp_channels
        except Exception as e:
            log.error("Background loading error: %s" % e, module="Search")
            self._loading_error = str(e)
        finally:
            self._loading_complete = True

    def load_all_channels(self):
        """Load all channels in background thread to avoid GUI freeze"""
        if getattr(self, '_loading_in_progress', False):
            self["status"].setText(_("Loading already in progress..."))
            return

        self._loading_in_progress = True
        self["status"].setText(_("Loading all channels in background..."))
        self.all_channels = []

        self.load_thread = threading.Thread(
            target=self._load_all_channels_thread)
        self.load_thread.daemon = True
        self.load_thread.start()

        self.load_check_timer = eTimer()
        self.load_check_timer_conn = timer_connect(
            self.load_check_timer, self._check_loading_complete)
        self.load_check_timer.start(500)

    def open_keyboard(self):
        """Open virtual keyboard"""
        self.session.openWithCallback(
            self.keyboard_callback,
            VirtualKeyBoard,
            title=_("Search Channels"),
            text=self.search_query
        )

    def keyboard_callback(self, result):
        """Handle keyboard input"""
        if result is not None:
            self.search_query = result
            self["search_text"].setText(self.search_query)
            self["status"].setText(_("Searching..."))

            self.search_timer.start(300, True)

    def key_number(self, number):
        """Handle numeric key press (T9 style)"""
        key_chars = {
            2: "abc2", 3: "def3", 4: "ghi4", 5: "jkl5", 6: "mno6",
            7: "pqrs7", 8: "tuv8", 9: "wxyz9", 0: " 0", 1: "."
        }

        if number in key_chars:
            chars = key_chars[number]
            current_time = time.time()

            if self.last_key == number and current_time - self.last_key_time < 1.0:
                if self.search_query and self.search_query[-1] in chars:
                    current_index = chars.index(self.search_query[-1])
                    next_index = (current_index + 1) % len(chars)
                    self.search_query = self.search_query[:-
                                                          1] + chars[next_index]
                else:
                    self.search_query += chars[0]
            else:
                self.search_query += chars[0]

            self["search_text"].setText(self.search_query)
            self["status"].setText(_("Searching..."))

            self.search_timer.start(500, True)

            self.last_key = number
            self.last_key_time = current_time
            self.key_timer.start(1000, True)

    def search_with_string(self):
        """Callback from NumericalTextInput"""
        pass

    def finishKeyInput(self):
        """Reset key state after inactivity"""
        self.last_key = None
        self.key_timer.stop()

    def clear_search(self):
        """Clear search text and reset to full channel list"""
        self.search_query = ""
        self["search_text"].setText("")
        if hasattr(self, 'all_channels') and self.all_channels:
            self.search_results = self.all_channels[:]
            self.display_search_results()
            self["status"].setText(
                _("Showing all %d channels") % len(
                    self.all_channels))
        else:
            self["menu"].setList([])
            self["status"].setText(_("Press GREEN for keyboard..."))

    def match_channel(self, channel, query):
        """Check if channel matches search query"""
        name = channel.get('name', '').lower()
        if query in name:
            return True

        description = channel.get('description', '').lower()
        if description and query in description:
            return True

        group = channel.get('group', '').lower()
        if group and query in group:
            return True

        # [TVGarden patch] cerca anche nel media_type (es. "web", "tv")
        media_type = channel.get('media_type', '').lower()
        if media_type and query in media_type:
            return True

        return False

    def perform_search(self):
        query = self.search_query.lower()
        log.debug("Searching '%s' in %d channels" %
                  (query, len(self.all_channels)), module="Search")

        if len(self.all_channels) < 100:
            log.warning("Very few channels (%d)!" %
                        len(self.all_channels), module="Search")

        self.search_results = []
        self.menu_channels = []

        try:
            for channel in self.all_channels:
                if self.match_channel(channel, query):
                    self.search_results.append(channel)
        except Exception as e:
            log.error("Search error: %s" % e, module="Search")

        self.search_results.sort(key=lambda c: c.get('name', '').lower())

        self.display_search_results()

    def display_search_results(self):
        """Display search results in menu"""
        log.info("Found %d results" %
                 len(self.search_results), module="Search")

        config = get_config()
        max_channels = config.get("search_max_results", 500)

        log.debug(
            "Using max_channels limit: %d" %
            max_channels, module="Search")

        menu_items = []
        self.menu_channels = []
        valid_count = 0
        youtube_count = 0
        problematic_count = 0
        skipped_by_limit = 0
        tv_count = 0
        web_count = 0

        for idx, channel in enumerate(self.search_results):
            if max_channels > 0:
                if idx >= max_channels:
                    log.debug(
                        "Stopped at %d results (limit: %d)" %
                        (idx, max_channels), module="Search")
                    skipped_by_limit = len(self.search_results) - idx
                    break

            name = channel.get('name', 'Result %d' % (idx + 1))
            stream_url, found_in, is_youtube = extract_stream_url(channel)

            if not stream_url or not is_valid_stream_url(stream_url):
                problematic_count += 1
                continue

            if is_youtube:
                youtube_count += 1

            log.debug(
                "Channel: %s, URL: %s, is_youtube: %s" %
                (name, stream_url, is_youtube), module="Search")

            # [TVGarden patch] Conta per media_type e crea prefisso
            media_type = channel.get('media_type', 'tv')
            media_label = MEDIA_LABELS.get(media_type, "TV")

            if media_type == "tv":
                tv_count += 1
            elif media_type == "webcams":
                web_count += 1

            # Display name con prefisso [TV] / [WEB]
            extra_info = []
            if channel.get('category'):
                extra_info.append(channel['category'])
            if channel.get('country'):
                extra_info.append(channel['country'])

            display_name = "[%s] %s" % (media_label, name)
            if is_youtube:
                display_name = "[%s][YT] %s" % (media_label, name)
            if extra_info:
                display_name += " [%s]" % ', '.join(extra_info)

            channel_data = {
                'name': name,
                'url': stream_url,
                'stream_url': stream_url,
                'logo': channel.get('logo'),
                'id': channel.get('nanoid', 'srch_%d' % idx),
                'description': channel.get('description', ''),
                'group': channel.get('group', ''),
                'language': get_channel_language(channel),
                'country': channel.get('country', ''),
                'is_youtube': is_youtube,
                'found_in': found_in,
                'media_type': media_type,  # [TVGarden patch]
            }

            menu_items.append((display_name, len(self.menu_channels)))
            self.menu_channels.append(channel_data)
            valid_count += 1

        log.info("Valid channels found: %d" %
                 len(menu_items), module="Search")
        self["menu"].setList(menu_items)

        if max_channels > 0 and len(self.search_results) > max_channels:
            msg = _("Showing {shown} of {total} results")
            status_text = msg.format(
                shown=min(max_channels, valid_count),
                total=len(self.search_results)
            )
        else:
            status_text = _("Found %d channels") % valid_count

        # [TVGarden patch] Info su TV vs Webcams
        if tv_count or web_count:
            status_text += " [TV: %d / WEB: %d]" % (tv_count, web_count)

        if youtube_count > 0:
            status_text += " " + _("(%d YouTube)") % youtube_count

        if problematic_count > 0:
            status_text += " " + \
                _("(%d without stream)") % problematic_count

        if skipped_by_limit > 0:
            status_text += " " + _("(limited to first %d)") % max_channels

        self["status"].setText(status_text)

        if menu_items:
            if self.menu_channels:
                self.current_channel = self.menu_channels[0]
        else:
            self["status"].setText(
                _("No channels found for: %s") %
                self.search_query)

        log.info(
            "Final: %d playable (TV:%d WEB:%d), %d YouTube, %d without stream, %d limited by config" %
            (valid_count,
             tv_count,
             web_count,
             youtube_count,
             problematic_count,
             skipped_by_limit),
            module="Search")

    def get_current_channel(self):
        menu_idx = self["menu"].getSelectedIndex()
        if menu_idx is not None and 0 <= menu_idx < len(self.menu_channels):
            return self.menu_channels[menu_idx], menu_idx
        return None, -1

    def play_channel(self):
        """Play selected channel"""
        channel, idx = self.get_current_channel()
        if not channel:
            return

        stream_url = channel.get('stream_url')
        if not stream_url:
            self["status"].setText(_("No stream URL"))
            return

        try:
            url_encoded = stream_url.replace(":", "%3a")
            name_encoded = channel['name'].replace(":", "%3a")
            ref_str = "4097:0:0:0:0:0:0:0:0:0:%s:%s" % (
                url_encoded, name_encoded)

            service_ref = eServiceReference(ref_str)
            service_ref.setName(channel['name'])

            self.session.open(
                TVGardenPlayer,
                service_ref,
                self.menu_channels,
                idx)

        except Exception as e:
            log.error("Play error: %s" % e, module="Search")
            self.session.open(
                MessageBox,
                _("Error opening player"),
                MessageBox.TYPE_ERROR)

    def toggle_favorite(self):
        """Add/remove channel from favorites"""
        channel, channel_idx = self.get_current_channel()
        if channel:
            if self.fav_manager.is_favorite(channel):
                self.fav_manager.remove(channel)
                self["status"].setText(_("Removed from favorites"))
            else:
                self.fav_manager.add(channel)
                self["status"].setText(_("Added to favorites"))

    def update_selected_index(self):
        """Update selected index from menu"""
        self.selectedIndex = self["menu"].getSelectedIndex()

    def up(self):
        self["menu"].up()
        self.update_selected_index()

    def down(self):
        self["menu"].down()
        self.update_selected_index()

    def left(self):
        self["menu"].pageUp()
        self.update_selected_index()

    def right(self):
        self["menu"].pageDown()
        self.update_selected_index()

    def exit(self):
        # Tell the loader thread to stop and stop polling it
        self._cancel_loading = True
        if self.load_check_timer:
            self.load_check_timer.stop()
        self.search_timer.stop()
        self.key_timer.stop()
        self.close()
