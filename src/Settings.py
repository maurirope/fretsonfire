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
Settings menu module for Frets on Fire.

This module provides the settings and configuration menu system, allowing
users to customize game options including:

- Game settings (language, lefty mode, tapping, score uploads)
- Video settings (resolution, fullscreen, FPS, multisampling)
- Audio settings (volume levels, frequency, buffer size)
- Key bindings (customizable control mapping)
- Mod settings (enable/disable installed modifications)

The module implements specialized menu choice classes that integrate with
the Config system for persistent storage of user preferences.
"""

import Menu
from Language import _
import Dialogs
import Config
import Mod
import Audio

import pygame

class ConfigChoice(Menu.Choice):
  """
  A menu choice that is bound to a configuration option.
  
  This class connects a menu selection to a configuration value, allowing
  users to modify settings through the menu interface. Changes can be
  applied immediately or deferred until explicitly saved.
  
  Attributes:
      config: The Config instance to read/write settings from.
      section: Configuration section name (e.g., 'game', 'video').
      option: Configuration option name within the section.
      changed: Flag indicating if the value has been modified.
      value: The new value if changed, None otherwise.
      autoApply: If True, changes are saved immediately on selection.
  """
  def __init__(self, config, section, option, autoApply = False):
    self.config    = config
    self.section   = section
    self.option    = option
    self.changed   = False
    self.value     = None
    self.autoApply = autoApply
    o = config.prototype[section][option]
    v = config.get(section, option)
    if isinstance(o.options, dict):
      values     = list(o.options.values())
      values.sort()
      try:
        valueIndex = values.index(o.options[v])
      except KeyError:
        valueIndex = 0
    elif isinstance(o.options, list):
      values     = o.options
      try:
        valueIndex = values.index(v)
      except ValueError:
        valueIndex = 0
    else:
      raise RuntimeError("No usable options for %s.%s." % (section, option))
    Menu.Choice.__init__(self, text = o.text, callback = self.change, values = values, valueIndex = valueIndex)
    
  def change(self, value):
    """
    Handle selection of a new value.
    
    Args:
        value: The new value selected from the options list.
    """
    o = self.config.prototype[self.section][self.option]
    
    if isinstance(o.options, dict):
      for k, v in list(o.options.items()):
        if v == value:
          value = k
          break
    
    self.changed = True
    self.value   = value
    
    if self.autoApply:
      self.apply()

  def apply(self):
    """Apply the changed value to the configuration if modified."""
    if self.changed:
      self.config.set(self.section, self.option, self.value)

class VolumeConfigChoice(ConfigChoice):
  """
  A configuration choice specialized for volume settings with audio preview.
  
  Extends ConfigChoice to play a sound preview when the volume is changed,
  giving users immediate feedback on their volume selection.
  
  Attributes:
      engine: The game engine instance for accessing audio system.
  """
  def __init__(self, engine, config, section, option, autoApply = False):
    ConfigChoice.__init__(self, config, section, option, autoApply)
    self.engine = engine

  def change(self, value):
    """
    Handle volume change and play preview sound.
    
    Args:
        value: The new volume level selected.
    """
    ConfigChoice.change(self, value)
    sound = self.engine.data.screwUpSound
    sound.setVolume(self.value)
    sound.play()

class KeyConfigChoice(Menu.Choice):
  """
  A menu choice for configuring keyboard bindings.
  
  Allows users to remap game controls by pressing a new key when selected.
  Displays the current key binding and updates it when a new key is pressed.
  
  Attributes:
      engine: The game engine instance for input handling.
      config: The Config instance to store key bindings.
      section: Configuration section name (typically 'player').
      option: Configuration option name for the specific key binding.
      changed: Flag indicating if the binding was modified.
      value: The new key value if changed.
  """
  def __init__(self, engine, config, section, option):
    self.engine  = engine
    self.config  = config
    self.section = section
    self.option  = option
    self.changed = False
    self.value   = None
    Menu.Choice.__init__(self, text = "", callback = self.change)

  def getText(self, selected):
    """
    Get display text showing the control name and current key binding.
    
    Args:
        selected: Whether this menu item is currently selected.
    
    Returns:
        str: Formatted string with control name and key name.
    """
    def keycode(k):
      try:
        return int(k)
      except:
        return getattr(pygame, k)
    o = self.config.prototype[self.section][self.option]
    v = self.config.get(self.section, self.option)
    return "%s: %s" % (o.text, pygame.key.name(keycode(v)).capitalize())
    
  def change(self):
    """
    Prompt user to press a new key for this control binding.
    
    Opens a dialog asking the user to press a key. If a valid key
    is pressed, updates the configuration and reloads controls.
    """
    o = self.config.prototype[self.section][self.option]

    if isinstance(o.options, dict):
      for k, v in list(o.options.items()):
        if v == value:
          value = k
          break

    key = Dialogs.getKey(self.engine, _("Press a key for '%s' or Escape to cancel.") % (o.text))

    if key:
      self.config.set(self.section, self.option, key)
      self.engine.input.reloadControls()

  def apply(self):
    """No-op: key changes are applied immediately in change()."""
    pass


class SettingsMenu(Menu.Menu):
  """
  Main settings menu with categorized configuration options.
  
  Provides a hierarchical menu structure for all game settings including
  game options, key bindings, video settings, and audio settings. Changes
  to most settings require clicking 'Apply New Settings' and restarting
  the game to take effect.
  
  Attributes:
      engine: The game engine instance.
      settingsToApply: List of all ConfigChoice instances that need
          to be saved when applying settings.
  """
  
  def __init__(self, engine):
    self.engine = engine
    applyItem = [(_("Apply New Settings"), self.applySettings)]

    modSettings = [
      ConfigChoice(engine.config, "mods",  "mod_" + m) for m in Mod.getAvailableMods(engine)
    ] + applyItem

    gameSettings = [
      (_("Mod settings"), modSettings),
      ConfigChoice(engine.config, "game",  "language"),
      ConfigChoice(engine.config, "game",  "leftymode", autoApply = True),
      ConfigChoice(engine.config, "game",  "tapping", autoApply = True),
      ConfigChoice(engine.config, "game",  "uploadscores", autoApply = True),
      ConfigChoice(engine.config, "game",  "compactlist", autoApply = True),
      ConfigChoice(engine.config, "game",  "autopreview", autoApply = True),
      ConfigChoice(engine.config, "game",  "artistsort", autoApply = True),
    ]
    gameSettingsMenu = Menu.Menu(engine, gameSettings + applyItem)

    keySettings = [
      (_("Test Keys"), lambda: Dialogs.testKeys(engine)),
      KeyConfigChoice(engine, engine.config, "player", "key_action1"),
      KeyConfigChoice(engine, engine.config, "player", "key_action2"),
      KeyConfigChoice(engine, engine.config, "player", "key_1"),
      KeyConfigChoice(engine, engine.config, "player", "key_2"),
      KeyConfigChoice(engine, engine.config, "player", "key_3"),
      KeyConfigChoice(engine, engine.config, "player", "key_4"),
      KeyConfigChoice(engine, engine.config, "player", "key_5"),
      KeyConfigChoice(engine, engine.config, "player", "key_left"),
      KeyConfigChoice(engine, engine.config, "player", "key_right"),
      KeyConfigChoice(engine, engine.config, "player", "key_up"),
      KeyConfigChoice(engine, engine.config, "player", "key_down"),
      KeyConfigChoice(engine, engine.config, "player", "key_cancel"),
    ]
    keySettingsMenu = Menu.Menu(engine, keySettings)

    modes = engine.video.getVideoModes()
    modes.reverse()
    Config.define("video",  "resolution", str,   "640x480", text = _("Video Resolution"), options = ["%dx%d" % (m[0], m[1]) for m in modes])
    videoSettings = [
      ConfigChoice(engine.config, "video",  "resolution"),
      ConfigChoice(engine.config, "video",  "fullscreen"),
      ConfigChoice(engine.config, "video",  "fps"),
      ConfigChoice(engine.config, "video",  "multisamples"),
      #ConfigChoice(engine.config, "opengl", "svgshaders"),    # shaders broken at the moment
      #ConfigChoice(engine.config, "opengl", "svgquality"),
      ConfigChoice(engine.config, "video", "fontscale"),
    ]
    videoSettingsMenu = Menu.Menu(engine, videoSettings + applyItem)

    volumeSettings = [
      VolumeConfigChoice(engine, engine.config, "audio",  "guitarvol"),
      VolumeConfigChoice(engine, engine.config, "audio",  "songvol"),
      VolumeConfigChoice(engine, engine.config, "audio",  "rhythmvol"),
      VolumeConfigChoice(engine, engine.config, "audio",  "screwupvol"),
    ]
    volumeSettingsMenu = Menu.Menu(engine, volumeSettings + applyItem)

    audioSettings = [
      (_("Volume Settings"), volumeSettingsMenu),
      ConfigChoice(engine.config, "audio",  "delay"),
      ConfigChoice(engine.config, "audio",  "frequency"),
      ConfigChoice(engine.config, "audio",  "bits"),
      ConfigChoice(engine.config, "audio",  "buffersize"),
    ]
    audioSettingsMenu = Menu.Menu(engine, audioSettings + applyItem)

    settings = [
      (_("Game Settings"),     gameSettingsMenu),
      (_("Key Settings"),      keySettingsMenu),
      (_("Video Settings"),    videoSettingsMenu),
      (_("Audio Settings"),    audioSettingsMenu),
    ]

    self.settingsToApply = settings + \
                           videoSettings + \
                           audioSettings + \
                           volumeSettings + \
                           gameSettings + \
                           modSettings

    Menu.Menu.__init__(self, engine, settings)

  def applySettings(self):
    """
    Save all modified settings to configuration file.
    
    Iterates through all setting options and applies any changes,
    then displays a message prompting the user to restart the game.
    """
    for option in self.settingsToApply:
      if isinstance(option, ConfigChoice):
        option.apply()

    Dialogs.showMessage(self.engine, _("Settings saved. Please restart the game to activate the new settings."))

class GameSettingsMenu(Menu.Menu):
  """
  In-game settings menu for quick volume adjustments.
  
  A simplified settings menu accessible during gameplay that only
  includes volume controls with immediate application (no restart required).
  """
  def __init__(self, engine):
    settings = [
      VolumeConfigChoice(engine, engine.config, "audio",  "guitarvol", autoApply = True),
      VolumeConfigChoice(engine, engine.config, "audio",  "songvol", autoApply = True),
      VolumeConfigChoice(engine, engine.config, "audio",  "rhythmvol", autoApply = True),
      VolumeConfigChoice(engine, engine.config, "audio",  "screwupvol", autoApply = True),
    ]
    Menu.Menu.__init__(self, engine, settings)
