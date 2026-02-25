#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Settings Screen
Plugin configuration interface
Based on TV Garden Project
"""
from __future__ import print_function
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.TextBox import TextBox
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.ConfigList import ConfigListScreen
from Components.config import (
    ConfigInteger,
    ConfigSelection,
    ConfigYesNo,
    ConfigText,
    ConfigNothing,
    getConfigListEntry,
    NoSave
)
from .. import _, USER_AGENT
from ..helpers import log
from .config import get_config
from .update_manager import UpdateManager


class LogViewerScreen(TextBox):
    skin = """
        <screen name="LogViewerScreen" position="center,center" size="1280,720" title="TV Garden Logs" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/redbutton.png" position="32,688" size="140,6" alphatest="blend" zPosition="1" transparent="1" />
            <!--
            <ePixmap name="" position="0,0" size="1280,720" alphatest="blend" zPosition="-1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/hd/background.png" scale="1" />
            -->
            <widget name="background" position="0,0" size="1280,720" backgroundColor="#1a1a2e" />
            <ePixmap name="" position="1041,628" size="200,80" alphatest="blend" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/logo.png" scale="1" transparent="1" />
            <widget name="key_red" position="33,649" zPosition="1" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend"/>
            <widget name="text" position="28,45" size="1220,570" font="Console;24" itemHeight="50" backgroundColor="#16213e" transparent="0" />
            <eLabel backgroundColor="#001a2336" position="5,639" size="1270,60" zPosition="-80" />
            <eLabel name="" position="19,36" size="1235,585" zPosition="-1" backgroundColor="#00171a1c" foregroundColor="#00171a1c" />
        </screen>
    """

    def __init__(self, session, max_lines=100):
        self.config = get_config()
        dynamic_skin = self.config.load_skin("LogViewerScreen", self.skin)
        self.skin = dynamic_skin

        # Get log contents
        log_contents = log.get_log_contents(max_lines=max_lines)
        if not log_contents or "Log file not found" in log_contents:
            log_contents = _("Log file is empty or not found")

        # Initialize TextBox with log contents
        TextBox.__init__(
            self,
            session,
            text=log_contents,
            title=_("TV Garden Logs"))

        self["key_red"] = StaticText(_("Close"))
        self["actions"] = ActionMap(
            [
                "SetupActions",
                "ColorActions",
                "DirectionActions"
            ],
            {
                "cancel": self.close,
                "red": self.close,
                "ok": self.close,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
                "pageUp": self.pageUp,
                "pageDown": self.pageDown,
            }, -2
        )

    def pageUp(self):
        """Scroll up"""
        self["text"].pageUp()

    def pageDown(self):
        """Scroll down"""
        self["text"].pageDown()

    def close(self):
        """Close the log viewer"""
        TextBox.close(self)


class TVGardenSettings(ConfigListScreen, Screen):
    """Settings screen using Enigma2's config system"""

    skin = """
        <screen name="TVGardenSettings" position="center,center" size="1280,720" title="TV Garden Settings" backgroundColor="#1a1a2e" flags="wfNoBorder">
            <ePixmap pixmap="skin_default/buttons/red.png" position="33,650" size="140,40" alphatest="blend" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="174,650" size="140,40" alphatest="blend" />
            <!--
            <ePixmap name="" position="0,0" size="1280,720" alphatest="blend" zPosition="-1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/images/hd/background.png" scale="1" />
            -->
            <widget name="background" position="0,0" size="1280,720" backgroundColor="#1a1a2e" />
            <ePixmap name="" position="1039,531" size="200,80" alphatest="blend" zPosition="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/TVGarden/icons/logo.png" scale="1" transparent="1" />
            <widget name="key_red" position="33,649" zPosition="1" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend" />
            <widget name="key_green" position="174,650" zPosition="1" size="140,40" font="Regular;20" foregroundColor="#3333ff" halign="center" valign="center" transparent="1" alphatest="blend" />
            <widget name="config" position="28,116" size="680,474" scrollbarMode="showOnDemand" backgroundColor="#16213e" />
            <widget name="status" position="603,643" size="648,50" font="Regular; 22" halign="center" foregroundColor="#3333ff" transparent="1" />
            <eLabel backgroundColor="#001a2336" position="5,639" size="1270,60" zPosition="-80" />
            <eLabel name="" position="24,101" size="694,502" zPosition="-1" backgroundColor="#00171a1c" foregroundColor="#00171a1c" />
            <widget source="session.VideoPicture" render="Pig" position="739,140" zPosition="19" size="520,308" backgroundColor="transparent" transparent="0" />
        </screen>
    """

    def __init__(self, session):
        self.config = get_config()
        dynamic_skin = self.config.load_skin("TVGardenSettings", self.skin)
        self.skin = dynamic_skin

        Screen.__init__(self, session)
        self.onChangedEntry = []
        self.setup_title = (_("TV Garden Settings"))
        self.list = []
        ConfigListScreen.__init__(
            self,
            self.list,
            session=session,
            on_change=self.changedEntry)
        self["key_red"] = StaticText(_("Back"))
        self["key_green"] = StaticText(_("Save"))
        self["status"] = StaticText(_("Set options"))
        self["actions"] = ActionMap(
            ["SetupActions", "ColorActions", "DirectionActions"],
            {
                "cancel": self.cancel,
                "green": self.save,
                "ok": self.handle_ok,
                "up": self.keyUp,
                "down": self.keyDown,
                "left": self.keyLeft,
                "right": self.keyRight,
            }, -2
        )

        # ========= NETWORK =========
        self.cfg_user_agent = ConfigText(
            default=self.config.get("user_agent", USER_AGENT),
            fixed_size=False
        )

        # NOTA: connection_timeout è utilizzato in:
        # - helpers.py: funzione download_url()
        # - api_manager.py: richieste HTTP
        # - cache.py: operazioni di rete

        self.cfg_connection_timeout = ConfigInteger(
            default=self.config.get("connection_timeout", 30),
            limits=(10, 300)
        )
        self.initConfig()
        self.createSetup()
        self.onChangedEntry.append(self.updateStatus)
        self.onLayoutFinish.append(self.__layoutFinished)

    def __layoutFinished(self):
        self.setTitle(self.setup_title)

    def updateStatus(self):
        current = self["config"].getCurrent()
        if current:
            current_text = current[0]
            config_item = current[1]

            if isinstance(config_item, ConfigNothing) or "===" in current_text:
                self["status"].setText(_("Set options"))
            else:
                self["status"].setText(_("Editing: %s") % current_text)
        else:
            self["status"].setText(_("Set options"))

    def changedEntry(self):
        self.item = self["config"].getCurrent()
        for x in self.onChangedEntry:
            x()

        try:
            if isinstance(
                    self["config"].getCurrent()[1],
                    ConfigYesNo) or isinstance(
                    self["config"].getCurrent()[1],
                    ConfigSelection):
                self.createSetup()
        except BaseException:
            pass

    def getCurrentEntry(self):
        return self["config"].getCurrent() and self["config"].getCurrent()[
            0] or ""

    def getCurrentValue(self):
        return self["config"].getCurrent() and str(
            self["config"].getCurrent()[1].getText()) or ""

    def apply_logging_settings(self):
        """Apply logging settings immediately"""
        try:
            log_level = self.config.get("log_level", "INFO")
            log.set_level(log_level)
            log_to_file = self.config.get("log_to_file", True)
            log.enable_file_logging(log_to_file)
            log.info(
                "Logging settings applied: level=%s, file=%s" %
                (log_level, log_to_file), "Settings")
        except Exception as e:
            log.error(
                "Failed to apply logging settings: %s" %
                e, module="Settings")

    def _reset_action_selections(self):
        """Reset action selections to default"""
        for i, entry in enumerate(self["config"].list):
            display_name = entry[0]
            config_item = entry[1]

            if display_name in [
                    _("View Log File"),
                    _("Clear Log Files Now"),
                    _("Check for Updates")]:
                if hasattr(config_item, 'value'):
                    config_item.value = config_item.choices[0][0] if config_item.choices else ""

        self["config"].invalidateCurrent()

    def handle_ok(self):
        """Handle OK button based on current selection"""
        current = self["config"].getCurrent()
        if not current:
            return

        display_name = current[0]
        config_item = current[1]

        if "===" in display_name or isinstance(config_item, ConfigNothing):
            return

        log.debug("OK pressed on: %s" % display_name, module="Settings")

        if display_name == _("View Log File"):
            self._execute_view_logs()
            self._reset_action_selections()
            return
        elif display_name == _("Clear Log Files Now"):
            self.clear_logs()
            self._reset_action_selections()
            return
        elif display_name == _("Check for Updates"):
            self.check_for_updates()
            self._reset_action_selections()
            return
        elif isinstance(config_item, ConfigNothing):
            return

    def _execute_view_logs(self):
        """Execute view logs directly"""
        try:
            self.session.open(LogViewerScreen)
        except Exception as e:
            log.error("Error opening log viewer: %s" % e, module="Settings")

    def clear_logs(self):
        """Clear log files"""
        try:
            self.session.openWithCallback(
                self._clear_logs_callback,
                MessageBox,
                _("Are you sure you want to clear all log files?"),
                MessageBox.TYPE_YESNO
            )
        except Exception as e:
            self["status"].setText(_("Error: %s") % str(e))

    def _clear_logs_callback(self, result):
        """Callback dopo clear logs"""
        if result:
            try:
                log.clear_logs()
                self["status"].setText(_("Logs cleared"))
                self.session.open(
                    MessageBox,
                    _("Log files cleared successfully"),
                    MessageBox.TYPE_INFO,
                    timeout=3
                )
            except Exception as e:
                self.session.open(
                    MessageBox,
                    _("Error clearing logs: %s") % str(e),
                    MessageBox.TYPE_ERROR
                )

    def check_for_updates(self):
        """Check for updates from settings"""
        log.debug("check_for_updates called from settings", module="Settings")
        UpdateManager.check_for_updates(self.session, self["status"])

    def initConfig(self):
        """Initialize all configuration objects"""
        # ========= PLAYER =========
        self.cfg_player = ConfigSelection(
            default=self.config.get("player", "auto"),
            choices=[
                ("auto", _("Auto")),
                ("exteplayer3", _("ExtePlayer3")),
                ("gstplayer", _("GStreamer"))
            ]
        )

        # ========= DISPLAY =========
        # self.cfg_skin = ConfigSelection(
        #     default=self.config.get("skin", "auto"),
        #     choices=[
        #         ("auto", _("Auto")),
        #         ("hd", _("HD")),
        #         ("fhd", _("FHD")),
        #         ("wqhd", _("WQHD"))
        #     ]
        # )

        self.cfg_show_flags = ConfigYesNo(
            default=self.config.get("show_flags", True)
        )

        self.cfg_show_logos = ConfigYesNo(
            default=self.config.get("show_logos", False)
        )

        # ========= BROWSER =========
        self.cfg_max_channels = ConfigSelection(
            default=self.config.get("max_channels", 500),
            choices=[
                (100, _("100 channels")),
                (250, _("250 channels")),
                (500, _("500 channels")),
                (1000, _("1000 channels")),
                (0, _("All channels"))
            ]
        )

        self.cfg_max_channels_for_sub_bouquet = ConfigSelection(
            default=self.config.get("max_channels_for_sub_bouquet", 500),
            choices=[
                (100, _("100 channels")),
                (250, _("250 channels")),
                (500, _("500 channels")),
                (1000, _("1000 channels")),
                (2000, _("2000 channels")),
                (5000, _("5000 channels"))
            ]
        )

        self.cfg_default_view = ConfigSelection(
            default=self.config.get("default_view", "countries"),
            choices=[
                ("countries", _("Countries")),
                ("categories", _("Categories")),
                ("favorites", _("Favorites"))
            ]
        )

        # ========= FAVORITES =========
        # self.cfg_favorites_autosave = ConfigYesNo(
        #     default=self.config.get("favorites_autosave", True)
        # )

        # self.cfg_max_favorites = ConfigInteger(
        #     default=self.config.get("max_favorites", 100),
        #     limits=(10, 500)
        # )

        # ========= SEARCH =========
        self.cfg_search_max_results = ConfigInteger(
            default=self.config.get("search_max_results", 200),
            limits=(10, 1000)
        )

        # ========= EXPORT =========
        self.cfg_export_enabled = ConfigYesNo(
            default=self.config.get("export_enabled", True)
        )

        self.cfg_max_channels_for_bouquet = ConfigSelection(
            default=self.config.get("max_channels_for_bouquet", 500),
            choices=[
                (50, _("50 channels")),
                (100, _("100 channels")),
                (250, _("250 channels")),
                (500, _("500 channels")),
                (1000, _("1000 channels")),
                (0, _("All channels"))
            ]
        )

        self.cfg_bouquet_name_prefix = ConfigText(
            default=self.config.get("bouquet_name_prefix", "TVGarden"),
            fixed_size=False
        )

        self.cfg_list_position = ConfigSelection(
            default=self.config.get("list_position", "bottom"),
            choices=[
                ("top", _("Top")),
                ("bottom", _("Bottom"))
            ]
        )

        # ========= PERFORMANCE =========
        self.cfg_use_hardware_acceleration = ConfigYesNo(
            default=self.config.get("use_hardware_acceleration", True)
        )

        self.cfg_buffer_size = ConfigSelection(
            default=self.config.get("buffer_size", 2048),
            choices=[
                (512, _("512 KB")),
                (1024, _("1 MB")),
                (2048, _("2 MB")),
                (4096, _("4 MB")),
                (8192, _("8 MB"))
            ]
        )

        self.cfg_memory_optimization = ConfigYesNo(
            default=self.config.get("memory_optimization", True)
        )

        # ========= NETWORK =========
        self.cfg_user_agent = ConfigText(
            default=self.config.get("user_agent", USER_AGENT),
            fixed_size=False
        )

        self.cfg_connection_timeout = ConfigInteger(
            default=self.config.get("connection_timeout", 30),
            limits=(10, 300)
        )

        # ========= CACHE =========
        self.cfg_cache_enabled = ConfigYesNo(
            default=self.config.get("cache_enabled", True)
        )

        self.cfg_cache_size = ConfigInteger(
            default=self.config.get("cache_size", 500),
            limits=(10, 5000)
        )

        self.cfg_force_refresh_export = ConfigYesNo(
            default=self.config.get("force_refresh_export", False)
        )

        self.cfg_force_refresh_browsing = ConfigYesNo(
            default=self.config.get("force_refresh_browsing", False)
        )

        self.cfg_refresh_method = ConfigSelection(
            default=self.config.get("refresh_method", "clear_cache"),
            choices=[
                ("clear_cache", _("Clear Cache")),
                ("force_refresh", _("Force Refresh"))
            ]
        )

        # ========= LOGGING =========
        self.cfg_log_level = ConfigSelection(
            default=self.config.get("log_level", "INFO"),
            choices=[
                ("DEBUG", _("Debug")),
                ("INFO", _("Info")),
                ("WARNING", _("Warning")),
                ("ERROR", _("Error")),
                ("CRITICAL", _("Critical"))
            ]
        )

        self.cfg_log_to_file = ConfigYesNo(
            default=self.config.get("log_to_file", True)
        )

        # ========= ACTIONS =========
        self.cfg_check_for_updates = ConfigSelection(
            choices=[("check", _("Press OK to check for updates"))],
            default="check"
        )

        self.cfg_view_log_file = ConfigSelection(
            choices=[("open", _("Press OK to view logs"))],
            default="open"
        )

        self.cfg_clear_logs_now = ConfigSelection(
            choices=[("clear", _("Press OK to clear logs"))],
            default="clear"
        )

    def createSetup(self):
        """Create the setup list with organized sections"""
        self.list = []

        # ============ DISPLAY SETTINGS ============
        section = _('=== Browser Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(
            getConfigListEntry(
                _("Default View"),
                self.cfg_default_view))
        self.list.append(
            getConfigListEntry(
                _("Max channels for country"),
                self.cfg_max_channels))
        self.list.append(
            getConfigListEntry(
                _("Show Flags"),
                self.cfg_show_flags))
        self.list.append(
            getConfigListEntry(
                _("Show Logos"),
                self.cfg_show_logos))

        # ============ PLAYER SETTINGS ============
        section = _('=== Player Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(getConfigListEntry(_("Player"), self.cfg_player))

        # ============ EXPORT SETTINGS ============
        section = _('=== Export Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(
            getConfigListEntry(
                _("Enable Export"),
                self.cfg_export_enabled))
        if self.cfg_export_enabled.value:
            self.list.append(
                getConfigListEntry(
                    _("List Position"),
                    self.cfg_list_position))
            self.list.append(
                getConfigListEntry(
                    _("Bouquet Name Prefix"),
                    self.cfg_bouquet_name_prefix))
            self.list.append(
                getConfigListEntry(
                    _("Max Channels for Bouquet"),
                    self.cfg_max_channels_for_bouquet))
            self.list.append(
                getConfigListEntry(
                    _("Max Channels for Sub-Bouquet"),
                    self.cfg_max_channels_for_sub_bouquet))

        # ============ PERFORMANCE SETTINGS ============
        section = _('=== Performance Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(
            getConfigListEntry(
                _("Memory Optimization"),
                self.cfg_memory_optimization))
        self.list.append(
            getConfigListEntry(
                _("Use Hardware Acceleration"),
                self.cfg_use_hardware_acceleration))
        self.list.append(
            getConfigListEntry(
                _("Buffer Size"),
                self.cfg_buffer_size))

        # ============ NETWORK SETTINGS ============
        section = _('=== Network Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(
            getConfigListEntry(
                _("User Agent"),
                self.cfg_user_agent))
        self.list.append(
            getConfigListEntry(
                _("Connection Timeout"),
                self.cfg_connection_timeout))

        # ============ CACHE SETTINGS ============
        section = _('=== Cache Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(
            getConfigListEntry(
                _("Enable Cache"),
                self.cfg_cache_enabled))

        if self.cfg_cache_enabled.value:
            self.list.append(
                getConfigListEntry(
                    _("Cache Size"),
                    self.cfg_cache_size))
            self.list.append(
                getConfigListEntry(
                    _("Refresh Method"),
                    self.cfg_refresh_method))
            self.list.append(
                getConfigListEntry(
                    _("Force Refresh on Browsing"),
                    self.cfg_force_refresh_browsing))
            self.list.append(
                getConfigListEntry(
                    _("Force Refresh on Export"),
                    self.cfg_force_refresh_export))

        # ============ SEARCH SETTINGS ============
        section = _('=== Search Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(
            getConfigListEntry(
                _("Max Search Results"),
                self.cfg_search_max_results))

        # ============ LOGGING SETTINGS ============
        section = _('=== Logging Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(
            getConfigListEntry(
                _("Log Level"),
                self.cfg_log_level))
        self.list.append(
            getConfigListEntry(
                _("Log to File"),
                self.cfg_log_to_file))
        if self.cfg_log_to_file.value:
            section = _('=== Log Maintenance ===')
            self.list.append(
                getConfigListEntry(
                    section, NoSave(
                        ConfigNothing())))
            self.list.append(
                getConfigListEntry(
                    _("View Log File"),
                    self.cfg_view_log_file))
            self.list.append(
                getConfigListEntry(
                    _("Clear Log Files Now"),
                    self.cfg_clear_logs_now))

        # ============ UPDATE SETTINGS ============
        section = _('=== Update Settings ===')
        self.list.append(getConfigListEntry(section, NoSave(ConfigNothing())))
        self.list.append(
            getConfigListEntry(
                _("Check for Updates"),
                self.cfg_check_for_updates))

        # ===== FINISH =====
        self["config"].list = self.list
        self["config"].l.setList(self.list)

    def save(self):
        """Save all settings - UPDATED VERSION"""
        log.debug("Starting save...", module="Settings")

        # Build the configuration from UI values
        config_data = {}

        # PLAYER
        if hasattr(self, 'cfg_player'):
            config_data["player"] = self.cfg_player.value

        # DISPLAY
        if hasattr(self, 'cfg_show_flags'):
            config_data["show_flags"] = self.cfg_show_flags.value
        if hasattr(self, 'cfg_show_logos'):
            config_data["show_logos"] = self.cfg_show_logos.value

        # BROWSER
        if hasattr(self, 'cfg_max_channels'):
            try:
                max_channels_val = self.cfg_max_channels.value
                if isinstance(max_channels_val, tuple):
                    config_data["max_channels"] = int(max_channels_val[0])
                else:
                    config_data["max_channels"] = int(max_channels_val)
            except BaseException:
                config_data["max_channels"] = 500

        if hasattr(self, 'cfg_default_view'):
            config_data["default_view"] = self.cfg_default_view.value

        if hasattr(self, 'cfg_max_channels_for_sub_bouquet'):
            config_data["max_channels_for_sub_bouquet"] = self.cfg_max_channels_for_sub_bouquet.value

        # CACHE SETTINGS
        if hasattr(self, 'cfg_cache_enabled'):
            config_data["cache_enabled"] = self.cfg_cache_enabled.value
        if hasattr(self, 'cfg_cache_size'):
            config_data["cache_size"] = self.cfg_cache_size.value
        if hasattr(self, 'cfg_force_refresh_export'):
            config_data["force_refresh_export"] = self.cfg_force_refresh_export.value
        if hasattr(self, 'cfg_force_refresh_browsing'):
            config_data["force_refresh_browsing"] = self.cfg_force_refresh_browsing.value
        if hasattr(self, 'cfg_refresh_method'):
            config_data["refresh_method"] = self.cfg_refresh_method.value

        # EXPORT SETTINGS
        if hasattr(self, 'cfg_export_enabled'):
            config_data["export_enabled"] = self.cfg_export_enabled.value

        if config_data.get("export_enabled", True):
            if hasattr(self, 'cfg_max_channels_for_bouquet'):
                try:
                    max_bouquet_val = self.cfg_max_channels_for_bouquet.value
                    if isinstance(max_bouquet_val, tuple):
                        config_data["max_channels_for_bouquet"] = int(
                            max_bouquet_val[0])
                    else:
                        config_data["max_channels_for_bouquet"] = int(
                            max_bouquet_val)
                except BaseException:
                    config_data["max_channels_for_bouquet"] = 500

            if hasattr(self, 'cfg_bouquet_name_prefix'):
                config_data["bouquet_name_prefix"] = self.cfg_bouquet_name_prefix.value

            if hasattr(self, 'cfg_list_position'):
                config_data["list_position"] = self.cfg_list_position.value

        # PERFORMANCE SETTINGS
        if hasattr(self, 'cfg_use_hardware_acceleration'):
            config_data["use_hardware_acceleration"] = self.cfg_use_hardware_acceleration.value
        if hasattr(self, 'cfg_buffer_size'):
            config_data["buffer_size"] = int(self.cfg_buffer_size.value)
        if hasattr(self, 'cfg_memory_optimization'):
            config_data["memory_optimization"] = self.cfg_memory_optimization.value

        # NETWORK SETTINGS
        if hasattr(self, 'cfg_user_agent'):
            config_data["user_agent"] = self.cfg_user_agent.value

        # CONNECTION TIMEOUT
        if hasattr(self, 'cfg_connection_timeout'):
            config_data["connection_timeout"] = self.cfg_connection_timeout.value

        # SEARCH SETTINGS
        if hasattr(self, 'cfg_search_max_results'):
            config_data["search_max_results"] = self.cfg_search_max_results.value

        # LOGGING SETTINGS
        if hasattr(self, 'cfg_log_level'):
            config_data["log_level"] = self.cfg_log_level.value
        if hasattr(self, 'cfg_log_to_file'):
            config_data["log_to_file"] = self.cfg_log_to_file.value

        config = get_config()

        # Merge new settings with existing ones
        # (keeping settings untouched by the UI)
        current_config = config.config.copy()
        current_config.update(config_data)

        config.config = config.validate_config(current_config)

        if config.save_config():
            log.info("Config saved successfully to disk", module="Settings")
        else:
            log.error("Failed to save config to disk!", module="Settings")

        # Apply logging settings
        self.apply_logging_settings()

        self.close(True)

    def keyDown(self):
        """Down arrow - navigate skipping separators."""
        # current_index = self["config"].getCurrentIndex()
        list_length = len(self["config"].list)

        # Navigate down using moveSelection
        self["config"].instance.moveSelection(self["config"].instance.moveDown)

        # Check if we are on a separator
        current = self["config"].getCurrent()
        if current:
            display_name = current[0]
            config_item = current[1]

            # If it's a separator, skip another item down
            if "===" in display_name or isinstance(config_item, ConfigNothing):
                # If not already at the bottom, move down one more
                if self["config"].getCurrentIndex() < list_length - 1:
                    self["config"].instance.moveSelection(
                        self["config"].instance.moveDown)

        self.updateStatus()

    def keyUp(self):
        """Up arrow - navigate skipping separators."""
        # Navigate up using moveSelection
        # current_index = self["config"].getCurrentIndex()
        list_length = len(self["config"].list)
        self["config"].instance.moveSelection(self["config"].instance.moveUp)

        # Check if we are on a separator
        current = self["config"].getCurrent()
        if current:
            display_name = current[0]
            config_item = current[1]

            # If it's a separator, skip another item down
            if "===" in display_name or isinstance(config_item, ConfigNothing):
                # If not already at the bottom, move down one more
                if self["config"].getCurrentIndex() < list_length - 1:
                    self["config"].instance.moveSelection(
                        self["config"].instance.moveUp)

        self.updateStatus()

    def keyLeft(self):
        """Left arrow - navigation only."""
        # ConfigListScreen.keyLeft(self)
        self.updateStatus()

    def keyRight(self):
        """Right arrow - navigation only."""
        # ConfigListScreen.keyRight(self)
        self.updateStatus()

    def cancel(self):
        """Cancel without saving"""
        self.close(False)
