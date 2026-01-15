#####################################################################
# -*- coding: utf-8 -*-                                             #
#                                                                   #
# Frets on Fire                                                     #
# Copyright (C) 2006 Sami Kyöstilä                                  #
# Python 3 Port (2026)                                              #
#                                                                   #
# This program is free software; you can redistribute it and/or     #
# modify it under the terms of the GNU General Public License       #
# as published by the Free Software Foundation; either version 2    #
# of the License, or (at your option) any later version.            #
#                                                                   #
# This program is distributed in the hope that it will be useful,   #
# but WITHOUT ANY WARRANTY; without even the implied warranty of    #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the     #
# GNU General Public License for more details.                      #
#                                                                   #
# You should have received a copy of the GNU General Public License #
# along with this program; if not, write to the Free Software       #
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,        #
# MA  02110-1301, USA.                                              #
#####################################################################

"""
Internationalization (i18n) module for Frets on Fire.

This module provides localization support by loading translation catalogs
from .mo files. It defines a global translator function '_' that can be
imported throughout the application to translate user-facing strings.

The module:
    - Discovers available language translations in the data/translations directory
    - Loads the appropriate GNU gettext catalog based on user configuration
    - Provides a fallback dummy translator when no translation is available
    - Registers language options in the game configuration

Usage:
    from Language import _
    translated_text = _("Hello World")
"""

import Config
import Version
import Log
import gettext
import os
import glob

Config.define("game", "language", str, "")


def getAvailableLanguages():
  """
  Discover all available language translations.
  
  Scans the translations directory for compiled .mo files and extracts
  the language names from the filenames.
  
  Returns:
      list: A list of available language names (e.g., ['Finnish', 'German', 'Spanish']).
            Language names are capitalized with underscores replaced by spaces.
  """
  return [os.path.basename(l).capitalize().replace(".mo", "").replace("_", " ") for l in glob.glob(os.path.join(Version.dataPath(), "translations", "*.mo"))]

def dummyTranslator(string):
  """
  Passthrough translator used when no language translation is loaded.
  
  Args:
      string: The string to translate.
      
  Returns:
      str: The original string unchanged.
  """
  return string


language = Config.load(Version.appName() + ".ini").get("game", "language")
_ = dummyTranslator

if language:
  try:
    trFile = os.path.join(Version.dataPath(), "translations", "%s.mo" % language.lower().replace(" ", "_"))
    catalog = gettext.GNUTranslations(open(trFile, "rb"))
    def translate(m):
      return catalog.gettext(m)
    _ = translate
  except Exception as x:
    Log.warn("Unable to select language '%s': %s" % (language, x))
    language = None

# Define the config key again now that we have some options for it
langOptions = {"": "English"}
for lang in getAvailableLanguages():
  langOptions[lang] = _(lang)
Config.define("game", "language", str, "", _("Language"), langOptions)
