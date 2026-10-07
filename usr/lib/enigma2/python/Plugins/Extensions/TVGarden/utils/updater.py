#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Updater Module
Based on TV Garden Project
"""
import time
import shutil
import subprocess
import tempfile
from re import sub, search
from os import makedirs, listdir, chmod, unlink
from os.path import join, exists, getmtime
from urllib.request import urlopen, Request

from ..helpers import log
from .. import _, PLUGIN_VERSION, PLUGIN_PATH, USER_AGENT


class PluginUpdater:
    """Plugin update manager"""

    # Repository information
    REPO_OWNER = "OwnerPlugins"
    REPO_NAME = "TVGarden"
    REPO_BRANCH = "main"

    # GitHub URLs (version check and installer MUST use the same repo)
    RAW_CONTENT = "https://raw.githubusercontent.com"
    INSTALLER_URL = "%s/%s/%s/%s/installer.sh" % (
        RAW_CONTENT, REPO_OWNER, REPO_NAME, REPO_BRANCH)

    # Backup directory (in RAM: keep only the most recent backups)
    BACKUP_DIR = "/tmp/tvgarden_backup"
    MAX_BACKUPS = 1

    def __init__(self):
        self.current_version = PLUGIN_VERSION
        self.user_agent = USER_AGENT
        self.backup_path = None

        # Create backup directory
        if not exists(self.BACKUP_DIR):
            try:
                makedirs(self.BACKUP_DIR, mode=0o755)
            except Exception as e:
                log.error("Cannot create backup dir: %s" % e, module="Updater")

    def get_latest_version(self):
        """Get latest version from installer.sh - Python 2/3 compatible"""
        try:
            installer_url = self.INSTALLER_URL

            log.debug(
                "Checking version from: %s" %
                installer_url, module="Updater")

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
                # version='1.1' o version="1.1"
                r"version\s*=\s*['\"](\d+\.\d+)['\"]",
                r"version\s*:\s*['\"](\d+\.\d+)['\"]",  # version: '1.1'
                r"Version\s*=\s*['\"](\d+\.\d+)['\"]",  # Version='1.1'
            ]

            for pattern in patterns:
                match = search(pattern, content)
                if match:
                    version = match.group(1)
                    log.info(
                        "Found version %s using pattern: %s" %
                        (version, pattern), module="Updater")
                    return version

            # No guessing from random numbers in the script
            log.warning(
                "No version pattern found in installer.sh",
                module="Updater")
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

    def _check_update_sync(self):
        """Return True (newer), False (up to date) or None (error)"""
        latest = self.get_latest_version()
        log.debug("Latest: %s, current: %s" %
                  (latest, self.current_version), module="Updater")
        if latest is None:
            return None
        return self.compare_versions(latest, self.current_version) > 0

    def check_update(self, callback=None):
        """
        Check if an update is available. The network request runs in a
        worker thread; callback(True/False/None) runs on the GUI thread.
        """
        log.debug("PluginUpdater.check_update called", module="Updater")

        def safe_callback(result):
            if callback:
                callback(result)

        try:
            from twisted.internet import threads
            d = threads.deferToThread(self._check_update_sync)
            d.addCallback(safe_callback)
            d.addErrback(lambda failure: safe_callback(None))
        except Exception as e:
            log.error("Error in check_update: %s" % e, module="Updater")
            try:
                safe_callback(self._check_update_sync())
            except Exception:
                safe_callback(None)

    def download_update(self, callback=None):
        """
        Download and install the update in a worker thread;
        callback(success, message) runs on the GUI thread.
        """
        def safe_callback(result):
            if callback:
                callback(*result)

        try:
            from twisted.internet import threads
            d = threads.deferToThread(self._download_update_sync)
            d.addCallback(safe_callback)
            d.addErrback(lambda failure: safe_callback(
                (False, _("Update error: %s") % failure.getErrorMessage())))
        except Exception as e:
            log.error("Cannot start update thread: %s" % e, module="Updater")
            safe_callback(self._download_update_sync())

    def _download_update_sync(self):
        """Create backup, run installer, restore on failure"""
        log.info("Starting update process...", module="Updater")
        success = False
        message = ""

        try:
            # Step 1: Create backup
            if not self.create_backup():
                return False, _("Failed to create backup. Update cancelled.")

            # Step 2: Download and run installer
            if self.download_and_run_installer():
                success = True
                message = _("Update completed successfully!")
            else:
                # Step 3: Restore backup if failed
                if self.restore_backup():
                    message = _("Update failed. Restored from backup.")
                else:
                    message = _(
                        "Update failed and backup restore also failed!")

        except Exception as e:
            log.error("Update process error: %s" % e, module="Updater")
            # Try to restore backup
            try:
                self.restore_backup()
            except BaseException:
                pass
            message = _("Update error: %s") % str(e)

        return success, message

    def download_and_run_installer(self):
        """Download installer.sh over verified HTTPS, then run it"""
        script_path = None
        try:
            log.info("Downloading installer: %s" %
                     self.INSTALLER_URL, module="Updater")
            req = Request(self.INSTALLER_URL,
                          headers={'User-Agent': self.user_agent})
            response = urlopen(req, timeout=30)
            try:
                script = response.read()
            finally:
                response.close()

            if not script.startswith(b"#!"):
                log.error("Downloaded installer is not a shell script",
                          module="Updater")
                return False

            fd, script_path = tempfile.mkstemp(suffix=".sh")
            with open(fd, 'wb') as f:
                f.write(script)
            chmod(script_path, 0o700)

            log.info("Running TVGarden installer...", module="Updater")
            result = subprocess.call(["/bin/sh", script_path])

            if result == 0:
                log.info("Installer completed successfully", module="Updater")
                return True
            log.error(
                "Installer failed with exit code: %d" %
                result, module="Updater")
            return False

        except Exception as e:
            log.error("Installer execution error: %s" % e, module="Updater")
            return False
        finally:
            if script_path:
                try:
                    unlink(script_path)
                except OSError:
                    pass

    def _cleanup_old_backups(self):
        """Keep only the newest MAX_BACKUPS backups (they live in RAM)"""
        try:
            backups = [join(self.BACKUP_DIR, d) for d in listdir(self.BACKUP_DIR)
                       if d.startswith("backup_v")]
            backups.sort(key=getmtime)
            for path in backups[:max(0, len(backups) - self.MAX_BACKUPS)]:
                shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            log.debug("Backup cleanup failed: %s" % e, module="Updater")

    def create_backup(self):
        """Create backup of current plugin"""
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_name = "backup_v%s_%s" % (self.current_version, timestamp)
            self.backup_path = join(self.BACKUP_DIR, backup_name)

            if exists(PLUGIN_PATH):
                log.info(
                    "Creating backup to: %s" %
                    self.backup_path, module="Updater")
                shutil.copytree(PLUGIN_PATH, self.backup_path)
                log.info("Backup created successfully", module="Updater")
                self._cleanup_old_backups()
                return True
            else:
                log.error(
                    "Plugin path not found: %s" %
                    PLUGIN_PATH, module="Updater")
                return False
        except Exception as e:
            log.error("Backup failed: %s" % e, module="Updater")
            return False

    def restore_backup(self):
        """Restore from backup"""
        try:
            if self.backup_path and exists(self.backup_path):
                log.info(
                    "Restoring from backup: %s" %
                    self.backup_path, module="Updater")

                # Remove current plugin
                if exists(PLUGIN_PATH):
                    shutil.rmtree(PLUGIN_PATH)

                # Restore from backup
                shutil.copytree(self.backup_path, PLUGIN_PATH)
                log.info("Restored successfully", module="Updater")
                return True
            else:
                log.error(
                    "Backup not found: %s" %
                    self.backup_path, module="Updater")
                return False
        except Exception as e:
            log.error("Restore failed: %s" % e, module="Updater")
            return False


def perform_update(callback=None):
    """Simple update"""
    updater = PluginUpdater()
    return updater.download_update(callback)
