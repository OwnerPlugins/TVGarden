#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Updater Module
Based on TV Garden Project
"""
from __future__ import print_function
import time
import shutil
import subprocess
from re import sub, search
from os import makedirs
from os.path import join, exists
from sys import version_info

from ..helpers import log
from .. import _, PLUGIN_VERSION, PLUGIN_PATH, USER_AGENT

if version_info[0] == 3:
    from urllib.request import urlopen, Request
else:
    from urllib2 import urlopen, Request


class PluginUpdater:
    """Plugin update manager"""

    # Repository information
    REPO_OWNER = "Belfagor2005"
    REPO_NAME = "TVGarden"
    REPO_BRANCH = "main"

    # GitHub URLs
    RAW_CONTENT = "https://raw.githubusercontent.com"
    INSTALLER_URL = "https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh"

    # Backup directory
    BACKUP_DIR = "/tmp/tvgarden_backup"

    def __init__(self):
        self.current_version = PLUGIN_VERSION
        self.user_agent = USER_AGENT
        self.backup_path = None

        # Create backup directory
        if not exists(self.BACKUP_DIR):
            makedirs(self.BACKUP_DIR, mode=0o755)

    def get_latest_version(self):
        """Get latest version from installer.sh - Python 2/3 compatible"""
        try:
            installer_url = "https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh"

            log.debug("Checking version from: %s" % installer_url, module="Updater")

            headers = {'User-Agent': self.user_agent}
            req = Request(installer_url, headers=headers)

            response = None
            try:
                response = urlopen(req, timeout=10)
                content = response.read().decode('utf-8')
            finally:
                if response:
                    response.close()

            patterns = [
                r"version\s*=\s*['\"](\d+\.\d+)['\"]",  # version='1.1' o version="1.1"
                r"version\s*:\s*['\"](\d+\.\d+)['\"]",  # version: '1.1'
                r"Version\s*=\s*['\"](\d+\.\d+)['\"]",  # Version='1.1'
            ]

            for pattern in patterns:
                match = search(pattern, content)
                if match:
                    version = match.group(1)
                    log.info("Found version %s using pattern: %s" % (version, pattern), module="Updater")
                    return version

            log.warning("No version pattern found in installer.sh", module="Updater")
            fallback = search(r'(\d+\.\d+)', content)
            if fallback:
                version = fallback.group(1)
                log.info("Fallback found version: %s" % version, module="Updater")
                return version

            return None

        except Exception as e:
            log.error("Error getting latest version: %s" % e, module="Updater")
            return None

    def compare_versions(self, v1, v2):
        """Compare version strings"""
        try:
            # Clean version strings
            v1_clean = sub(r'[^\d.]', '', v1)
            v2_clean = sub(r'[^\d.]', '', v2)

            v1_parts = list(map(int, v1_clean.split('.')))
            v2_parts = list(map(int, v2_clean.split('.')))

            # Pad with zeros if needed
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts += [0] * (max_len - len(v1_parts))
            v2_parts += [0] * (max_len - len(v2_parts))

            for i in range(max_len):
                if v1_parts[i] > v2_parts[i]:
                    return 1
                elif v1_parts[i] < v2_parts[i]:
                    return -1
            return 0
        except Exception as e:
            log.error("Version compare error: %s" % e, module="Updater")
            return 0

    def check_update(self, callback=None):
        """Check if update is available - VERSIONE SINCROZINATA"""
        log.debug("PluginUpdater.check_update called", module="Updater")

        try:
            latest = self.get_latest_version()
            log.debug("get_latest_version returned: %s" % latest, module="Updater")
            log.debug("Current version: %s" % self.current_version, module="Updater")

            if latest is None:
                log.warning("Could not get latest version", module="Updater")
                if callback:
                    callback(None)
                return

            # Compare versions
            is_newer = self.compare_versions(latest, self.current_version) > 0
            log.debug("Version comparison: is_newer = %s" % is_newer, module="Updater")

            if callback:
                log.debug("Calling callback with: %s" % is_newer, module="Updater")
                callback(is_newer)

        except Exception as e:
            log.error("Error in check_update: %s" % e, module="Updater")
            if callback:
                callback(None)

    def download_update(self, callback=None):
        """Download and install update - VERSIONE SINCROZINATA"""
        log.info("Starting update process...", module="Updater")
        success = False
        message = ""

        try:
            # Step 1: Create backup
            if not self.create_backup():
                message = _("Failed to create backup. Update cancelled.")
                if callback:
                    callback(False, message)
                return

            # Step 2: Download and run installer
            if self.download_and_run_installer():
                success = True
                message = _("Update completed successfully!")
            else:
                # Step 3: Restore backup if failed
                if self.restore_backup():
                    message = _("Update failed. Restored from backup.")
                else:
                    message = _("Update failed and backup restore also failed!")

        except Exception as e:
            log.error("Update process error: %s" % e, module="Updater")
            # Try to restore backup
            try:
                self.restore_backup()
            except:
                pass
            message = _("Update error: %s") % str(e)

        if callback:
            callback(success, message)

    def download_and_run_installer(self):
        """Download and run installer script - USANDO WGET COME NELL'INSTALLER"""
        try:
            log.info("Running TVGarden installer...", module="Updater")
            cmd = 'wget -q --no-check-certificate "https://raw.githubusercontent.com/Belfagor2005/TVGarden/main/installer.sh" -O - | /bin/sh'
            log.debug("Executing: %s" % cmd, module="Updater")
            result = subprocess.call(cmd, shell=True)

            if result == 0:
                log.info("Installer completed successfully", module="Updater")
                return True
            else:
                log.error("Installer failed with exit code: %d" % result, module="Updater")
                return False

        except Exception as e:
            log.error("Installer execution error: %s" % e, module="Updater")
            return False

    def create_backup(self):
        """Create backup of current plugin"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = "backup_v%s_%s" % (self.current_version, timestamp)
            self.backup_path = join(self.BACKUP_DIR, backup_name)

            if exists(PLUGIN_PATH):
                log.info("Creating backup to: %s" % self.backup_path, module="Updater")
                shutil.copytree(PLUGIN_PATH, self.backup_path)
                log.info("Backup created successfully", module="Updater")
                return True
            else:
                log.error("Plugin path not found: %s" % PLUGIN_PATH, module="Updater")
                return False
        except Exception as e:
            log.error("Backup failed: %s" % e, module="Updater")
            return False

    def restore_backup(self):
        """Restore from backup"""
        try:
            if self.backup_path and exists(self.backup_path):
                log.info("Restoring from backup: %s" % self.backup_path, module="Updater")

                # Remove current plugin
                if exists(PLUGIN_PATH):
                    shutil.rmtree(PLUGIN_PATH)

                # Restore from backup
                shutil.copytree(self.backup_path, PLUGIN_PATH)
                log.info("Restored successfully", module="Updater")
                return True
            else:
                log.error("Backup not found: %s" % self.backup_path, module="Updater")
                return False
        except Exception as e:
            log.error("Restore failed: %s" % e, module="Updater")
            return False


def perform_update(callback=None):
    """Simple update"""
    updater = PluginUpdater()
    return updater.download_update(callback)
