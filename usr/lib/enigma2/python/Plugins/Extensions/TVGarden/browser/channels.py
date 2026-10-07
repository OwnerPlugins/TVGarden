#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Channels Browser
List and play IPTV channels
Based on TV Garden Project

[TVGarden patch] Supporto multi-sorgente (tv / webcams).
Il browser accetta `media_type` e lo propaga a:
- cache.get_country_channels()
- cache.get_category_channels()
"""
import os
import tempfile
from os import unlink
from os.path import exists
from enigma import ePicLoad, eServiceReference
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap

from ..helpers import (
    is_valid_stream_url,
    extract_stream_url,
    get_channel_language,
    bouquet_service_lines,
    add_bouquet_to_index,
    encode_bouquet_text,
    log
)
from .base import BaseBrowser
from ..utils.config import PluginConfig, get_config
from ..utils.cache import CacheManager, open_url
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
            <widget source="title" position="44,57" size="1770,60" font="Regular;48" foregroundColor="#ffff00" zPosition="5" render="Label" backgroundColor="#ff000000" />

            <!-- Status -->
            <widget source="status" render="Label" position="921,976" size="976,61" font="Regular;32" halign="center" foregroundColor="#3333ff" transparent="1" alphatest="blend" />

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
                 category_id=None, category_name=None, media_type="tv"):
        # [TVGarden patch] media_type: "tv" (default) oppure "webcams"
        self.media_type = media_type

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

        # [TVGarden patch] Prefisso per il titolo in base al media_type
        media_label = "Webcams" if self.media_type == "webcams" else "Channels"

        title = ""
        if country_name:
            title = "%s - %s" % (media_label, str(country_name))
        elif category_name:
            title = "%s - %s" % (media_label, str(category_name))

        self.setTitle(title)

        self._load_export_settings()

        self["menu"] = MenuList([])
        self['title'] = StaticText(
            "TV Garden %s | by Lululla" % PLUGIN_VERSION)
        self["status"] = StaticText(_("Loading channels..."))
        self["logo"] = Pixmap()
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Play"))
        self["key_yellow"] = StaticText(_("Favorite"))
        self["key_blue"] = StaticText("")

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"], {
            "cancel": self.exit,
            "ok": self.play_channel,
            "red": self.exit,
            "green": self.play_channel,
            "yellow": self.toggle_favorite,
            "blue": self.export_current_view,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
            "menu": self.channel_menu,
        }, -2)

        self.show_logos = self.config.get("show_logos", True)
        self.logo_request = 0
        self.logo_temp_path = None

        self.picload = ePicLoad()
        try:
            # DreamOS: keep the connection object alive
            self.picload_conn = self.picload.PictureData.connect(
                self.update_logo)
        except AttributeError:
            self.picload_conn = None
            self.picload.PictureData.get().append(self.update_logo)

        self["menu"].onSelectionChanged.append(self.onSelectionChanged)
        self.onFirstExecBegin.append(self.load_channels)
        self.onClose.append(self.cleanup)

    def cleanup(self):
        """Release picload and temp files"""
        self.logo_request += 1
        self._remove_logo_temp()
        try:
            if self.picload_conn is None:
                self.picload.PictureData.get().remove(self.update_logo)
        except Exception:
            pass
        self.picload_conn = None

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

        if self.menu_channels and get_config().get("export_enabled", True):
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

            cache_enabled = config.get("cache_enabled", True)
            force_refresh_browsing = config.get(
                "force_refresh_browsing", False)

            channels = []
            if self.country_code:
                log.debug(
                    "Loading country channels: %s (media_type=%s)" %
                    (self.country_code, self.media_type), module="Channels")

                # [TVGarden patch] Passiamo media_type
                if hasattr(self.cache, 'get_country_channels'):
                    try:
                        channels = self.cache.get_country_channels(
                            self.country_code,
                            media_type=self.media_type,
                            force_refresh=force_refresh_browsing
                        )
                    except TypeError:
                        # Retrocompatibilità
                        try:
                            channels = self.cache.get_country_channels(
                                self.country_code,
                                force_refresh=force_refresh_browsing
                            )
                        except TypeError:
                            channels = self.cache.get_country_channels(
                                self.country_code)
                else:
                    channels = []

            elif self.category_id:
                log.debug(
                    "Loading category channels: %s (media_type=%s)" %
                    (self.category_id, self.media_type), module="Channels")

                # [TVGarden patch] Passiamo media_type
                if hasattr(self.cache, 'get_category_channels'):
                    try:
                        channels = self.cache.get_category_channels(
                            self.category_id,
                            media_type=self.media_type,
                            force_refresh=force_refresh_browsing
                        )
                    except TypeError:
                        try:
                            channels = self.cache.get_category_channels(
                                self.category_id,
                                force_refresh=force_refresh_browsing
                            )
                        except TypeError:
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

            self.channels = channels

            menu_items = []
            self.menu_channels = []

            youtube_count = 0
            valid_count = 0
            problematic_count = 0
            skipped_count = 0

            for idx, channel in enumerate(channels):
                if max_channels > 0 and idx >= max_channels:
                    log.debug(
                        "Stopped at %d channels (limit: %d)" %
                        (idx, max_channels), module="Channels")
                    skipped_count = len(channels) - idx
                    break

                name = channel.get("name", "Channel %d" % (idx + 1))

                stream_url, found_in, is_youtube = extract_stream_url(channel)

                if is_youtube:
                    youtube_count += 1

                if not stream_url:
                    log.warning(
                        "✗ No stream URL: %s" %
                        name, module="Channels")
                    continue

                if not is_valid_stream_url(stream_url):
                    log.warning(
                        "✗ Invalid URL format: %s" %
                        name, module="Channels")
                    continue

                stream_url_to_use = stream_url

                channel_data = {
                    "name": str(name or ""),
                    "url": stream_url_to_use,
                    "stream_url": stream_url_to_use,
                    "logo": channel.get("logo") or channel.get("icon") or channel.get("image"),
                    "id": str(channel.get("nanoid", "ch_%d" % idx)),
                    "description": str(channel.get("description", "")),
                    "group": str(channel.get("group", "")),
                    "language": get_channel_language(channel),
                    "country": str(channel.get("country", "")),
                    "found_in": str(found_in),
                    "original_index": idx,
                    "is_youtube": is_youtube,
                    "media_type": self.media_type,  # [TVGarden patch]
                }

                self.menu_channels.append(channel_data)

                valid_count += 1
                log.debug("✓ Added: %s" % name, module="Channels")

            self.menu_channels.sort(key=lambda c: c['name'].lower())
            menu_items = []
            for idx, c in enumerate(self.menu_channels):
                display_name = c['name']
                if c.get('is_youtube', False):
                    display_name = "[YT] " + display_name
                menu_items.append((display_name, idx))

            self["menu"].setList(menu_items)

            if menu_items and config.get("export_enabled", True):
                self["key_blue"].setText(_("Export"))
            else:
                self["key_blue"].setText("")

            if menu_items:
                selected_idx = menu_items[0][1]
                if 0 <= selected_idx < len(self.menu_channels):
                    self.current_channel = self.menu_channels[selected_idx]
                    log.debug(
                        "First channel: %s" %
                        self.current_channel['name'],
                        module="Channels")
                    self.update_channel_selection(0)

            cache_info = ""
            if force_refresh_browsing:
                cache_info = _(" [Fresh data]")
            elif not cache_enabled:
                cache_info = _(" [Cache disabled]")

            if max_channels > 0 and len(channels) > max_channels:
                msg = _("Showing {shown} of {total} channels")
                status_text = msg.format(
                    shown=valid_count,
                    total=len(channels)
                )
            else:
                status_text = _("Found %d playable channels") % valid_count

            status_text += cache_info

            if youtube_count > 0:
                status_text += " " + _("(%d YouTube)") % youtube_count

            if problematic_count > 0:
                status_text += " " + \
                    _("(filtered %d problematic)") % problematic_count

            if skipped_count > 0 and max_channels > 0:
                status_text += " " + _("(limited to first %d)") % max_channels

            self["status"].setText(status_text)

            log.info(
                "Playable: %d, YouTube: %d, Filtered problematic: %d, Config limit: %d, Skipped by limit: %d" %
                (valid_count,
                 youtube_count,
                 problematic_count,
                 max_channels,
                 skipped_count),
                module="Channels")

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
            if logo_url and self.show_logos:
                self.download_logo(logo_url)
            else:
                self.logo_request += 1
                self["logo"].hide()
        else:
            log.error("ERROR: Index %d out of range (0-%d)" %
                      (index, len(self.menu_channels) - 1), module="Channels")

    def _remove_logo_temp(self):
        if self.logo_temp_path:
            try:
                unlink(self.logo_temp_path)
            except OSError:
                pass
            self.logo_temp_path = None

    def update_logo(self, picInfo=None):
        """ePicLoad finished decoding: show the logo, drop the temp file"""
        ptr = self.picload.getData()
        if ptr and self["logo"].instance:
            self["logo"].instance.setPixmap(ptr)
            self["logo"].show()
        else:
            self["logo"].hide()
        self._remove_logo_temp()

    def download_logo(self, url):
        """Download the logo in a worker thread, then decode it"""
        self.logo_request += 1
        request_id = self.logo_request
        self["logo"].hide()
        try:
            from twisted.internet import threads
            d = threads.deferToThread(open_url, url, 5)
            d.addCallback(self._logo_downloaded, request_id)
            d.addErrback(self._logo_failed)
        except Exception as e:
            log.error("Error downloading logo: %s" % e, module="Channels")

    def _logo_failed(self, failure):
        log.debug("Logo not available: %s" %
                  failure.getErrorMessage(), module="Channels")

    def _logo_downloaded(self, logo_data, request_id):
        # Ignore stale answers (selection changed or screen closed)
        if request_id != self.logo_request or not logo_data:
            return
        try:
            self._remove_logo_temp()
            temp_fd, temp_path = tempfile.mkstemp(suffix='.png')
            with os.fdopen(temp_fd, 'wb') as f:
                f.write(logo_data)
            # The file is removed in update_logo, once decoding is done
            self.logo_temp_path = temp_path

            size = self["logo"].instance.size()
            self.picload.setPara(
                (size.width(), size.height(), 1, 1, False, 1, "#00000000"))
            if exists('/var/lib/dpkg/info'):
                self.picload.startDecode(temp_path, 0, 0, False)
            else:
                self.picload.startDecode(temp_path)
        except Exception as e:
            log.error("Error decoding logo: %s" % e, module="Channels")
            self._remove_logo_temp()
            self["logo"].hide()

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
        if not get_config().get("export_enabled", True):
            return
        if not self.menu_channels:
            self.session.open(
                MessageBox,
                _("No channels to export"),
                MessageBox.TYPE_INFO,
                timeout=2)
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

        bouquet_name = "tvgarden_%s" % safe_name
        userbouquet_file = "/etc/enigma2/userbouquet.%s.tv" % bouquet_name

        msg = _("Export {count} channels to bouquet '{name}'?").format(
            count=len(self.menu_channels), name=display_name)
        self.session.openWithCallback(
            lambda r: self._do_export(
                userbouquet_file,
                display_name,
                bouquet_name) if r else None,
            MessageBox,
            msg,
            MessageBox.TYPE_YESNO)

    def _do_export(self, userbouquet_file, display_name, bouquet_name):
        try:
            channels = self.menu_channels
            if self.max_channels_for_bouquet > 0:
                channels = channels[:self.max_channels_for_bouquet]

            prefix = encode_bouquet_text(self.bouquet_name_prefix)
            title = encode_bouquet_text(display_name)
            exported = 0
            with open(userbouquet_file, "w") as f:
                f.write("#NAME %s - %s\n" % (prefix, title))
                f.write(
                    "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | %s %s | ---\n" %
                    (prefix, title))
                f.write("#DESCRIPTION --- | %s %s | ---\n" % (prefix, title))

                for ch in channels:
                    stream_url = ch.get('stream_url') or ch.get('url')
                    # YouTube pages cannot be played from a bouquet
                    if not stream_url or ch.get('is_youtube'):
                        continue
                    f.write(
                        bouquet_service_lines(
                            stream_url, ch.get(
                                'name', '')))
                    exported += 1

            if exported == 0:
                try:
                    unlink(userbouquet_file)
                except OSError:
                    pass
                self.session.open(
                    MessageBox,
                    _("No valid streams found"),
                    MessageBox.TYPE_ERROR,
                    timeout=3)
                return

            add_bouquet_to_index(
                "userbouquet.%s.tv" % bouquet_name,
                get_config().get("list_position", "bottom"))

            from enigma import eDVBDB
            eDVBDB.getInstance().reloadBouquets()
            self.session.open(
                MessageBox, _("Exported %d channels to '%s'") %
                (exported, display_name), MessageBox.TYPE_INFO, timeout=4)

        except Exception as e:
            log.error("Export error: %s" % e, module="Channels")
            self.session.open(
                MessageBox, _("Export error: %s") %
                str(e), MessageBox.TYPE_ERROR, timeout=4)

    def play_channel(self):
        """Play the selected channel."""
        menu_idx = self["menu"].getSelectedIndex()

        if menu_idx is None or menu_idx < 0 or menu_idx >= len(
                self.menu_channels):
            log.error("ERROR: Invalid index %s" % menu_idx, module="Channels")
            return

        selected_channel = self.menu_channels[menu_idx]
        stream_url = selected_channel.get(
            "stream_url") or selected_channel.get("url")

        if not stream_url:
            self["status"].setText(_("No stream URL"))
            return

        log.debug("===== PASSING TO PLAYER =====", module="Channels")
        log.debug(
            "Channel: %s" %
            selected_channel.get('name'),
            module="Channels")
        log.debug("Index: %d" % menu_idx, module="Channels")
        log.debug("Total: %d" % len(self.menu_channels), module="Channels")
        log.debug("URL: %s..." % stream_url[:80], module="Channels")

        service_ref = eServiceReference(4097, 0, stream_url)
        service_ref.setName(selected_channel.get("name", "TV Garden"))

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
        """Handle up key (logo update comes from onSelectionChanged)"""
        self["menu"].up()

    def down(self):
        """Handle down key"""
        self["menu"].down()

    def left(self):
        """Handle left key"""
        self["menu"].pageUp()

    def right(self):
        """Handle right key"""
        self["menu"].pageDown()

    def exit(self):
        """Exit browser"""
        self.close()
