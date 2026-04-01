#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Favorites Browser
Browse and manage favorite channels
Based on TV Garden Project
"""
from __future__ import print_function
from Screens.TextBox import TextBox
from enigma import eServiceReference
from Screens.ChoiceBox import ChoiceBox
from Components.MenuList import MenuList
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap

from .base import BaseBrowser
from ..utils.cache import CacheManager
from ..utils.config import PluginConfig
from ..utils.favorites import FavoritesManager
from ..helpers import is_valid_stream_url, log
from ..player.iptv_player import TVGardenPlayer
from .. import _, PLUGIN_VERSION


class FavoritesBrowser(BaseBrowser):
    """Browse and manage favorite channels"""

    skin = """
        <screen name="FavoritesBrowser" position="center,center" size="1920,1080" title="TV Garden" backgroundColor="#1a1a2e" flags="wfNoBorder">
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
        dynamic_skin = self.config.load_skin("FavoritesBrowser", self.skin)
        self.skin = dynamic_skin

        BaseBrowser.__init__(self, session)
        self.session = session
        self.fav_manager = FavoritesManager()
        self.cache = CacheManager()
        self.menu_channels = []
        self.current_channel = None
        self["menu"] = MenuList([])
        self['title'] = StaticText(
            "TV Garden %s | by Lululla" %
            PLUGIN_VERSION)
        self["status"] = StaticText(_("Loading favorites..."))
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Play"))
        self["key_yellow"] = StaticText(_("Options"))
        self["key_blue"] = StaticText(_("Export"))
        self["actions"] = ActionMap(["TVGardenActions", "OkCancelActions", "ColorActions", "DirectionActions"], {
            "cancel": self.exit,
            "ok": self.play_channel,
            "red": self.exit,
            "green": self.play_channel,
            "yellow": self.options_favorite,
            "blue": self.export_bouquet,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
        }, -2)
        self.onFirstExecBegin.append(self.load_favorites)

    def load_favorites(self):
        """Load favorites from file"""
        try:
            favorites = self.fav_manager.get_all()
            log.info(
                "Loaded %d favorites" %
                len(favorites), module="Favorites")

            favorites.sort(key=lambda c: c.get('name', '').lower())
            menu_items = []
            self.menu_channels = []

            for idx, channel in enumerate(favorites):
                name = channel.get('name', 'Favorite %d' % (idx + 1))

                # Extract stream URL
                stream_url = channel.get('stream_url') or channel.get('url')

                # Validate URL
                if stream_url and is_valid_stream_url(stream_url):
                    # Add extra info for display
                    extra_info = []
                    if channel.get('country'):
                        extra_info.append(channel['country'])
                    if channel.get('category'):
                        extra_info.append(channel['category'])

                    display_name = name
                    if extra_info:
                        display_name += " [%s]" % ', '.join(extra_info)

                    # Create channel object
                    channel_data = {
                        'name': name,
                        'url': stream_url,
                        'stream_url': stream_url,
                        'logo': channel.get('logo') or channel.get('icon'),
                        'id': channel.get('id', 'fav_%d' % idx),
                        'description': channel.get('description', ''),
                        'group': channel.get('group', ''),
                        'language': channel.get('language', ''),
                        'country': channel.get('country', ''),
                        'is_youtube': False
                    }

                    menu_items.append((display_name, idx))
                    self.menu_channels.append(channel_data)

            self["menu"].setList(menu_items)

            if menu_items:
                self["status"].setText(
                    _("%d favorite channels") %
                    len(menu_items))
                # Select first item
                if self.menu_channels:
                    self.current_channel = self.menu_channels[0]
            else:
                self["status"].setText(_("No favorite channels"))
                self.current_channel = None

        except Exception as e:
            log.error("Error loading favorites: %s" % e, module="Favorites")
            self["status"].setText(_("Error loading favorites"))

    def options_favorite(self):
        """Options menu for yellow button"""
        channel, index = self.get_current_channel()
        if not channel:
            self["status"].setText(_("No channel selected"))
            return

        options = [
            (_("View Channel Info"), "info"),
            (_("Remove from Favorites"), "remove"),
            (_("Clear All Favorites"), "clear_all"),
            (_("Export to Enigma2 Bouquet"), "export_single"),
            (_("Export ALL Database (Single File)"), "export_all_database"),
            (_("Export ALL Database (Multi-File)"), "export_all_hierarchical"),
            (_("Remove Bouquet from Enigma2"), "remove_bouquet"),
        ]

        self.session.openWithCallback(
            self._handle_yellow_option,
            ChoiceBox,
            title=_("Options for: %s") % channel.get('name'),
            list=options
        )

    def _handle_yellow_option(self, result):
        """Handle yellow menu option with MessageBox"""
        if result is None:
            return

        channel, index = self.get_current_channel()
        if not channel:
            return

        option_id = result[1]

        if option_id == "remove":
            self._remove_current_favorite()

        elif option_id == "export_single":
            self.session.openWithCallback(
                lambda r: self._export_single_confirmation(r, channel),
                MessageBox,
                _("Export '%s' to Enigma2 bouquet?") % channel.get('name', ''),
                MessageBox.TYPE_YESNO
            )

        elif option_id == "remove_bouquet":
            self.session.openWithCallback(
                lambda r: self._remove_bouquet_confirmation(r),
                MessageBox,
                _("Remove TV Garden bouquet from Enigma2?"),
                MessageBox.TYPE_YESNO
            )

        elif option_id == "clear_all":
            self.session.openWithCallback(
                lambda r: self._clear_all_confirmation(r),
                MessageBox,
                _("Clear ALL favorites?"),
                MessageBox.TYPE_YESNO
            )

        elif option_id == "export_all_database":
            self.session.openWithCallback(
                self._execute_export_all_database,
                MessageBox,
                _("Export ALL channels from TV Garden database?\nThis may take some time."),
                MessageBox.TYPE_YESNO)

        elif option_id == "export_all_hierarchical":
            self.session.openWithCallback(
                lambda r: self._execute_export_all_hierarchical(r),
                MessageBox,
                _("Export ALL channels with multi-file structure?\nThis will create smaller bouquet files for better performance."),
                MessageBox.TYPE_YESNO)

        elif option_id == "info":
            self._show_channel_info(channel)

    def _export_single_confirmation(self, result, channel):
        """Export single after confirmation"""
        if result:
            success, message = self.fav_manager.export_single_channel(channel)
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
                timeout=3
            )
            self["status"].setText(message)

    def _remove_bouquet_confirmation(self, result):
        """Remove bouquet after confirmation"""
        if result:
            success, message = self.fav_manager.remove_bouquet()
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
                timeout=3
            )
            self["status"].setText(message)

    def _remove_current_favorite(self):
        """Remove favorite with MessageBox"""
        channel, index = self.get_current_channel()
        if not channel:
            return

        channel_name = channel.get('name', _('Unknown'))

        self.session.openWithCallback(
            lambda r: self._execute_removal(r, channel),
            MessageBox,
            _("Remove '%s' from favorites?") % channel_name,
            MessageBox.TYPE_YESNO
        )

    def _execute_removal(self, result, channel):
        """Execute removal after confirmation"""
        if not result:
            return

        success, message = self.fav_manager.remove(channel)

        if success:
            self.load_favorites()
            self["status"].setText(_("%d favorites") % len(self.menu_channels))

        self.session.open(
            MessageBox,
            message,
            MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
            timeout=3
        )

    def _execute_export_all_database(self, result):
        """Execute export of all database channels (single file)"""
        if not result:
            return

        self["status"].setText(_("Loading all channels..."))

        success, message = self.fav_manager.export_all_channels()

        self.session.open(
            MessageBox,
            message,
            MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
            timeout=5
        )

        if success:
            self["status"].setText(_("Database exported successfully"))
        else:
            self["status"].setText(_("Export failed"))

    def _execute_export_all_hierarchical(self, result):
        """Execute export of all database channels with hierarchical structure"""
        if not result:
            return

        self["status"].setText(_("Creating hierarchical structure..."))

        success, message = self.fav_manager.export_all_channels_hierarchical()

        self.session.open(
            MessageBox,
            message,
            MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
            timeout=8
        )

        if success:
            self["status"].setText(_("Hierarchical export completed"))
        else:
            self["status"].setText(_("Export failed"))

    def get_current_channel(self):
        """Get currently selected channel"""
        menu_idx = self["menu"].getSelectedIndex()
        if menu_idx is not None and 0 <= menu_idx < len(self.menu_channels):
            return self.menu_channels[menu_idx], menu_idx

        return None, -1

    def play_channel(self):
        """Play selected favorite channel"""
        channel, channel_idx = self.get_current_channel()
        if not channel:
            self["status"].setText(_("No channel selected"))
            return

        stream_url = channel.get('stream_url') or channel.get('url')
        if not stream_url:
            self["status"].setText(_("No stream URL available"))
            return

        try:
            # Create service reference
            url_encoded = stream_url.replace(":", "%3a")
            name_encoded = channel['name'].replace(":", "%3a")
            ref_str = "4097:0:0:0:0:0:0:0:0:0:%s:%s" % (
                url_encoded, name_encoded)

            service_ref = eServiceReference(ref_str)
            service_ref.setName(channel['name'])

            # Open player with favorites list
            log.info("Playing: %s" % channel['name'], module="Favorites")
            self.session.open(
                TVGardenPlayer,
                service_ref,
                self.menu_channels,
                channel_idx)

        except Exception as e:
            log.error("Player error: %s" % e, module="Favorites")
            self.session.open(MessageBox,
                              _("Error opening player"),
                              MessageBox.TYPE_ERROR)

    def export_bouquet(self):
        """Export all favorites to Enigma2 bouquet"""
        if not self.menu_channels:
            self.session.open(
                MessageBox,
                _("No favorites to export"),
                MessageBox.TYPE_INFO,
                timeout=3
            )
            return

        self.session.openWithCallback(
            self._export_all_confirmation,
            MessageBox,
            _("Export ALL %d favorites to Enigma2 bouquet?") % len(
                self.menu_channels),
            MessageBox.TYPE_YESNO)

    def _export_all_confirmation(self, result):
        """Handle export confirmation"""
        if result:
            success, message = self.fav_manager.export_to_bouquet(
                self.menu_channels)
            self["status"].setText(message)
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_INFO if success else MessageBox.TYPE_ERROR,
                timeout=4
            )

    def _show_channel_info(self, channel):
        """Show detailed channel info"""
        try:
            info_text = "=== %s ===\n\n" % channel.get('name', 'Unknown')

            if channel.get('description'):
                info_text += "Description: %s\n" % channel['description']

            if channel.get('country'):
                info_text += "Country: %s\n" % channel['country']

            if channel.get('category'):
                info_text += "Category: %s\n" % channel['category']

            if channel.get('language'):
                info_text += "Language: %s\n" % channel['language']

            if channel.get('group'):
                info_text += "Group: %s\n" % channel['group']

            stream_url = channel.get('stream_url') or channel.get('url', '')
            if stream_url:
                info_text += "\nStream URL:\n"
                if len(stream_url) > 150:
                    info_text += "%s...\n...%s" % (
                        stream_url[:100], stream_url[-50:])
                else:
                    info_text += stream_url

            self.session.open(
                TextBox,
                text=info_text,
                title=_("Channel Information"),
                # pigless=True
            )

        except Exception as e:
            log.error("Error showing channel info: %s" % e, module="Favorites")

    def _clear_all_confirmation(self, result):
        """Clear all after confirmation"""
        if not result:
            return

        success, message = self.fav_manager.clear_all()
        if success:
            self.load_favorites()

            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_INFO,
                timeout=3
            )
        else:
            self.session.open(
                MessageBox,
                message,
                MessageBox.TYPE_ERROR,
                timeout=3
            )

    def up(self):
        """Handle up key"""
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
