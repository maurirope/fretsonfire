#####################################################################
# -*- coding: utf-8 -*-                                             #
#                                                                   #
# Frets on Fire                                                     #
# Copyright (C) 2006 Sami Kyöstilä                                  #
# Single Player Refactor (2026)                                     #
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
Scene management for single-player mode.
Simplified from the original networked architecture.
"""

from Player import Player
from View import BackgroundLayer
from Input import KeyListener
from Camera import Camera
import Player
import Config

from OpenGL.GL import *
from OpenGL.GLU import *
import math
import colorsys
import pygame


class ObjectCollection:
  """Collection of game objects with ID-based access."""
  def __init__(self):
    self.objects = {}
    self._nextId = 0

  def add(self, obj):
    self._nextId += 1
    self.objects[self._nextId] = obj
    return self._nextId

  def remove(self, id):
    if id in self.objects:
      del self.objects[id]

  def get(self, id):
    return self.objects.get(id)

  def id(self, obj):
    """Get the ID for an object."""
    for id, o in self.objects.items():
      if o is obj:
        return id
    return None

  def __iter__(self):
    return iter(self.objects.values())

  def __getitem__(self, id):
    return self.objects[id]

  def __setitem__(self, id, value):
    self.objects[id] = value


class Scene(BackgroundLayer):
  """Base class for game scenes."""
  def __init__(self, engine, owner, **args):
    self.objects = ObjectCollection()
    self.args    = args
    self.owner   = owner
    self.engine  = engine
    self.actors  = []
    self.camera  = Camera()
    self.world   = None
    self.space   = None
    self.time    = 0.0
    self.players = []
    self.createCommon(**args)

  def addPlayer(self, player):
    self.players.append(player)

  def removePlayer(self, player):
    self.players.remove(player)

  def createCommon(self, **args):
    pass

  def runCommon(self, ticks, session):
    pass
    
  def run(self, ticks):
    self.time += ticks / 50.0


class SceneClient(Scene, KeyListener):
  """Client-side scene for single-player gameplay."""
  def __init__(self, engine, owner, session, **args):
    Scene.__init__(self, engine, owner, **args)
    self.session = session
    self.player = self.session.getLocalPlayer()
    self.controls = Player.Controls()
    self.createClient(**args)

  def createClient(self, **args):
    pass

  def createActor(self, name):
    """Create an actor directly (no network involved)."""
    pass

  def shown(self):
    self.engine.input.addKeyListener(self)

  def hidden(self):
    self.engine.input.removeKeyListener(self)

  def keyPressed(self, key, str):
    c = self.controls.keyPressed(key)
    if c:
      # In single-player, apply controls directly to player
      if self.player:
        self.player.controls.flags = self.controls.flags
      return True
    return False

  def keyReleased(self, key):
    c = self.controls.keyReleased(key)
    if c:
      # In single-player, apply controls directly to player
      if self.player:
        self.player.controls.flags = self.controls.flags
      return True
    return False

  def run(self, ticks):
    self.runCommon(ticks, self.session)
    Scene.run(self, ticks)
    
  def render3D(self):
    for actor in self.actors:
      actor.render()

  def render(self, visibility, topMost):
    font = self.engine.data.font

    # render the scene
    try:
      glMatrixMode(GL_PROJECTION)
      glPushMatrix()
      glLoadIdentity()
      gluPerspective(60, self.engine.view.aspectRatio, 0.1, 1000)
      glMatrixMode(GL_MODELVIEW)
      glLoadIdentity()
      
      glPushMatrix()
      self.camera.apply()
  
      self.render3D()
    finally:
      glPopMatrix()
      glMatrixMode(GL_PROJECTION)
      glPopMatrix()
      glMatrixMode(GL_MODELVIEW)


# SceneServer is kept as a stub for compatibility
# but is not used in single-player mode
class SceneServer(Scene):
  """Server-side scene - not used in single-player mode."""
  pass
