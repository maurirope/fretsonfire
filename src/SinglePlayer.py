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
Single-player game session management for Frets on Fire.

This module provides a simplified session architecture that replaces the
original networked Session/World/Lobby system. It manages:

- Player creation and tracking
- Scene lifecycle (creation, switching, deletion)
- Game flow from song selection to results
- Cleanup and return to main menu

The SinglePlayerSession class acts as a local coordinator, while
SinglePlayerGameTask provides the task-based interface for the engine.

Typical usage:
    session = SinglePlayerSession(engine)
    player = session.createPlayer("Player 1")
    session.startGame()

Classes:
    SinglePlayerSession: Manages player and scene state for single-player games.
    SinglePlayerGameTask: Engine task wrapper for session management.
"""

from Player import Player
from Language import _
import SceneFactory
import Song
import Config

STARTUP_SCENE = "SongChoosingScene"

class SinglePlayerSession:
  """
  A simplified session manager for single-player games.

  Replaces the original networked Session/World/Lobby architecture with
  a lightweight local implementation. Manages the player, active scenes,
  and game objects without network overhead.

  Attributes:
      engine: Reference to the GameEngine instance.
      player: The local Player object, or None if not created.
      scenes: List of currently active Scene instances.
      objects: Dictionary mapping object IDs to game objects.
      _nextId: Counter for generating unique object IDs.
      id: The local player's ID (always 1 for single-player).
      isConnected: Compatibility flag (always True for single-player).
  """

  def __init__(self, engine):
    """Initialize the single-player session.

    Args:
        engine: The GameEngine instance that owns this session.
    """
    self.engine = engine
    self.player = None
    self.scenes = []
    self.objects = {}
    self._nextId = 1
    self.id = 1  # Local player ID
    self.isConnected = True

  def generateId(self):
    """Generate a unique object ID.

    Returns:
        Integer ID, incrementing with each call.
    """
    id = self._nextId
    self._nextId += 1
    return id

  def createPlayer(self, name):
    """Create and register the local player.

    Args:
        name: Display name for the player.

    Returns:
        The newly created Player instance.
    """
    self.player = Player(self.id, name)
    return self.player

  def getLocalPlayer(self):
    """Get the local player instance.

    Returns:
        The Player object for the local player, or None if not created.
    """
    return self.player

  def createScene(self, name, **args):
    """Create and start a new game scene.

    Creates a scene using the SceneFactory, registers it with the engine,
    adds the local player to the scene, and pushes it to the view stack.

    Args:
        name: Scene class name (e.g., 'SongChoosingScene', 'GuitarScene').
        **args: Additional keyword arguments passed to the scene constructor.

    Returns:
        Integer ID assigned to the created scene.
    """
    import Log
    Log.debug("SinglePlayerSession.createScene(%s) called" % name)
    id = self.generateId()
    scene = SceneFactory.create(
      engine=self.engine,
      name=name,
      owner=self.id,
      session=self,
      **args
    )
    self.objects[id] = scene
    self.scenes.append(scene)
    self.engine.addTask(scene)
    
    # Enter the scene with the player
    if self.player:
      scene.addPlayer(self.player)
      self.engine.view.pushLayer(scene)
    
    Log.debug("Scene created. Tasks: %d, Layers: %d" % (len(self.engine.tasks), len(self.engine.view.layers)))
    return id

  def deleteScene(self, scene):
    """Remove and clean up a scene.

    Removes the scene from the active scenes list, unregisters it from
    the engine task system, pops it from the view stack if present,
    and removes it from the objects dictionary.

    Args:
        scene: The Scene instance to remove.
    """
    import Log
    Log.debug("SinglePlayerSession.deleteScene() called for %s" % scene.__class__.__name__)
    if scene in self.scenes:
      self.scenes.remove(scene)
      self.engine.removeTask(scene)
      # Pop the scene from the view if it's a layer
      if scene in self.engine.view.layers:
        self.engine.view.popLayer(scene)
      # Find and remove from objects
      for id, obj in list(self.objects.items()):
        if obj is scene:
          del self.objects[id]
          break
    Log.debug("Tasks remaining: %d, Scenes remaining: %d" % (len(self.engine.tasks), len(self.scenes)))

  def startGame(self, libraryName=None, songName=None):
    """Start the game by creating the initial scene.

    Creates the startup scene (typically SongChoosingScene) with optional
    pre-selected library and song.

    Args:
        libraryName: Optional name of the song library to open.
        songName: Optional name of the song to pre-select.
    """
    args = {}
    if libraryName:
      args['libraryName'] = libraryName
    if songName:
      args['songName'] = songName
    self.createScene(STARTUP_SCENE, **args)

  def finishGame(self):
    """End the current game and return to the main menu.

    Cleans up all active scenes, pops all view layers, and pushes
    the MainMenu layer onto the view stack.
    """
    import Log
    Log.debug("SinglePlayerSession.finishGame() called")
    # Clean up all scenes
    for scene in list(self.scenes):
      self.deleteScene(scene)
    
    # Signal game finished
    import MainMenu
    self.engine.view.popAllLayers()
    self.engine.view.pushLayer(MainMenu.MainMenu(self.engine))

  def close(self):
    """Close the session and release resources.

    Currently a no-op as single-player sessions don't require
    explicit cleanup beyond scene deletion.
    """
    pass


class SinglePlayerGameTask:
  """
  Engine task that manages a single-player game session.

  Provides a task-based interface for the engine to manage the game
  session lifecycle. The task runs every frame and can be used to
  quit the game cleanly.

  Attributes:
      engine: Reference to the GameEngine instance.
      session: The SinglePlayerSession being managed.
      player: Reference to the local Player for convenience.
  """

  def __init__(self, engine, session):
    """Initialize the game task.

    Args:
        engine: The GameEngine instance.
        session: The SinglePlayerSession to manage.
    """
    self.engine = engine
    self.session = session
    self.player = session.getLocalPlayer()

  def quit(self):
    """Quit the game session and return to the main menu.

    Calls finishGame() on the session and removes this task from
    the engine's task list.
    """
    self.session.finishGame()
    self.engine.removeTask(self)

  def run(self, ticks):
    """Execute one frame of the game task.

    Currently a no-op as game logic is handled by individual scenes.

    Args:
        ticks: Number of milliseconds since the last frame.
    """
    pass
