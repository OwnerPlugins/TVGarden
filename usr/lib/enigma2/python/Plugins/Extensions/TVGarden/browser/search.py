#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - SearchBrowser
Live search
Data Source: TV Garden Project
"""
from __future__ import print_function

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
from ..helpers import log  # , is_valid_stream_url
from ..utils.favorites import FavoritesManager
from ..player.iptv_player import TVGardenPlayer
from ..utils.config import PluginConfig, get_config

from .. import _, PLUGIN_VERSION


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
            <widget name="title" position="49,-8" size="1770,60" font="Regular;48" foregroundColor="#ffff00" zPosition="5" render="Label" backgroundColor="#ff000000" />

            <!-- Search label and text (specifici per SearchBrowser) -->
            <widget name="search_label" position="48,55" size="610,90" zPosition="10" font="Regular;34" halign="right" valign="center" foregroundColor="#ffffff" render="Label" />
            <widget name="search_text" position="671,55" size="1220,90" zPosition="10" font="Regular;34" halign="left" valign="center" backgroundColor="#2d3047" foregroundColor="#ffffff" render="Label" />

            <!-- Status -->
            <widget name="status" position="921,976" size="976,61" font="Regular;32" halign="center" foregroundColor="#3333ff" transparent="1" alphatest="blend" />

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
        try:
            self.key_timer.timeout.connect(self.finishKeyInput)
        except BaseException:
            self.key_timer.callback.append(self.finishKeyInput)
        self['title'] = StaticText(
            "TV Garden %s | by Lululla" %
            PLUGIN_VERSION)
        self["search_label"] = StaticText(_("Search:"))
        self["search_text"] = StaticText("")
        self["menu"] = MenuList([])
        self["status"] = StaticText(_("Press GREEN for keyboard..."))
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Keyboard"))
        self["key_yellow"] = StaticText(_("Favorite"))
        self["key_blue"] = StaticText(_("Clear"))

        self["actions"] = ActionMap(["TVGardenActions",
                                     "OkCancelActions",
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
        try:
            self.search_timer.timeout.connect(self.perform_search)
        except AttributeError:
            self.search_timer.callback.append(self.perform_search)

        self.numerical_input = NumericalTextInput(self.search_with_string)
        self.onFirstExecBegin.append(self.load_all_channels)

    def _update_status(self, text):
        """Thread-safe status update (posts an event to the main queue)"""
        # Use callFromThread if available, otherwise use eTimer
        try:
            from twisted.internet import reactor
            reactor.callFromThread(self._set_status_text, text)
        except ImportError:
            # Fallback: use eTimer to post the update
            self._pending_status = text
            if not hasattr(self, '_status_timer'):
                self._status_timer = eTimer()
                self._status_timer.timeout.connect(self._apply_pending_status)
                self._status_timer.start(100)

    def _set_status_text(self, text):
        self["status"].setText(text)

    def _apply_pending_status(self):
        if hasattr(self, '_pending_status'):
            self["status"].setText(self._pending_status)
            self._pending_status = None

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
                log.info("Total channels loaded: %d" % len(self.all_channels))
                self["status"].setText(
                    _("Ready - %d channels") % len(self.all_channels))
                self.search_results = self.all_channels[:]
                self.display_search_results()
            else:
                self["status"].setText(_("No channels loaded"))
                log.error("No _loaded_channels found")

            # Cleanup
            for attr in [
                '_loading_complete',
                '_loaded_channels',
                    '_loading_error']:
                if hasattr(self, attr):
                    delattr(self, attr)

    def _load_all_channels_thread(self):
        """Background thread: fetch all countries and accumulate channels"""
        config = get_config()
        force_refresh = config.get("force_refresh_browsing", False)
        timeout = config.get("connection_timeout", 10)

        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)

        temp_channels = []

        try:
            countries = self.cache.get_countries_metadata(
                force_refresh=force_refresh)
            total_countries = len(countries)
            processed = 0

            for code, info in countries.items():
                processed += 1
                self._update_status(
                    _("Loading countries: %s (%d/%d)") %
                    (code.upper(), processed, total_countries))
                try:
                    channels = self.cache.get_country_channels(
                        code, force_refresh=force_refresh)
                    if channels:
                        for ch in channels:
                            ch['country'] = info.get('name', code)
                        temp_channels.extend(channels)
                        log.debug(
                            "Added %d from %s" %
                            (len(channels), code), module="Search")
                except Exception as e:
                    log.debug("Skipped %s: %s" %
                              (code, str(e)[:50]), module="Search")
                    continue

            self._loaded_channels = temp_channels
            self._loading_complete = True

        except Exception as e:
            log.error("Background loading error: %s" % e, module="Search")
            self._loading_error = str(e)
            self._loading_complete = True
        finally:
            socket.setdefaulttimeout(original_timeout)

    def load_all_channels(self):
        """Load all channels in background thread to avoid GUI freeze"""
        if hasattr(self, '_loading_in_progress') and self._loading_in_progress:
            self["status"].setText(_("Loading already in progress..."))
            return

        self._loading_in_progress = True
        self["status"].setText(_("Loading all channels in background..."))
        self.all_channels = []

        # Start background thread
        self.load_thread = threading.Thread(
            target=self._load_all_channels_thread)
        self.load_thread.daemon = True
        self.load_thread.start()

        self.load_check_timer = eTimer()
        self.load_check_timer.callback.append(self._check_loading_complete)
        self.load_check_timer.start(500)  # check every 500ms

    def _add_channels_incrementally(self, new_channels, country_name):
        """Thread-safe: posta l'aggiornamento della GUI nel main thread"""
        from twisted.internet import reactor
        reactor.callFromThread(
            self._do_add_channels,
            new_channels,
            country_name)

    def _do_add_channels(self, new_channels, country_name):
        if not new_channels:
            return
        self.all_channels.extend(new_channels)
        log.debug("Added %d from %s, total: %d" % (len(new_channels), country_name, len(self.all_channels)))
        # if not self.search_query:
        #     self.search_results = self.all_channels[:]
        #     self.display_search_results()
        #     self["status"].setText(_("Loading... %d channels so far") % len(self.all_channels))
        # else:
        #     self.perform_search()
        self["status"].setText(_("Loading... %d channels so far") % len(self.all_channels))

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

            # Check if same key pressed quickly (cycle through chars)
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

            # Start search timer
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
        # Search in name
        name = channel.get('name', '').lower()
        if query in name:
            return True

        # Search in description
        description = channel.get('description', '').lower()
        if description and query in description:
            return True

        # Search in group/category
        group = channel.get('group', '').lower()
        if group and query in group:
            return True

        return False

    def perform_search(self):
        query = self.search_query.lower()
        log.debug("Searching '%s' in %d channels" %
                  (query, len(self.all_channels)), module="Search")

        if len(self.all_channels) < 100:
            log.warning("Very few channels (%d)!" %
                        len(self.all_channels), module="Search")
            log.warning(
                "This might explain limited search results",
                module="Search")

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

        # Get configurable limit
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

        for idx, channel in enumerate(self.search_results):
            # Apply configurable limit (0 = all channels)
            if max_channels > 0:
                if idx >= max_channels:
                    log.debug(
                        "Stopped at %d results (limit: %d)" %
                        (idx, max_channels), module="Search")
                    skipped_by_limit = len(self.search_results) - idx
                    break

            name = channel.get('name', 'Result %d' % (idx + 1))
            stream_url = None
            found_in = None
            is_youtube = False

            # 1. iptv_urls
            if 'iptv_urls' in channel and isinstance(
                    channel['iptv_urls'], list):
                for url in channel['iptv_urls']:
                    if isinstance(url, str) and url.strip():
                        stream_url = url.strip()
                        found_in = "iptv_urls"
                        break

            # 2. stream_urls
            if not stream_url and 'stream_urls' in channel and isinstance(
                    channel['stream_urls'], list):
                for url in channel['stream_urls']:
                    if isinstance(url, str) and url.strip():
                        stream_url = url.strip()
                        found_in = "stream_urls"
                        break

            # 3. youtube_urls (skip)
            if not stream_url and 'youtube_urls' in channel and isinstance(
                    channel['youtube_urls'], list):
                for url in channel['youtube_urls']:
                    if isinstance(url, str) and url.strip():
                        stream_url = url.strip()
                        found_in = "youtube_urls"
                        is_youtube = True
                        break

            # 4. Fallback a 'url'
            if not stream_url and 'url' in channel and isinstance(
                    channel['url'], str) and channel['url'].strip():
                stream_url = channel['url'].strip()
                found_in = "url"

            # 5. Basic URL validation
            # if not stream_url:
                # continue

            # 6. Skip YouTube
            if is_youtube:
                youtube_count += 1
                continue
            log.debug("Channel: %s, URL: %s, is_youtube: %s" % (name, stream_url, is_youtube))

            # # 7. Advanced validation
            """
            if not is_valid_stream_url(stream_url):
                continue

            # 8. Skip problematic patterns (same as channels.py)
            stream_lower = stream_url.lower()
            problematic_patterns = [
                "moveonjoy.com", ".mpd", "/dash/", "drm", "widevine",
                "playready", "fairplay", "keydelivery", "license.",
                "encryption", "akamaihd.net", "level3.net"
            ]

            is_problematic = False
            for pattern in problematic_patterns:
                if pattern in stream_lower:
                    problematic_count += 1
                    is_problematic = True
                    break

            if is_problematic:
                continue
            """

            # Create display name
            extra_info = []
            if channel.get('category'):
                extra_info.append(channel['category'])
            if channel.get('country'):
                extra_info.append(channel['country'])
            display_name = name
            if extra_info:
                display_name += " [%s]" % ', '.join(extra_info)

            # Create channel data
            channel_data = {
                'name': name,
                'url': stream_url,
                'stream_url': stream_url,
                'logo': channel.get('logo'),
                'id': channel.get('nanoid', 'srch_%d' % idx),
                'description': channel.get('description', ''),
                'group': channel.get('group', ''),
                'language': channel.get('language', ''),
                'country': channel.get('country', ''),
                'is_youtube': False,
                'found_in': found_in
            }

            menu_items.append((display_name, idx))
            self.menu_channels.append(channel_data)
            valid_count += 1

        # Update UI
        log.info("Valid channels found: %d" % len(menu_items))
        self["menu"].setList(menu_items)

        # Build status message
        if max_channels > 0 and len(self.search_results) > max_channels:
            msg = _("Showing {shown} of {total} results")
            status_text = msg.format(
                shown=min(max_channels, valid_count),
                total=len(self.search_results)
            )
        else:
            status_text = _("Found %d channels") % valid_count

        if youtube_count > 0:
            status_text += " " + _("(skipped %d YouTube)") % youtube_count

        if problematic_count > 0:
            status_text += " " + \
                _("(filtered %d problematic)") % problematic_count

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
            "Final: %d playable, %d YouTube skipped, %d problematic filtered, %d limited by config" %
            (valid_count, youtube_count, problematic_count, skipped_by_limit), module="Search")

    def extract_stream_url(self, channel):
        """Extract stream URL from channel (priorità: iptv_urls -> stream_urls -> youtube_urls -> url)"""
        # 1. iptv_urls
        if 'iptv_urls' in channel and isinstance(channel['iptv_urls'], list):
            for url in channel['iptv_urls']:
                if isinstance(url, str) and url.strip():
                    return url.strip()
        # 2. stream_urls
        if 'stream_urls' in channel and isinstance(
                channel['stream_urls'], list):
            for url in channel['stream_urls']:
                if isinstance(url, str) and url.strip():
                    return url.strip()
        # 3. youtube_urls (skip)
        if 'youtube_urls' in channel and isinstance(
                channel['youtube_urls'], list):
            for url in channel['youtube_urls']:
                if isinstance(url, str) and url.strip():
                    return None  # Skip YouTube
        # 4. Fallback a 'url'
        return channel.get('url', '')

    def create_channel_data(self, channel, stream_url):
        """Create channel data for player"""
        return {
            'name': channel.get('name', ''),
            'url': stream_url,
            'stream_url': stream_url,
            'logo': channel.get('logo') or channel.get('icon'),
            'id': channel.get('nanoid', ''),
            'description': channel.get('description', ''),
            'group': channel.get('group', '') or channel.get('category', ''),
            'language': channel.get('language', ''),
            'country': channel.get('country', ''),
            'category': channel.get('category', ''),
            'is_youtube': False
        }

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

    def moveUp(self):
        self["menu"].up()
        self.update_selected_index()

    def moveDown(self):
        self["menu"].down()
        self.update_selected_index()

    def moveLeft(self):
        self["menu"].pageUp()
        self.update_selected_index()

    def moveRight(self):
        self["menu"].pageDown()
        self.update_selected_index()

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
        if hasattr(self, 'load_thread') and self.load_thread.is_alive():
            self.load_thread = None
        if self.search_timer.isActive():
            self.search_timer.stop()
        self.close()
