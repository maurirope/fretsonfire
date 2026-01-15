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
View and Layer Management
=========================

This module provides the layer-based UI system for Frets on Fire.
The View manages a stack of layers that are rendered with visibility
transitions.

Layer System:
    - Layers are stacked, with the top layer receiving input focus
    - Background layers stay visible when other layers are on top
    - Layers fade in/out during transitions
    - Each layer has render(), shown(), hidden() lifecycle methods

Example:
    view = View(engine)
    view.pushLayer(MainMenu(engine))   # Show main menu
    view.pushLayer(SettingsMenu())      # Settings slides in on top
    view.popLayer(settingsMenu)         # Settings slides out
"""

from OpenGL.GL import *
from OpenGL.GLU import *

import Log
from Task import Task


class Layer(Task):
    """
    Base class for UI layers.
    
    A Layer is a visual element that can be pushed onto the View stack.
    Layers handle their own rendering and respond to lifecycle events.
    
    Methods to override:
        render(visibility, topMost): Draw the layer
        shown(): Called when layer becomes visible
        hidden(): Called when layer is removed
        run(ticks): Called each frame for updates
    """
    
    def render(self, visibility, topMost):
        """
        Render the layer.
        
        Args:
            visibility (float): 0.0 (invisible) to 1.0 (fully visible)
            topMost (bool): True if this is the top layer
        """
        pass
    
    def shown(self):
        """Called when the layer is pushed onto the view."""
        pass
  
    def hidden(self):
        """Called when the layer is removed from the view."""
        pass

    def run(self, ticks):
        """
        Update the layer each frame.
        
        Args:
            ticks (int): Milliseconds since last frame
        """
        pass

    def isBackgroundLayer(self):
        """
        Check if this is a background layer.
        
        Background layers stay visible when other layers are on top.
        
        Returns:
            bool: True if this is a background layer
        """
        return False


class BackgroundLayer(Layer):
    """
    A layer that stays visible behind other layers.
    
    Use this for main menus, game scenes, and other screens that
    should remain visible when dialogs are shown on top.
    """
    
    def isBackgroundLayer(self):
        return True


class View(Task):
    """
    Manages a stack of layers with visibility transitions.
    
    The View handles:
    - Layer stack management (push/pop)
    - Fade in/out transitions
    - Rendering all visible layers
    - OpenGL projection setup
    
    Attributes:
        layers (list): Stack of active layers
        visibility (dict): Current visibility (0-1) for each layer
        transitionTime (float): Duration of fade transitions in ms
        geometry (tuple): Current viewport geometry
        aspectRatio (float): Screen width/height ratio
    """
    
    def __init__(self, engine, geometry=None):
        """
        Initialize the view.
        
        Args:
            engine: The game engine
            geometry: Optional viewport geometry (x, y, w, h)
        """
        Task.__init__(self)
        self.layers = []
        self.incoming = []       # Layers currently fading in
        self.outgoing = []       # Layers currently fading out
        self.visibility = {}     # Current visibility per layer
        self.transitionTime = 512.0
        self.geometry = geometry or glGetIntegerv(GL_VIEWPORT)
        self.savedGeometry = None
        self.engine = engine
        w = self.geometry[2] - self.geometry[0]
        h = self.geometry[3] - self.geometry[1]
        self.aspectRatio = float(w) / float(h)

    def pushLayer(self, layer):
        """
        Push a layer onto the view stack.
        
        The layer will fade in and become the top layer.
        
        Args:
            layer (Layer): The layer to push
        """
        Log.debug("View: Push: %s" % layer.__class__.__name__)
        
        if layer not in self.layers:
            self.layers.append(layer)
            self.incoming.append(layer)
            self.visibility[layer] = 0.0
            layer.shown()
        elif layer in self.outgoing:
            layer.hidden()
            layer.shown()
            self.outgoing.remove(layer)
        self.engine.addTask(layer)

    def topLayer(self):
        """
        Get the current top layer.
        
        Returns:
            Layer: The topmost non-outgoing layer, or None
        """
        layers = list(self.layers)
        layers.reverse()
        for layer in layers:
            if layer not in self.outgoing:
                return layer
        return None

    def popLayer(self, layer):
        """
        Remove a layer from the view stack.
        
        The layer will fade out before being fully removed.
        
        Args:
            layer (Layer): The layer to remove
        """
        Log.debug("View: Pop: %s" % layer.__class__.__name__)
        
        if layer in self.incoming:
            self.incoming.remove(layer)
        if layer in self.layers and layer not in self.outgoing:
            self.outgoing.append(layer)

    def popAllLayers(self):
        """Remove all layers from the view."""
        Log.debug("View: Pop all")
        for layer in list(self.layers):
            self.popLayer(layer)

    def isTransitionInProgress(self):
        """
        Check if any layer transition is in progress.
        
        Returns:
            bool: True if layers are fading in or out
        """
        return bool(self.incoming or self.outgoing)
  
    def run(self, ticks):
        """
        Update layer visibility transitions.
        
        Args:
            ticks (int): Milliseconds since last frame
        """
        if not self.layers:
            return

        topLayer = self.topLayer()
        t = ticks / self.transitionTime
        
        for layer in list(self.layers):
            if layer not in self.visibility:
                continue
            
            # Fade out layers that are leaving or not on top
            if layer in self.outgoing or (layer is not topLayer and not layer.isBackgroundLayer()):
                if self.visibility[layer] > 0.0:
                    self.visibility[layer] = max(0.0, self.visibility[layer] - t)
                else:
                    self.visibility[layer] = 0.0
                    if layer in self.outgoing:
                        self.outgoing.remove(layer)
                        self.layers.remove(layer)
                        del self.visibility[layer]
                        self.engine.removeTask(layer)
                        layer.hidden()
                    if layer in self.incoming:
                        self.incoming.remove(layer)
            
            # Fade in layers that are entering or on top
            elif layer in self.incoming or layer is topLayer:
                if self.visibility[layer] < 1.0:
                    self.visibility[layer] = min(1.0, self.visibility[layer] + t)
                else:
                    self.visibility[layer] = 1.0
                    if layer in self.incoming:
                        self.incoming.remove(layer)

    def setOrthogonalProjection(self, normalize=True, yIsDown=True):
        """
        Set up 2D orthogonal projection for UI rendering.
        
        Args:
            normalize (bool): If True, use normalized coordinates (0-1)
            yIsDown (bool): If True, Y increases downward (screen coords)
        """
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        viewport = glGetIntegerv(GL_VIEWPORT)
        if normalize:
            w = viewport[2] - viewport[0]
            h = viewport[3] - viewport[1]
            # Aspect ratio correction for 4:3 reference
            h *= (float(w) / float(h)) / (4.0 / 3.0)
            viewport = [0, 0, 1, h / w]
  
        if yIsDown:
            glOrtho(viewport[0], viewport[2] - viewport[0],
                    viewport[3] - viewport[1], viewport[1], -100, 100)
        else:
            glOrtho(viewport[0], viewport[2] - viewport[0],
                    viewport[1], viewport[3] - viewport[1], -100, 100)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
  
    def resetProjection(self):
        """Restore the previous projection matrix."""
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def setGeometry(self, geometry):
        """
        Set a custom viewport geometry.
        
        Args:
            geometry: Tuple of (x, y, width, height), can use floats (0-1)
        """
        viewport = glGetIntegerv(GL_VIEWPORT)
        w = viewport[2] - viewport[0]
        h = viewport[3] - viewport[1]
        s = (w, h, w, h)

        geometry = tuple([
            int(s[i] * coord) if isinstance(coord, float) else int(coord)
            for i, coord in enumerate(geometry)
        ])
        self.savedGeometry, self.geometry = viewport, geometry
        glViewport(*geometry)
        glScissor(*geometry)

    def resetGeometry(self):
        """Restore the previous viewport geometry."""
        assert self.savedGeometry, "No saved geometry to restore"
        
        self.savedGeometry, geometry = None, self.savedGeometry
        self.geometry = geometry
        glViewport(*geometry)
        glScissor(*geometry)

    def render(self):
        """Render all visible layers from bottom to top."""
        for layer in self.layers:
            layer.render(self.visibility[layer], layer == self.layers[-1])
