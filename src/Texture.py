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
Texture loading and management module for Frets on Fire.

This module provides OpenGL texture handling capabilities including:
- Loading textures from image files (via PIL) and pygame surfaces
- Framebuffer Object (FBO) support for render-to-texture operations
- Texture atlasing for efficient batch rendering
- Automatic mipmap generation and texture filtering

The module supports various image formats through PIL and handles
both power-of-two and non-power-of-two textures (with FBO support).
"""



import Log
import Config
import pygame
import io
from OpenGL.GL import *
from OpenGL.GLU import *
from queue import Queue, Empty

try:
  from PIL import Image
except ImportError:
  import Image

try:
  from PIL import PngImagePlugin
except ImportError:
  import PngImagePlugin

Config.define("opengl", "supportfbo", bool, False)

try:
  from glew import *
except ImportError:
  #Log.warn("GLEWpy not found -> Emulating Render to texture functionality.")
  pass

class TextureException(Exception):
  """Exception raised for texture-related errors.
  
  Raised when texture operations fail, such as unsupported image modes
  or invalid texture dimensions for the current OpenGL context.
  """
  pass

# A queue containing (function, args) pairs that clean up deleted OpenGL handles.
# The functions are called in the main OpenGL thread.
cleanupQueue = Queue()

class Framebuffer:
  """Wrapper for OpenGL Framebuffer Objects (FBO) for render-to-texture.
  
  Provides render-to-texture functionality using OpenGL framebuffer objects
  when available, with fallback to glCopyTexSubImage2D for older hardware.
  
  Attributes:
      fboSupported: Class-level flag indicating FBO hardware support.
      emulated: Whether FBO is being emulated (no native support).
      size: Tuple of (width, height) for the framebuffer.
      colorbuf: OpenGL texture handle for the color buffer.
      generateMipmap: Whether to generate mipmaps after rendering.
      fb: OpenGL framebuffer object handle.
      depthbuf: OpenGL renderbuffer handle for depth buffer.
      stencilbuf: OpenGL renderbuffer handle for stencil buffer.
  """
  fboSupported = None

  def __init__(self, texture, width, height, generateMipmap = False):
    """Initialize a framebuffer for render-to-texture operations.
    
    Args:
        texture: OpenGL texture handle to use as color attachment.
        width: Width of the framebuffer in pixels.
        height: Height of the framebuffer in pixels.
        generateMipmap: If True, generate mipmaps when resetting render target.
    
    Raises:
        TextureException: If FBO is not supported and dimensions are not
            power of two.
    """
    self.emulated       = not self._fboSupported()
    self.size           = (width, height)
    self.colorbuf       = texture
    self.generateMipmap = generateMipmap
    self.fb             = 0
    self.depthbuf       = 0
    self.stencilbuf     = 0
    
    if self.emulated:
      if (width & (width - 1)) or (height & (height - 1)):
        raise TextureException("Only power of two render target textures are supported when frame buffer objects support is missing.")
    else:
      self.fb             = glGenFramebuffersEXT(1)[0]
      self.depthbuf       = glGenRenderbuffersEXT(1)[0]
      self.stencilbuf     = glGenRenderbuffersEXT(1)[0]
      glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.fb)
      self._checkError()
      
    glBindTexture(GL_TEXTURE_2D, self.colorbuf)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    # PyOpenGL does not support NULL textures, so we must make a temporary buffer here
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, "\x00" * (width * height * 4))
    self._checkError()
    
    if self.emulated:
      return
    
    glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.fb)

    try:
      glFramebufferTexture2DEXT(GL_FRAMEBUFFER_EXT,
                                GL_COLOR_ATTACHMENT0_EXT,
                                GL_TEXTURE_2D, self.colorbuf, 0)
      self._checkError()
      
      # On current NVIDIA hardware, the stencil buffer must be packed
      # with the depth buffer (GL_NV_packed_depth_stencil) instead of
      # separate binding, so we must check for that extension here
      if glewGetExtension("GL_NV_packed_depth_stencil"):
        GL_DEPTH_STENCIL_EXT = 0x84F9
      
        glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, self.depthbuf)
        glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT,
                                 GL_DEPTH_STENCIL_EXT, width, height)
        glFramebufferRenderbufferEXT(GL_FRAMEBUFFER_EXT,
                                     GL_DEPTH_ATTACHMENT_EXT,
                                     GL_RENDERBUFFER_EXT, self.depthbuf)
        self._checkError()
      else:
        glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, self.depthbuf)
        glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT,
                                 GL_DEPTH_COMPONENT24, width, height)
        glFramebufferRenderbufferEXT(GL_FRAMEBUFFER_EXT,
                                     GL_DEPTH_ATTACHMENT_EXT,
                                     GL_RENDERBUFFER_EXT, self.depthbuf)
        self._checkError()
        glBindRenderbufferEXT(GL_RENDERBUFFER_EXT, self.stencilbuf)
        glRenderbufferStorageEXT(GL_RENDERBUFFER_EXT,
                                 GL_STENCIL_INDEX_EXT, width, height)
        glFramebufferRenderbufferEXT(GL_FRAMEBUFFER_EXT,
                                     GL_STENCIL_ATTACHMENT_EXT,
                                     GL_RENDERBUFFER_EXT, self.stencilbuf)
        self._checkError()
    finally:
      glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)

  def __del__(self):
    # Queue the buffers to be deleted later
    try:
      cleanupQueue.put((glDeleteBuffers, [3, [self.depthbuf, self.stencilbuf, self.fb]]))
    except NameError:
      pass
      
  def _fboSupported(self):
    """Check if framebuffer objects are supported by the current OpenGL context.
    
    Returns:
        bool: True if FBO extension is available and enabled, False otherwise.
    """
    if Framebuffer.fboSupported is not None:
      return Framebuffer.fboSupported
    Framebuffer.fboSupported = False
    
    if not Config.get("opengl", "supportfbo"):
      Log.warn("Frame buffer object support disabled in configuration.")
      return False
  
    if not "glewGetExtension" in globals():
      Log.warn("GLEWpy not found, so render to texture functionality disabled.")
      return False

    glewInit()

    if not glewGetExtension("GL_EXT_framebuffer_object"):
      Log.warn("No support for framebuffer objects, so render to texture functionality disabled.")
      return False
      
    if glGetString(GL_VENDOR) == "ATI Technologies Inc.":
      Log.warn("Frame buffer object support disabled until ATI learns to make proper OpenGL drivers (no stencil support).")
      return False
      
    Framebuffer.fboSupported = True
    return True

  def _checkError(self):
    """Check for OpenGL errors (currently disabled).
    
    Note:
        This method is currently a no-op as glGetError() checking
        has been disabled for performance reasons.
    """
    pass
    # No glGetError() anymore...
    #err = glGetError()
    #if (err != GL_NO_ERROR):
    #  raise TextureException(gluErrorString(err))

  def setAsRenderTarget(self):
    """Set this framebuffer as the current OpenGL render target.
    
    All subsequent rendering operations will draw to this framebuffer's
    texture instead of the default screen framebuffer.
    """
    if not self.emulated:
      glBindTexture(GL_TEXTURE_2D, 0)
      glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.fb)
      self._checkError()

  def resetDefaultRenderTarget(self):
    """Reset rendering to the default screen framebuffer.
    
    Restores the default framebuffer as the render target and optionally
    generates mipmaps for the texture that was rendered to. In emulated
    mode, copies the rendered content from the screen to the texture.
    """
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    if not self.emulated:
      glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
      glBindTexture(GL_TEXTURE_2D, self.colorbuf)
      if self.generateMipmap:
        glGenerateMipmapEXT(GL_TEXTURE_2D)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
      else:
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    else:
      glBindTexture(GL_TEXTURE_2D, self.colorbuf)
      glCopyTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 0, 0, self.size[0], self.size[1])
      glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
      
class Texture:
  """Represents an OpenGL texture, optionally loaded from disk in any format supported by PIL.
  
  This class manages OpenGL texture objects and provides methods for loading
  textures from various sources including image files, PIL images, and pygame
  surfaces. It also supports render-to-texture via framebuffer objects.
  
  Attributes:
      texture: OpenGL texture handle.
      texEnv: Texture environment mode (default GL_MODULATE).
      glTarget: OpenGL texture target (default GL_TEXTURE_2D).
      framebuffer: Optional Framebuffer for render-to-texture.
      name: Path to the source image file, if loaded from disk.
      size: Normalized texture coordinates (0.0-1.0) for the usable area.
      pixelSize: Actual pixel dimensions of the texture.
      format: OpenGL pixel format (GL_RGB, GL_RGBA, etc.).
      components: Number of color components per pixel.
  """

  def __init__(self, name = None, target = GL_TEXTURE_2D):
    """Initialize a new texture, optionally loading from a file.
    
    Args:
        name: Optional path to an image file to load.
        target: OpenGL texture target (default GL_TEXTURE_2D).
    """
    # Delete all pending textures
    try:
      func, args = cleanupQueue.get_nowait()
      func(*args)
    except Empty:
      pass
    
    self.texture = glGenTextures(1)
    self.texEnv = GL_MODULATE
    self.glTarget = target
    self.framebuffer = None

    self.setDefaults()
    self.name = name

    if name:
      self.loadFile(name)

  def loadFile(self, name):
    """Load the texture from an image file on disk.
    
    Args:
        name: Path to the image file. Supports any format that PIL can read.
    """
    self.loadImage(Image.open(name))
    self.name = name

  def loadImage(self, image):
    """Load the texture from a PIL Image object.
    
    Args:
        image: A PIL Image object in RGBA, RGB, or L (grayscale) mode.
    
    Raises:
        TextureException: If the image mode is not supported.
    """
    image = image.transpose(Image.FLIP_TOP_BOTTOM)
    if image.mode == "RGBA":
      string = image.tobytes('raw', 'RGBA', 0, -1)
      self.loadRaw(image.size, string, GL_RGBA, 4)
    elif image.mode == "RGB":
      string = image.tobytes('raw', 'RGB', 0, -1)
      self.loadRaw(image.size, string, GL_RGB, 3)
    elif image.mode == "L":
      string = image.tobytes('raw', 'L', 0, -1)
      self.loadRaw(image.size, string, GL_LUMINANCE, 1)
    else:
      raise TextureException("Unsupported image mode '%s'" % image.mode)

  def prepareRenderTarget(self, width, height, generateMipmap = True):
    """Prepare this texture for use as a render target.
    
    Args:
        width: Width of the render target in pixels.
        height: Height of the render target in pixels.
        generateMipmap: If True, generate mipmaps after rendering.
    """
    self.framebuffer = Framebuffer(self.texture, width, height, generateMipmap)
    self.pixelSize   = (width, height)
    self.size        = (1.0, 1.0)

  def setAsRenderTarget(self):
    """Set this texture as the current render target.
    
    Raises:
        AssertionError: If prepareRenderTarget was not called first.
    """
    assert self.framebuffer
    self.framebuffer.setAsRenderTarget()

  def resetDefaultRenderTarget(self):
    """Reset to rendering to the default screen buffer.
    
    Raises:
        AssertionError: If prepareRenderTarget was not called first.
    """
    assert self.framebuffer
    self.framebuffer.resetDefaultRenderTarget()

  def nextPowerOfTwo(self, n):
    """Calculate the next power of two >= n.
    
    Args:
        n: Input integer.
    
    Returns:
        int: The smallest power of two that is >= n.
    """
    m = 1
    while m < n:
      m <<= 1
    return m

  def loadSurface(self, surface, monochrome = False, alphaChannel = False):
    """Load the texture from a pygame surface.
    
    The surface is automatically resized to power-of-two dimensions if needed.
    The size attribute is adjusted to reflect the usable portion of the texture.
    
    Args:
        surface: A pygame Surface object to load.
        monochrome: If True, convert to grayscale (luminance) texture.
        alphaChannel: If True, preserve alpha channel (RGBA format).
    """

    # make it a power of two
    self.pixelSize = w, h = surface.get_size()
    w2, h2 = [self.nextPowerOfTwo(x) for x in [w, h]]
    if w != w2 or h != h2:
      s = pygame.Surface((w2, h2), pygame.SRCALPHA, 32)
      s.blit(surface, (0, h2 - h))
      surface = s
    
    if monochrome:
      # pygame doesn't support monochrome, so the fastest way
      # appears to be using PIL to do the conversion.
      string = pygame.image.tobytes(surface, "RGB")
      image = Image.fromstring("RGB", surface.get_size(), string).convert("L")
      string = image.tobytes('raw', 'L', 0, -1)
      self.loadRaw(surface.get_size(), string, GL_LUMINANCE, GL_INTENSITY8)
    else:
      if alphaChannel:
        string = pygame.image.tobytes(surface, "RGBA", True)
        self.loadRaw(surface.get_size(), string, GL_RGBA, 4)
      else:
        string = pygame.image.tobytes(surface, "RGB", True)
        self.loadRaw(surface.get_size(), string, GL_RGB, 3)
    self.size = (w / w2, h / h2)

  def loadSubsurface(self, surface, position = (0, 0), monochrome = False, alphaChannel = False):
    """Load a pygame surface into a sub-region of this texture.
    
    Args:
        surface: A pygame Surface object to load.
        position: Tuple (x, y) specifying where to place the surface.
        monochrome: If True, convert to grayscale (luminance) texture.
        alphaChannel: If True, preserve alpha channel (RGBA format).
    """

    if monochrome:
      # pygame doesn't support monochrome, so the fastest way
      # appears to be using PIL to do the conversion.
      string = pygame.image.tobytes(surface, "RGB")
      image = Image.fromstring("RGB", surface.get_size(), string).convert("L")
      string = image.tobytes('raw', 'L', 0, -1)
      self.loadSubRaw(surface.get_size(), position, string, GL_INTENSITY8)
    else:
      if alphaChannel:
        string = pygame.image.tobytes(surface, "RGBA", True)
        self.loadSubRaw(surface.get_size(), position, string, GL_RGBA)
      else:
        string = pygame.image.tobytes(surface, "RGB", True)
        self.loadSubRaw(surface.get_size(), position, string, GL_RGB)

  def loadRaw(self, size, string, format, components):
    """Load raw pixel data into the texture with mipmap generation.
    
    Args:
        size: Tuple (width, height) of the image in pixels.
        string: Raw pixel data as bytes.
        format: OpenGL pixel format constant (GL_RGB, GL_RGBA, GL_LUMINANCE).
        components: Number of components or internal format constant.
    """
    self.pixelSize = size
    self.size = (1.0, 1.0)
    self.format = format
    self.components = components
    (w, h) = size
    Texture.bind(self)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    gluBuild2DMipmaps(self.glTarget, components, w, h, format, GL_UNSIGNED_BYTE, string)

  def loadSubRaw(self, size, position, string, format):
    """Load raw pixel data into a sub-region of the texture.
    
    Args:
        size: Tuple (width, height) of the sub-image in pixels.
        position: Tuple (x, y) offset into the texture.
        string: Raw pixel data as bytes.
        format: OpenGL pixel format constant.
    """
    Texture.bind(self)
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    glTexSubImage2D(self.glTarget, 0, position[0], position[1], size[0], size[1], format, GL_UNSIGNED_BYTE, string)

  def loadEmpty(self, size, format):
    """Initialize the texture with empty (zeroed) pixel data.
    
    Args:
        size: Tuple (width, height) of the texture in pixels.
        format: OpenGL pixel format constant.
    """
    self.pixelSize = size
    self.size = (1.0, 1.0)
    self.format = format
    Texture.bind(self)
    glTexImage2D(GL_TEXTURE_2D, 0, format, size[0], size[1], 0,
                 format, GL_UNSIGNED_BYTE, "\x00" * (size[0] * size[1] * 4))

  def setDefaults(self):
    """Set the default OpenGL options for this texture.
    
    Configures clamping, linear mipmap filtering, and perspective correction.
    """
    self.setRepeat()
    self.setFilter()
    glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)

  def setRepeat(self, u=GL_CLAMP, v=GL_CLAMP):
    """Set texture wrapping mode for U and V coordinates.
    
    Args:
        u: Wrapping mode for U (horizontal) coordinate. Default GL_CLAMP.
        v: Wrapping mode for V (vertical) coordinate. Default GL_CLAMP.
    """
    Texture.bind(self)
    glTexParameteri(self.glTarget, GL_TEXTURE_WRAP_S, u)
    glTexParameteri(self.glTarget, GL_TEXTURE_WRAP_T, v)

  def setFilter(self, min=GL_LINEAR_MIPMAP_LINEAR, mag=GL_LINEAR):
    """Set texture filtering mode for minification and magnification.
    
    Args:
        min: Minification filter. Default GL_LINEAR_MIPMAP_LINEAR.
        mag: Magnification filter. Default GL_LINEAR.
    """
    Texture.bind(self)
    glTexParameteri(self.glTarget, GL_TEXTURE_MIN_FILTER, min)
    glTexParameteri(self.glTarget, GL_TEXTURE_MAG_FILTER, mag)

  def __del__(self):
    # Queue this texture to be deleted later
    try:
      cleanupQueue.put((glDeleteTextures, [self.texture]))
    except NameError:
      pass

  def bind(self, glTarget = None):
    """Bind this texture in the current OpenGL context.
    
    Args:
        glTarget: Optional texture target override. If None, uses self.glTarget.
    """
    if not glTarget:
        glTarget = self.glTarget
    glBindTexture(glTarget, self.texture)
    glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, self.texEnv)

#
# Texture atlas
#
TEXTURE_ATLAS_SIZE = 1024

class TextureAtlasFullException(Exception):
  """Exception raised when the texture atlas has no room for more surfaces."""
  pass

class TextureAtlas(object):
  """A texture atlas for packing multiple surfaces into a single texture.
  
  Texture atlases improve rendering performance by reducing texture bind
  calls when drawing many small images. Surfaces are packed left-to-right,
  top-to-bottom using a simple row-based algorithm.
  
  Attributes:
      texture: The underlying Texture object.
      cursor: Current (x, y) position for the next surface.
      rowHeight: Height of the current row being filled.
      surfaceCount: Number of surfaces added to the atlas.
  """
  def __init__(self, size = TEXTURE_ATLAS_SIZE):
    """Initialize an empty texture atlas.
    
    Args:
        size: Size of the atlas texture (width and height) in pixels.
              Default is TEXTURE_ATLAS_SIZE (1024).
    """
    self.texture      = Texture()
    self.cursor       = (0, 0)
    self.rowHeight    = 0
    self.surfaceCount = 0
    self.texture.loadEmpty((size, size), GL_RGBA)

  def add(self, surface, margin = 0):
    """Add a pygame surface to the texture atlas.
    
    Args:
        surface: A pygame Surface to add to the atlas.
        margin: Optional margin around the surface in pixels.
    
    Returns:
        tuple: Normalized texture coordinates (u1, v1, u2, v2) for the
            uploaded surface region.
    
    Raises:
        ValueError: If the surface is too large to fit in the atlas.
        TextureAtlasFullException: If there is no room left in the atlas.
    """
    w, h = surface.get_size()
    x, y = self.cursor

    w += margin
    h += margin

    if w > self.texture.pixelSize[0] or h > self.texture.pixelSize[1]:
      raise ValueError("Surface is too big to fit into atlas.")

    if x + w >= self.texture.pixelSize[0]:
      x = 0
      y += self.rowHeight
      self.rowHeight = 0

    if y + h >= self.texture.pixelSize[1]:
      Log.debug("Texture atlas %s full after %d surfaces." % (self.texture.pixelSize, self.surfaceCount))
      raise TextureAtlasFullException()

    self.texture.loadSubsurface(surface, position = (x, y), alphaChannel = True)

    self.surfaceCount += 1
    self.rowHeight = max(self.rowHeight, h)
    self.cursor = (x + w, y + h)

    # Return the coordinates for the uploaded texture patch
    w -= margin
    h -= margin
    return  x      / float(self.texture.pixelSize[0]),  y      / float(self.texture.pixelSize[1]), \
           (x + w) / float(self.texture.pixelSize[0]), (y + h) / float(self.texture.pixelSize[1])

  def bind(self):
    """Bind the atlas texture in the current OpenGL context."""
    self.texture.bind()
