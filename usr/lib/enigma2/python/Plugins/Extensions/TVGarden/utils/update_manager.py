#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Update Manager
Centralized update functions using existing updater.py
"""
from __future__ import print_function
from Screens.MessageBox import MessageBox

from .updater import PluginUpdater
from ..helpers import log
from .. import _


class UpdateManager:
    """Centralized update manager using existing PluginUpdater"""

    @staticmethod
    def check_for_updates(session, status_label=None):
        """Check for updates - unified function for both plugin and settings"""
        print("UpdateManager.check_for_updates called")

        if status_label:
            status_label.setText(_("Checking for updates..."))

        try:
            updater = PluginUpdater()
            print("PluginUpdater created successfully")

            def update_callback(result):
                print("update_callback received result: %s" % result)

                if result is None:
                    if status_label:
                        status_label.setText(_("Update check failed"))
                    session.open(MessageBox,
                                 _("Could not check for updates. Check internet connection."),
                                 MessageBox.TYPE_ERROR)

                elif result:
                    if status_label:
                        status_label.setText(_("Update available!"))
                    UpdateManager.ask_to_update(session, status_label, updater)

                else:
                    if status_label:
                        status_label.setText(_("Plugin is up to date"))
                    session.open(MessageBox,
                                 _("You have the latest version of TVGarden."),
                                 MessageBox.TYPE_INFO)

            print("Calling updater.check_update()")
            updater.check_update(update_callback)

        except Exception as e:
            print("Error in check_for_updates: %s" % str(e))
            if status_label:
                status_label.setText(_("Update check error"))
            session.open(MessageBox,
                         _("Could not check for updates: %s") % str(e),
                         MessageBox.TYPE_ERROR)

    @staticmethod
    def ask_to_update(session, status_label=None, updater=None):
        """Ask user if they want to update"""
        if updater is None:
            updater = PluginUpdater()

        def update_confirmed(result):
            log.debug("User update confirmation: %s" % result, module="UpdateManager")
            if result:
                UpdateManager.perform_update(session, status_label, updater)
            elif status_label:
                status_label.setText(_("Update cancelled"))

        message = _("A new version is available!\n\nUpdate now?\n\n(Recommended to backup first)")
        session.openWithCallback(update_confirmed,
                                 MessageBox,
                                 message,
                                 MessageBox.TYPE_YESNO)

    @staticmethod
    def perform_update(session, status_label=None, updater=None):
        """Perform the update"""
        if updater is None:
            updater = PluginUpdater()

        def update_progress(success, message):
            log.debug("Update progress: success=%s, message=%s" % (success, message), module="UpdateManager")
            if success:
                if status_label:
                    status_label.setText(_("Update successful!"))

                restart_msg = _("%s\n\nRestart Enigma2 now for changes to take effect.") % message
                session.openWithCallback(
                    lambda result: UpdateManager.restart_enigma2(session, result),
                    MessageBox,
                    restart_msg,
                    MessageBox.TYPE_YESNO
                )
            else:
                if status_label:
                    status_label.setText(_("Update failed"))
                session.open(MessageBox,
                             message,
                             MessageBox.TYPE_ERROR)

        if status_label:
            status_label.setText(_("Updating plugin... Please wait"))

        log.debug("Starting download_update()", module="UpdateManager")
        updater.download_update(update_progress)

    @staticmethod
    def restart_enigma2(session, result):
        """Restart Enigma2 if user confirms"""
        log.debug("Restart Enigma2 confirmation: %s" % result, module="UpdateManager")
        if result:
            try:
                from enigma import quitMainloop
                quitMainloop(3)  # 3 = Restart Enigma2
                log.debug("Enigma2 restart initiated", module="UpdateManager")
            except Exception as e:
                log.error("Failed to restart Enigma2: %s" % e, module="UpdateManager")
                session.open(MessageBox,
                             _("Please restart Enigma2 manually."),
                             MessageBox.TYPE_INFO)
