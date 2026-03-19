#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Helpers Module
Based on TV Garden Project by Lululla
Data Source: TV Garden Project
"""
from __future__ import print_function

from sys import stderr
from os import remove, makedirs
from os.path import join, exists
from datetime import datetime
from enigma import getDesktop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
import codecs

from . import PLUGIN_NAME, PLUGIN_PATH


# Helper to load skin
def load_skin_file(skin_name):
    """Load skin file for current resolution"""
    skin_file = join(SKIN_PATH, "%s.xml" % skin_name)

    # Fallback to HD if skin not found for current resolution
    if not fileExists(skin_file):
        skin_file = join(DEFAULT_SKIN_PATH, "%s.xml" % skin_name)

    # Read skin content
    if fileExists(skin_file):
        try:
            f = None
            try:
                f = codecs.open(skin_file, 'r', 'utf-8')
                return f.read()
            finally:
                if f:
                    f.close()
        except:
            pass

    return None


# ============ DETECT SCREEN RESOLUTION ============
def get_screen_resolution():
    """Get current screen resolution"""
    desktop = getDesktop(0)
    return desktop.size()


def get_resolution_type():
    """Get resolution type: hd, fhd, wqhd"""
    width = get_screen_resolution().width()

    if width >= 2560:
        return 'wqhd'
    elif width >= 1920:
        return 'fhd'
    else:  # 1280x720 or smaller
        return 'hd'


# ============ SKIN TEMPLATES ============
def get_skin_template(screen_name):
    """Get skin template for a screen"""
    templates = {
        'main': """
<screen name="TVGardenMain" position="center,center" size="{width},{height}" title="TV Garden">
    <ePixmap pixmap="{images_path}/background.png" position="0,0" size="{width},{height}" zPosition="-1" />
    <widget name="menu" position="50,80" size="{menu_width},{menu_height}" backgroundColor="#1a1a2e" />
    <widget name="status" position="50,{status_y}" size="{menu_width},30" font="Regular;18" halign="center" />
</screen>
""",
        'countries': """
<screen name="CountriesBrowser" position="center,center" size="{width},{height}" title="Countries">
    <widget name="menu" position="50,80" size="{menu_width},{menu_height}" backgroundColor="#16213e" />
    <widget name="flag" position="{flag_x},{flag_y}" size="120,80" alphatest="blend" />
</screen>
"""
    }

    # Calculate dimensions based on resolution
    width = get_screen_resolution().width()
    height = get_screen_resolution().height()

    if RESOLUTION_TYPE == 'wqhd':
        menu_width = width - 100
        menu_height = height - 200
        status_y = height - 60
        flag_x = width - 180
        flag_y = 100
    elif RESOLUTION_TYPE == 'fhd':
        menu_width = width - 100
        menu_height = height - 200
        status_y = height - 60
        flag_x = width - 180
        flag_y = 100
    else:  # hd
        menu_width = width - 60
        menu_height = height - 160
        status_y = height - 50
        flag_x = width - 140
        flag_y = 80

    template = templates.get(screen_name, '')
    return template.format(
        width=width,
        height=height,
        menu_width=menu_width,
        menu_height=menu_height,
        status_y=status_y,
        flag_x=flag_x,
        flag_y=flag_y,
        images_path=IMAGES_PATH
    )


def get_plugin_path():
    """Get absolute path to plugin directory"""
    return resolveFilename(SCOPE_PLUGINS, "Extensions/%s" % PLUGIN_NAME)


def get_icons_path():
    """Get path to icons directory"""
    return join(get_plugin_path(), "icons")


def get_skins_path():
    """Get path to skins directory"""
    return join(get_plugin_path(), "skins")


def get_config_path():
    """Get path to config directory"""
    return "/etc/enigma2/tvgarden"


# Determine skin path based on resolution
RESOLUTION_TYPE = get_resolution_type()
SKIN_PATH = join(PLUGIN_PATH, "skin", RESOLUTION_TYPE)
IMAGES_PATH = join(PLUGIN_PATH, "images", RESOLUTION_TYPE)

# Fallback paths
DEFAULT_SKIN_PATH = join(PLUGIN_PATH, "skin", "hd")
DEFAULT_IMAGES_PATH = join(PLUGIN_PATH, "images", "hd")

REPO_BASE = "https://raw.githubusercontent.com/Belfagor2005/tv-garden-channel-list/main"


def get_metadata_url():
    return "https://raw.githubusercontent.com/Belfagor2005/tv-garden-channel-list/main/channels/raw/countries_metadata.json"


def get_country_url(country_code):
    return "https://raw.githubusercontent.com/Belfagor2005/tv-garden-channel-list/main/channels/raw/countries/%s.json" % country_code.lower()


def get_category_url(category_id):
    return "https://raw.githubusercontent.com/Belfagor2005/tv-garden-channel-list/main/channels/raw/categories/%s.json" % category_id


def get_categories_url():
    return "https://api.github.com/repos/Belfagor2005/tv-garden-channel-list/contents/channels/raw/categories"


def get_all_channels_url():
    return "https://raw.githubusercontent.com/Belfagor2005/tv-garden-channel-list/main/channels/raw/categories/all-channels.json"


def get_flag_url(country_code, size=80):
    """Get URL for country flag"""
    return "https://flagcdn.com/w%d/%s.png" % (size, country_code.lower())


CATEGORIES = [
    {'id': 'all-channels', 'name': 'All Channels'},
    {'id': 'animation', 'name': 'Animation'},
    {'id': 'auto', 'name': 'Auto'},
    {'id': 'business', 'name': 'Business'},
    {'id': 'classic', 'name': 'Classic'},
    {'id': 'comedy', 'name': 'Comedy'},
    {'id': 'cooking', 'name': 'Cooking'},
    {'id': 'culture', 'name': 'Culture'},
    {'id': 'documentary', 'name': 'Documentary'},
    {'id': 'education', 'name': 'Education'},
    {'id': 'entertainment', 'name': 'Entertainment'},
    {'id': 'family', 'name': 'Family'},
    {'id': 'general', 'name': 'General'},
    {'id': 'kids', 'name': 'Kids'},
    {'id': 'legislative', 'name': 'Legislative'},
    {'id': 'lifestyle', 'name': 'Lifestyle'},
    {'id': 'movies', 'name': 'Movies'},
    {'id': 'music', 'name': 'Music'},
    {'id': 'news', 'name': 'News'},
    {'id': 'outdoor', 'name': 'Outdoor'},
    {'id': 'public', 'name': 'Public'},
    {'id': 'relax', 'name': 'Relax'},
    {'id': 'religious', 'name': 'Religious'},
    {'id': 'science', 'name': 'Science'},
    {'id': 'series', 'name': 'Series'},
    {'id': 'shop', 'name': 'Shop'},
    {'id': 'show', 'name': 'Show'},
    {'id': 'sports', 'name': 'Sports'},
    {'id': 'top-news', 'name': 'Top News'},
    {'id': 'travel', 'name': 'Travel'},
    {'id': 'weather', 'name': 'Weather'}
]


def get_category_name(category_id):
    """Get display name for category ID"""
    for cat in CATEGORIES:
        if cat['id'] == category_id:
            return cat['name']
    return category_id


def safe_get(dictionary, keys, default=None):
    """Safely get nested dictionary value"""
    current = dictionary
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def format_channel_count(count):
    """Format channel count for display"""
    if count == 0:
        return "No channels"
    elif count == 1:
        return "1 channel"
    else:
        return "%d channels" % count


def is_valid_stream_url(url):
    """Check if URL looks like a valid stream for Enigma2"""
    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    valid_prefixes = ('http://', 'https://', 'rtmp://', 'rtsp://')

    if not any(url.startswith(prefix) for prefix in valid_prefixes):
        return False

    supported_patterns = ('.m3u8', '.mp4', '.ts', '.avi', '.mkv', '.flv', 'mpegts')

    url_lower = url.lower()
    for pattern in supported_patterns:
        if pattern in url_lower:
            return True

    if url.startswith(('http://', 'https://')):
        return True

    return False


# ============ LOGGING ============
LOG_PATH_DIR = "/tmp/tvgarden_cache"
LOG_PATH = join(LOG_PATH_DIR, "tvgarden.log")

# Create log directory if not exists
if not exists(LOG_PATH_DIR):
    try:
        makedirs(LOG_PATH_DIR, mode=0o755)
    except:
        pass


class TVGardenLog:
    """Enhanced logging system for TV Garden"""

    # Log levels
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    # Colors for console (optional)
    COLORS = {
        DEBUG: "\033[94m",      # Blue
        INFO: "\033[92m",       # Green
        WARNING: "\033[93m",    # Yellow
        ERROR: "\033[91m",      # Red
        CRITICAL: "\033[95m",   # Magenta
        'END': "\033[0m"        # Reset
    }

    # Configuration
    _log_to_file = True
    _log_to_console = True
    _min_level = INFO
    _log_file = None

    def __call__(self, message, level="INFO", module=""):
        """Allow calling instance like log("message")"""
        self.log(message, level, module)

    @classmethod
    def setup(cls, config=None):
        """Setup logging from config"""
        if config:
            log_level = config.get("log_level", "INFO").upper()
            cls._min_level = log_level
            cls._log_to_file = config.get("log_to_file", True)

        # Create initial log entry
        cls.info("TV Garden logging system initialized", "System")

    @classmethod
    def _should_log(cls, level):
        """Check if message should be logged based on level"""
        level_priority = [cls.DEBUG, cls.INFO, cls.WARNING, cls.ERROR, cls.CRITICAL]
        return level_priority.index(level) >= level_priority.index(cls._min_level)

    @classmethod
    def log(cls, message, level=INFO, module=""):
        """Enhanced logging function"""

        # Filter by level
        if not cls._should_log(level):
            return

        # Timestamp with milliseconds
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Format message
        module_prefix = "[%s] " % module if module else ""
        full_message = "[%s] [%s] %s%s" % (timestamp, level, module_prefix, message)

        # Console output (with colors if supported)
        if cls._log_to_console:
            color = cls.COLORS.get(level, "")
            reset = cls.COLORS.get('END', '')
            print("%s%s%s" % (color, full_message, reset), file=stderr)

        # File output
        if cls._log_to_file:
            try:
                import codecs
                f = None
                try:
                    f = codecs.open(LOG_PATH, "a", "utf-8")
                    f.write(full_message + u"\n")
                finally:
                    if f:
                        f.close()
            except Exception as e:
                print("Log file error: %s" % e, file=stderr)

    # Shortcut methods (the ones you'll use most)
    @classmethod
    def debug(cls, message, module=""):
        cls.log(message, cls.DEBUG, module)

    @classmethod
    def info(cls, message, module=""):
        cls.log(message, cls.INFO, module)

    @classmethod
    def warning(cls, message, module=""):
        cls.log(message, cls.WARNING, module)

    @classmethod
    def error(cls, message, module=""):
        cls.log(message, cls.ERROR, module)

    @classmethod
    def critical(cls, message, module=""):
        cls.log(message, cls.CRITICAL, module)

    # Utility methods
    @classmethod
    def set_level(cls, level):
        """Set minimum log level"""
        valid_levels = [cls.DEBUG, cls.INFO, cls.WARNING, cls.ERROR, cls.CRITICAL]
        if level in valid_levels:
            cls._min_level = level
            cls.info("Log level changed to %s" % level, "System")

    @classmethod
    def enable_file_logging(cls, enable=True):
        """Enable/disable file logging"""
        cls._log_to_file = enable

    @classmethod
    def get_log_path(cls):
        """Get log file path"""
        return LOG_PATH

    @classmethod
    def clear_logs(cls):
        """Clear log file"""
        try:
            if exists(LOG_PATH):
                remove(LOG_PATH)
                cls.info("Log file cleared", "System")
        except Exception as e:
            cls.error("Failed to clear log: %s" % e, "System")

    @classmethod
    def get_log_contents(cls, max_lines=100):
        """Get last N lines from log file"""
        try:
            if exists(LOG_PATH):
                import codecs
                f = None
                try:
                    f = codecs.open(LOG_PATH, "r", "utf-8")
                    lines = f.readlines()
                    return "".join(lines[-max_lines:])
                finally:
                    if f:
                        f.close()
            return "Log file not found"
        except Exception as e:
            return "Error reading log: %s" % e


# Create global instance
log = TVGardenLog()


# Legacy function for backward compatibility
def simple_log(message, level="INFO"):
    """Backward compatible simple logging function"""
    log.log(message, level, "Legacy")
