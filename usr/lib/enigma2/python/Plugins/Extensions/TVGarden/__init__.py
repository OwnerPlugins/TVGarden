#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TV Garden Plugin for Enigma2
Based on TV Garden Project
"""
from __future__ import print_function
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Components.Language import language
from os.path import exists
from os import environ
import gettext

PLUGIN_NAME = "TVGarden"
PLUGIN_VERSION = "1.9"
PLUGIN_PATH = resolveFilename(SCOPE_PLUGINS, "Extensions/{}".format(PLUGIN_NAME))
PLUGIN_ICON = resolveFilename(SCOPE_PLUGINS, "Extensions/TVGarden/icons/plugin.png")
USER_AGENT = "TVGarden-Enigma2-Updater/%s" % PLUGIN_VERSION
PluginLanguageDomain = 'TVGarden'
PluginLanguagePath = "Extensions/TVGarden/locale"
isDreambox = exists("/usr/bin/apt-get")


def localeInit():
    if isDreambox:
        lang = language.getLanguage()[:2]
        environ["LANGUAGE"] = lang
    if PLUGIN_NAME and PluginLanguagePath:
        gettext.bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


if isDreambox:
    def _(txt):
        return gettext.dgettext(PluginLanguageDomain, txt) if txt else ""
else:
    def _(txt):
        translated = gettext.dgettext(PluginLanguageDomain, txt)
        if translated:
            return translated
        else:
            print("[%s] fallback to default translation for %s" % (PluginLanguageDomain, txt))
            return gettext.gettext(txt)

localeInit()
language.addCallback(localeInit)

# Make translation available to all modules
__all__ = ['_', 'PLUGIN_NAME', 'PLUGIN_VERSION', 'PLUGIN_PATH', 'PLUGIN_ICON']
