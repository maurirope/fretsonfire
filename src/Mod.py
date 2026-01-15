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
Mod (modification) support module for Frets on Fire.

This module provides functionality for discovering, loading, and managing
game modifications. Mods are stored as subdirectories in the 'mods' folder
and can override or extend game assets such as graphics, themes, and songs.

Mod System:
    - Mods are directories within data/mods/
    - Each mod can be enabled/disabled via the game configuration
    - Active mods add their directories to the resource search path
    - Multiple mods can be active simultaneously

Usage:
    import Mod
    Mod.init(engine)  # Initialize mod system and load active mods
    available = Mod.getAvailableMods(engine)  # List available mods
    Mod.activateMod(engine, 'CustomTheme')  # Activate a specific mod
"""

import os
import Config
from Language import _


def _getModPath(engine):
  """
  Get the filesystem path to the mods directory.
  
  Args:
      engine: The game engine instance.
      
  Returns:
      str: Absolute path to the mods directory.
  """
  return engine.resource.fileName("mods")


def init(engine):
  """
  Initialize the mod system.
  
  Scans for available mods, registers configuration options for each,
  and activates any mods that are enabled in the configuration.
  
  Args:
      engine: The game engine instance.
  """
  # Define configuration keys for all available mods
  for m in getAvailableMods(engine):
    Config.define("mods", "mod_" + m, bool, False, text=m, options={False: _("Off"), True: _("On")})

  # Init all active mods
  for m in getActiveMods(engine):
    activateMod(engine, m)


def getAvailableMods(engine):
  """
  Get a list of all available mods.
  
  Scans the mods directory for subdirectories (excluding hidden directories
  starting with '.').
  
  Args:
      engine: The game engine instance.
      
  Returns:
      list: A list of mod names (directory names) available for activation.
  """
  modPath = _getModPath(engine)
  try:
    dirList = os.listdir(modPath)
  except OSError as e:
    import Log
    Log.warn("Could not find mods directory")
    return []
  return [m for m in dirList if os.path.isdir(os.path.join(modPath, m)) and not m.startswith(".")]


def getActiveMods(engine):
  """
  Get a list of currently enabled mods.
  
  Checks the configuration for each available mod to determine which
  ones are enabled.
  
  Args:
      engine: The game engine instance.
      
  Returns:
      list: A sorted list of enabled mod names.
  """
  mods = []
  for mod in getAvailableMods(engine):
    if engine.config.get("mods", "mod_" + mod):
      mods.append(mod)
  mods.sort()
  return mods


def activateMod(engine, modName):
  """
  Activate a mod by adding its directory to the resource path.
  
  When activated, the mod's assets will override or extend the
  base game assets.
  
  Args:
      engine: The game engine instance.
      modName: The name of the mod to activate.
  """
  modPath = _getModPath(engine)
  m = os.path.join(modPath, modName)
  if os.path.isdir(m):
    engine.resource.addDataPath(m)


def deactivateMod(engine, modName):
  """
  Deactivate a mod by removing its directory from the resource path.
  
  Args:
      engine: The game engine instance.
      modName: The name of the mod to deactivate.
  """
  modPath = _getModPath(engine)
  m = os.path.join(modPath, modName)
  engine.resource.removeDataPath(m)
