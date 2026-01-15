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
Game data and assets loader module.

This module provides the Data class which manages loading and access to
globally used game resources including fonts, sound effects, and SVG
drawings. It handles font customization with special glyphs and provides
convenient access to UI sounds.

The module defines special character constants (STAR1, STAR2, LEFT, RIGHT,
BALL1, BALL2) that map to custom font glyphs rendered from SVG images.
"""

from Font import Font
from Texture import Texture
from Svg import SvgDrawing, SvgContext
from Texture import Texture
from Audio import Sound
from Language import _
import random
import Language
import Config

# these constants define a few customized letters in the default font
STAR1 = str('\x10')
STAR2 = str('\x11')
LEFT  = str('\x12')
RIGHT = str('\x13')
BALL1 = str('\x14')
BALL2 = str('\x15')

class Data(object):
  """
  A collection of globally used data resources such as fonts and sound effects.

  This class serves as a central repository for game assets that are used
  throughout the application, including fonts, UI sounds, and decorative
  graphics. It handles asynchronous loading of resources and provides
  convenient property-based access to randomly selected sound effects.

  Attributes:
      resource (Resource): The resource manager for loading assets.
      svg (SvgContext): The SVG rendering context.
      star1 (SvgDrawing): Star graphic variant 1 for font customization.
      star2 (SvgDrawing): Star graphic variant 2 for font customization.
      left (SvgDrawing): Left arrow graphic for font customization.
      right (SvgDrawing): Right arrow graphic for font customization.
      ball1 (SvgDrawing): Ball graphic variant 1 for font customization.
      ball2 (SvgDrawing): Ball graphic variant 2 for font customization.
      loadingImage (SvgDrawing): Loading screen image.
      font (Font): Default game font for regular text.
      bigFont (Font): Large title font for headings.
      screwUpSounds (list): Collection of screw-up/mistake sound effects.
      acceptSound (Sound): Sound played when accepting a selection.
      cancelSound (Sound): Sound played when canceling.
      selectSound1 (Sound): Selection crunch sound variant 1.
      selectSound2 (Sound): Selection crunch sound variant 2.
      selectSound3 (Sound): Selection crunch sound variant 3.
      startSound (Sound): Sound played when starting a game.
  """

  def __init__(self, resource, svg):
    """
    Initialize the Data object and begin loading all game resources.

    Args:
        resource (Resource): The resource manager used to load and locate
            game assets from the data directory.
        svg (SvgContext): The SVG rendering context for drawing vector
            graphics.
    """
    self.resource = resource
    self.svg      = svg

    # load font customization images
    self.loadSvgDrawing(self, "star1",   "star1.svg", textureSize = (128, 128))
    self.loadSvgDrawing(self, "star2",   "star2.svg", textureSize = (128, 128))
    self.loadSvgDrawing(self, "left",    "left.svg",  textureSize = (128, 128))
    self.loadSvgDrawing(self, "right",   "right.svg", textureSize = (128, 128))
    self.loadSvgDrawing(self, "ball1",   "ball1.svg", textureSize = (128, 128))
    self.loadSvgDrawing(self, "ball2",   "ball2.svg", textureSize = (128, 128))

    # load misc images
    self.loadSvgDrawing(self, "loadingImage", "loading.svg", textureSize = (256, 256))

    # load all the data in parallel
    asciiOnly = not bool(Language.language)
    reversed  = _("__lefttoright__") == "__righttoleft__" and True or False
    scale     = Config.get("video", "fontscale")
    fontSize  = [22, 108]
    
    if asciiOnly:
      font    = resource.fileName("default.ttf")
      bigFont = resource.fileName("title.ttf")
    else:
      font    = \
      bigFont = resource.fileName("international.ttf")

    # load fonts
    font1     = lambda: Font(font,    fontSize[0], scale = scale, reversed = reversed, systemFont = not asciiOnly)
    font2     = lambda: Font(bigFont, fontSize[1], scale = scale, reversed = reversed, systemFont = not asciiOnly)
    resource.load(self, "font",         font1, onLoad = self.customizeFont)
    resource.load(self, "bigFont",      font2, onLoad = self.customizeFont)

    # load sounds
    resource.load(self, "screwUpSounds", self.loadScrewUpSounds)
    self.loadSoundEffect(self, "acceptSound",  "in.ogg")
    self.loadSoundEffect(self, "cancelSound",  "out.ogg")
    self.loadSoundEffect(self, "selectSound1", "crunch1.ogg")
    self.loadSoundEffect(self, "selectSound2", "crunch2.ogg")
    self.loadSoundEffect(self, "selectSound3", "crunch3.ogg")
    self.loadSoundEffect(self, "startSound",   "start.ogg")

  def loadSoundEffect(self, target, name, fileName):
    """
    Load a sound effect asynchronously and set its volume.

    Args:
        target: The object to attach the loaded sound to.
        name (str): The attribute name to assign the sound to on target.
        fileName (str): The filename of the sound file in the data directory.
    """
    volume   = Config.get("audio", "guitarvol")
    fileName = self.resource.fileName(fileName)
    self.resource.load(target, name, lambda: Sound(fileName), onLoad = lambda s: s.setVolume(volume))

  def loadScrewUpSounds(self):
    """
    Load all screw-up/mistake sound effects.

    Returns:
        list[Sound]: A list of Sound objects for mistake/screw-up audio.
    """
    return [Sound(self.resource.fileName("fiba%d.ogg" % i)) for i in range(1, 7)]
    
  def loadSvgDrawing(self, target, name, fileName, textureSize = None):
    """
    Load an SVG drawing synchronously.

    @param target:      An object that will own the drawing
    @param name:        The name of the attribute the drawing will be assigned to
    @param fileName:    The name of the file in the data directory
    @param textureSize  Either None or (x, y), in which case the file will
                        be rendered to an x by y texture
    @return:            L{SvgDrawing} instance
    """
    fileName = self.resource.fileName(fileName)
    drawing  = self.resource.load(target, name, lambda: SvgDrawing(self.svg, fileName), synch = True)
    if textureSize:
      drawing.convertToTexture(textureSize[0], textureSize[1])
    return drawing
      
      
  def customizeFont(self, font):
    """
    Apply custom glyph images to a font.

    Replaces predefined character codes with custom SVG-rendered textures
    to provide special decorative characters in the font.

    Args:
        font (Font): The font instance to customize with special glyphs.
    """
    # change some predefined characters to custom images
    font.setCustomGlyph(STAR1, self.star1.texture)
    font.setCustomGlyph(STAR2, self.star2.texture)
    font.setCustomGlyph(LEFT,  self.left.texture)
    font.setCustomGlyph(RIGHT, self.right.texture)
    font.setCustomGlyph(BALL1, self.ball1.texture)
    font.setCustomGlyph(BALL2, self.ball2.texture)

  def getSelectSound(self):
    """@return: A randomly chosen selection sound."""
    return random.choice([self.selectSound1, self.selectSound2, self.selectSound3])

  selectSound = property(getSelectSound)

  def getScrewUpSound(self):
    """@return: A randomly chosen screw-up sound."""
    return random.choice(self.screwUpSounds)

  screwUpSound = property(getScrewUpSound)

  def essentialResourcesLoaded(self):
    """
    Check if essential resources have finished loading.

    Essential resources are those required for basic UI rendering,
    primarily the fonts needed to display text.

    Returns:
        bool: True if essential resources (fonts) have been loaded,
            False otherwise.
    """
    return bool(self.font and self.bigFont)

  def resourcesLoaded(self):
    """
    Check if all resources have finished loading.

    Returns:
        bool: True if all resources have been loaded (no None values
            remain in the object's attributes), False otherwise.
    """
    return not None in list(self.__dict__.values())
