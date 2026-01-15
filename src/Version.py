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
Version information module for Frets on Fire.

This module provides version identification and application metadata
functions used throughout the game. It handles version string generation,
application naming, and data path resolution for both development and
frozen (packaged) builds.

Module Constants:
    VERSION: The major.minor version string (e.g., '1.3').

Usage:
    import Version
    print(Version.version())   # e.g., '1.3.110'
    print(Version.appName())   # 'fretsonfire'
    data_dir = Version.dataPath()  # Path to game data files
"""

import sys
import os

VERSION = '1.3'

def appName():
  """
  Get the application's internal name.
  
  Used for configuration file naming, log files, and user data directories.
  
  Returns:
      str: The application name ('fretsonfire').
  """
  return "fretsonfire"


def revision():
  """
  Get the SVN revision number from version control metadata.
  
  Extracts the revision number from the SVN keyword substitution string.
  
  Returns:
      int: The SVN revision number.
  """
  return int("$LastChangedRevision: 110 $".split(" ")[1])


def version():
  """
  Get the full version string.
  
  Combines the major.minor version with the SVN revision number.
  
  Returns:
      str: The full version string (e.g., '1.3.110').
  """
  return "%s.%d" % (VERSION, revision())


def dataPath():
  """
  Get the path to the game's data directory.
  
  Determines the correct data path based on whether the application
  is running as a frozen executable (py2exe, PyInstaller) or from
  source code.
  
  Returns:
      str: The path to the data directory containing game assets.
  """
  # Determine whether we're running from an exe or not
  if hasattr(sys, "frozen"):
    if os.name == "posix":
      dataPath = os.path.join(os.path.dirname(sys.argv[0]), "../lib/fretsonfire")
      if not os.path.isdir(dataPath):
        dataPath = "data"
    else:
      dataPath = "data"
  else:
    dataPath = os.path.join("..", "data")
  return dataPath
  
