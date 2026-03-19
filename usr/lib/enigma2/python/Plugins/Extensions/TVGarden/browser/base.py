#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TV Garden Plugin - Base Browser
Base class for all browser screens
Based on TV Garden Project
"""
from __future__ import print_function
from enigma import eTimer
from Screens.Screen import Screen
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap

from .. import _


class BaseBrowser(Screen):
    """Base class for all browser screens"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        self.timer = eTimer()
        try:
            self.timer_conn = self.timer.timeout.connect(self.on_timer)
        except AttributeError:
            self.timer.callback.append(self.on_timer)
        self.current_page = 0
        self.items_per_page = 10

        self["menu"] = MenuList([])
        self["status"] = StaticText("")

        self["actions"] = ActionMap(["TVGardenActions", "DirectionActions", "OkCancelActions"], {
            "cancel": self.exit,
            "ok": self.select_item,
            "up": self.up,
            "down": self.down,
            "left": self.left,
            "right": self.right,
        }, -1)

    def on_timer(self):
        """Timer callback for auto-refresh or updates"""
        pass

    def exit(self):
        """Exit the browser"""
        self.close()

    def select_item(self):
        """Select current item - to be overridden by subclasses"""
        pass

    def up(self):
        """Move selection up"""
        self["menu"].up()
        self.on_selection_changed()

    def down(self):
        """Move selection down"""
        self["menu"].down()
        self.on_selection_changed()

    def left(self):
        """Move to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()

    def right(self):
        """Move to next page"""
        if (self.current_page + 1) * self.items_per_page < len(self.get_all_items()):
            self.current_page += 1
            self.load_page()

    def on_selection_changed(self):
        """Called when selection changes - to be overridden"""
        pass

    def get_all_items(self):
        """Get all items - to be overridden"""
        return []

    def load_page(self):
        """Load current page items"""
        all_items = self.get_all_items()
        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_items = all_items[start:end]

        self["menu"].setList(page_items)
        self.update_status()

    def update_status(self):
        """Update status label"""
        total = len(self.get_all_items())
        if total == 0:
            self["status"].setText(_("No items"))
            return

        current = self["menu"].getSelectedIndex() + 1 + (self.current_page * self.items_per_page)
        translation = _("Item {} of {}").format(current, total)
        self["status"].setText(translation)

    def apply_filter(self, text):
        """Apply text filter"""
        self.filter_text = text.lower()
        self.current_page = 0
        self.load_page()

    def refresh_data(self):
        """Refresh data from source"""
        self.current_page = 0
        self.load_page()

    def show_context_menu(self):
        """Show context menu for current item"""
        from Screens.ChoiceBox import ChoiceBox

        menu_items = [
            ("Info", "info"),
            ("Add to Favorites", "favorite"),
            ("Play", "play"),
            ("Search Similar", "search"),
        ]

        self.session.openWithCallback(self.context_menu_callback,
                                      ChoiceBox,
                                      title="Options",
                                      list=menu_items)

    def context_menu_callback(self, choice):
        """Handle context menu selection"""
        if choice:
            action = choice[1]
            if action == "info":
                self.show_item_info()
            elif action == "favorite":
                self.add_to_favorites()
            elif action == "play":
                self.play_item()

    def show_item_info(self):
        """Show info about current item - to be overridden"""
        pass

    def add_to_favorites(self):
        """Add current item to favorites - to be overridden"""
        pass

    def play_item(self):
        """Play current item - to be overridden"""
        pass

    def create_menu_item(self, text, data=None, icon=None):
        """Create a standardized menu item"""
        display_text = text
        if icon:
            display_text = "[%s] %s" % (icon, text)
        return (display_text, data)
