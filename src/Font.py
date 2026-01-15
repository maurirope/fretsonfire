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
Font Rendering Module.

This module provides texture-mapped font rendering for OpenGL using pygame's
font system. It renders text by caching individual glyph textures in a
texture atlas and compositing them using OpenGL quads.

Key Features:
    - TTF font loading via pygame.font
    - Glyph caching in texture atlases for efficient rendering
    - Optional text outline/shadow effect
    - String caching for repeated text rendering
    - Support for custom glyph replacement with textures
    - Right-to-left text support via reversed rendering

Example:
    >>> font = Font("font.ttf", size=32, outline=True)
    >>> font.render("Hello World", pos=(0.1, 0.5), scale=0.002)
"""

import pygame
import numpy
from OpenGL.GL import *
import sys

from Texture import Texture, TextureAtlas, TextureAtlasFullException

class Font:
  """A texture-mapped font for OpenGL rendering.
  
  Renders text using pygame's font system with glyphs cached in OpenGL
  texture atlases. Supports styling options like bold, italic, underline,
  and optional shadow/outline effects.
  
  Attributes:
      size: Font size in points.
      scale: Global scale multiplier for rendering.
      glyphCache: Dictionary mapping characters to (texture, coords) tuples.
      glyphSizeCache: Dictionary mapping characters to (width, height) tuples.
      outline: Whether to render a shadow outline behind text.
      glyphTextures: List of TextureAtlas instances for glyph storage.
      reversed: Whether to render text right-to-left.
      stringCache: Cache of pre-computed vertex data for rendered strings.
      stringCacheLimit: Maximum number of strings to cache.
      font: Underlying pygame.font.Font instance.
  """
  
  def __init__(self, fileName, size, bold = False, italic = False, underline = False, outline = True,
               scale = 1.0, reversed = False, systemFont = False):
    """Initialize a font from a TTF file.
    
    Args:
        fileName: Path to the TTF font file.
        size: Font size in points.
        bold: Whether to render in bold style. Defaults to False.
        italic: Whether to render in italic style. Defaults to False.
        underline: Whether to render with underline. Defaults to False.
        outline: Whether to draw a shadow outline. Defaults to True.
        scale: Global scale multiplier. Defaults to 1.0.
        reversed: Whether to render text right-to-left. Defaults to False.
        systemFont: Whether to try loading a system font first.
            Defaults to False.
    """
    pygame.font.init()
    self.size             = size
    self.scale            = scale
    self.glyphCache       = {}
    self.glyphSizeCache   = {}
    self.outline          = outline
    self.glyphTextures    = []
    self.reversed         = reversed
    self.stringCache      = {}
    self.stringCacheLimit = 256
    # Try loading a system font first if one was requested
    self.font           = None
    if systemFont and sys.platform != "win32":
      try:
        self.font       = pygame.font.SysFont(None, size)
      except:
        pass
    if not self.font:
      self.font         = pygame.font.Font(fileName, size)
    self.font.set_bold(bold)
    self.font.set_italic(italic)
    self.font.set_underline(underline)

  def getStringSize(self, s, scale = 0.002):
    """Get the dimensions of a string when rendered with this font.
    
    Args:
        s: The string to measure.
        scale: Scale factor for the measurement. Defaults to 0.002.
    
    Returns:
        Tuple of (width, height) in scaled units.
    """
    w = 0
    h = 0
    scale *= self.scale
    for ch in s:
      try:
        s = self.glyphSizeCache[ch]
      except:
        s = self.glyphSizeCache[ch] = self.font.size(ch)
      w += s[0]
      h = max(s[1], h)
    return (w * scale, h * scale)

  def getHeight(self):
    """Get the height of this font.
    
    Returns:
        The font height in scaled units.
    """
    return self.font.get_height() * self.scale

  def getLineSpacing(self):
    """Get the line spacing of this font.
    
    Returns:
        The recommended line spacing in scaled units.
    """
    return self.font.get_linesize() * self.scale
    
  def setCustomGlyph(self, character, texture):
    """Replace a character with a custom texture.
    
    Allows substituting a character's glyph with an arbitrary texture,
    useful for embedding icons or special symbols in text.
    
    Args:
        character: The character to replace (single character string).
        texture: Texture instance to use for the character.
    """
    texture.setFilter(GL_LINEAR, GL_LINEAR)
    texture.setRepeat(GL_CLAMP, GL_CLAMP)
    self.glyphCache[character]     = (texture, (0.0, 0.0, texture.size[0], texture.size[1]))
    s = .75 * self.getHeight() / float(texture.pixelSize[0])
    self.glyphSizeCache[character] = (texture.pixelSize[0] * s, texture.pixelSize[1] * s)

  def _renderString(self, text, pos, direction, scale):
    """Internal method to render a string using cached geometry.
    
    Builds vertex and texture coordinate arrays for the text glyphs,
    caching them for repeated rendering of the same string.
    
    Args:
        text: The string to render.
        pos: Tuple of (x, y) position for the text origin.
        direction: Tuple of (dx, dy) for text flow direction.
        scale: Scale factor for rendering.
    """
    if not text:
      return

    if not (text, scale) in self.stringCache:
      currentTexture = None
      #x, y           = pos[0], pos[1]
      x, y           = 0.0, 0.0
      vertices       = numpy.empty((4 * len(text), 2), numpy.float32)
      texCoords      = numpy.empty((4 * len(text), 2), numpy.float32)
      vertexCount    = 0
      cacheEntry     = []

      for i, ch in enumerate(text):
        g, coordinates     = self.getGlyph(ch)
        w, h               = self.getStringSize(ch, scale = scale)
        tx1, ty1, tx2, ty2 = coordinates

        # Set the initial texture
        if currentTexture is None:
          currentTexture = g

        # If the texture changed, flush the geometry
        if currentTexture != g:
          cacheEntry.append((currentTexture, vertexCount, numpy.array(vertices[:vertexCount]), numpy.array(texCoords[:vertexCount])))
          currentTexture = g
          vertexCount = 0

        vertices[vertexCount + 0]  = (x,     y)
        vertices[vertexCount + 1]  = (x + w, y)
        vertices[vertexCount + 2]  = (x + w, y + h)
        vertices[vertexCount + 3]  = (x,     y + h)
        texCoords[vertexCount + 0] = (tx1, ty2)
        texCoords[vertexCount + 1] = (tx2, ty2)
        texCoords[vertexCount + 2] = (tx2, ty1)
        texCoords[vertexCount + 3] = (tx1, ty1)
        vertexCount += 4

        x += w * direction[0]
        y += w * direction[1]
      cacheEntry.append((currentTexture, vertexCount, vertices[:vertexCount], texCoords[:vertexCount]))

      # Don't store very short strings
      if len(text) > 5:
        # Limit the cache size
        if len(self.stringCache) > self.stringCacheLimit:
          del self.stringCache[list(self.stringCache.keys())[0]]
        self.stringCache[(text, scale)] = cacheEntry
    else:
      cacheEntry = self.stringCache[(text, scale)]

    glPushMatrix()
    glTranslatef(pos[0], pos[1], 0)
    for texture, vertexCount, vertices, texCoords in cacheEntry:
      texture.bind()
      glVertexPointer(2, GL_FLOAT, 0, vertices)
      glTexCoordPointer(2, GL_FLOAT, 0, texCoords)
      glDrawArrays(GL_QUADS, 0, vertexCount)
    glPopMatrix()

  def render(self, text, pos = (0, 0), direction = (1, 0), scale = 0.002):
    """Draw text to the screen.
    
    Renders text at the specified position with optional outline effect.
    Uses OpenGL vertex arrays for efficient rendering.
    
    Args:
        text: The string to draw.
        pos: Tuple of (x, y) position in normalized coordinates.
            Defaults to (0, 0).
        direction: Tuple of (dx, dy) for text flow direction.
            Defaults to (1, 0) for left-to-right.
        scale: Scale factor for text size. Defaults to 0.002.
    """
    glEnable(GL_TEXTURE_2D)
    glEnableClientState(GL_VERTEX_ARRAY)
    glEnableClientState(GL_TEXTURE_COORD_ARRAY)

    scale *= self.scale

    if self.reversed:
      text = "".join(reversed(text))

    if self.outline:
      glPushAttrib(GL_CURRENT_BIT)
      glColor4f(0, 0, 0, glGetFloatv(GL_CURRENT_COLOR)[3])
      self._renderString(text, (pos[0] + 0.003, pos[1] + 0.003), direction, scale)
      glPopAttrib()

    self._renderString(text, pos, direction, scale)
    
    glDisableClientState(GL_VERTEX_ARRAY)
    glDisableClientState(GL_TEXTURE_COORD_ARRAY)
    glDisable(GL_TEXTURE_2D)

  def _allocateGlyphTexture(self):
    """Allocate a new texture atlas for glyph storage.
    
    Creates a TextureAtlas sized to the maximum texture size supported
    by the graphics hardware.
    
    Returns:
        A new TextureAtlas instance configured for glyph rendering.
    """
    t = TextureAtlas(size = glGetInteger(GL_MAX_TEXTURE_SIZE))
    t.texture.setFilter(GL_LINEAR, GL_LINEAR)
    t.texture.setRepeat(GL_CLAMP, GL_CLAMP)
    self.glyphTextures.append(t)
    return t

  def getGlyph(self, ch):
    """Get the texture and coordinates for a character glyph.
    
    Renders the glyph to a texture if not already cached. Uses a texture
    atlas to efficiently pack multiple glyphs into a single texture.
    
    Args:
        ch: Single character string to get the glyph for.
    
    Returns:
        Tuple of (TextureAtlas, (tx1, ty1, tx2, ty2)) where the texture
        coordinates define the glyph's location in the atlas.
    """
    try:
      return self.glyphCache[ch]
    except KeyError:
      s = self.font.render(ch, True, (255, 255, 255))

      # Draw outlines
      """
      import Image, ImageFilter
      srcImg = Image.fromstring("RGBA", s.get_size(), pygame.image.tostring(s, "RGBA"))
      img    = Image.fromstring("RGBA", s.get_size(), pygame.image.tostring(s, "RGBA"))
      for y in xrange(img.size[1]):
        for x in xrange(img.size[0]):
          a = 0
          ns = 3
          n = 0
          for ny in range(max(0, y - ns), min(img.size[1], y + ns)):
            for nx in range(max(0, x - ns), min(img.size[0], x + ns)):
              a += srcImg.getpixel((nx, ny))[3]
              n += 1
          if a and srcImg.getpixel((x, y))[3] == 0:
            img.putpixel((x, y), (0, 0, 0, a / n))
      s = pygame.image.fromstring(img.tostring(), s.get_size(), "RGBA")
      """

      if not self.glyphTextures:
        texture = self._allocateGlyphTexture()
      else:
        texture = self.glyphTextures[-1]

      # Insert the texture into the glyph cache
      try:
        coordinates = texture.add(s)
      except TextureAtlasFullException:
        # Try again with a fresh atlas
        texture = self._allocateGlyphTexture()
        return self.getGlyph(ch)

      self.glyphCache[ch] = (texture, coordinates)
      return (texture, coordinates)
