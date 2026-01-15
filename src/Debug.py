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
Debug overlay layer for Frets on Fire.

This module provides a visual debugging overlay that displays real-time
information about the game engine's internal state, including:
- Active tasks and frame tasks
- Rendering layers (active, incoming, outgoing)
- Loaded scenes and resource loaders
- Input listeners (mouse, keyboard, system)
- System statistics (threads, FPS, sessions)

The debug layer can be toggled during gameplay to help developers
diagnose performance issues, track resource loading, and understand
the current state of the game engine.
"""

from OpenGL.GL import *
from View import Layer

import gc
import threading
import Log

class DebugLayer(Layer):
  """
  A visual overlay layer that displays debug information about the game engine.
  
  This layer renders text information in a green color over the game view,
  organized into sections showing tasks, layers, scenes, loaders, input
  listeners, and system statistics.
  
  Attributes:
      engine: Reference to the main game engine instance.
  """
  
  def __init__(self, engine):
    """Initialize the debug layer.
    
    Args:
        engine: The GameEngine instance to monitor and display info for.
    """
    self.engine = engine
    #gc.set_debug(gc.DEBUG_LEAK)

  def className(self, instance):
    """Extract the class name from an object instance.
    
    Args:
        instance: Any object instance.
        
    Returns:
        The class name as a string (without module prefix).
    """
    return str(instance.__class__).split(".")[1]
  
  def render(self, visibility, topMost):
    """Render the debug overlay with engine state information.
    
    Args:
        visibility: The visibility level of this layer (0.0 to 1.0).
        topMost: Whether this layer is currently the topmost layer.
    """
    self.engine.view.setOrthogonalProjection(normalize = True)
    
    try:
      font = self.engine.data.font
      scale = 0.0008
      glColor3f(.25, 1, .25)

      x, y = (.05, .05)
      h = font.getHeight() * scale
      
      font.render("Tasks:", (x, y), scale = scale)
      for task in self.engine.tasks + self.engine.frameTasks:
        font.render(self.className(task), (x + .1, y), scale = scale)
        y += h
        
      x, y = (.5, .05)
      font.render("Layers:", (x, y), scale = scale)
      for layer in self.engine.view.layers + self.engine.view.incoming + self.engine.view.outgoing + list(self.engine.view.visibility.keys()):
        font.render(self.className(layer), (x + .1, y), scale = scale)
        y += h
        
      x, y = (.05, .4)
      font.render("Scenes:", (x, y), scale = scale)
      if "world" in dir(self.engine.server):
        for scene in self.engine.server.world.scenes:
          font.render(self.className(scene), (x + .1, y), scale = scale)
          y += h
        
      x, y = (.5, .4)
      font.render("Loaders:", (x, y), scale = scale)
      for loader in self.engine.resource.loaders:
        font.render(str(loader), (x + .1, y), scale = scale)
        y += h
        
      x, y = (.5, .55)
      font.render("Input:", (x, y), scale = scale)
      for listener in self.engine.input.mouseListeners + \
                      self.engine.input.keyListeners + \
                      self.engine.input.systemListeners + \
                      self.engine.input.priorityKeyListeners:
        font.render(self.className(listener), (x + .1, y), scale = scale)
        y += h
        
      x, y = (.05, .55)
      font.render("System:", (x, y), scale = scale)
      font.render("%d threads" % threading.activeCount(), (x + .1, y), scale = scale)
      y += h
      font.render("%.2f fps" % self.engine.timer.fpsEstimate, (x + .1, y), scale = scale)
      y += h
      font.render("%d sessions, server %s" % (len(self.engine.sessions), self.engine.server and "on" or "off"), (x + .1, y), scale = scale)
      #y += h
      #font.render("%d gc objects" % len(gc.get_objects()), (x + .1, y), scale = scale)
      #y += h
      #font.render("%d collected" % gc.collect(), (x + .1, y), scale = scale)

    finally:
      self.engine.view.resetProjection()

  def gcDump(self):
    """Perform garbage collection and dump garbage objects to a file.
    
    Runs a garbage collection cycle, logs statistics about collected
    objects, and writes any remaining garbage objects to 'gcdump.txt'
    for debugging memory leaks.
    """
    import World
    before = len(gc.get_objects())
    coll   = gc.collect()
    after  = len(gc.get_objects())
    Log.debug("%d GC objects collected, total %d -> %d." % (coll, before, after))
    fn = "gcdump.txt"
    f = open(fn, "w")
    n = 0
    gc.collect()
    for obj in gc.garbage:
      try:
        print(obj, file=f)
        n += 1
      except:
        pass
    f.close()
    Log.debug("Wrote a dump of %d GC garbage objects to %s." % (n, fn))
