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
Video display initialization and management module.

This module provides the Video class for handling pygame/OpenGL display
initialization, video mode configuration, fullscreen toggling, and
display buffer management. It serves as the primary interface for
setting up the game's graphical output.
"""

import pygame
import os
from OpenGL.GL import *
from OpenGL.GL.ARB.multisample import *
import Log


class Video:
  """Manages video display initialization and OpenGL rendering context.

  This class handles the creation and configuration of the pygame display
  surface with OpenGL support, including multisampling (antialiasing),
  fullscreen mode, and display buffer management.

  Attributes:
      screen: The pygame display surface, or None if not initialized.
      caption: The window title string displayed in the title bar.
      fullscreen: Boolean indicating whether fullscreen mode is active.
      flags: The pygame display flags used for the current video mode.
  """

  def __init__(self, caption="Game"):
    """Initialize the Video manager.

    Args:
        caption: The window title to display. Defaults to "Game".
    """
    self.screen     = None
    self.caption    = caption
    self.fullscreen = False
    self.flags      = True

  def setMode(self, resolution, fullscreen=False, flags=pygame.OPENGL | pygame.DOUBLEBUF,
              multisamples=0):
    """Set the video display mode with OpenGL context.

    Initializes pygame display with the specified resolution and OpenGL
    attributes. Configures 32-bit color depth (8 bits per channel) and
    optional multisampling for antialiasing.

    Args:
        resolution: A tuple (width, height) specifying the display resolution.
        fullscreen: If True, enable fullscreen mode. Defaults to False.
        flags: Pygame display flags. Defaults to OPENGL | DOUBLEBUF.
        multisamples: Number of samples for antialiasing (0 to disable).
            Defaults to 0.

    Returns:
        bool: True if the display was successfully created, False otherwise.

    Raises:
        Exception: If video setup fails without multisampling fallback option.
    """
    if fullscreen:
      flags |= pygame.FULLSCREEN
      
    self.flags      = flags
    self.fullscreen = fullscreen

    try:    
      pygame.display.quit()
    except:
      pass
      
    pygame.display.init()
    
    pygame.display.gl_set_attribute(pygame.GL_RED_SIZE,   8)
    pygame.display.gl_set_attribute(pygame.GL_GREEN_SIZE, 8)
    pygame.display.gl_set_attribute(pygame.GL_BLUE_SIZE,  8)
    pygame.display.gl_set_attribute(pygame.GL_ALPHA_SIZE, 8)
      
    if multisamples:
      pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1);
      pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, multisamples);

    try:
      self.screen = pygame.display.set_mode(resolution, flags)
    except Exception as e:
      Log.error(str(e))
      if multisamples:
        Log.warn("Video setup failed. Trying without antialiasing.")
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0);
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 0);
        multisamples = 0
        self.screen = pygame.display.set_mode(resolution, flags)
      else:
        Log.error("Video setup failed. Make sure your graphics card supports 32 bit display modes.")
        raise

    pygame.display.set_caption(self.caption)
    pygame.mouse.set_visible(False)

    if multisamples:
      try:
        glEnable(GL_MULTISAMPLE_ARB)
      except:
        pass

    return bool(self.screen)

  def toggleFullscreen(self):
    """Toggle between fullscreen and windowed display modes.

    Returns:
        bool: True if the toggle was successful, False otherwise.

    Raises:
        AssertionError: If called before the display screen is initialized.
    """
    assert self.screen

    return pygame.display.toggle_fullscreen()

  def flip(self):
    """Swap the front and back display buffers.

    Updates the display by swapping the OpenGL double buffers,
    making the rendered frame visible on screen.
    """
    pygame.display.flip()

  def getVideoModes(self):
    """Get a list of available fullscreen video modes.

    Returns:
        list: A list of (width, height) tuples representing available
            display resolutions, sorted from largest to smallest.
            Returns -1 if any resolution is supported.
    """
    return pygame.display.list_modes()
