#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Helpers Module
Based on TV Garden Project by Lululla
Data Source: TV Garden Project

[TVGarden patch] Aggiunto supporto multi-sorgente (tv / webcams).
Tutte le funzioni URL accettano `media_type` con fallback su "tv".
Le liste di categorie sono state rimosse: vengono lette dinamicamente
dalla GitHub API tramite CacheManager.get_available_categories().
"""
from sys import stderr
from os import remove, makedirs
from os.path import join, exists
from datetime import datetime
from enigma import getDesktop
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, fileExists
import codecs
import re

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
        except BaseException:
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
SKIN_PATH = join(PLUGIN_PATH, "skins", RESOLUTION_TYPE)
IMAGES_PATH = join(PLUGIN_PATH, "images", RESOLUTION_TYPE)

# Fallback paths
DEFAULT_SKIN_PATH = join(PLUGIN_PATH, "skins", "hd")
DEFAULT_IMAGES_PATH = join(PLUGIN_PATH, "images", "hd")

REPO_BASE = "https://raw.githubusercontent.com/OwnerPlugins/famelack-data/main"

# ============ MEDIA TYPE HANDLING ============
# [TVGarden patch] Whitelist per media_type. Aggiungere qui eventuali
# nuove sorgenti in futuro (es. "radio").
VALID_MEDIA = ("tv", "webcams")


def _media_path(media_type):
    """Sanitize media_type, fallback su 'tv' se non valido."""
    if media_type not in VALID_MEDIA:
        return "tv"
    return media_type


# ============ URL BUILDERS ============
# [TVGarden patch] Tutte le funzioni accettano media_type (default "tv")
# per retrocompatibilità con il codice esistente.

def get_metadata_url(media_type="tv"):
    return "%s/%s/raw/countries_metadata.json" % (
        REPO_BASE, _media_path(media_type))


def get_country_url(country_code, media_type="tv"):
    return "%s/%s/raw/countries/%s.json" % (
        REPO_BASE, _media_path(media_type), country_code.lower()
    )


def get_category_url(category_id, media_type="tv"):
    return "%s/%s/raw/categories/%s.json" % (
        REPO_BASE, _media_path(media_type), category_id
    )


def get_categories_url(media_type="tv"):
    return "https://api.github.com/repos/OwnerPlugins/famelack-data/contents/%s/raw/categories" % _media_path(
        media_type)


def get_all_channels_url(media_type="tv"):
    return "%s/%s/raw/categories/all.json" % (
        REPO_BASE, _media_path(media_type))


# Data codes that differ from the ISO 3166 codes used by flagcdn.com
FLAG_CODE_ALIASES = {
    'uk': 'gb',
}


def get_flag_url(country_code, size=80):
    """Get URL for country flag"""
    code = country_code.lower()
    code = FLAG_CODE_ALIASES.get(code, code)
    return "https://flagcdn.com/w%d/%s.png" % (size, code)


# ============ CATEGORY FALLBACK ============
# [TVGarden patch] Le categorie vengono lette dinamicamente dalla GitHub API
# tramite CacheManager.get_available_categories(media_type).
# Qui sotto solo un fallback MINIMO usato se la API non risponde
# E la cache è vuota (es. primo avvio offline).
CATEGORIES_FALLBACK = [
    {'id': 'all', 'name': 'All'},
]


def get_category_name(category_id, media_type="tv"):
    """
    [TVGarden patch] Lookup name per category_id.
    Non usa più una lista hardcoded: prova a leggere dal cache.
    Se il cache non è disponibile, ritorna l'id formattato.
    """
    # Formattazione leggibile fallback (es. "top-news" -> "Top News")
    try:
        return category_id.replace('-', ' ').replace('_', ' ').title()
    except BaseException:
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
    return url.startswith(valid_prefixes)


def is_youtube_url(url):
    """Check if URL points to YouTube"""
    if not url or not isinstance(url, str):
        return False
    url = url.lower()
    return ("youtube.com" in url or "youtu.be" in url or
            "youtube-nocookie.com" in url)


def youtube_watch_url(url):
    """
    Convert any YouTube link (embed, nocookie, youtu.be, live, shorts)
    to https://www.youtube.com/watch?v=ID, the form Enigma2 YouTube
    resolvers (ytdlpwrapper) recognise in bouquets. Other URLs unchanged.
    """
    if not is_youtube_url(url):
        return url
    patterns = (
        r'[?&]v=([^&#]+)',
        r'youtu\.be/([^/?&#]+)',
        r'/(?:embed|live|shorts|v)/([^/?&#]+)',
    )
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return "https://www.youtube.com/watch?v=%s" % match.group(1)
    return url


def bouquet_stream_url(channel):
    """
    URL to write in a bouquet for a channel dict
    (YouTube links converted to watch URLs). Returns (url, is_youtube).
    """
    stream_url = channel.get('stream_url') or channel.get('url') or ''
    is_youtube = bool(channel.get('is_youtube')) or is_youtube_url(stream_url)
    if is_youtube:
        stream_url = youtube_watch_url(stream_url)
    return stream_url, is_youtube


YOUTUBE_BOUQUET_NOTE = (
    "YouTube entries play from the bouquet only with the yt-dlp wrapper "
    "plugin (enigma2-plugin-extensions-ytdlpwrapper).")


def _first_url(values):
    """Return first non-empty string from a list"""
    if isinstance(values, list):
        for url in values:
            if isinstance(url, str) and url.strip():
                return url.strip()
    return None


def extract_stream_url(channel):
    """
    Extract the playable URL from a channel entry.

    Supports the current data format with nested "sources"
    ({"sources": {"streams": [...], "youtube": [...]}}) and the
    old flat keys (iptv_urls, youtube_urls, stream_urls, url).

    Returns a tuple (stream_url, found_in, is_youtube);
    stream_url is None when nothing usable is found.
    """
    if not isinstance(channel, dict):
        return None, None, False

    sources = channel.get("sources")
    if isinstance(sources, dict):
        for key in ("streams", "iptv", "youtube", "iframe"):
            url = _first_url(sources.get(key))
            if not url:
                continue
            # Generic iframe pages cannot be played, only YouTube embeds
            if key == "iframe" and not is_youtube_url(url):
                continue
            return url, "sources.%s" % key, is_youtube_url(url)

    for key in ("iptv_urls", "youtube_urls", "stream_urls"):
        url = _first_url(channel.get(key))
        if url:
            return url, key, is_youtube_url(url)

    url = channel.get("url") or channel.get("stream_url")
    if isinstance(url, str) and url.strip():
        url = url.strip()
        return url, "url", is_youtube_url(url)

    return None, None, False


def timer_connect(timer, callback):
    """
    Connect an eTimer callback on both DreamOS and OE images.
    The returned connection object (DreamOS) MUST be kept alive by the
    caller, otherwise the callback is disconnected immediately.
    """
    try:
        return timer.timeout.connect(callback)
    except AttributeError:
        timer.callback.append(callback)
        return None


def get_channel_language(channel):
    """Return language string (supports 'language' and 'languages')"""
    language = channel.get("language")
    if language:
        return str(language)
    languages = channel.get("languages")
    if isinstance(languages, list):
        return ", ".join(str(lang) for lang in languages if lang)
    return ""


def encode_bouquet_text(text):
    """Make text safe for a single bouquet line"""
    if not text:
        return ""
    return str(text).replace("\r", " ").replace("\n", " ").strip()


def bouquet_service_lines(stream_url, name):
    """Return the #SERVICE / #DESCRIPTION lines for a stream"""
    url = encode_bouquet_text(stream_url).replace(":", "%3a")
    name = encode_bouquet_text(name)
    return "#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n#DESCRIPTION %s\n" % (
        url, name.replace(":", "%3a"), name)


def add_bouquet_to_index(
        bouquet_file,
        position="bottom",
        bouquets_index="/etc/enigma2/bouquets.tv"):
    """
    Add a userbouquet reference to bouquets.tv (once), honouring the
    'top'/'bottom' list position. Returns True on success.
    """
    entry = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet' % bouquet_file
    try:
        lines = []
        if exists(bouquets_index):
            with open(bouquets_index, "r") as f:
                lines = f.read().splitlines()

        if entry in [line.strip() for line in lines]:
            return True

        if not lines:
            lines = ["#NAME Bouquets (TV)"]

        if position == "top":
            # Insert right after the #NAME header (if present)
            insert_at = 1 if lines and lines[0].startswith("#NAME") else 0
            lines.insert(insert_at, entry)
        else:
            while lines and not lines[-1].strip():
                lines.pop()
            lines.append(entry)

        with open(bouquets_index, "w") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except Exception as e:
        log.error("Error updating %s: %s" %
                  (bouquets_index, e), module="Bouquet")
        return False


# ============ LOGGING ============
LOG_PATH_DIR = "/tmp/tvgarden_cache"
LOG_PATH = join(LOG_PATH_DIR, "tvgarden.log")

# Create log directory if not exists
if not exists(LOG_PATH_DIR):
    try:
        makedirs(LOG_PATH_DIR, mode=0o755)
    except BaseException:
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
            log_level = str(config.get("log_level", "INFO")).upper()
            if log_level in (cls.DEBUG, cls.INFO, cls.WARNING,
                             cls.ERROR, cls.CRITICAL):
                cls._min_level = log_level
            cls._log_to_file = config.get("log_to_file", True)

        # Create initial log entry
        cls.info("TV Garden logging system initialized", "System")

    @classmethod
    def _should_log(cls, level):
        """Check if message should be logged based on level"""
        level_priority = [
            cls.DEBUG,
            cls.INFO,
            cls.WARNING,
            cls.ERROR,
            cls.CRITICAL]
        try:
            return level_priority.index(
                level) >= level_priority.index(cls._min_level)
        except ValueError:
            # Unknown level names are always logged
            return True

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
        full_message = "[%s] [%s] %s%s" % (
            timestamp, level, module_prefix, message)

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
        valid_levels = [
            cls.DEBUG,
            cls.INFO,
            cls.WARNING,
            cls.ERROR,
            cls.CRITICAL]
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
