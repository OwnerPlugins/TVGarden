#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Favorites Manager
Manages favorite channels storage
Based on TV Garden Project
"""
from __future__ import print_function
import time
from os import makedirs, remove, system
from os.path import exists, join
from json import load, dump
from hashlib import md5
from shutil import copy2

from ..helpers import log, get_all_channels_url
from ..utils.config import get_config
from ..utils.cache import CacheManager
from .. import _


ENIGMA_PATH = "/etc/enigma2"


class FavoritesManager:
    """Manage favorite channels"""
    def __init__(self):
        self.fav_dir = "/etc/enigma2/tvgarden/favorites"
        self.fav_file = join(self.fav_dir, "favorites.json")

        if not exists(self.fav_dir):
            makedirs(self.fav_dir)

        self.favorites = self.load_favorites()
        log.info("Initialized with %d favorites" % len(self.favorites), module="Favorites")

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
                    return load(f)
            except:
                return []
        return []

    def save_favorites(self):
        """Save favorites to file"""
        try:
            with open(self.fav_file, 'w') as f:
                dump(self.favorites, f, indent=2)
            return True
        except:
            return False

    def save_bouquet_file(self, filepath, data):
        """Save bouquet file (NON gzip)"""
        try:
            with open(filepath, 'w') as f:
                dump(data, f, indent=2)
            return True
        except Exception as e:
            log.error("Error saving bouquet %s: %s" % (filepath, e), module="Favorites")
            return False

    def generate_id(self, channel):
        """Generate unique ID for channel"""
        # Use stream URL as base for ID
        stream_url = channel.get('stream_url', '')
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

        channel_id = self.generate_id(channel)
        channel_name = channel.get('name', 'Unknown')

        channel['id'] = channel_id
        channel['added'] = time.time()

        self.favorites.append(channel)

        if self.save_favorites():
            log.info("✓ Added to favorites: %s" % channel_name, module="Favorites")
            return True, _("Added to favorites: %s") % channel_name
        else:
            log.error("✗ Failed to save favorites: %s" % channel_name, module="Favorites")
            return False, _("Error saving favorites")

    def remove(self, channel):
        """Remove channel from favorites"""
        channel_id = self.generate_id(channel)
        channel_name = channel.get('name', 'Unknown')

        for i, fav in enumerate(self.favorites):
            if fav.get('id') == channel_id:
                del self.favorites[i]
                if self.save_favorites():
                    log.info("✓ Removed from favorites: %s" % channel_name, module="Favorites")
                    return True, _("Removed from favorites: %s") % channel_name
                else:
                    log.error("✗ Failed to save after removal: %s" % channel_name, module="Favorites")
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
            name = fav.get('name', '').lower()
            group = fav.get('group', '').lower()
            desc = fav.get('description', '').lower()

            if query in name or query in group or query in desc:
                results.append(fav)
        return results

    def _create_bouquet_files(self):
        """Create actual bouquet files - LULULLA STYLE"""
        try:
            bouquet_name = "TVGarden"
            tag = "tvgarden"
            userbouquet_file = "/etc/enigma2/userbouquet.%s_%s.tv" % (tag, bouquet_name)

            with open(userbouquet_file, "w") as f:
                # LULULLA STYLE HEADER
                f.write("#NAME TV Garden Favorites by Lululla\n")
                f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0:::--- | TV Garden Favorites by Lululla | ---\n")
                f.write("#DESCRIPTION --- | TV Garden Favorites by Lululla | ---\n")

                for idx, channel in enumerate(self.favorites, 1):
                    name = channel.get('name', 'Channel %d' % idx)
                    stream_url = channel.get('stream_url') or channel.get('url', '')

                    if not stream_url:
                        continue

                    url_encoded = stream_url.replace(":", "%3a")
                    name_encoded = name.replace(":", "%3a")

                    # ONE service line for channel
                    service_line = '#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n' % (url_encoded, name_encoded)
                    f.write(service_line)
                    f.write('#DESCRIPTION %s\n' % name)

            return True

        except Exception as e:
            log.error("Error: %s" % e, module="Favorites")
            return False

    def export_to_bouquet(self, channels=None, bouquet_name=None):
        """Export channels to an Enigma2 bouquet file"""
        try:
            if channels is None:
                channels = self.favorites

            if not channels or len(channels) == 0:
                return False, _("No channels to export")

            # Read configuration
            config = get_config()
            max_channels = config.get("max_channels_for_bouquet", 100)

            # Apply channel limit if specified
            if max_channels > 0 and len(channels) > max_channels:
                channels = channels[:max_channels]
                log.info("Limited to %d channels" % max_channels, module="Favorites")

            tag = "tvgarden"

            # If no bouquet name is provided, use prefix + favorites
            if bouquet_name is None:
                prefix = config.get("bouquet_name_prefix", "TVGarden")
                bouquet_name = "%s_favorites" % prefix.lower()

            userbouquet_file = "/etc/enigma2/userbouquet.%s_%s.tv" % (tag, bouquet_name)

            # 1. Group channels by country
            channels_by_country = {}
            for channel in channels:
                country = channel.get('country', 'Unknown')
                if country not in channels_by_country:
                    channels_by_country[country] = []
                channels_by_country[country].append(channel)

            # 2. Write the bouquet file
            try:
                f = open(userbouquet_file, "w")

                # Write header
                f.write("#NAME TV Garden Favorites by Lululla\n")
                f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | TV Garden Favorites by Lululla | ---\n")
                f.write("#DESCRIPTION --- | TV Garden Favorites by Lululla | ---\n")

                valid_count = 0

                # 3. Write countries and channels
                for country in sorted(channels_by_country.keys()):
                    country_channels = channels_by_country[country]

                    if not country_channels:
                        continue

                    # Country separator
                    f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- %s ---\n" % country.upper())
                    f.write("#DESCRIPTION --- %s ---\n" % country.upper())

                    # Write channels for this country
                    for channel in country_channels:
                        name = channel.get('name', 'Channel')
                        stream_url = channel.get('stream_url') or channel.get('url', '')

                        if not stream_url:
                            continue

                        # Encoding
                        url_encoded = stream_url.replace(":", "%3a")
                        name_encoded = name.replace(":", "%3a")

                        # Write channel entry
                        f.write('#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n' % (url_encoded, name_encoded))
                        f.write('#DESCRIPTION %s\n' % name)

                        valid_count += 1

                f.close()

            except Exception as e:
                log.error("Error writing bouquet file: %s" % e, module="Favorites")
                return False, _("Error writing file: %s") % str(e)

            if valid_count == 0:
                return False, _("No valid stream URLs found")

            # Add to bouquets and reload
            self._add_to_bouquets_tv(tag, bouquet_name)
            self._reload_bouquets()

            return True, _("Exported %d channels to bouquet") % valid_count

        except Exception as e:
            log.error("Error: %s" % e, module="Favorites")
            return False, _("Error: %s") % str(e)

    def export_to_bouquetxxx(self, channels=None, bouquet_name=None):
        """Export channels to an Enigma2 bouquet file"""
        try:
            if channels is None:
                channels = self.favorites

            if not channels or len(channels) == 0:
                return False, _("No channels to export")

            # Read configuration
            config = get_config()
            max_channels = config.get("max_channels_for_bouquet", 100)

            # Apply channel limit if specified
            if max_channels > 0 and len(channels) > max_channels:
                channels = channels[:max_channels]
                log.info("Limited to %d channels" % max_channels, module="Favorites")

            tag = "tvgarden"

            # If no bouquet name is provided, use prefix + favorites
            if bouquet_name is None:
                prefix = config.get("bouquet_name_prefix", "TVGarden")
                bouquet_name = "%s_favorites" % prefix.lower()

            userbouquet_file = "/etc/enigma2/userbouquet.%s_%s.tv" % (tag, bouquet_name)

            # 1. Group channels by country
            channels_by_country = {}
            for channel in channels:
                country = channel.get('country', 'Unknown')
                if country not in channels_by_country:
                    channels_by_country[country] = []
                channels_by_country[country].append(channel)

            try:
                f = open(userbouquet_file, "w")
                try:
                    f.write("#NAME TV Garden Favorites by Lululla\n")
                    f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | TV Garden Favorites by Lululla | ---\n")
                    f.write("#DESCRIPTION --- | TV Garden Favorites by Lululla | ---\n")

                    valid_count = 0

                    # 2. Process each country group
                    for country, country_channels in channels_by_country.items():
                        # Add country marker
                        f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- %s ---\n" % country.upper())
                        f.write("#DESCRIPTION --- %s ---\n" % country.upper())

                        # Write channels for this country
                        for channel in country_channels:
                            name = channel.get('name', 'Channel')
                            stream_url = channel.get('stream_url') or channel.get('url', '')

                            if not stream_url:
                                continue

                            # Encoding
                            url_encoded = stream_url.replace(":", "%3a")
                            name_encoded = name.replace(":", "%3a")

                            # Use 4097:0:1:0:0:0:0:0:0:0 format
                            service_line = '#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n' % (url_encoded, name_encoded)
                            f.write(service_line)
                            f.write('#DESCRIPTION %s\n' % name)

                            valid_count += 1

                    # Remove last empty line if needed
                    f.seek(0, 2)  # Go to end of file
                    f.seek(f.tell() - 1, 0)  # Go back one character
                    if f.read(1) == '\n':
                        f.seek(f.tell() - 1, 0)
                        f.truncate()

                finally:
                    f.close()

            except Exception as e:
                log.error("Error writing bouquet file: %s" % e, module="Favorites")
                return False, _("Error writing file: %s") % str(e)

            if valid_count == 0:
                return False, _("No valid stream URLs found")

            # Add to bouquets and reload
            self._add_to_bouquets_tv(tag, bouquet_name)
            self._reload_bouquets()

            return True, _("Exported %d channels to bouquet") % valid_count

        except Exception as e:
            log.error("Error: %s" % e, module="Favorites")
            return False, _("Error: %s") % str(e)

    def export_all_channels(self, bouquet_name=None):
        """Export ALL channels from TV Garden database"""
        try:
            cache = CacheManager()
            config = get_config()

            log.info("Starting export of ALL channels from database", module="Favorites")
            all_channels_url = get_all_channels_url()

            try:
                # Read from settings
                cache_enabled = config.get("cache_enabled", True)
                force_refresh_export = config.get("force_refresh_export", False)

                if cache_enabled:
                    all_channels_data = cache.fetch_url(all_channels_url, force_refresh=force_refresh_export)
                else:
                    # Cache disabled, always fresh
                    all_channels_data = cache._fetch_url(all_channels_url)

                if not all_channels_data:
                    return False, _("Empty database")

                log.debug(
                    "Data type: %s, length: %d" % (type(all_channels_data), len(all_channels_data)),
                    module="Favorites"
                )

                # Log first channel for debugging
                if all_channels_data and len(all_channels_data) > 0:
                    log.debug(
                        "First channel keys: %s" % list(all_channels_data[0].keys()),
                        module="Favorites"
                    )
                    log.debug(
                        "First channel iptv_urls: %s" % all_channels_data[0].get('iptv_urls', []),
                        module="Favorites"
                    )

            except Exception as e:
                log.error("Failed to fetch: %s" % e, module="Favorites")
                return False, _("Failed to load database")

            all_channels = []
            country_counts = {}

            if isinstance(all_channels_data, list):
                log.info(
                    "Processing %d channels from database" % len(all_channels_data),
                    module="Favorites"
                )

                for idx, channel in enumerate(all_channels_data):
                    try:
                        # Get stream URL from iptv_urls list
                        iptv_urls = channel.get('iptv_urls', [])
                        stream_url = None

                        if isinstance(iptv_urls, list) and len(iptv_urls) > 0:
                            stream_url = iptv_urls[0]
                        elif channel.get('youtube_urls'):
                            # Skip YouTube channels
                            continue

                        if not stream_url:
                            continue

                        # Skip problematic streams
                        stream_lower = stream_url.lower()
                        problematic_patterns = [
                            '.mpd', '/dash/', 'drm', 'widevine', 'flex-cdn.net'
                        ]

                        if any(p in stream_lower for p in problematic_patterns):
                            log.debug(
                                "Skipped problematic: %s" % channel.get('name', ''),
                                module="Favorites"
                            )
                            continue

                        # Get country code
                        country_code = channel.get('country', 'UNKNOWN')
                        if country_code not in country_counts:
                            country_counts[country_code] = 0
                        country_counts[country_code] += 1

                        # Build channel data
                        channel_data = {
                            'name': channel.get('name', 'Channel %d' % idx),
                            'stream_url': stream_url,
                            'url': stream_url,
                            'country': country_code,
                            'language': channel.get('language', ''),
                            'isGeoBlocked': channel.get('isGeoBlocked', False)
                        }

                        all_channels.append(channel_data)

                        # Log progress every 100 channels
                        if idx % 100 == 0:
                            log.debug(
                                "Processed %d/%d channels" %
                                (idx, len(all_channels_data)),
                                module="Favorites"
                            )

                    except Exception as e:
                        log.debug(
                            "Error processing channel %d: %s" % (idx, e),
                            module="Favorites"
                        )
                        continue

            log.info(
                "Total valid channels loaded: %d from %d countries" %
                (len(all_channels), len(country_counts)),
                module="Favorites"
            )

            # Log top 5 countries
            sorted_countries = sorted(
                country_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            for country, count in sorted_countries:
                log.info(
                    "  %s: %d channels" % (country, count),
                    module="Favorites"
                )

            if len(all_channels) == 0:
                return False, _("No valid channels found in database")

            # Remaining code to create the bouquet
            tag = "tvgarden"
            config = get_config()

            if bouquet_name is None:
                prefix = config.get("bouquet_name_prefix", "TVGarden")
                bouquet_name = "%s_all_channels" % prefix.lower()

            userbouquet_file = "/etc/enigma2/userbouquet.%s_%s.tv" % (
                tag, bouquet_name
            )

            # Group channels by country
            channels_by_country = {}
            for channel in all_channels:
                country = channel.get('country', 'UNKNOWN')
                if country not in channels_by_country:
                    channels_by_country[country] = []
                channels_by_country[country].append(channel)

            # Write the bouquet file organized by country
            with open(userbouquet_file, "w") as f:
                f.write("#NAME %s - TV Garden All by Lululla\n" % prefix)
                f.write(
                    "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | %s TV Garden by Lululla | ---\n"
                    % prefix
                )
                f.write(
                    "#DESCRIPTION --- | %s TV Garden by Lululla | ---\n"
                    % prefix
                )

                valid_count = 0

                # OPTIMIZED WRITE
                for country in sorted(channels_by_country.keys()):
                    country_channels = channels_by_country[country]

                    if not country_channels:
                        continue

                    # OPTIMIZED COUNTRY SEPARATOR (single line)
                    country_display = (
                        country.upper() if country != 'UNKNOWN' else 'OTHER'
                    )
                    f.write(
                        "#SERVICE 1:64:0:0:0:0:0:0:0:0::%s (%d)\n" %
                        (country_display, len(country_channels))
                    )

                    # COMPACT CHANNEL FORMAT
                    for channel in country_channels:
                        name = channel.get('name', '').strip()
                        stream_url = channel.get('stream_url') or channel.get('url', '')

                        if not name or not stream_url:
                            continue

                        # Encoding
                        url_encoded = stream_url.replace(":", "%3a")
                        name_encoded = name.replace(":", "%3a")

                        # Use 4097:0:1:0:0:0:0:0:0:0 format
                        service_line = (
                            "#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n" %
                            (url_encoded, name_encoded)
                        )

                        f.write(service_line)
                        f.write("#DESCRIPTION %s\n" % name)
                        valid_count += 1

                log.info(
                    "Created OPTIMIZED bouquet with %d channels" % valid_count,
                    module="Favorites"
                )

            if valid_count == 0:
                return False, _("No valid stream URLs found")

            # Add to bouquets.tv and reload
            self._add_to_bouquets_tv(tag, bouquet_name)
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
            log.error("Error exporting all channels: %s" % e, module="Favorites")
            import traceback
            traceback.print_exc()
            return False, _("Error") + ": " + str(e)

    def _reload_bouquets(self):
        """Reload bouquets in Enigma2"""
        try:
            from enigma import eDVBDB
            db = eDVBDB.getInstance()
            db.reloadServicelist()
            db.reloadBouquets()

            # Additional delay to ensure reload completes
            time.sleep(1)
            log.info("Bouquets reloaded via eDVBDB", module="Favorites")
            return True

        except Exception as e:
            log.error("eDVBDB reload failed: %s" % e, module="Favorites")

            # Fallback: try shell command
            try:
                system("wget -qO - http://127.0.0.1/web/servicelistreload > /dev/null 2>&1")
                log.info("Bouquets reloaded via web interface", module="Favorites")
                return True
            except:
                log.error("All reload methods failed", module="Favorites")
                return False

    def _add_to_bouquets_tv(self, tag, bouquet_name):
        """Add bouquet reference to bouquets.tv"""
        try:
            bouquet_tv_file = "/etc/enigma2/bouquets.tv"
            bouquet_line = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.%s_%s.tv" ORDER BY bouquet\n' % (tag, bouquet_name)

            if exists(bouquet_tv_file):
                # Read entire file
                with open(bouquet_tv_file, "r") as f:
                    content = f.read()
                    lines = content.split('\n')

                # Check if already exists
                if bouquet_line.strip() in [line.strip() for line in lines if line.strip()]:
                    log.info("Bouquet already in bouquets.tv", module="Favorites")
                    return True

                # Check if last line is empty
                last_line_empty = (not lines or lines[-1].strip() == '')

                # Append to file
                with open(bouquet_tv_file, "a") as f:
                    if not last_line_empty:
                        f.write("\n")
                    f.write(bouquet_line)

                log.info("Added bouquet to END of bouquets.tv", module="Favorites")
                return True
            else:
                # Create new bouquets.tv file
                with open(bouquet_tv_file, "w") as f:
                    f.write("#NAME Bouquets (TV)\n")
                    f.write("#SERVICE 1:7:1:0:0:0:0:0:0:0:\n")
                    f.write("\n# TV Garden Favorites\n")
                    f.write(bouquet_line)

                log.info("Created bouquets.tv with TV Garden bouquet", module="Favorites")
                return True

        except Exception as e:
            log.error("Error updating bouquets.tv: %s" % e, module="Favorites")
            return False

    def remove_bouquet(self, bouquet_name=None):
        """Remove bouquet while PRESERVING original order"""
        try:
            tag = "tvgarden"
            removed_files = 0
            removed_lines = 0

            # 1. SAFE REMOVAL from bouquets.tv (preserve order)
            bouquet_tv_file = "/etc/enigma2/bouquets.tv"

            if exists(bouquet_tv_file):
                # Backup original file
                backup_file = "%s.backup" % bouquet_tv_file
                copy2(bouquet_tv_file, backup_file)

                # Read original lines without altering order
                with open(bouquet_tv_file, "r") as f:
                    lines = f.readlines()

                # Remove ALL lines containing userbouquet.tvgarden_
                new_lines = []
                for line in lines:
                    if 'userbouquet.%s_' % tag in line:
                        removed_lines += 1
                        continue
                    new_lines.append(line)

                # Write back only if modifications were made
                if len(new_lines) != len(lines):
                    with open(bouquet_tv_file, "w") as f:
                        f.writelines(new_lines)
                    log.info("Removed %d bouquet references from bouquets.tv" % removed_lines, module="Favorites")

            # 2. Find and remove ALL bouquet files with the tag
            import glob
            bouquet_patterns = [
                "/etc/enigma2/userbouquet.%s_*.tv" % tag,
                "/etc/enigma2/subbouquet.%s_*.tv" % tag,
                "/etc/enigma2/userbouquet.%s_*.del" % tag,
                "/etc/enigma2/userbouquet.%s_*.radio" % tag,
                "/etc/enigma2/userbouquet.%s_*.tv.backup" % tag
            ]

            for pattern in bouquet_patterns:
                for file_path in glob.glob(pattern):
                    try:
                        remove(file_path)
                        removed_files += 1
                        log.info("Removed: %s" % file_path, module="Favorites")
                    except Exception as e:
                        log.error("Failed to remove %s: %s" % (file_path, e), module="Favorites")

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
                config = get_config()
                prefix = config.get("bouquet_name_prefix", "TVGarden")
                bouquet_name = "%s_favorites" % prefix.lower()

            userbouquet_file = "/etc/enigma2/userbouquet.%s_%s.tv" % (tag, bouquet_name)

            name = channel.get('name', 'TV Garden Channel')
            stream_url = channel.get('stream_url') or channel.get('url', '')

            if not stream_url:
                return False, _("No stream URL")

            # Check if file exists to determine write mode
            file_exists = exists(userbouquet_file)
            file_mode = "a" if file_exists else "w"

            with open(userbouquet_file, file_mode) as f:
                # If creating a new file, add Lululla-style header
                if file_mode == "w":
                    f.write("#NAME TV Garden Favorites\n")
                    f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | TV Garden Favorites by Lululla | ---\n")
                    f.write("#DESCRIPTION --- | TV Garden Favorites by Lululla | ---\n")

                # Add channel
                url_encoded = stream_url.replace(":", "%3a")
                name_encoded = name.replace(":", "%3a")

                service_line = '#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n' % (url_encoded, name_encoded)
                f.write(service_line)
                f.write('#DESCRIPTION %s\n' % name)

            # Update bouquets and reload
            self._add_to_bouquets_tv(tag, bouquet_name)
            self._reload_bouquets()

            return True, _("Channel added to bouquet")

        except Exception as e:
            log.error("Error: %s" % e, module="Favorites")
            return False, _("Error: %s") % str(e)

    def export_all_channels_hierarchical(self, bouquet_name=None):
        """Export ALL channels with hierarchical structure"""
        try:
            cache = CacheManager()
            config = get_config()

            log.info("Starting hierarchical export of ALL channels", module="Favorites")
            all_channels_url = get_all_channels_url()

            try:
                cache_enabled = config.get("cache_enabled", True)
                force_refresh = config.get("force_refresh_export", False)

                if cache_enabled:
                    all_channels_data = cache.fetch_url(all_channels_url, force_refresh=force_refresh)
                else:
                    all_channels_data = cache._fetch_url(all_channels_url)

                if not all_channels_data:
                    return False, _("Empty database")

            except Exception as e:
                log.error("Failed to fetch: %s" % e, module="Favorites")
                return False, _("Failed to load database")

            all_channels = []

            if isinstance(all_channels_data, list):
                for idx, channel in enumerate(all_channels_data):
                    try:
                        iptv_urls = channel.get('iptv_urls', [])
                        stream_url = None

                        if isinstance(iptv_urls, list) and len(iptv_urls) > 0:
                            stream_url = iptv_urls[0]
                        elif channel.get('youtube_urls'):
                            continue

                        if not stream_url:
                            continue

                        stream_lower = stream_url.lower()
                        problematic_patterns = ['.mpd', '/dash/', 'drm', 'widevine', 'flex-cdn.net']

                        if any(p in stream_lower for p in problematic_patterns):
                            continue

                        channel_data = {
                            'name': channel.get('name', 'Channel %d' % idx),
                            'stream_url': stream_url,
                            'url': stream_url,
                            'country': channel.get('country', 'UNKNOWN'),
                        }

                        all_channels.append(channel_data)

                    except Exception:
                        continue

            if len(all_channels) == 0:
                return False, _("No valid channels found in database")

            channels_by_country = {}
            for channel in all_channels:
                country = channel.get('country', 'UNKNOWN')
                if country not in channels_by_country:
                    channels_by_country[country] = []
                channels_by_country[country].append(channel)

            tag = "tvgarden"
            config = get_config()

            if bouquet_name is None:
                prefix = config.get("bouquet_name_prefix", "TVGarden")
                bouquet_name = "%s_complete" % prefix.lower()

            exported_countries = []
            total_channels = 0

            for country in sorted(channels_by_country.keys()):
                country_channels = channels_by_country[country]

                if not country_channels:
                    continue

                country_subs = self._create_country_sub_bouquets(
                    country, country_channels, tag, "tv"
                )

                if country_subs:
                    country_info = {
                        'name': country,
                        'subs': country_subs,
                        'total_channels': sum(len(sub['channels']) for sub in country_subs)
                    }
                    exported_countries.append(country_info)
                    total_channels += country_info['total_channels']

            if not exported_countries:
                return False, _("No channels to export")

            config_obj = get_config()
            list_position = config_obj.get("list_position", "bottom")

            container_info = self._create_main_container(
                exported_countries, tag, bouquet_name, "tv", list_position
            )

            country_list_lines = []
            for i, country_info in enumerate(exported_countries[:10]):
                line = "  • %s: %d channels in %d files" % (
                    country_info['name'],
                    country_info['total_channels'],
                    len(country_info['subs'])
                )
                country_list_lines.append(line)

            country_list = "\n".join(country_list_lines)

            if len(exported_countries) > 10:
                country_list += "\n  • ... and %d more countries" % (len(exported_countries) - 10)

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
            log.error("Error in hierarchical export: %s" % e, module="Favorites")
            return False, _("Error: %s") % str(e)

    def _create_country_sub_bouquets(self, country, channels, tag, bouquet_type):
        """Create sub-bouquets for a single country (only split if >500 channels)"""
        config = get_config()
        max_channels_for_sub = config.get("max_channels_for_sub_bouquet", 500)

        sub_bouquets = []

        # Usa max_channels_for_sub invece di 500 hardcoded
        if len(channels) <= max_channels_for_sub:
            # Create safe filename
            safe_country = country.lower().replace(' ', '_').replace('-', '_')

            # subbouquet.tvgarden_italy.tv (NO part1)
            sub_name = "subbouquet.%s_%s" % (tag, safe_country)
            sub_file = "%s.%s" % (sub_name, bouquet_type)
            sub_path = join(ENIGMA_PATH, sub_file)

            # Write the single sub-bouquet
            with open(sub_path, 'w') as f:
                f.write("#NAME %s by Lululla\n" % country)
                f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- %s ---\n" % country)
                f.write("#DESCRIPTION --- %s ---\n" % country)

                for channel in channels:
                    name = channel.get('name', '').strip()
                    stream_url = channel.get('stream_url') or channel.get('url', '')

                    if not name or not stream_url:
                        continue

                    url_encoded = stream_url.replace(":", "%3a")
                    name_encoded = name.replace(":", "%3a")

                    service_line = '#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n' % (url_encoded, name_encoded)
                    f.write(service_line)
                    f.write('#DESCRIPTION %s\n' % name)

            sub_bouquets.append({
                'file': sub_file,
                'name': country,
                'channels': channels,
                'reference': sub_name
            })

            log.info(
                "Created single sub-bouquet: %s with %d channels" %
                (sub_file, len(channels)),
                module="Favorites"
            )

        # If the country has > 500 channels, split into parts
        else:
            num_chunks = (
                (len(channels) + max_channels_for_sub - 1) //
                max_channels_for_sub
            )

            for chunk_num in range(num_chunks):
                start_idx = chunk_num * max_channels_for_sub
                end_idx = start_idx + max_channels_for_sub
                chunk = channels[start_idx:end_idx]

                # Create safe filename
                safe_country = country.lower().replace(' ', '_').replace('-', '_')

                # subbouquet.tvgarden_italy_part1.tv
                sub_name = "subbouquet.%s_%s_part%d" % (
                    tag, safe_country, chunk_num + 1
                )
                sub_file = "%s.%s" % (sub_name, bouquet_type)
                sub_path = join(ENIGMA_PATH, sub_file)

                # Write the sub-bouquet
                with open(sub_path, 'w') as f:
                    f.write(
                        "#NAME %s - Part %d by Lululla\n" %
                        (country, chunk_num + 1)
                    )
                    f.write(
                        "#SERVICE 1:64:0:0:0:0:0:0:0:0::--- %s Part %d ---\n" %
                        (country, chunk_num + 1)
                    )
                    f.write(
                        "#DESCRIPTION --- %s Part %d ---\n" %
                        (country, chunk_num + 1)
                    )

                    for channel in chunk:
                        name = channel.get('name', '').strip()
                        stream_url = channel.get('stream_url') or channel.get('url', '')

                        if not name or not stream_url:
                            continue

                        url_encoded = stream_url.replace(":", "%3a")
                        name_encoded = name.replace(":", "%3a")

                        service_line = '#SERVICE 4097:0:1:0:0:0:0:0:0:0:%s:%s\n' % (url_encoded, name_encoded)
                        f.write(service_line)
                        f.write('#DESCRIPTION %s\n' % name)

                sub_bouquets.append({
                    'file': sub_file,
                    'name': "%s - Part %d" % (country, chunk_num + 1),
                    'channels': chunk,
                    'reference': sub_name
                })

                log.info(
                    "Created sub-bouquet part: %s with %d channels" %
                    (sub_file, len(chunk)),
                    module="Favorites"
                )

        return sub_bouquets

    def _create_main_container(self, exported_countries, tag, bouquet_name, bouquet_type, list_position):
        """Create main container bouquet"""
        container_name = "userbouquet.%s_%s_container.%s" % (tag, bouquet_name, bouquet_type)
        container_path = join(ENIGMA_PATH, container_name)

        with open(container_path, 'w') as f:
            f.write("#NAME TV Garden - Complete Database by Lululla\n")
            f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- | TV Garden Complete Database | ---\n")
            f.write("#DESCRIPTION --- | TV Garden Complete Database | ---\n")

            for country_info in exported_countries:
                country = country_info['name']
                country_subs = country_info['subs']

                country_display = country.upper() if country != 'UNKNOWN' else 'OTHER'
                f.write("#SERVICE 1:64:0:0:0:0:0:0:0:0::--- %s (%d channels) ---\n" %
                        (country_display, country_info['total_channels']))
                f.write("#DESCRIPTION --- %s (%d channels) ---\n" %
                        (country_display, country_info['total_channels']))

                for sub in country_subs:
                    bouquet_line = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' % sub['file']
                    f.write(bouquet_line)

        self._add_to_bouquets_tv(tag, "%s_container" % bouquet_name)

        self._reload_bouquets()

        log.info("Created main container: %s (reloaded bouquets)" % container_name, module="Favorites")

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
            log.info("✓ Cleared all favorites (%d)" % count, module="Favorites")
            return True, _("Cleared %d favorites") % count
        else:
            log.error("✗ Failed to clear favorites", module="Favorites")
            return False, _("Error clearing favorites")
