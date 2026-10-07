#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Favorites Manager
Manages favorite channels storage
Based on TV Garden Project
"""
import re
import time
from os import makedirs, remove, system, rename
from os.path import exists, join
from json import load, dump
from hashlib import md5
from shutil import copy2

from ..helpers import (
    log,
    get_all_channels_url,
    extract_stream_url,
    get_channel_language,
    bouquet_service_lines,
    bouquet_stream_url,
    YOUTUBE_BOUQUET_NOTE,
    add_bouquet_to_index,
    encode_bouquet_text
)
from ..utils.config import get_config
from ..utils.cache import CacheManager
from .. import _


ENIGMA_PATH = "/etc/enigma2"

# Streams that Enigma2 players cannot handle
PROBLEMATIC_PATTERNS = ['.mpd', '/dash/', 'drm', 'widevine', 'flex-cdn.net']


def _database_stream_url(channel):
    """Playable URL of a database entry, or None (YouTube/DRM skipped)"""
    stream_url, found_in, is_youtube = extract_stream_url(channel)
    if not stream_url or is_youtube:
        return None
    stream_lower = stream_url.lower()
    if any(p in stream_lower for p in PROBLEMATIC_PATTERNS):
        return None
    return stream_url


def _safe_file_part(text):
    """Make text usable inside a bouquet file name"""
    return re.sub(
        r'[^a-z0-9_]+',
        '_',
        str(text).lower()).strip('_') or 'unknown'


class FavoritesManager:
    """Manage favorite channels"""

    def __init__(self):
        self.fav_dir = "/etc/enigma2/tvgarden/favorites"
        self.fav_file = join(self.fav_dir, "favorites.json")

        if not exists(self.fav_dir):
            try:
                makedirs(self.fav_dir)
            except Exception as e:
                log.error("Cannot create %s: %s" %
                          (self.fav_dir, e), module="Favorites")

        self.favorites = self.load_favorites()
        log.info("Initialized with %d favorites" %
                 len(self.favorites), module="Favorites")

    def get_all(self):
        """Get all favorites"""
        if hasattr(self, 'favorites'):
            return self.favorites
        else:
            # Fallback
            log.warning("self.favorites doesn't exist!", module="Favorites")
            return []

    def load_favorites(self):
        """Load favorites from file"""
        if exists(self.fav_file):
            try:
                with open(self.fav_file, 'r') as f:
                    data = load(f)
                if isinstance(data, list):
                    return data
                raise ValueError("favorites file is not a list")
            except Exception as e:
                # Keep the damaged file instead of overwriting it later
                broken = "%s.broken_%d" % (self.fav_file, int(time.time()))
                log.error("Cannot read favorites (%s), saved as %s" %
                          (e, broken), module="Favorites")
                try:
                    copy2(self.fav_file, broken)
                except Exception:
                    pass
                return []
        return []

    def save_favorites(self):
        """Save favorites to file (atomic)"""
        try:
            tmp_file = self.fav_file + ".tmp"
            with open(tmp_file, 'w') as f:
                dump(self.favorites, f, indent=2)
            rename(tmp_file, self.fav_file)
            return True
        except Exception as e:
            log.error("Error saving favorites: %s" % e, module="Favorites")
            return False

    def save_bouquet_file(self, filepath, data):
        """Save bouquet file (NON gzip)"""
        try:
            with open(filepath, 'w') as f:
                dump(data, f, indent=2)
            return True
        except Exception as e:
            log.error(
                "Error saving bouquet %s: %s" %
                (filepath, e), module="Favorites")
            return False

    def generate_id(self, channel):
        """Generate unique ID for channel"""
        # Use stream URL as base for ID
        stream_url = channel.get('stream_url') or channel.get('url', '')
        if stream_url:
            return md5(stream_url.encode()).hexdigest()[:16]

        # Fallback to name and other attributes
        name = channel.get('name', '')
        group = channel.get('group', '')
        return md5("%s%s" % (name, group).encode()).hexdigest()[:16]

    def add(self, channel):
        """Add channel to favorites"""
        if self.is_favorite(channel):
            return False, _("Already in favorites")

        channel_name = channel.get('name', 'Unknown')

        # Store a copy: do not modify the caller's channel dict
        channel = dict(channel)
        channel['id'] = self.generate_id(channel)
        channel['added'] = time.time()

        self.favorites.append(channel)

        if self.save_favorites():
            log.info(
                "✓ Added to favorites: %s" %
                channel_name, module="Favorites")
            return True, _("Added to favorites: %s") % channel_name
        else:
            log.error(
                "✗ Failed to save favorites: %s" %
                channel_name, module="Favorites")
            return False, _("Error saving favorites")

    def remove(self, channel):
        """Remove channel from favorites"""
        channel_id = self.generate_id(channel)
        channel_name = channel.get('name', 'Unknown')
        channel_url = channel.get('stream_url') or channel.get('url')

        for i, fav in enumerate(self.favorites):
            fav_url = fav.get('stream_url') or fav.get('url')
            if (channel_url and fav_url == channel_url) or \
                    fav.get('id') in (channel_id, channel.get('id')):
                del self.favorites[i]
                if self.save_favorites():
                    log.info(
                        "✓ Removed from favorites: %s" %
                        channel_name, module="Favorites")
                    return True, _("Removed from favorites: %s") % channel_name
                else:
                    log.error(
                        "✗ Failed to save after removal: %s" %
                        channel_name, module="Favorites")
                    return False, _("Error saving favorites")

        return False, _("Channel not found in favorites")

    def is_favorite(self, channel):
        """Check if channel is already in favorites"""
        if not channel:
            return False

        channel_url = channel.get('stream_url') or channel.get('url')
        if channel_url and self.is_url_in_favorites(channel_url):
            return True

        channel_id = self.generate_id(channel)
        for fav in self.favorites:
            if fav.get('id') == channel_id:
                return True

        return False

    def is_url_in_favorites(self, url):
        """Check if specific URL is already in favorites"""
        if not url:
            return False

        for fav in self.favorites:
            fav_url = fav.get('stream_url') or fav.get('url')
            if fav_url and fav_url == url:
                return True

        return False

    def search(self, query):
        """Search in favorites"""
        query = query.lower()
        results = []
        for fav in self.favorites:
            name = str(fav.get('name', '')).lower()
            group = str(fav.get('group', '')).lower()
            desc = str(fav.get('description', '')).lower()

            if query in name or query in group or query in desc:
                results.append(fav)
        return results

    def _bouquet_path(self, tag, bouquet_name):
        return "%s/userbouquet.%s_%s.tv" % (
            ENIGMA_PATH, tag, _safe_file_part(bouquet_name))

    def export_to_bouquet(self, channels=None, bouquet_name=None):
        """Export channels to an Enigma2 bouquet file"""
        try:
            if channels is None:
                channels = self.favorites

            if not channels:
                return False, _("No channels to export")

            # Read configuration
            config = get_config()
            max_channels = config.get("max_channels_for_bouquet", 500)

            # Apply channel limit if specified
            if max_channels > 0 and len(channels) > max_channels:
                channels = channels[:max_channels]
                log.info(
                    "Limited to %d channels" %
                    max_channels, module="Favorites")

            tag = "tvgarden"

            # If no bouquet name is provided, use prefix + favorites
            if bouquet_name is None:
                prefix = config.get("bouquet_name_prefix", "TVGarden")
                bouquet_name = "%s_favorites" % prefix.lower()
            bouquet_name = _safe_file_part(bouquet_name)

            userbouquet_file = self._bouquet_path(tag, bouquet_name)

            # 1. Group channels by country
            channels_by_country = {}
            for channel in channels:
                country = channel.get('country') or 'Unknown'
                channels_by_country.setdefault(country, []).append(channel)

            # 2. Write the bouquet file
            valid_count = 0
            youtube_count = 0
            try:
                with open(userbouquet_file, "w") as f:
                    f.write("#NAME TV Garden Favorites by Lululla\n")
                    f.write(
                        "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | TV Garden Favorites by Lululla | ---\n")
                    f.write(
                        "#DESCRIPTION --- | TV Garden Favorites by Lululla | ---\n")

                    for country in sorted(channels_by_country.keys()):
                        country_label = encode_bouquet_text(country).upper()
                        f.write(
                            "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- %s ---\n" %
                            country_label)
                        f.write("#DESCRIPTION --- %s ---\n" % country_label)

                        for channel in channels_by_country[country]:
                            stream_url, is_youtube = bouquet_stream_url(
                                channel)
                            if not stream_url:
                                continue
                            f.write(bouquet_service_lines(
                                stream_url, channel.get('name', 'Channel')))
                            valid_count += 1
                            if is_youtube:
                                youtube_count += 1
            except Exception as e:
                log.error(
                    "Error writing bouquet file: %s" %
                    e, module="Favorites")
                return False, _("Error writing file: %s") % str(e)

            if valid_count == 0:
                return False, _("No valid stream URLs found")

            # Add to bouquets and reload
            self._add_to_bouquets_tv(tag, bouquet_name)
            self._reload_bouquets()

            message = _("Exported %d channels to bouquet") % valid_count
            if youtube_count:
                message += "\n\n%s" % _(YOUTUBE_BOUQUET_NOTE)
            return True, message

        except Exception as e:
            log.error("Error: %s" % e, module="Favorites")
            return False, _("Error: %s") % str(e)

    def _load_database_channels(self):
        """
        Download the whole database (all.json) and return
        (channels, error_message). Each channel is a dict with
        name / stream_url / url / country / language.
        """
        cache = CacheManager()
        config = get_config()
        all_channels_url = get_all_channels_url()

        try:
            if config.get("cache_enabled", True):
                data = cache.fetch_url(
                    all_channels_url,
                    force_refresh=config.get("force_refresh_export", False))
            else:
                data = cache._fetch_url(all_channels_url)
        except Exception as e:
            log.error("Failed to fetch: %s" % e, module="Favorites")
            return [], _("Failed to load database")

        if not data or not isinstance(data, list):
            return [], _("Empty database")

        log.info("Processing %d channels from database" %
                 len(data), module="Favorites")

        channels = []
        for idx, channel in enumerate(data):
            if not isinstance(channel, dict):
                continue
            stream_url = _database_stream_url(channel)
            if not stream_url:
                continue
            channels.append({
                'name': channel.get('name') or 'Channel %d' % idx,
                'stream_url': stream_url,
                'url': stream_url,
                'country': str(channel.get('country') or 'UNKNOWN'),
                'language': get_channel_language(channel),
                'isGeoBlocked': channel.get('isGeoBlocked', False)
            })

        if not channels:
            return [], _("No valid channels found in database")
        return channels, None

    @staticmethod
    def _group_by_country(channels):
        grouped = {}
        for channel in channels:
            grouped.setdefault(channel.get('country', 'UNKNOWN'), []).append(
                channel)
        return grouped

    def export_all_channels(self, bouquet_name=None, reload_bouquets=True):
        """
        Export ALL channels from TV Garden database (single file).
        Safe to run in a worker thread with reload_bouquets=False:
        the caller must then call _reload_bouquets() on the GUI thread.
        """
        try:
            log.info(
                "Starting export of ALL channels from database",
                module="Favorites")
            all_channels, error = self._load_database_channels()
            if error:
                return False, error

            channels_by_country = self._group_by_country(all_channels)
            log.info(
                "Total valid channels loaded: %d from %d countries" %
                (len(all_channels), len(channels_by_country)),
                module="Favorites")

            tag = "tvgarden"
            prefix = get_config().get("bouquet_name_prefix", "TVGarden")
            if bouquet_name is None:
                bouquet_name = "%s_all_channels" % prefix.lower()
            bouquet_name = _safe_file_part(bouquet_name)
            prefix = encode_bouquet_text(prefix)

            userbouquet_file = self._bouquet_path(tag, bouquet_name)

            valid_count = 0
            with open(userbouquet_file, "w") as f:
                f.write("#NAME %s - TV Garden All by Lululla\n" % prefix)
                f.write(
                    "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | %s TV Garden by Lululla | ---\n" %
                    prefix)
                f.write(
                    "#DESCRIPTION --- | %s TV Garden by Lululla | ---\n" %
                    prefix)

                for country in sorted(channels_by_country.keys()):
                    country_channels = channels_by_country[country]
                    country_display = (
                        country.upper() if country != 'UNKNOWN' else 'OTHER')
                    f.write(
                        "#SERVICE 1:64:0:0:0:0:0:0:0:0::%s (%d)\n" %
                        (encode_bouquet_text(country_display),
                         len(country_channels)))
                    f.write("#DESCRIPTION %s (%d)\n" %
                            (encode_bouquet_text(country_display),
                             len(country_channels)))

                    for channel in country_channels:
                        name = str(channel.get('name', '')).strip()
                        if not name:
                            continue
                        f.write(bouquet_service_lines(
                            channel['stream_url'], name))
                        valid_count += 1

            log.info("Created bouquet with %d channels" %
                     valid_count, module="Favorites")

            if valid_count == 0:
                return False, _("No valid stream URLs found")

            self._add_to_bouquets_tv(tag, bouquet_name)
            if reload_bouquets:
                self._reload_bouquets()

            message = (
                _("Exported") + " " +
                str(valid_count) + " " +
                _("channels from") + " " +
                str(len(channels_by_country)) + " " +
                _("countries")
            )
            return True, message

        except Exception as e:
            log.error(
                "Error exporting all channels: %s" %
                e, module="Favorites")
            return False, _("Error") + ": " + str(e)

    def _reload_bouquets(self):
        """Reload bouquets in Enigma2 (GUI thread only)"""
        try:
            from enigma import eDVBDB
            db = eDVBDB.getInstance()
            db.reloadServicelist()
            db.reloadBouquets()
            log.info("Bouquets reloaded via eDVBDB", module="Favorites")
            return True

        except Exception as e:
            log.error("eDVBDB reload failed: %s" % e, module="Favorites")

            # Fallback: OpenWebif
            result = system(
                "wget -qO - http://127.0.0.1/web/servicelistreload?mode=2 > /dev/null 2>&1")
            if result == 0:
                log.info(
                    "Bouquets reloaded via web interface",
                    module="Favorites")
                return True
            log.error("All reload methods failed", module="Favorites")
            return False

    def _add_to_bouquets_tv(self, tag, bouquet_name):
        """Add bouquet reference to bouquets.tv (honours list_position)"""
        position = get_config().get("list_position", "bottom")
        ok = add_bouquet_to_index(
            "userbouquet.%s_%s.tv" % (tag, bouquet_name), position)
        if ok:
            log.info("Bouquet referenced in bouquets.tv (%s)" %
                     position, module="Favorites")
        return ok

    def remove_bouquet(self, bouquet_name=None):
        """
        Remove TV Garden bouquets while PRESERVING the order of the others.
        bouquet_name=None removes ALL TV Garden bouquets.
        """
        try:
            import glob
            tag = "tvgarden"
            removed_files = 0
            removed_lines = 0

            if bouquet_name:
                safe = _safe_file_part(bouquet_name)
                marker = 'userbouquet.%s_%s.tv' % (tag, safe)
                bouquet_patterns = [
                    "%s/userbouquet.%s_%s.tv" % (ENIGMA_PATH, tag, safe)]
            else:
                marker = 'userbouquet.%s_' % tag
                bouquet_patterns = [
                    "%s/userbouquet.%s_*.tv" % (ENIGMA_PATH, tag),
                    "%s/subbouquet.%s_*.tv" % (ENIGMA_PATH, tag),
                    "%s/userbouquet.%s_*.del" % (ENIGMA_PATH, tag),
                    "%s/userbouquet.%s_*.radio" % (ENIGMA_PATH, tag),
                    "%s/userbouquet.%s_*.tv.backup" % (ENIGMA_PATH, tag)
                ]

            # 1. SAFE REMOVAL from bouquets.tv (preserve order)
            bouquet_tv_file = join(ENIGMA_PATH, "bouquets.tv")
            if exists(bouquet_tv_file):
                copy2(bouquet_tv_file, "%s.backup" % bouquet_tv_file)

                with open(bouquet_tv_file, "r") as f:
                    lines = f.readlines()

                new_lines = []
                for line in lines:
                    if marker in line:
                        removed_lines += 1
                        continue
                    new_lines.append(line)

                if removed_lines:
                    with open(bouquet_tv_file, "w") as f:
                        f.writelines(new_lines)
                    log.info(
                        "Removed %d bouquet references from bouquets.tv" %
                        removed_lines, module="Favorites")

            # 2. Remove the bouquet files
            for pattern in bouquet_patterns:
                for file_path in glob.glob(pattern):
                    try:
                        remove(file_path)
                        removed_files += 1
                        log.info("Removed: %s" % file_path, module="Favorites")
                    except Exception as e:
                        log.error(
                            "Failed to remove %s: %s" %
                            (file_path, e), module="Favorites")

            # 3. SOFT RELOAD
            self._reload_bouquets()

            message = (
                _("Removed") + " " +
                str(removed_files) + " " +
                _("files and") + " " +
                str(removed_lines) + " " +
                _("bouquet references")
            )
            return True, message

        except Exception as e:
            log.error("Error removing bouquet: %s" % e, module="Favorites")
            return False, _("Error: %s") % str(e)

    def export_single_channel(self, channel, bouquet_name=None):
        """Export a single channel to bouquet - LULULLA STYLE"""
        try:
            tag = "tvgarden"

            # If no bouquet name is provided, use prefix + favorites
            if bouquet_name is None:
                prefix = get_config().get("bouquet_name_prefix", "TVGarden")
                bouquet_name = "%s_favorites" % prefix.lower()
            bouquet_name = _safe_file_part(bouquet_name)

            userbouquet_file = self._bouquet_path(tag, bouquet_name)

            name = channel.get('name', 'TV Garden Channel')
            stream_url, is_youtube = bouquet_stream_url(channel)

            if not stream_url:
                return False, _("No stream URL")

            service_lines = bouquet_service_lines(stream_url, name)
            url_line = service_lines.split("\n")[0]

            if exists(userbouquet_file):
                with open(userbouquet_file, "r") as f:
                    content = f.read()
                if url_line in content.splitlines():
                    return False, _("Channel already in bouquet")
                with open(userbouquet_file, "a") as f:
                    if content and not content.endswith("\n"):
                        f.write("\n")
                    f.write(service_lines)
            else:
                with open(userbouquet_file, "w") as f:
                    f.write("#NAME TV Garden Favorites\n")
                    f.write(
                        "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | TV Garden Favorites by Lululla | ---\n")
                    f.write(
                        "#DESCRIPTION --- | TV Garden Favorites by Lululla | ---\n")
                    f.write(service_lines)

            # Update bouquets and reload
            self._add_to_bouquets_tv(tag, bouquet_name)
            self._reload_bouquets()

            message = _("Channel added to bouquet")
            if is_youtube:
                message += "\n\n%s" % _(YOUTUBE_BOUQUET_NOTE)
            return True, message

        except Exception as e:
            log.error("Error: %s" % e, module="Favorites")
            return False, _("Error: %s") % str(e)

    def export_all_channels_hierarchical(
            self, bouquet_name=None, reload_bouquets=True):
        """
        Export ALL channels with hierarchical structure.
        Safe to run in a worker thread with reload_bouquets=False.
        """
        try:
            log.info(
                "Starting hierarchical export of ALL channels",
                module="Favorites")
            all_channels, error = self._load_database_channels()
            if error:
                return False, error

            channels_by_country = self._group_by_country(all_channels)

            tag = "tvgarden"
            config = get_config()
            if bouquet_name is None:
                prefix = config.get("bouquet_name_prefix", "TVGarden")
                bouquet_name = "%s_complete" % prefix.lower()
            bouquet_name = _safe_file_part(bouquet_name)

            exported_countries = []
            total_channels = 0

            for country in sorted(channels_by_country.keys()):
                country_subs = self._create_country_sub_bouquets(
                    country, channels_by_country[country], tag, "tv")

                if country_subs:
                    country_info = {
                        'name': country,
                        'subs': country_subs,
                        'total_channels': sum(
                            sub['count'] for sub in country_subs)}
                    exported_countries.append(country_info)
                    total_channels += country_info['total_channels']

            if not exported_countries:
                return False, _("No channels to export")

            container_info = self._create_main_container(
                exported_countries, tag, bouquet_name, "tv",
                reload_bouquets=reload_bouquets)

            country_list_lines = []
            for country_info in exported_countries[:10]:
                country_list_lines.append("  • %s: %d channels in %d files" % (
                    country_info['name'],
                    country_info['total_channels'],
                    len(country_info['subs'])))

            country_list = "\n".join(country_list_lines)
            if len(exported_countries) > 10:
                country_list += "\n  • ... and %d more countries" % (
                    len(exported_countries) - 10)

            message = (
                _("Hierarchical export completed!") + "\n\n" +
                _("Statistics:") + "\n" +
                _("Total channels:") + " " + str(total_channels) + "\n" +
                _("Countries exported:") + " " + str(len(exported_countries)) + "\n" +
                _("Files created:") + " " +
                str(sum(len(c['subs']) for c in exported_countries)) + "\n\n" +
                _("Structure created:") + "\n" +
                country_list + "\n\n" +
                _("Main bouquet:") + " '" + container_info['name'] + "'"
            )

            return True, message

        except Exception as e:
            log.error(
                "Error in hierarchical export: %s" %
                e, module="Favorites")
            return False, _("Error: %s") % str(e)

    def _write_sub_bouquet(self, sub_path, title, channels):
        """Write one sub-bouquet file, return number of channels written"""
        title = encode_bouquet_text(title)
        count = 0
        with open(sub_path, 'w') as f:
            f.write("#NAME %s by Lululla\n" % title)
            f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- %s ---\n" % title)
            f.write("#DESCRIPTION --- %s ---\n" % title)
            for channel in channels:
                name = str(channel.get('name', '')).strip()
                stream_url = channel.get(
                    'stream_url') or channel.get('url', '')
                if not name or not stream_url:
                    continue
                f.write(bouquet_service_lines(stream_url, name))
                count += 1
        return count

    def _create_country_sub_bouquets(
            self, country, channels, tag, bouquet_type):
        """Create sub-bouquets for a single country (split if too big)"""
        max_channels_for_sub = get_config().get(
            "max_channels_for_sub_bouquet", 500)
        safe_country = _safe_file_part(country)

        # 0 = no limit: a single file per country
        if max_channels_for_sub <= 0 or len(channels) <= max_channels_for_sub:
            chunks = [channels]
        else:
            chunks = [channels[i:i + max_channels_for_sub]
                      for i in range(0, len(channels), max_channels_for_sub)]

        sub_bouquets = []
        for chunk_num, chunk in enumerate(chunks, 1):
            if len(chunks) == 1:
                sub_name = "subbouquet.%s_%s" % (tag, safe_country)
                title = country
            else:
                sub_name = "subbouquet.%s_%s_part%d" % (
                    tag, safe_country, chunk_num)
                title = "%s - Part %d" % (country, chunk_num)

            sub_file = "%s.%s" % (sub_name, bouquet_type)
            count = self._write_sub_bouquet(
                join(ENIGMA_PATH, sub_file), title, chunk)
            if not count:
                continue

            sub_bouquets.append({
                'file': sub_file,
                'name': title,
                'count': count,
                'reference': sub_name
            })
            log.info("Created sub-bouquet: %s with %d channels" %
                     (sub_file, count), module="Favorites")

        return sub_bouquets

    def _create_main_container(
            self,
            exported_countries,
            tag,
            bouquet_name,
            bouquet_type,
            reload_bouquets=True):
        """Create main container bouquet"""
        container_name = "userbouquet.%s_%s_container.%s" % (
            tag, bouquet_name, bouquet_type)
        container_path = join(ENIGMA_PATH, container_name)

        with open(container_path, 'w') as f:
            f.write("#NAME TV Garden - Complete Database by Lululla\n")
            f.write(
                "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | TV Garden Complete Database | ---\n")
            f.write("#DESCRIPTION --- | TV Garden Complete Database | ---\n")

            for country_info in exported_countries:
                country = country_info['name']
                country_display = encode_bouquet_text(
                    country.upper() if country != 'UNKNOWN' else 'OTHER')
                f.write(
                    "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- %s (%d channels) ---\n" %
                    (country_display, country_info['total_channels']))
                f.write("#DESCRIPTION --- %s (%d channels) ---\n" %
                        (country_display, country_info['total_channels']))

                for sub in country_info['subs']:
                    f.write(
                        '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' %
                        sub['file'])

        self._add_to_bouquets_tv(tag, "%s_container" % bouquet_name)
        if reload_bouquets:
            self._reload_bouquets()

        log.info("Created main container: %s" %
                 container_name, module="Favorites")

        return {
            'name': container_name,
            'path': container_path,
            'countries': len(exported_countries)
        }

    def clear_all(self):
        """Clear all favorites"""
        count = len(self.favorites)
        self.favorites = []
        if self.save_favorites():
            log.info(
                "✓ Cleared all favorites (%d)" %
                count, module="Favorites")
            return True, _("Cleared %d favorites") % count
        else:
            log.error("✗ Failed to clear favorites", module="Favorites")
            return False, _("Error clearing favorites")
