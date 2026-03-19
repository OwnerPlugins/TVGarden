#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Channels Browser
List and play IPTV channels
Based on TV Garden Project
"""
from __future__ import print_function

import tempfile
from os import unlink
from os.path import exists
from sys import stderr, version_info
from enigma import ePicLoad, eServiceReference
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap

if version_info[0] == 3:
    from urllib.request import urlopen
else:
    from urllib2 import urlopen


try:
    from ..helpers import is_valid_stream_url, log
except ImportError as e:
    print("[CHANNELS IMPORT ERROR] %s" % e, file=stderr)

    # Fallback functions
    def log(msg, level="INFO"):
        print("[%s] TVGarden: %s" % (level, msg))

    def is_valid_stream_url(url):
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        valid_prefixes = ('http://', 'https://', 'rtmp://', 'rtsp://')
        return any(url.startswith(prefix)
                   for prefix in valid_prefixes) or '.m3u8' in url.lower()


from .base import BaseBrowser
from ..utils.config import PluginConfig, get_config
from ..utils.cache import CacheManager
from ..utils.favorites import FavoritesManager
from ..player.iptv_player import TVGardenPlayer
from .. import _, PLUGIN_VERSION


class ChannelsBrowser(BaseBrowser):
    skin = """
        <screen name="ChannelsBrowser" position="center,center" size="1920,1080" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
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

            <!-- Menu (lista canali) -->
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

            <!-- Channel logo (specifico per ChannelsBrowser) -->
            <widget name="logo" position="1149,712" size="285,180" alphatest="blend" scale="1" zPosition="4" />
        </screen>
    """

    def __init__(self, session, country_code=None, country_name=None,
                 category_id=None, category_name=None):

        self.config = PluginConfig()
        dynamic_skin = self.config.load_skin("ChannelsBrowser", self.skin)
        self.skin = dynamic_skin

        BaseBrowser.__init__(self, session)
        self.session = session
        self.cache = CacheManager()
        self.channels = []
        self.menu_channels = []
        self.current_channel = None

        self.fav_manager = FavoritesManager()

        self.country_code = country_code
        self.country_name = country_name
        self.category_id = category_id
        self.category_name = category_name

        title = ""
        if country_name:
            title = "Channels - %s" % str(country_name)
        elif category_name:
            title = "Channels - %s" % str(category_name)

        self.setTitle(title)

        self._load_export_settings()

        self["menu"] = MenuList([])
        self['title'] = StaticText(
            "TV Garden %s | by Lululla" %
            PLUGIN_VERSION)
        self["status"] = StaticText(_("Loading channels..."))
        self["logo"] = Pixmap()
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Play"))
        self["key_yellow"] = StaticText(_("Favorite"))
        self["key_blue"] = StaticText("")

        self["actions"] = ActionMap(["TVGardenActions", "OkCancelActions", "ColorActions"], {
            "cancel": self.exit,
            "ok": self.play_channel,
            "red": self.exit,
            "green": self.play_channel,
            "yellow": self.toggle_favorite,
            # "blue": self.show_info,
            "blue": self.export_current_view if self.menu_channels else lambda: None,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
            "menu": self.channel_menu,
        }, -2)

        self.picload = ePicLoad()

        if exists('/var/lib/dpkg/info'):
            # DreamOS
            self.picload_conn = self.picload.PictureData.connect(
                self.update_logo)
        else:
            self.picload_conn = self.picload.PictureData.get().append(self.update_logo)

        self.onFirstExecBegin.append(self.load_channels)
        # self.onLayoutFinish.append(self.refresh)

    def onSelectionChanged(self):
        """Called when menu selection changes"""
        current_index = self["menu"].getSelectedIndex()
        if current_index is not None:
            self.update_channel_selection(current_index)

    def channel_menu(self):
        """Show channel context menu"""
        menu = [
            (_("Play Channel"), "play"),
            (_("Add to Favorites"), "favorite"),
            (_("Channel Information"), "info"),
        ]

        if self.menu_channels:
            menu.append((_("Export Current View"), "export_current"))

        self.session.openWithCallback(self.menu_callback, ChoiceBox,
                                      title=_("Channel Menu"), list=menu)

    def menu_callback(self, choice):
        """Handle menu selection"""
        if choice:
            if choice[1] == "play":
                self.play_channel()
            elif choice[1] == "favorite":
                self.toggle_favorite()
            elif choice[1] == "info":
                self.show_info()
            elif choice[1] == "export_current":
                self.export_current_view()

    def load_channels(self):
        """Load channels for current context (country or category)"""
        try:
            config = get_config()
            max_channels = config.get("max_channels", 500)

            # Cache settings
            cache_enabled = config.get("cache_enabled", True)
            force_refresh_browsing = config.get(
                "force_refresh_browsing", False)

            channels = []
            if self.country_code:
                log.debug(
                    "Loading country channels: %s" %
                    self.country_code, module="Channels")
                # Use cache with config
                if hasattr(self.cache, 'get_country_channels'):
                    try:
                        channels = self.cache.get_country_channels(
                            self.country_code,
                            force_refresh=force_refresh_browsing
                        )
                    except TypeError:
                        # Method doesn't support force_refresh parameter
                        channels = self.cache.get_country_channels(
                            self.country_code)
                else:
                    channels = []

            elif self.category_id:
                log.debug(
                    "Loading category channels: %s" %
                    self.category_id, module="Channels")
                # Use cache with config
                if hasattr(self.cache, 'get_category_channels'):
                    try:
                        channels = self.cache.get_category_channels(
                            self.category_id,
                            force_refresh=force_refresh_browsing
                        )
                    except TypeError:
                        # Method doesn't support force_refresh parameter
                        channels = self.cache.get_category_channels(
                            self.category_id)
                else:
                    channels = []
            else:
                log.error(
                    "ERROR: No country_code or category_id!",
                    module="Channels")
                return

            log.debug(
                "Total channels received: %d" %
                len(channels), module="Channels")
            log.debug(
                "Max channels limit: %d (0=all)" %
                max_channels, module="Channels")
            log.debug("Cache enabled: %s, Force refresh: %s" %
                      (cache_enabled, force_refresh_browsing), module="Channels")

            # Save the ORIGINAL channels
            self.channels = channels

            # Process channels list
            menu_items = []
            self.menu_channels = []

            youtube_count = 0
            valid_count = 0
            problematic_count = 0
            skipped_count = 0

            for idx, channel in enumerate(channels):
                # Apply configurable limit (0 = all channels)
                if max_channels > 0 and idx >= max_channels:
                    log.debug(
                        "Stopped at %d channels (limit: %d)" %
                        (idx, max_channels), module="Channels")
                    skipped_count = len(channels) - idx
                    break

                name = channel.get("name", "Channel %d" % (idx + 1))

                stream_url = None
                found_in = None
                is_youtube = False

                # 1. Check iptv_urls
                if (
                    "iptv_urls" in channel
                    and isinstance(channel["iptv_urls"], list)
                    and channel["iptv_urls"]
                ):
                    for url in channel["iptv_urls"]:
                        if isinstance(url, str) and url.strip():
                            stream_url = url.strip()
                            found_in = "iptv_urls"
                            break

                # 2. If not found, check youtube_urls
                if (
                    not stream_url
                    and "youtube_urls" in channel
                    and isinstance(channel["youtube_urls"], list)
                    and channel["youtube_urls"]
                ):
                    for url in channel["youtube_urls"]:
                        if isinstance(url, str) and url.strip():
                            stream_url = url.strip()
                            found_in = "youtube_urls"
                            is_youtube = True
                            break

                # 3. If YouTube → skip for now
                if is_youtube:
                    youtube_count += 1
                    print(
                        "[CHANNELS DEBUG] ⏭️ Skipping YouTube: %s" % name,
                        file=stderr
                    )
                    continue  # skip this channel

                # 4. Basic URL validation
                if not stream_url:
                    log.warning(
                        "✗ No stream URL: %s" %
                        name, module="Channels")
                    continue

                # 5. Advanced validation: playable URL
                if not is_valid_stream_url(stream_url):
                    log.warning(
                        "✗ Invalid URL format: %s" %
                        name, module="Channels")
                    continue

                # 6. CRITICAL FILTER: skip known problematic hosts/protocols
                stream_lower = stream_url.lower()

                problematic_patterns = [
                    "moveonjoy.com",  # caused crashes in logs
                    ".mpd",           # DASH DRM
                    "/dash/",         # DASH stream
                    "drm",
                    "widevine",       # DRM: Widevine
                    "playready",      # DRM: PlayReady
                    "fairplay",       # DRM: Apple FairPlay
                    "keydelivery",
                    "license.",
                    "encryption",
                    "akamaihd.net",   # often DRM
                    "level3.net"      # problematic CDN
                ]

                is_problematic = False
                for pattern in problematic_patterns:
                    if pattern in stream_lower:
                        log.warning("⚠️ Skipping problematic pattern '%s': %s..." % (
                            pattern, name[:30]), module="Channels")
                        problematic_count += 1
                        is_problematic = True
                        break

                if is_problematic:
                    continue

                # 7. Prefer HTTP over HTTPS (more stable on Enigma2)
                stream_url_to_use = stream_url

                # Debug URL type
                if stream_url.startswith("http://"):
                    log.debug("   HTTP URL (good)", module="Channels")
                elif stream_url.startswith("https://"):
                    log.debug(
                        "   HTTPS URL (may have issues)",
                        module="Channels")
                elif stream_url.startswith("rtmp://") or stream_url.startswith("rtsp://"):
                    log.debug(
                        "   RTMP/RTSP URL (needs gstreamer)",
                        module="Channels")

                # 8. Build channel object
                channel_data = {
                    "name": str(
                        name or ""),
                    "url": stream_url_to_use,
                    "stream_url": stream_url_to_use,
                    "logo": channel.get("logo") or channel.get("icon") or channel.get("image"),
                    "id": str(
                        channel.get(
                            "nanoid",
                            "ch_%d" %
                            idx)),
                    "description": str(
                        channel.get(
                            "description",
                            "")),
                    "group": str(
                        channel.get(
                            "group",
                            "")),
                    "language": str(
                        channel.get(
                            "language",
                            "")),
                    "country": str(
                        channel.get(
                            "country",
                            "")),
                    "found_in": str(found_in),
                    "original_index": idx,
                    "is_youtube": False,
                }

                menu_items.append((name, idx))
                self.menu_channels.append(channel_data)
                valid_count += 1
                log.debug("✓ Added: %s" % name, module="Channels")

            self["menu"].setList(menu_items)

            if menu_items:
                self["key_blue"].setText(_("Export"))
            else:
                self["key_blue"].setText("")

            self["menu"].onSelectionChanged.append(self.onSelectionChanged)
            if menu_items:
                selected_idx = menu_items[0][1]
                if 0 <= selected_idx < len(self.menu_channels):
                    self.current_channel = self.menu_channels[selected_idx]
                    log.debug(
                        "First channel: %s" %
                        self.current_channel['name'],
                        module="Channels")
                    self.update_channel_selection(0)

            # Build status message with cache info
            cache_info = ""
            if force_refresh_browsing:
                cache_info = _(" [Fresh data]")
            elif not cache_enabled:
                cache_info = _(" [Cache disabled]")

            if max_channels > 0 and len(channels) > max_channels:
                msg = _("Showing {shown} of {total} channels")
                status_text = msg.format(
                    shown=min(max_channels, valid_count),
                    total=valid_count + youtube_count + problematic_count
                )
            else:
                status_text = _("Found %d playable channels") % valid_count

            # Add cache info
            status_text += cache_info

            if youtube_count > 0:
                status_text += " " + _("(skipped %d YouTube)") % youtube_count

            if problematic_count > 0:
                status_text += " " + \
                    _("(filtered %d problematic)") % problematic_count

            if skipped_count > 0 and max_channels > 0:
                status_text += " " + _("(limited to first %d)") % max_channels

            self["status"].setText(status_text)

            log.info(
                "Playable: %d, Skipped YouTube: %d, Filtered problematic: %d, Config limit: %d, Skipped by limit: %d" %
                (valid_count, youtube_count, problematic_count, max_channels, skipped_count), module="Channels")

            log.info("Cache status: enabled=%s, force_refresh=%s" %
                     (cache_enabled, force_refresh_browsing), module="Channels")

        except Exception as e:
            log.error("load_channels failed: %s" % e, module="Channels")
            import traceback
            traceback.print_exc()
            self["status"].setText(_("Error loading channels"))

    def update_channel_selection(self, index):
        """Update selection and load logo"""
        log.debug(
            "update_channel_selection called with index: %d" %
            index, module="Channels")
        if 0 <= index < len(self.menu_channels):
            self.current_channel = self.menu_channels[index]
            log.debug(
                "Selected channel: %s" %
                self.current_channel['name'],
                module="Channels")
            log.debug(
                "Stream URL: %s" %
                self.current_channel.get(
                    'stream_url',
                    'NONE'),
                module="Channels")

            logo_url = self.current_channel.get('logo')
            if logo_url:
                log.debug("Loading logo: %s..." %
                          logo_url[:50], module="Channels")
                self.download_logo(logo_url)
            else:
                log.debug("No logo available", module="Channels")
                self["logo"].hide()
        else:
            log.error("ERROR: Index %d out of range (0-%d)" %
                      (index, len(self.menu_channels) - 1), module="Channels")

    def update_logo(self, picInfo=None):
        """Update logo pixmap"""
        ptr = self.picload.getData()
        if ptr:
            self["logo"].instance.setScale(1)
            self["logo"].instance.setPixmap(ptr)
            self["logo"].show()
            log.debug("logo displayed", module="Channels")
        else:
            self["logo"].hide()
            log.debug("No logo data, hiding", module="Channels")

    def download_logo(self, url):
        """Download and display channel logo"""
        try:
            try:
                response = urlopen(url, timeout=5)
                try:
                    logo_data = response.read()
                finally:
                    response.close()
            except Exception as e:
                log.error("Error downloading logo: %s" % e, module="Channels")
                self["logo"].hide()
                return

            try:
                from os import close
                temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
                close(temp_fd)
                f = None
                try:
                    f = open(temp_path, 'wb')
                    f.write(logo_data)
                finally:
                    if f:
                        f.close()
            except Exception as e:
                log.error(
                    "Error creating temp file: %s" %
                    e, module="Channels")
                self["logo"].hide()
                return

            # Load with ePicLoad
            self.picload.setPara((80, 50, 1, 1, False, 1, "#00000000"))

            if exists('/var/lib/dpkg/info'):
                # DreamOS
                self.picload.startDecode(temp_path, 0, 0, False)
            else:
                # Python2 images
                self.picload.startDecode(temp_path)

            try:
                unlink(temp_path)
            except BaseException:
                pass
        except Exception as e:
            log.error("Error downloading logo: %s" % e, module="Channels")
            self["logo"].hide()

    def generate_country_bouquet(self, country_code, channels):
        """Generate bouquet for a specific country"""
        try:
            if not channels:
                return False, "No channels for country: %s" % country_code

            tag = "tvgarden"

            # Use prefix from config
            config = get_config()
            prefix = config.get("bouquet_name_prefix", "TVGarden")

            # Create bouquet name: prefix_countrycode
            bouquet_name = "%s_%s" % (prefix.lower(), country_code.lower())
            userbouquet_file = "/etc/enigma2/userbouquet.%s_%s.tv" % (
                tag, bouquet_name)

            valid_count = 0
            with open(userbouquet_file, "w") as f:
                # Use prefix in display name
                f.write("#NAME %s - %s\n" % (prefix, country_code.upper()))
                f.write(
                    "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | %s %s | ---\n" %
                    (prefix, country_code.upper()))
                f.write(
                    "#DESCRIPTION --- | %s %s | ---\n" %
                    (prefix, country_code.upper()))

                for channel in channels:
                    name = channel.get('name', '')
                    stream_url = channel.get(
                        'stream_url') or channel.get('url', '')

                    if not stream_url:
                        continue

                    url_encoded = stream_url.replace(":", "%3a")
                    name_encoded = name.replace(":", "%3a")

                    f.write(
                        "#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n" %
                        (url_encoded, name_encoded))
                    f.write("#DESCRIPTION %s\n" % name)

                    valid_count += 1

            if valid_count == 0:
                return False, "No valid streams for country: %s" % country_code

            self._add_to_bouquets_tv(tag, bouquet_name)
            self._reload_bouquets()

            return True, "Exported %d channels for %s" % (
                valid_count, country_code.upper())

        except Exception as e:
            return False, "Error: %s" % str(e)

    def generate_all_countries_bouquet(self):
        """Generate separate bouquets for each country"""
        try:
            cache = CacheManager()

            # Get all countries
            countries_meta = cache.get_countries_metadata()

            results = []
            for country_code in countries_meta.keys():
                # Load channels for this country
                channels = cache.get_country_channels(country_code)

                if channels:
                    success, message = self.generate_country_bouquet(
                        country_code, channels)
                    results.append((country_code, success, message))

            # Also create a bouquet containing all countries
            if results:
                all_channels = []
                for country_code, success, msg in results:
                    if success:
                        channels = cache.get_country_channels(country_code)
                        if channels:
                            # Limit to 10 for country
                            all_channels.extend(channels[:10])

                if all_channels:
                    self.export_to_bouquet(all_channels, "all_countries")

            return True, "Generated bouquets for %d countries" % len(results)

        except Exception as e:
            return False, "Error generating country bouquets: %s" % str(e)

    def _load_export_settings(self):
        """Load ONLY the export settings actually used in channels browser"""
        try:
            config = get_config()
            self.max_channels_for_bouquet = config.get(
                "max_channels_for_bouquet", 100)
            self.bouquet_name_prefix = config.get(
                "bouquet_name_prefix", "TVGarden")
            log.debug("Local export settings loaded", module="Channels")
        except Exception as e:
            self.max_channels_for_bouquet = 100
            self.bouquet_name_prefix = "TVGarden"
            log.error(
                "Error loading export settings: %s" %
                e, module="Channels")

    def export_current_view(self):
        """Export CURRENTLY VISIBLE channels to bouquet"""
        if not self.menu_channels:
            self.session.open(MessageBox, _("No channels to export"),
                              MessageBox.TYPE_INFO, timeout=2)
            return

        if not self.menu_channels:
            self["key_blue"].setText("")
            self.session.open(MessageBox, _("No channels to export"),
                              MessageBox.TYPE_INFO, timeout=2)
            return

        if self.country_name:
            display_name = self.country_name
            safe_name = self.country_code.lower() if self.country_code else "country"
        elif self.category_name:
            base_name = self.category_name.split(
                ' (')[0] if ' (' in self.category_name else self.category_name
            display_name = base_name
            safe_name = ''.join(c for c in base_name.lower()
                                if c.isalnum() or c == '_')[:30]
        else:
            display_name = _("Channels")
            safe_name = "channels"

        bouquet_name = "%s_%s" % (self.bouquet_name_prefix.lower(), safe_name)

        msg = _("Export {count} channels to bouquet '{name}'?").format(
            count=len(self.menu_channels),
            name=display_name
        )

        self.session.openWithCallback(
            lambda r: self.execute_export(
                bouquet_name,
                display_name) if r else None,
            MessageBox,
            msg,
            MessageBox.TYPE_YESNO)

    def execute_export(self, bouquet_name, display_name):
        """Perform actual export"""
        try:
            success, msg = self.fav_manager.export_to_bouquet(
                self.menu_channels,
                bouquet_name
            )

            self.session.open(
                MessageBox,
                msg,
                MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
                timeout=4
            )

        except Exception as e:
            log.error("Export error: %s" % e, module="Channels")
            self.session.open(
                MessageBox,
                _("Export failed: %s") % str(e),
                MessageBox.TYPE_ERROR,
                timeout=4
            )

    def play_channel(self):
        """Play the selected channel."""
        # 1. Get the correct index from the menu
        menu_idx = self["menu"].getSelectedIndex()
        log.debug("Menu index: %d" % menu_idx, module="Channels")

        if menu_idx is None or menu_idx < 0 or menu_idx >= len(
                self.menu_channels):
            log.error("ERROR: Invalid index %d" % menu_idx, module="Channels")
            return

        # 2. Get the selected channel by index
        selected_channel = self.menu_channels[menu_idx]
        stream_url = selected_channel.get(
            "stream_url") or selected_channel.get("url")

        if not stream_url:
            self["status"].setText(_("No stream URL"))
            return

        # 3. Critical debug info
        log.debug("===== PASSING TO PLAYER =====", module="Channels")
        log.debug(
            "Channel: %s" %
            selected_channel.get('name'),
            module="Channels")
        log.debug("Index: %d" % menu_idx, module="Channels")
        log.debug("Total: %d" % len(self.menu_channels), module="Channels")
        log.debug("URL: %s..." % stream_url[:80], module="Channels")

        # 4. Create a basic service reference
        service_ref = eServiceReference(4097, 0, stream_url)
        service_ref.setName(selected_channel.get("name", "TV Garden"))

        # 5. Pass to player: service_ref, channel list, index
        self.session.open(
            TVGardenPlayer,
            service_ref,
            self.menu_channels,
            menu_idx
        )

    def toggle_favorite(self):
        """Toggle favorite with MessageBox"""
        if not self.current_channel:
            return

        channel_name = self.current_channel.get('name', _('Unknown'))

        if self.fav_manager.is_favorite(self.current_channel):
            self.session.openWithCallback(
                lambda r: self._remove_favorite_confirmation(r),
                MessageBox,
                _("Remove '%s' from favorites?") % channel_name,
                MessageBox.TYPE_YESNO
            )
        else:
            success, message = self.fav_manager.add(self.current_channel)
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
                timeout=3
            )

    def _remove_favorite_confirmation(self, result):
        """Remove if confirmed"""
        if result and self.current_channel:
            success, message = self.fav_manager.remove(self.current_channel)
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
                timeout=3
            )

    def show_info(self):
        """Show channel information"""
        if self.current_channel:
            info = "%s\n\n" % self.current_channel.get('name', 'Unknown')

            desc = self.current_channel.get('description')
            if desc:
                info += "%s\n\n" % desc

            stream_url = self.current_channel.get('stream_url', 'N/A')
            if len(stream_url) > 60:
                info += _("Stream: %s...") % stream_url[:60]
            else:
                info += _("Stream: %s") % stream_url

            self.session.open(MessageBox, info, MessageBox.TYPE_INFO)

    def up(self):
        """Handle up key"""
        self["menu"].up()
        current_index = self["menu"].getSelectedIndex()
        log.debug("Up -> index: %d" % current_index, module="Channels")
        self.update_channel_selection(current_index)

    def down(self):
        """Handle down key"""
        self["menu"].down()
        current_index = self["menu"].getSelectedIndex()
        log.debug("Down -> index: %d" % current_index, module="Channels")
        self.update_channel_selection(current_index)

    def left(self):
        """Handle left key"""
        self["menu"].pageUp()
        current_index = self["menu"].getSelectedIndex()
        log.debug("Left -> index: %d" % current_index, module="Channels")
        self.update_channel_selection(current_index)

    def right(self):
        """Handle right key"""
        self["menu"].pageDown()
        current_index = self["menu"].getSelectedIndex()
        log.debug("Right -> index: %d" % current_index, module="Channels")
        self.update_channel_selection(current_index)

    def exit(self):
        """Exit browser"""
        self.close()
