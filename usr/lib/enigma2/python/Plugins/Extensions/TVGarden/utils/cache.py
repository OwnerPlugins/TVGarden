#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Cache Module
Smart caching with TTL + gzip
Based on TV Garden Project

[TVGarden patch] Supporto multi-sorgente (tv / webcams).
- Tutte le funzioni pubbliche accettano `media_type` (default "tv")
- Le cache key sono separate per media_type (no collisioni TV/Webcams)
- get_available_categories() legge dalla GitHub API con fallback minimo
"""
import time
import hashlib
import gzip
from os.path import join, exists, getmtime, getsize
from os import listdir, remove, makedirs
from json import load, loads, dump, dumps
from urllib.request import urlopen, Request

from .config import get_config


try:
    from ..helpers import (
        get_metadata_url,
        get_country_url,
        get_category_url,
        get_categories_url,
        get_all_channels_url,
        CATEGORIES_FALLBACK,
        log
    )
except ImportError as e:
    print('Error import helpers:', str(e))

    def log(message, level="INFO", module=""):
        print("[%s] [%s] TVGarden: %s" % (level, module, message))

    CATEGORIES_FALLBACK = [{'id': 'all', 'name': 'All'}]

    def get_metadata_url(media_type="tv"):
        return "https://raw.githubusercontent.com/OwnerPlugins/famelack-data/refs/heads/main/%s/raw/countries_metadata.json" % media_type

    def get_country_url(code, media_type="tv"):
        return "https://raw.githubusercontent.com/OwnerPlugins/famelack-data/refs/heads/main/%s/raw/countries/%s.json" % (media_type, code.lower())

    def get_category_url(cat_id, media_type="tv"):
        return "https://raw.githubusercontent.com/OwnerPlugins/famelack-data/refs/heads/main/%s/raw/categories/%s.json" % (media_type, cat_id)

    def get_categories_url(media_type="tv"):
        return "https://api.github.com/repos/OwnerPlugins/famelack-data/contents/%s/raw/categories" % media_type

    def get_all_channels_url(media_type="tv"):
        return "https://raw.githubusercontent.com/OwnerPlugins/famelack-data/refs/heads/main/%s/raw/categories/all.json" % media_type


class CacheManager:
    """Smart cache manager with TTL support"""

    def __init__(self):
        self.cache_dir = "/tmp/tvgarden_cache"

        # DEBUG: Verify directory
        log.debug("Cache directory: %s, exists: %s" %
                  (self.cache_dir, exists(self.cache_dir)), module="Cache")

        if not exists(self.cache_dir):
            makedirs(self.cache_dir)

        files = listdir(self.cache_dir)
        log.debug("Files in cache: %s" % files, module="Cache")

        self.cache_data = {}
        self._load_cache()
        log.info("Initialized at %s" % self.cache_dir, module="Cache")

    def _load_cache(self):
        """Load memory cache from disk"""
        try:
            cache_file = join(self.cache_dir, "memory_cache.json")
            if exists(cache_file):
                with open(cache_file, 'r') as f:
                    self.cache_data = load(f)
                log.debug(
                    "Memory cache loaded from %s" %
                    cache_file, module="Cache")
                return True
        except Exception as e:
            log.error("Error loading memory cache: %s" % e, module="Cache")
        return False

    def _save_cache(self):
        """Save memory cache to disk"""
        try:
            cache_file = join(self.cache_dir, "memory_cache.json")
            f = None
            try:
                f = open(cache_file, 'w')
                dump(self.cache_data, f)
                log.debug(
                    "Memory cache saved to %s" %
                    cache_file, module="Cache")
                return True
            finally:
                if f:
                    f.close()
        except Exception as e:
            log.error("Error saving memory cache: %s" % e, module="Cache")
            return False

    def get_cache_info(self):
        """Get detailed cache information"""
        try:
            files = []
            try:
                files = listdir(self.cache_dir)
            except Exception as e:
                log.error("Cannot list cache dir: %s" % str(e), module="Cache")
                return {'error': str(e)}

            # Filter real cache files (exclude logs)
            cache_files = []
            for f in files:
                # Include .gz files and .json cache files (not logs)
                if (f.endswith('.gz') or (f.endswith('.json')
                                          and f not in ['memory_cache.json', 'tvgarden.log'])):
                    cache_files.append(f)

            # Calculate total size
            total_size = 0
            for f in cache_files:
                file_path = join(self.cache_dir, f)
                try:
                    total_size += getsize(file_path)
                except BaseException:
                    pass

            info = {
                'total_files': len(cache_files),
                'cache_files': cache_files[:10],
                'total_size_kb': total_size / 1024.0,
                'cache_dir': self.cache_dir,
                'memory_entries': len(self.cache_data)
            }

            log.debug("Cache info: %d files, %.1fKB" % (
                len(cache_files), total_size / 1024.0
            ), module="Cache")
            return info

        except Exception as e:
            log.error("Error getting cache info: %s" % str(e), module="Cache")
            return {'error': str(e)}

    def _get_cache_key(self, url):
        """Generate cache key from URL"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, key):
        """Get cache file path"""
        return join(self.cache_dir, "%s.json.gz" % key)

    def _is_cache_valid(self, cache_path, ttl=3600):
        """Check if cache is still valid"""
        if not exists(cache_path):
            return False

        file_age = time.time() - getmtime(cache_path)
        return file_age < ttl

    def _get_cached(self, cache_key):
        """Get data from cache"""
        cache_path = self._get_cache_path(cache_key)
        if exists(cache_path):
            try:
                with gzip.open(cache_path, 'rb') as f:
                    compressed_data = f.read()

                json_str = compressed_data.decode('utf-8')

                # Parse JSON
                return loads(json_str)

            except Exception as e:
                log.error(
                    "Error reading %s: %s" %
                    (cache_key, e), module="Cache")
        return None

    def _set_cached(self, cache_key, data):
        """Save data to cache"""
        cache_path = self._get_cache_path(cache_key)
        try:
            try:
                text_type = unicode  # Python 2
            except NameError:
                text_type = str      # Python 3

            json_str = dumps(data, ensure_ascii=False)

            if isinstance(json_str, text_type):
                json_str = json_str.encode('utf-8')

            with gzip.open(cache_path, 'wb') as f:
                f.write(json_str)

            return True

        except Exception as e:
            log.error("Error saving %s: %s" % (cache_key, e), module="Cache")
            return False

    def _fetch_url(self, url):
        """Fetch URL"""
        try:
            headers = {'User-Agent': 'TVGarden-Enigma2/1.0'}
            req = Request(url, headers=headers)
            config = get_config()
            timeout = config.get("connection_timeout", 10)

            log.debug(
                "Fetching URL: %s (timeout: %ss)" %
                (url, timeout), module="Cache")

            response = None
            try:
                response = urlopen(req, timeout=timeout)

                # === CRITICAL FIX FOR PYTHON 2 ===
                # 1. First, check HTTP status code
                if hasattr(response, 'getcode'):
                    http_code = response.getcode()
                    log.debug(
                        "HTTP Status Code: %d" %
                        http_code, module="Cache")

                    if http_code != 200:
                        log.error(
                            "HTTP Error %d for URL: %s" %
                            (http_code, url), module="Cache")
                        try:
                            error_body = response.read()
                            if isinstance(error_body, bytes):
                                log.debug("Error body: %s" %
                                          error_body[:100], module="Cache")
                        except BaseException:
                            pass
                        raise Exception("HTTP Error %d" % http_code)

                # 2. Read response data
                raw_data = response.read()
                log.debug(
                    "Raw data type: %s, length: %d"
                    % (type(raw_data), len(raw_data) if raw_data else 0),
                    module="Cache"
                )

                # 3. IF raw_data is int → THIS IS AN HTTP ERROR IN PYTHON 2
                if isinstance(raw_data, int):
                    http_code = raw_data
                    log.error(
                        "PYTHON 2 BUG: response.read() returned int %d for URL: %s" %
                        (http_code, url), module="Cache")
                    raise Exception("HTTP Error %d (Python 2 bug)" % http_code)

                # 4. Convert to bytes if needed
                if isinstance(raw_data, str):  # Python 2 string
                    raw_data = raw_data.encode('utf-8')

                if not isinstance(raw_data, bytes):
                    log.error(
                        "Invalid data type: %s for URL: %s"
                        % (type(raw_data), url),
                        module="Cache"
                    )
                    raise Exception("Invalid response type")
                # === END FIX ===

                # raw_data is now guaranteed to be bytes
                data = raw_data

                if len(data) > 0:
                    log.debug("First 100 chars: %s" %
                              data[:100], module="Cache")

                # Try to decode as JSON
                try:
                    json_data = loads(data.decode('utf-8'))
                    log.debug(
                        "Successfully decoded JSON, type: %s" %
                        type(json_data), module="Cache")
                    return json_data
                except Exception as json_error:
                    log.debug(
                        "JSON decode failed: %s" %
                        json_error, module="Cache")
                    # Try gzip decompression
                    try:
                        return loads(gzip.decompress(data).decode('utf-8'))
                    except BaseException:
                        # Fallback: return decoded text
                        return data.decode('utf-8', errors='ignore')

            finally:
                if response:
                    response.close()

        except Exception as e:
            log.error("Error fetching %s: %s" % (url, str(e)), module="Cache")
            raise

    def fetch_url(self, url, force_refresh=False, ttl=3600):
        """Fetch URL with caching support"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)

        log.debug("Fetch URL: %s" % url, module="Cache")
        log.debug("Cache key: %s" % cache_key, module="Cache")
        log.debug("Force refresh: %s" % force_refresh, module="Cache")

        if not force_refresh and self._is_cache_valid(cache_path, ttl):
            try:
                log.debug("Using CACHED data for: %s" % url, module="Cache")
                return self._get_cached(cache_key)
            except BaseException:
                log.debug("Cache read failed, fetching fresh", module="Cache")
                pass

        try:
            log.debug("Fetching FRESH data for: %s" % url, module="Cache")
            result = self._fetch_url(url)

            log.debug("Saving to cache: %s" % cache_key, module="Cache")
            self._set_cached(cache_key, result)

            return result
        except Exception as e:
            log.error("Error in fetch_url: %s" % e, module="Cache")
            raise

    # ============================================================
    # [TVGarden patch] Categorie lette dinamicamente dalla GitHub API
    # ============================================================
    def get_available_categories(self, media_type="tv", force_refresh=False):
        """
        Get list of available categories from GitHub directory.

        Legge dinamicamente i file .json presenti in:
            {media_type}/raw/categories/
        e ritorna una lista di dict {'id': ..., 'name': ...}.

        Fallback: se la API non risponde E la cache è vuota,
        ritorna CATEGORIES_FALLBACK (solo "all").
        """
        cache_key = "available_categories_%s" % media_type

        # 1. Cache in-memory (se non forziamo refresh)
        if not force_refresh and cache_key in self.cache_data:
            log.debug(
                "Using MEMORY cached categories for %s (%d)" %
                (media_type, len(self.cache_data[cache_key])),
                module="Cache")
            return self.cache_data[cache_key]

        # 2. Cache su disco (via fetch_url, che è md5-based)
        try:
            categories_url = get_categories_url(media_type)
            log.debug("Fetching categories for %s from %s" %
                      (media_type, categories_url), module="Cache")

            data = self.fetch_url(categories_url, force_refresh=force_refresh)

            # Extract .json filenames
            categories = []
            for item in data:
                if item.get('name', '').endswith('.json'):
                    category_id = item['name'].replace('.json', '')
                    name = category_id.replace('-', ' ').replace('_', ' ').title()
                    categories.append({'id': category_id, 'name': name})

            # Ordina: "all" prima, poi il resto alfabetico
            categories.sort(key=lambda c: (c['id'] != 'all', c['name'].lower()))

            # Salva in memory
            self.cache_data[cache_key] = categories
            self._save_cache()

            log.info(
                "Found %d categories for %s from GitHub" %
                (len(categories), media_type), module="Cache")
            return categories

        except Exception as e:
            log.error("Error getting categories for %s: %s" %
                      (media_type, e), module="Cache")

            # Fallback: cache disco già presente? La usiamo.
            # (fetch_url la userebbe, ma se siamo qui è perché è fallito tutto)
            log.warning(
                "Using minimal fallback for %s categories" % media_type,
                module="Cache")
            return list(CATEGORIES_FALLBACK)

    # ============================================================
    # [TVGarden patch] get_country_channels con media_type
    # ============================================================
    def get_country_channels(self, country_code, media_type="tv", force_refresh=False):
        """Get channels for specific country - WORKING VERSION"""
        try:
            url = get_country_url(country_code, media_type)
            log.debug("Fetching %s/%s (force_refresh=%s)" %
                      (media_type, country_code, force_refresh), module="Cache")

            # 1. Fetch the raw JSON data
            raw_result = self.fetch_url(url, force_refresh)

            log.debug("RAW RESULT TYPE: %s" % type(raw_result), module="Cache")

            if raw_result is None:
                log.error("NULL result for %s/%s" %
                          (media_type, country_code), module="Cache")
                return []

            # 2. CASE 1: Already a list of channels (old structure)
            if isinstance(raw_result, list):
                log.info(
                    "✓ Direct list: %d channels for %s/%s" %
                    (len(raw_result), media_type, country_code), module="Cache")
                return raw_result

            # 3. CASE 2: Dictionary (new structure)
            if isinstance(raw_result, dict):
                dict_keys = list(raw_result.keys())
                log.debug("Dict keys: %s" % dict_keys[:10], module="Cache")

                country_code_upper = country_code.upper()
                country_code_lower = country_code.lower()

                country_data = None
                found_key = None

                if country_code_upper in raw_result:
                    country_data = raw_result[country_code_upper]
                    found_key = country_code_upper
                elif country_code_lower in raw_result:
                    country_data = raw_result[country_code_lower]
                    found_key = country_code_lower
                else:
                    for key in dict_keys:
                        if isinstance(
                                key, str) and key.upper() == country_code_upper:
                            country_data = raw_result[key]
                            found_key = key
                            break

                if not country_data:
                    log.error(
                        "Country '%s' not found in keys: %s" %
                        (country_code, dict_keys), module="Cache")
                    return []

                log.debug(
                    "Found country data under key: '%s'" %
                    found_key, module="Cache")

                if isinstance(country_data, list):
                    log.info(
                        "✓ Country data is list: %d channels for %s/%s" %
                        (len(country_data), media_type, country_code),
                        module="Cache")
                    return country_data

                if isinstance(country_data, dict):
                    channel_fields = ['channels', 'items', 'streams', 'data']

                    for field in channel_fields:
                        if field in country_data:
                            field_data = country_data[field]
                            if isinstance(field_data, list):
                                log.info(
                                    "✓ Found %d channels in field '%s' for %s/%s" %
                                    (len(field_data), field, media_type, country_code),
                                    module="Cache")
                                return field_data

                    log.error("No 'channels' field found for %s/%s. Available keys: %s" % (
                        media_type, country_code, list(country_data.keys())),
                        module="Cache")
                    return []

                log.error(
                    "Unexpected country data type for %s/%s: %s" %
                    (media_type, country_code, type(country_data)),
                    module="Cache")
                return []

            # 4. CASE 3: Unexpected type
            log.error(
                "Unexpected raw result type for %s/%s: %s" %
                (media_type, country_code, type(raw_result)), module="Cache")
            return []

        except Exception as e:
            log.error(
                "ERROR in get_country_channels for %s/%s: %s" %
                (media_type, country_code, str(e)), module="Cache")
            import traceback
            traceback.print_exc()
            return []

    # ============================================================
    # [TVGarden patch] get_category_channels con media_type
    # Cache key SEPARATA per media_type (evita collisioni TV/Webcams)
    # ============================================================
    def get_category_channels(self, category_id, media_type="tv", force_refresh=False):
        """Get channels for a specific category"""
        cache_key = "cat_%s_%s" % (media_type, category_id)

        if not force_refresh:
            cached_data = self._get_cached(cache_key)
            if cached_data is not None:
                log.debug(
                    "Using CACHED data for category: %s/%s" %
                    (media_type, category_id), module="Cache")
                return cached_data

        try:
            url = get_category_url(category_id, media_type)
            log.debug(
                "Fetching FRESH data for category: %s/%s" %
                (media_type, category_id), module="Cache")
            data = self._fetch_url(url)

            channels = []
            if isinstance(data, list):
                channels = data
            elif isinstance(data, dict):
                for key in ['channels', 'items', 'streams', 'list']:
                    if key in data and isinstance(data[key], list):
                        channels = data[key]
                        break

            log.debug(
                "Extracted %d channels for %s/%s" %
                (len(channels), media_type, category_id), module="Cache")

            if channels:
                self._set_cached(cache_key, channels)
            return channels

        except Exception as e:
            log.error(
                "Failed to get category %s/%s: %s" %
                (media_type, category_id, e), module="Cache")
            import traceback
            traceback.print_exc()
        return []

    # ============================================================
    # [TVGarden patch] get_countries_metadata con media_type
    # ============================================================
    def get_countries_metadata(self, media_type="tv", force_refresh=False):
        """Get countries metadata"""
        url = get_metadata_url(media_type)
        return self.fetch_url(url, force_refresh)

    def clear_all(self):
        """Clear all cache"""
        # Clear disk cache
        for file in listdir(self.cache_dir):
            if file.endswith('.json.gz'):
                remove(join(self.cache_dir, file))

        # Clear memory cache
        self.cache_data = {}
        self._save_cache()

        log.info("Cache cleared (disk + memory)", module="Cache")
        return True

    def get_size(self):
        """Get cache size in items - Use get_cache_info"""
        try:
            info = self.get_cache_info()
            if 'error' in info:
                return 0
            return info.get('total_files', 0)
        except Exception as e:
            log.error("Error in get_size: %s" % str(e), module="Cache")
            return 0
