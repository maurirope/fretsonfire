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
Scene creation factory for Frets on Fire.

This module provides a factory pattern implementation for dynamically creating
game scene instances. It handles the import and instantiation of scene classes
such as GuitarScene, SongChoosingScene, and GameResultsScene.

The factory abstracts away the scene creation details, allowing the game engine
and session management to create scenes by name without needing direct imports.

Module Attributes:
    scenes: List of available scene module names that can be created.
"""

# Scenes
import glob

# Static list for now to ease building
#scenes = [n.replace(".py", "") for n in glob.glob("*Scene.py")]
scenes = ["GameResultsScene", "GuitarScene", "SongChoosingScene"]


def _import(name):
  """
  Dynamically import a scene module by name.
  
  Args:
      name: The name of the module to import (e.g., "GuitarScene").
  """
  globals()[name] = __import__(name)


def create(engine, name, owner, server = None, session = None, **args):
  """
  Create and return a scene instance by name.
  
  This factory function dynamically imports the specified scene module
  and instantiates its Client variant. For single-player mode, only
  the Client version of scenes is used.
  
  Args:
      engine: The game engine instance providing resources and services.
      name: The name of the scene to create (e.g., "GuitarScene").
      owner: The owner/parent of the scene (typically None or another scene).
      server: Legacy parameter for networked play, not used in single-player.
          Defaults to None.
      session: The game session managing the current gameplay state.
          Defaults to None.
      **args: Additional keyword arguments passed to the scene constructor.
          These vary by scene type (e.g., libraryName, songName).
  
  Returns:
      An instance of the requested scene's Client class (e.g., GuitarSceneClient).
  
  Example:
      >>> scene = create(engine, "SongChoosingScene", None, session=session)
      >>> scene = create(engine, "GuitarScene", None, session=session,
      ...                libraryName="songs", songName="tutorial")
  """
  _import(name)

  m = globals()[name]
  # For single-player, always use the Client version of scenes
  return getattr(m, name + "Client")(engine = engine, owner = owner, session = session, **args)
