#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Config Module
Settings and configuration management
Based on TV Garden Project
"""
from __future__ import print_function
from os.path import join, exists
from os import makedirs, chmod
from json import load, dump
from Tools.Directories import fileExists
from shutil import copy2

from .. import USER_AGENT
from .. import PLUGIN_PATH
from ..helpers import log


class PluginConfig:
    """Simple JSON configuration manager"""

    def __init__(self):
        # Paths
        self.config_dir = "/etc/enigma2/tvgarden"
        self.config_file = join(self.config_dir, "config.json")
        self.backup_file = join(self.config_dir, "config.json.backup")

        # Create config directory if not exists
        if not exists(self.config_dir):
            try:
                makedirs(self.config_dir)
                log.info("Created config directory: %s" % self.config_dir, module="Config")
            except Exception as e:
                log.error("Error creating config directory: %s" % e, module="Config")

        # ============ DEFAULT CONFIGURATION ============
        self.defaults = {
            # ============ PLAYER SETTINGS ============
            "player": "auto",                       # "auto", "exteplayer3", "gstplayer" - CHANGED TO AUTO

            # ============ DISPLAY SETTINGS ============
            # "skin": "auto",                       # "auto", "hd", "fhd", "wqhd", "sd"
            "show_flags": True,                     # Show country flags
            "show_logos": True,                     # Show channel logos
            "show_info": True,                      # Show channel info

            # ============ BROWSER SETTINGS ============
            "max_channels": 500,                    # Max channels for country (0=all)
            "sort_by": "name",                      # Sort channels by "name", "country", "category"
            "default_view": "countries",            # "countries", "categories", "favorites", "search"
            "refresh_method": "clear_cache",        # "clear_cache" or "force_refresh"

            # ============ CACHE SETTINGS ============
            "cache_enabled": True,                  # Enable caching
            "cache_ttl": 3600,                      # Cache time-to-live in seconds (1 hour)
            "cache_size": 500,                      # Maximum cache items - INCREASED
            "auto_refresh": False,                  # Automatic cache refresh - CHANGED TO FALSE
            "force_refresh_export": False,          # Force refresh when exporting (False = use cache)
            "force_refresh_browsing": False,        # Force refresh when browsing

            # ============ EXPORT SETTINGS ============
            "list_position": "bottom",              # "top" or "bottom" - bouquet position in Enigma2
            "bouquet_name_prefix": "TVGarden",      # Bouquet name prefix
            "export_enabled": True,                 # Enable bouquet export
            "max_channels_for_bouquet": 500,        # Max channels for bouquet
            "max_channels_for_sub_bouquet": 500,    # Max channels for sub bouquet

            # ============ NETWORK SETTINGS ============
            "user_agent": USER_AGENT,
            "use_proxy": False,
            "proxy_url": "",
            "connection_timeout": 30,               # Network connection timeout

            # ============ LOGGING SETTINGS ============
            "log_level": "INFO",                    # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
            "log_to_file": True,                    # Log to file

            # ============ UPDATE SETTINGS ============
            "auto_update": True,                    # Automatic updates
            "update_channel": "stable",             # "stable", "beta", "dev"
            "update_check_interval": 86400,         # Check for updates every 24 hours
            "notify_on_update": True,               # Notify when updates available
            "last_update_check": 0,                 # Timestamp of last update check

            # ============ FAVORITES SETTINGS ============
            "auto_add_favorite": False,             # Automatically add watched to favorites

            # ============ PERFORMANCE SETTINGS ============
            "use_hardware_acceleration": True,      # Use hardware acceleration
            "buffer_size": 2048,                    # Buffer size in KB (2MB)
            "memory_optimization": True,            # Enable memory optimization

            # ============ SEARCH SETTINGS ============
            "search_max_results": 200,              # Max results in search

            # ============ DEBUG/DEVELOPMENT ============
            "debug_mode": False,                    # Enable debug mode
            "test_mode": False,                     # Enable test features
            "developer_mode": False,                # Developer options

            # ============ LAST SESSION ============
            "last_country": None,
            "last_category": None,
            "last_channel": None,
            "last_search": "",
            "last_export_type": "single_file",      # "single_file" or "multi_file"

            # ============ STATISTICS ============
            "stats_enabled": True,
            "watch_time": 0,                        # Total watch time in seconds
            "channels_watched": 0,                  # Number of channels watched
            "exports_count": 0,                     # Number of bouquet exports
            "favorites_added": 0,                   # Number of favorites added
            "cache_hits": 0,                        # Number of cache hits
            "cache_misses": 0,                      # Number of cache misses

            # ============ ADVANCED SETTINGS ============
            "config_version": 2,                    # Configuration version for migrations
            "first_run": True,                      # First run flag
            "accepted_eula": False,                 # EULA accepted flag
            "telemetry": False,                     # Anonymous usage statistics
        }

        self.config = self.load_config()

    def load_config(self):
        """Load configuration from JSON file"""
        if fileExists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = load(f)

                # Merge with defaults for missing keys
                config = self.defaults.copy()
                config.update(loaded_config)

                # Validate and fix values
                config = self.validate_config(config)

                log.info("Configuration loaded successfully from %s" % self.config_file, module="Config")
                return config
            except Exception as e:
                log.error("Error loading config: %s" % e, module="Config")
                return self.restore_backup()

        # Create new config with defaults
        log.info("Creating new configuration with defaults", module="Config")
        return self.validate_config(self.defaults.copy())

    def save_config(self):
        """Save configuration to JSON file"""
        try:
            # Create backup before saving
            if fileExists(self.config_file):
                try:
                    copy2(self.config_file, self.backup_file)
                    log.debug("Created backup: %s" % self.backup_file, module="Config")
                except Exception as e:
                    log.warning("Could not create backup: %s" % e, module="Config")

            # Validate before saving
            self.config = self.validate_config(self.config)

            # Save config
            with open(self.config_file, 'w') as f:
                dump(self.config, f, indent=4, sort_keys=True)

            # Set proper permissions
            chmod(self.config_file, 0o644)

            log.info("Configuration saved to %s" % self.config_file, module="Config")
            return True
        except Exception as e:
            log.error("Error saving config: %s" % e, module="Config")
            return False

    def validate_config(self, config):
        """Validate and fix configuration values - UPDATED"""
        validated_config = config.copy()

        # Ensure max_channels is valid
        if 'max_channels' in validated_config:
            try:
                val = int(validated_config['max_channels'])
                if val < 0:
                    val = 0  # 0 = all channels
                elif val > 5000:
                    val = 5000
                validated_config['max_channels'] = val
            except (ValueError, TypeError):
                validated_config['max_channels'] = 500

        # Ensure player is valid
        valid_players = ['exteplayer3', 'gstplayer', 'auto']
        if validated_config.get('player') not in valid_players:
            validated_config['player'] = 'auto'

        # Ensure log_level is valid
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if validated_config.get('log_level') not in valid_log_levels:
            validated_config['log_level'] = 'INFO'

        # Ensure default_view is valid
        valid_views = ['countries', 'categories', 'favorites', 'search']
        if validated_config.get('default_view') not in valid_views:
            validated_config['default_view'] = 'countries'

        # Ensure buffer_size is reasonable
        if 'buffer_size' in validated_config:
            try:
                buffer_size = int(validated_config['buffer_size'])
                if buffer_size < 256:
                    buffer_size = 256
                elif buffer_size > 16384:
                    buffer_size = 16384
                validated_config['buffer_size'] = buffer_size
            except (ValueError, TypeError):
                validated_config['buffer_size'] = 2048

        # Ensure connection_timeout is reasonable
        if 'connection_timeout' in validated_config:
            try:
                timeout = int(validated_config['connection_timeout'])
                if timeout < 10:
                    timeout = 10
                elif timeout > 300:
                    timeout = 300
                validated_config['connection_timeout'] = timeout
            except (ValueError, TypeError):
                validated_config['connection_timeout'] = 30

        # Ensure cache_size is reasonable
        if 'cache_size' in validated_config:
            try:
                val = int(validated_config['cache_size'])
                if val < 10:
                    val = 10
                elif val > 5000:
                    val = 5000
                validated_config['cache_size'] = val
            except (ValueError, TypeError):
                validated_config['cache_size'] = 500

        # Ensure search_max_results is reasonable
        if 'search_max_results' in validated_config:
            try:
                val = int(validated_config['search_max_results'])
                if val < 10:
                    val = 10
                elif val > 1000:
                    val = 1000
                validated_config['search_max_results'] = val
            except (ValueError, TypeError):
                validated_config['search_max_results'] = 200

        # Ensure list_position is valid
        if 'list_position' in validated_config:
            if validated_config['list_position'] not in ['top', 'bottom']:
                validated_config['list_position'] = 'bottom'

        # Ensure refresh_method is valid
        if 'refresh_method' in validated_config:
            if validated_config['refresh_method'] not in ['clear_cache', 'force_refresh']:
                validated_config['refresh_method'] = 'clear_cache'

        # Ensure boolean values are actually boolean
        boolean_keys = [
            'show_flags', 'show_logos', 'cache_enabled',
            'force_refresh_export', 'force_refresh_browsing',
            'export_enabled', 'log_to_file',
            'use_hardware_acceleration', 'memory_optimization',
            'debug_mode',
        ]

        for key in boolean_keys:
            if key in validated_config:
                if not isinstance(validated_config[key], bool):
                    validated_config[key] = bool(validated_config[key])

        # Ensure string values are strings
        string_keys = [
            'player', 'log_level', 'default_view',
            'bouquet_name_prefix', 'user_agent', 'update_channel',
            'refresh_method', 'last_country', 'last_category', 'last_channel',
            'last_search', 'list_position'
        ]

        for key in string_keys:
            if key in validated_config and validated_config[key] is not None:
                value = validated_config[key]
                try:
                    validated_config[key] = str(value)
                except:
                    validated_config[key] = ''

        numeric_keys = [
            'max_channels', 'max_channels_for_bouquet',
            'max_channels_for_sub_bouquet', 'connection_timeout',
            'buffer_size', 'search_max_results', 'watch_time',
            'exports_count', 'cache_size', 'config_version',
        ]

        for key in numeric_keys:
            if key in validated_config:
                try:
                    validated_config[key] = int(validated_config[key])
                except (ValueError, TypeError):
                    if key in self.defaults:
                        validated_config[key] = self.defaults[key]

        return validated_config

    def _migrate_config_v2(self, config):
        """Migrate from config version 1 to 2 - SEMPLIFICATA"""
        log.info("Migrating config from version 1 to 2", module="Config")

        old_keys_to_remove = [
            'timeout', 'download_timeout', 'bouquet_auto_reload',
            'search_case_sensitive', 'skin', 'auto_update', 'update_channel',
            'update_check_interval', 'notify_on_update', 'auto_add_favorite',
            'show_info', 'sort_by', 'cache_ttl', 'auto_refresh',
            'use_proxy', 'proxy_url', 'favorites_autosave', 'max_favorites',
            'test_mode', 'developer_mode', 'last_export_type',
            'favorites_added', 'cache_hits', 'cache_misses', 'stats_enabled',
            'first_run', 'accepted_eula', 'telemetry'
        ]
        
        for key in old_keys_to_remove:
            if key in config:
                del config[key]

        new_keys_v2 = {
            'refresh_method': 'clear_cache',
            'list_position': 'bottom',
            'memory_optimization': True,
            'search_max_results': 200,
            'last_search': '',
            'exports_count': 0,
            'config_version': 2,
            'max_channels_for_sub_bouquet': 500
        }

        for key, default in new_keys_v2.items():
            if key not in config:
                config[key] = default

        if 'cache_size' in config and config['cache_size'] < 500:
            config['cache_size'] = 500

        if 'max_channels_for_bouquet' in config and config['max_channels_for_bouquet'] < 500:
            config['max_channels_for_bouquet'] = 500

        if 'force_refresh' in config:
            config['force_refresh_export'] = config['force_refresh']
            config['force_refresh_browsing'] = config['force_refresh']
            del config['force_refresh']

        return config

    def restore_backup(self):
        """Restore configuration from backup"""
        if fileExists(self.backup_file):
            try:
                with open(self.backup_file, 'r') as f:
                    backup_config = load(f)

                # Validate restored config
                validated_config = self.validate_config(backup_config)

                log.info("Configuration restored from backup: %s" % self.backup_file, module="Config")
                return validated_config
            except Exception as e:
                log.error("Error restoring backup: %s" % e, module="Config")

                # Return defaults if backup also fails
                return self.defaults.copy()
        else:
            log.warning("No backup found, using defaults", module="Config")
            return self.defaults.copy()

    def get(self, key, default=None):
        """Get config value"""
        if key in self.config:
            return self.config[key]
        elif default is not None:
            return default
        else:
            return self.defaults.get(key)

    def set(self, key, value):
        """Set config value and save"""
        self.config[key] = value
        return self.save_config()

    def delete(self, key):
        """Delete config key"""
        if key in self.config:
            del self.config[key]
            return self.save_config()
        return False

    def reset(self):
        """Reset to defaults"""
        self.config = self.defaults.copy()
        return self.save_config()

    def export(self, filepath):
        """Export config to file"""
        try:
            # Ensure directory exists
            export_dir = join(filepath, '..')
            if not exists(export_dir):
                makedirs(export_dir)

            with open(filepath, 'w') as f:
                dump(self.config, f, indent=4)

            log.info("Configuration exported to: %s" % filepath, module="Config")
            return True
        except Exception as e:
            log.error("Error exporting config: %s" % e, module="Config")
            return False

    def import_config(self, filepath):
        """Import config from file"""
        if fileExists(filepath):
            try:
                with open(filepath, 'r') as f:
                    imported = load(f)

                # Validate imported config
                validated_imported = self.validate_config(imported)

                # Merge with current config (keep current values for missing keys)
                for key, value in validated_imported.items():
                    self.config[key] = value

                log.info("Configuration imported from: %s" % filepath, module="Config")
                return self.save_config()
            except Exception as e:
                log.error("Error importing config: %s" % e, module="Config")
                return False
        else:
            log.error("Import file not found: %s" % filepath, module="Config")
            return False

    # Convenience methods
    def get_player(self):
        """Get configured player with auto-detection"""
        player = self.get('player', 'auto')
        if player == 'auto':
            try:
                import subprocess

                # Check for exteplayer3
                try:
                    p = subprocess.Popen(['which', 'exteplayer3'],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    output, error = p.communicate()
                    if p.returncode == 0:
                        return 'exteplayer3'
                except Exception:
                    pass

                # Check for gstplayer
                try:
                    p = subprocess.Popen(['which', 'gst-launch-1.0'],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
                    output, error = p.communicate()
                    if p.returncode == 0:
                        return 'gstplayer'
                except Exception:
                    pass

            except Exception as e:
                log.debug("Auto-detection failed: %s" % e, module="Config")

            return 'gstplayer'  # Default fallback
        return player

    def get_skin_resolution(self):
        """Get skin resolution name (hd, fhd, wqhd, sd)"""
        skin_setting = self.get('skin', 'auto')

        if skin_setting == 'auto':
            try:
                from enigma import getDesktop
                desktop = getDesktop(0)
                width = desktop.size().width()
                height = desktop.size().height()

                if width >= 2560 or height >= 1440:
                    return "wqhd"
                elif width >= 1920 or height >= 1080:
                    return "fhd"
                elif width >= 1280 or height >= 720:
                    return "hd"
                else:
                    return "sd"
            except Exception as e:
                log.error("Error detecting resolution: %s" % e, module="Config")
                return 'hd'  # Default fallback

        return skin_setting

    def load_skin(self, screen_name, default_skin):
        """
        Load skin from file or use default from class
        """
        if exists('/var/lib/dpkg/status'):
            log.info("Python2 image detected, using class skin for %s" % screen_name, module="Config")
            return default_skin
        
        resolution = self.get_skin_resolution()
        skin_file = join(PLUGIN_PATH, "skins", resolution, "%s.xml" % screen_name)
        
        if fileExists(skin_file):
            try:
                with open(skin_file, 'r') as f:
                    skin_content = f.read()
                log.info("Loaded skin from: %s" % skin_file, module="Config")
                return skin_content
            except Exception as e:
                log.error("Error loading XML skin: %s" % e, module="Config")
                return default_skin
        else:
            log.warning("XML skin not found for %s, using class skin" % screen_name, module="Config")
            return default_skin

    def get_skin_path(self):
        """Get skin path based on config and detection"""
        skin_setting = self.get('skin', 'auto')
        if skin_setting == 'auto':
            try:
                from ..helpers import get_resolution_type
                return get_resolution_type()
            except Exception as e:
                log.error("Error getting resolution type: %s" % e, module="Config")
                return 'hd'  # Default fallback
        return skin_setting

    def add_watch_time(self, seconds):
        """Add watch time to statistics"""
        if self.get('stats_enabled', True):
            current = self.get('watch_time', 0)
            self.set('watch_time', current + seconds)
            log.debug("Added %d seconds to watch time, total: %d" % (seconds, current + seconds), module="Config")

    def increment_channels_watched(self):
        """Increment channels watched counter"""
        if self.get('stats_enabled', True):
            current = self.get('channels_watched', 0)
            self.set('channels_watched', current + 1)
            log.debug("Incremented channels watched to: %d" % (current + 1), module="Config")

    def get_connection_timeout(self):
        """Get connection timeout in seconds"""
        return self.get('connection_timeout', 30)

    def get_buffer_size(self):
        """Get buffer size in KB"""
        return self.get('buffer_size', 2048)

    def is_debug_mode(self):
        """Check if debug mode is enabled"""
        return self.get('debug_mode', False)

    def use_hardware_acceleration(self):
        """Check if hardware acceleration should be used"""
        return self.get('use_hardware_acceleration', True)

    def get_all_settings(self):
        """Get all configuration as dictionary"""
        return self.config.copy()

    def get_settings_group(self, group_prefix):
        """
        Get all settings that start with a specific prefix
        Example: get_settings_group("log_") returns all logging settings
        """
        result = {}
        for key, value in self.config.items():
            if key.startswith(group_prefix):
                result[key] = value
        return result

    def update_settings(self, settings_dict, replace_all=False):
        """
        Update multiple settings at once
        Args:
            settings_dict: Dictionary with settings to update
            replace_all: If True, replace entire config with settings_dict
        Returns:
            True if successful, False otherwise
        """
        try:
            if replace_all:
                self.config = settings_dict.copy()
            else:
                for key, value in settings_dict.items():
                    self.config[key] = value

            return self.save_config()
        except Exception as e:
            log.error("Error updating settings: %s" % e, module="Config")
            return False

    def get_version(self):
        """Get configuration version (for future compatibility)"""
        return self.get('config_version', 1)

    def set_version(self, version):
        """Set configuration version"""
        self.config['config_version'] = version
        return self.save_config()


# Singleton instance
_config_instance = None


def get_config():
    """Get configuration singleton instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = PluginConfig()
    return _config_instance


def reload_config():
    """Reload configuration from disk"""
    if _config_instance is not None:
        _config_instance.config = _config_instance.load_config()
        log.info("Configuration reloaded from disk", module="Config")
    return _config_instance
