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
Credits screen module for Frets on Fire.

This module implements the animated credits sequence that displays
game contributors, song credits, and acknowledgments. It features
a smooth scrolling display with background animations and music.

Classes:
    Element: Base class for scrollable credit elements.
    Text: Renders styled text entries in the credits.
    Picture: Displays images (logos, artwork) in the credits.
    Credits: Main credits scene with scrolling animation and input handling.

The credits screen is typically accessed from the main menu and plays
background music while scrolling through the contributor list.
"""

import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
import math

from View import Layer
from Input import KeyListener
from Language import _
import MainMenu
import Song
import Version
import Player

class Element:
  """
  Base class for scrollable credit elements.
  
  Credit elements represent individual items that can be displayed
  in the scrolling credits sequence, such as text entries or images.
  Subclasses must implement getHeight() and render() methods.
  """
  
  def getHeight(self):
    """
    Get the height of this element.
    
    Returns:
        float: The height as a fraction of the screen height (0.0 to 1.0).
    """
    return 0

  def render(self, offset):
    """
    Render this element at the specified vertical position.
    
    Args:
        offset: Vertical offset as a fraction of screen height (0.0 = top, 1.0 = bottom).
    """
    pass


class Text(Element):
  """
  A styled text entry for the credits scroller.
  
  Renders text with configurable font, size, color, and alignment.
  Used for displaying contributor names, titles, and descriptions.
  
  Attributes:
      text: The text string to display.
      font: The Font object used for rendering.
      color: RGBA color tuple (r, g, b, a) for the text.
      alignment: Text alignment ('left', 'right', or 'center').
      scale: Font scaling factor.
      size: Calculated (width, height) tuple of the rendered text.
  """
  
  def __init__(self, font, scale, color, alignment, text):
    """
    Initialize a text element.
    
    Args:
        font: The Font object to use for rendering.
        scale: Font scaling factor.
        color: RGBA color tuple (r, g, b, a).
        alignment: Text alignment ('left', 'right', or 'center').
        text: The text string to display.
    """
    self.text      = text
    self.font      = font
    self.color     = color
    self.alignment = alignment
    self.scale     = scale
    self.size      = self.font.getStringSize(self.text, scale=scale)

  def getHeight(self):
    """
    Get the height of this text element.
    
    Returns:
        float: The text height as a fraction of screen height.
    """
    return self.size[1]

  def render(self, offset):
    """
    Render this text at the specified vertical position.
    
    Args:
        offset: Vertical offset as a fraction of screen height.
    """
    if self.alignment == "left":
      x = .1
    elif self.alignment == "right":
      x = .9 - self.size[0]
    elif self.alignment == "center":
      x = .5 - self.size[0] / 2
    glColor4f(*self.color)
    self.font.render(self.text, (x, offset), scale=self.scale)


class Picture(Element):
  """
  An image element for the credits scroller.
  
  Displays SVG images such as logos or artwork within the scrolling
  credits sequence.
  
  Attributes:
      height: The display height as a fraction of screen height.
      engine: Reference to the game engine.
      drawing: The loaded SVG drawing object.
  """
  
  def __init__(self, engine, fileName, height):
    """
    Initialize a picture element.
    
    Args:
        engine: The game engine instance.
        fileName: Name of the SVG file to load (relative to data path).
        height: Display height as a fraction of screen height (0.0 to 1.0).
    """
    self.height = height
    self.engine = engine
    engine.loadSvgDrawing(self, "drawing", fileName)

  def getHeight(self):
    """
    Get the height of this picture element.
    
    Returns:
        float: The configured height as a fraction of screen height.
    """
    return self.height

  def render(self, offset):
    """
    Render this picture at the specified vertical position.
    
    Args:
        offset: Vertical offset as a fraction of screen height.
    """
    self.drawing.transform.reset()
    w, h = self.engine.view.geometry[2:4]
    self.drawing.transform.translate(.5 * w, h - (.5 * self.height + offset) * h * float(w) / float(h))
    self.drawing.transform.scale(1, -1)
    self.drawing.draw()


class Credits(Layer, KeyListener):
  """
  Credits screen scene with animated scrolling display.
  
  Displays an animated credits sequence featuring contributor names,
  song credits, and acknowledgments. The scene includes background
  animations with floating images and plays background music.
  
  The credits can be dismissed by pressing cancel, key1, key2, or Enter.
  The scene automatically returns to the main menu when complete.
  
  Attributes:
      engine: Reference to the game engine.
      time: Animation time counter.
      offset: Current scroll position (1.0 = start, negative = scrolled up).
      song: The background music Song object.
      credits: List of Element objects to display in the scroller.
  """
  
  def __init__(self, engine, songName=None):
    """
    Initialize the credits scene.
    
    Args:
        engine: The game engine instance.
        songName: Optional song name to play (defaults to 'defy').
    """
    self.engine      = engine
    self.time        = 0.0
    self.offset      = 1.0
    self.songLoader  = self.engine.resource.load(self, "song", lambda: Song.loadSong(self.engine, "defy", playbackOnly = True),
                                                 onLoad = self.songLoaded)
    self.engine.loadSvgDrawing(self, "background1", "editor.svg")
    self.engine.loadSvgDrawing(self, "background2", "keyboard.svg")
    self.engine.loadSvgDrawing(self, "background3", "cassette.svg")
    self.engine.boostBackgroundThreads(True)

    nf = self.engine.data.font
    bf = self.engine.data.bigFont
    ns = 0.002
    bs = 0.001
    hs = 0.003
    c1 = (1, 1, .5, 1)
    c2 = (1, .75, 0, 1)

    space = Text(nf, hs, c1, "center", " ")
    self.credits = [
      Picture(self.engine, "logo.svg", .25),
      Text(nf, bs, c2, "center", " "),
      Text(nf, bs, c2, "center", _("Version %s") % Version.version()),
      Text(nf, ns, c1, "center", _("Python 3 Port & Refactor")),
      space,
      Text(nf, ns, c1, "left",   _("Python 3 Port,")),
      Text(nf, ns, c1, "left",   _("Modernization:")),
      Text(nf, ns, c2, "right",  "Mauricio Rodriguez Perdomo"),
      Text(nf, bs, c2, "right",  _("(2026)")),
      space,
      Text(nf, ns, c1, "left",   _("Original Game Design,")),
      Text(nf, ns, c1, "left",   _("Programming:")),
      Text(nf, ns, c2, "right",  "Sami Kyostila"),
      space,
      Text(nf, ns, c1, "left",   _("Music,")),
      Text(nf, ns, c1, "left",   _("Sound Effects:")),
      Text(nf, ns, c2, "right",  "Tommi Inkila"),
      space,
      Text(nf, ns, c1, "left",   _("Graphics:")),
      Text(nf, ns, c2, "right",  "Joonas Kerttula"),
      space,
      Text(nf, ns, c1, "left",   _("Introducing:")),
      Text(nf, ns, c2, "right",  "Mikko Korkiakoski"),
      Text(nf, ns, c2, "right",  _("as Jurgen, Your New God")),
      space,
      Text(nf, ns, c2, "right",  "Marjo Hakkinen"),
      Text(nf, ns, c2, "right",  _("as Groupie")),
      space,
      Text(nf, ns, c1, "left",   _("Song Credits:")),
      Text(nf, ns, c2, "right",  _("Bang Bang, Mystery Man")),
      Text(nf, bs, c2, "right",  _("music by Mary Jo and Tommi Inkila")),
      Text(nf, bs, c2, "right",  _("lyrics by Mary Jo")),
      space,
      Text(nf, ns, c2, "right",  _("Defy The Machine")),
      Text(nf, bs, c2, "right",  _("music by Tommi Inkila")),
      space,
      Text(nf, ns, c2, "right",  _("This Week I've Been")),
      Text(nf, ns, c2, "right",  _("Mostly Playing Guitar")),
      Text(nf, bs, c2, "right",  _("composed and performed by Tommi Inkila")),
      space,
      Text(nf, ns, c1, "left",   _("Testing:")),
      Text(nf, ns, c2, "right",  "Mikko Korkiakoski"),
      Text(nf, ns, c2, "right",  "Tomi Kyostila"),
      Text(nf, ns, c2, "right",  "Jani Vaarala"),
      Text(nf, ns, c2, "right",  "Juho Jamsa"),
      Text(nf, ns, c2, "right",  "Olli Jakola"),
      space,
      Text(nf, ns, c1, "left",   _("Mac OS X port:")),
      Text(nf, ns, c2, "right",  "Tero Pihlajakoski"),
      space,
      Text(nf, ns, c1, "left",   _("Special thanks to:")),
      Text(nf, ns, c2, "right",  "Tutorial inspired by adam02"),
      space,
      Text(nf, ns, c1, "left",   _("Made with:")),
      Text(nf, ns, c2, "right",  "Python"),
      Text(nf, bs, c2, "right",  "http://www.python.org"),
      space,
      Text(nf, ns, c2, "right",  "PyGame"),
      Text(nf, bs, c2, "right",  "http://www.pygame.org"),
      space,
      Text(nf, ns, c2, "right",  "PyOpenGL"),
      Text(nf, bs, c2, "right",  "http://pyopengl.sourceforge.net"),
      space,
      Text(nf, ns, c2, "right",  "Pillow"),
      Text(nf, bs, c2, "right",  "http://python-pillow.org"),
      space,
      Text(nf, ns, c2, "right",  "MXM Python Midi Package"),
      Text(nf, bs, c2, "right",  "(bundled)"),
      space,
      space,
      Text(nf, bs, c1, "center", _("Source Code available under the GNU General Public License")),
      Text(nf, bs, c2, "center", "https://github.com/skyostil/fretsonfire"),
      space,
      space,
      Text(nf, bs, c1, "center", _("Original game Copyright 2006-2008")),
      Text(nf, bs, c1, "center", _("Python 3 port Copyright 2026")),
    ]

  def songLoaded(self, song):
    """
    Callback when background music has finished loading.
    
    Args:
        song: The loaded Song object.
    """
    self.engine.boostBackgroundThreads(False)
    song.play()

  def shown(self):
    """Called when the credits scene becomes visible. Registers input listener."""
    self.engine.input.addKeyListener(self)

  def hidden(self):
    """Called when the credits scene is hidden. Fades music and returns to main menu."""
    if self.song:
      self.song.fadeout(1000)
    self.engine.input.removeKeyListener(self)
    self.engine.view.pushLayer(MainMenu.MainMenu(self.engine))

  def quit(self):
    """Exit the credits scene by removing it from the view layer stack."""
    self.engine.view.popLayer(self)

  def keyPressed(self, key, str):
    """
    Handle key press events.
    
    Allows the user to skip the credits by pressing cancel, fret keys, or Enter.
    
    Args:
        key: The pygame key code.
        str: The string representation of the key.
        
    Returns:
        bool: True to indicate the event was handled.
    """
    if self.engine.input.controls.getMapping(key) in [Player.CANCEL, Player.KEY1, Player.KEY2] or key == pygame.K_RETURN:
      self.songLoader.cancel()
      self.quit()
    return True

  def run(self, ticks):
    """
    Update the credits animation state.
    
    Args:
        ticks: Time elapsed since last update in milliseconds.
    """
    self.time   += ticks / 50.0
    if self.song:
      self.offset -= ticks / 5000.0

    if self.offset < -6.1:
      self.quit()

  def render(self, visibility, topMost):
    """
    Render the credits scene.
    
    Draws animated background images and scrolls through credit elements.
    
    Args:
        visibility: Scene visibility factor (0.0 to 1.0) for fade transitions.
        topMost: Whether this is the topmost visible layer.
    """
    v = 1.0 - ((1 - visibility) ** 2)

    # Render the background    
    t = self.time / 100 + 34
    w, h, = self.engine.view.geometry[2:4]
    r = .5
    for i, background in [(0, self.background1), (1, self.background2), (2, self.background3)]:
      background.transform.reset()
      background.transform.translate((1 - v) * 2 * w + w / 2 + math.cos(t / 2) * w / 2 * r, h / 2 + math.sin(t) * h / 2 * r)
      background.transform.translate(0, -h * (((self.offset + i * 2) % 6.0) - 3.0))
      background.transform.rotate(math.sin(t * 4 + i) / 2)
      background.transform.scale(math.sin(t / 8) + 3, math.sin(t / 8) + 3)
      background.draw()
    
    self.engine.view.setOrthogonalProjection(normalize = True)
    font = self.engine.data.font

    # render the scroller elements
    y = self.offset
    glTranslatef(-(1 - v), 0, 0)
    try:
      for element in self.credits:
        h = element.getHeight()
        if y + h > 0.0 and y < 1.0:
          element.render(y)
        y += h
        if y > 1.0:
          break
    finally:
      self.engine.view.resetProjection()
