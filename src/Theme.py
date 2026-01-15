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
Theme management module for Frets on Fire.

This module handles the game's visual theming system, providing color
scheme management for UI elements, guitar frets, and backgrounds.
Colors are stored in the configuration file as hex strings and converted
to OpenGL-compatible RGB tuples.

Module Attributes:
    backgroundColor (tuple): RGB tuple for the background color.
    baseColor (tuple): RGB tuple for default UI elements.
    selectedColor (tuple): RGB tuple for highlighted/selected elements.
    fretColors (list): List of 5 RGB tuples for the guitar fret buttons.

Usage:
    import Theme
    Theme.open(config)  # Load colors from config
    Theme.setSelectedColor()  # Apply selected color to OpenGL state
"""

from OpenGL.GL import *
import Config

# Read the color scheme from the config file
Config.define("theme", "background_color",  str, "#330000")
Config.define("theme", "base_color",        str, "#FFFF80")
Config.define("theme", "selected_color",    str, "#FFBF00")
Config.define("theme", "fret0_color",       str, "#22FF22")
Config.define("theme", "fret1_color",       str, "#FF2222")
Config.define("theme", "fret2_color",       str, "#FFFF22")
Config.define("theme", "fret3_color",       str, "#3333FF")
Config.define("theme", "fret4_color",       str, "#FF22FF")


def hexToColor(color):
  """
  Convert a hex color string to an RGB tuple.
  
  Supports both 3-character (#RGB) and 6-character (#RRGGBB) hex formats.
  
  Args:
      color: A hex color string (e.g., '#FF0000' or '#F00').
      
  Returns:
      tuple: An RGB tuple with float values in range 0.0-1.0.
             Returns (0, 0, 0) if the format is invalid.
  """
  if color[0] == "#":
    color = color[1:]
    if len(color) == 3:
      return (int(color[0], 16) / 15.0, int(color[1], 16) / 15.0, int(color[2], 16) / 15.0)
    return (int(color[0:2], 16) / 255.0, int(color[2:4], 16) / 255.0, int(color[4:6], 16) / 255.0)
  return (0, 0, 0)


def colorToHex(color):
  """
  Convert an RGB tuple to a hex color string.
  
  Args:
      color: An RGB tuple with float values in range 0.0-1.0.
      
  Returns:
      str: A 6-character hex color string (e.g., '#ff0000').
  """
  return "#" + ("".join(["%02x" % int(c * 255) for c in color]))

backgroundColor = None
baseColor       = None
selectedColor   = None
fretColors      = None


def open(config):
  """
  Load theme colors from the configuration.
  
  Reads color values from the theme section of the config and converts
  them from hex strings to RGB tuples, storing them in module-level
  variables for use throughout the application.
  
  Args:
      config: A Config object containing theme color settings.
  """
  global backgroundColor, baseColor, selectedColor, fretColors
  backgroundColor = hexToColor(config.get("theme", "background_color"))
  baseColor       = hexToColor(config.get("theme", "base_color"))
  selectedColor   = hexToColor(config.get("theme", "selected_color"))
  fretColors      = [hexToColor(config.get("theme", "fret%d_color" % i)) for i in range(5)]


def setSelectedColor(alpha=1.0):
  """
  Set the OpenGL color to the theme's selected/highlighted color.
  
  Args:
      alpha: Opacity value from 0.0 (transparent) to 1.0 (opaque). Defaults to 1.0.
  """
  glColor4f(*(selectedColor + (alpha,)))


def setBaseColor(alpha=1.0):
  """
  Set the OpenGL color to the theme's base/default color.
  
  Args:
      alpha: Opacity value from 0.0 (transparent) to 1.0 (opaque). Defaults to 1.0.
  """
  glColor4f(*(baseColor + (alpha,)))
