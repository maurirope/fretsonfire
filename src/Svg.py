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
SVG Image Loading and Rendering Module.

This module provides functionality for loading, parsing, and rendering SVG
(Scalable Vector Graphics) images in OpenGL. It supports a subset of the SVG
specification including paths, linear/radial gradients, and basic transforms.

The module uses a hybrid rendering approach:
    - Pre-rendered PNG textures are preferred when available for performance
    - SVG files can be parsed and rendered using OpenGL primitives
    - Caching mechanisms optimize repeated rendering operations

Key Components:
    - SvgDrawing: Main class for loading and drawing SVG images
    - SvgContext: OpenGL rendering context for SVG operations
    - SvgCache: Caching system for optimized repeated rendering
    - SvgHandler: SAX parser handler for SVG XML parsing
    - SvgTransform: 2D transformation matrix operations
    - SvgRenderStyle: Stroke and fill style management
    - SvgGradient: Gradient fill support (linear and radial)

Limitations:
    - Only translate() and matrix() transforms are supported
    - Only paths are supported (no rectangles, circles, etc.)
    - Only constant color, linear gradient, and radial gradient fills

Example:
    >>> context = SvgContext((0, 0, 800, 600))
    >>> drawing = SvgDrawing(context, "image.svg")
    >>> drawing.draw(color=(1, 1, 1, 1))
"""

import re
import os
import io
from xml import sax
from OpenGL.GL import *
from numpy import reshape, dot, transpose, identity, zeros, float32
from math import sin, cos

import Log
import Config
import SvgColors
from Texture import Texture, TextureException

# Amanith support is now deprecated
#try:
#  import amanith
#  import SvgColors
#  haveAmanith    = True
#except ImportError:
#  Log.warn("PyAmanith not found, SVG support disabled.")
#  import DummyAmanith as amanith
#  haveAmanith    = False
import DummyAmanith as amanith
haveAmanith = True

# Add support for 'foo in attributes' syntax
if not hasattr(sax.xmlreader.AttributesImpl, '__contains__'):
  sax.xmlreader.AttributesImpl.__contains__ = sax.xmlreader.AttributesImpl.has_key

#
#  Bugs and limitations:
#
#  - only the translate() and matrix() transforms are supported
#  - only paths are supported
#  - only constant color, linear gradient and radial gradient fill supported
#

Config.define("opengl",  "svgshaders",   bool,  False, text = "Use OpenGL SVG shaders",   options = {False: "No", True: "Yes"})

LOW_QUALITY    = amanith.G_LOW_RENDERING_QUALITY
NORMAL_QUALITY = amanith.G_NORMAL_RENDERING_QUALITY
HIGH_QUALITY   = amanith.G_HIGH_RENDERING_QUALITY

class SvgGradient:
  """Represents an SVG gradient (linear or radial) with transformation support.
  
  Attributes:
      gradientDesc: The Amanith gradient descriptor object.
      transform: SvgTransform instance for gradient coordinate transformation.
  """
  
  def __init__(self, gradientDesc, transform):
    """Initialize an SVG gradient.
    
    Args:
        gradientDesc: Amanith gradient descriptor from CreateLinearGradient
            or CreateRadialGradient.
        transform: SvgTransform instance for the gradient's coordinate space.
    """
    self.gradientDesc = gradientDesc
    self.transform = transform

  def applyTransform(self, transform):
    m = dot(transform.matrix, self.transform.matrix)
    self.gradientDesc.SetMatrix(transform.getGMatrix(m))

class SvgContext:
  """OpenGL rendering context for SVG drawing operations.
  
  Manages the Amanith drawing board, viewport geometry, projection settings,
  and rendering quality for SVG rendering.
  
  Attributes:
      kernel: Amanith GKernel instance.
      geometry: Tuple of (x, y, width, height) defining the viewport.
      drawBoard: Amanith GOpenGLBoard for rendering operations.
      transform: SvgTransform instance for coordinate transformations.
  """
  
  def __init__(self, geometry):
    """Initialize the SVG rendering context.
    
    Args:
        geometry: Tuple of (x, y, width, height) defining the viewport area.
    """
    self.kernel = amanith.GKernel()
    self.geometry = geometry
    self.drawBoard = amanith.GOpenGLBoard(geometry[0], geometry[0] + geometry[2],
                                          geometry[1], geometry[1] + geometry[3])
    self.drawBoard.SetShadersEnabled(Config.get("opengl", "svgshaders"))
    self.transform = SvgTransform()
    self.setGeometry(geometry)
    self.setProjection(geometry)
  
    # eat any possible OpenGL errors -- we can't handle them anyway
    try:
      glMatrixMode(GL_MODELVIEW)
    except:
      Log.warn("SVG renderer initialization failed; expect corrupted graphics. " +
               "To fix this, upgrade your OpenGL drivers and set your display " +
               "to 32 bit color precision.")

  def setGeometry(self, geometry = None):
    """Set the viewport geometry and scale transform.
    
    Args:
        geometry: Tuple of (x, y, width, height) for the viewport.
    """
    self.drawBoard.SetViewport(geometry[0], geometry[1],
                               geometry[2], geometry[3])
    self.transform.reset()
    self.transform.scale(geometry[2] / 640.0, geometry[3] / 480.0)

  def setProjection(self, geometry = None):
    """Set the projection matrix for rendering.
    
    Args:
        geometry: Optional tuple of (x, y, width, height). Uses stored
            geometry if not provided.
    """
    geometry = geometry or self.geometry
    self.drawBoard.SetProjection(geometry[0], geometry[0] + geometry[2],
                                 geometry[1], geometry[1] + geometry[3])
    self.geometry = geometry

  def setRenderingQuality(self, quality):
    # Ignored
    pass
    #if quality == LOW_QUALITY:
    #  q = amanith.G_LOW_RENDERING_QUALITY
    #elif quality == NORMAL_QUALITY:
    #  q = amanith.G_NORMAL_RENDERING_QUALITY
    #elif quality == HIGH_QUALITY:
    #  q = amanith.G_HIGH_RENDERING_QUALITY
    #else:
    #  raise RaiseValueError("Bad rendering quality.")
    #self.drawBoard.SetRenderingQuality(q)

  def getRenderingQuality(self):
    """Get the current rendering quality setting.
    
    Returns:
        Quality constant: LOW_QUALITY, NORMAL_QUALITY, or HIGH_QUALITY.
    """
    q = self.drawBoard.RenderingQuality()
    if q == amanith.G_LOW_RENDERING_QUALITY:
      return LOW_QUALITY
    elif q == amanith.G_NORMAL_RENDERING_QUALITY:
      return NORMAL_QUALITY
    return HIGH_QUALITY

  def clear(self, r = 0, g = 0, b = 0, a = 0):
    """Clear the drawing area with a specified color.
    
    Args:
        r: Red component (0.0-1.0). Defaults to 0.
        g: Green component (0.0-1.0). Defaults to 0.
        b: Blue component (0.0-1.0). Defaults to 0.
        a: Alpha component (0.0-1.0). Defaults to 0.
    """
    self.drawBoard.Clear(r, g, b, a)

class SvgRenderStyle:
  """Manages stroke and fill styling for SVG rendering.
  
  Handles parsing of SVG style attributes and applying them to the
  Amanith drawing board for rendering paths.
  
  Attributes:
      strokeColor: Stroke color as (r, g, b, a) tuple or SvgGradient.
      strokeWidth: Stroke width in pixels.
      fillColor: Fill color as (r, g, b, a) tuple or SvgGradient.
      strokeLineJoin: Line join style (miter, round, or bevel).
      strokeOpacity: Stroke opacity (0.0-1.0).
      fillOpacity: Fill opacity (0.0-1.0).
  """
  
  def __init__(self, baseStyle = None):
    """Initialize a render style, optionally copying from a base style.
    
    Args:
        baseStyle: Optional SvgRenderStyle to copy attributes from.
    """
    self.strokeColor = None
    self.strokeWidth = None
    self.fillColor = None
    self.strokeLineJoin = None
    self.strokeOpacity = None
    self.fillOpacity = None
    
    if baseStyle:
      self.__dict__.update(baseStyle.__dict__)

  def parseStyle(self, style):
    """Parse a CSS-style string into a dictionary.
    
    Args:
        style: CSS style string (e.g., "stroke:#000;fill:#fff").
    
    Returns:
        Dictionary mapping style property names to values.
    """
    s = {}
    for m in re.finditer(r"(.+?):\s*(.+?)(;|$)\s*", style):
      s[m.group(1)] = m.group(2)
    return s

  def parseColor(self, color, defs = None):
    if color.lower() == "none":
      return None

    try:
      return SvgColors.colors[color.lower()]
    except KeyError:
      pass
      
    if color[0] == "#":
      color = color[1:]
      if len(color) == 3:
        return (int(color[0], 16) / 15.0, int(color[1], 16) / 15.0, int(color[2], 16) / 15.0, 1.0)
      return (int(color[0:2], 16) / 255.0, int(color[2:4], 16) / 255.0, int(color[4:6], 16) / 255.0, 1.0)
    else:
      if not defs:
        Log.warn("No patterns or gradients defined.")
        return None
      m = re.match(r"url\(#(.+)\)", color)
      if m:
        id = m.group(1)
        if not id in defs:
          Log.warn("Pattern/gradient %s has not been defined." % id)
        return defs.get(id)

  def __eq__(self, s):
    if s:
      for k, v in list(self.__dict__.items()):
        if v != getattr(s, k):
          return False
      return True
    return False

  def __ne__(self, s):
    return not self.__eq__(s)

  def __repr__(self):
    return "<SvgRenderStyle " + " ".join(["%s:%s" % (k, v) for k, v in list(self.__dict__.items())]) + ">"

  def applyAttributes(self, attrs, defs):
    style = attrs.get("style")
    if style:
      style = self.parseStyle(style)
      #print style
      if "stroke" in style:
        self.strokeColor = self.parseColor(style["stroke"], defs)
      if "fill" in style:
        self.fillColor = self.parseColor(style["fill"], defs)
      if "stroke-width" in style:
        self.strokeWidth = float(style["stroke-width"].replace("px", ""))
      if "stroke-opacity" in style:
        self.strokeOpacity = float(style["stroke-opacity"])
      if "fill-opacity" in style:
        self.fillOpacity = float(style["fill-opacity"])
      if "stroke-linejoin" in style:
        j = style["stroke-linejoin"].lower()
        if j == "miter":
          self.strokeLineJoin = amanith.G_MITER_JOIN
        elif j == "round":
          self.strokeLineJoin = amanith.G_ROUND_JOIN
        elif j == "bevel":
          self.strokeLineJoin = amanith.G_BEVEL_JOIN

  def apply(self, drawBoard, transform):
    if self.strokeColor is not None:
      if isinstance(self.strokeColor, SvgGradient):
        self.strokeColor.applyTransform(transform)
        drawBoard.SetStrokePaintType(amanith.G_GRADIENT_PAINT_TYPE)
        drawBoard.SetStrokeGradient(self.strokeColor.gradientDesc)
      else:
        drawBoard.SetStrokePaintType(amanith.G_COLOR_PAINT_TYPE)
        drawBoard.SetStrokeColor(*self.strokeColor)
      drawBoard.SetStrokeEnabled(True)
    else:
      drawBoard.SetStrokeEnabled(False)
    
    if self.fillColor is not None:
      if isinstance(self.fillColor, SvgGradient):
        self.fillColor.applyTransform(transform)
        drawBoard.SetFillPaintType(amanith.G_GRADIENT_PAINT_TYPE)
        drawBoard.SetFillGradient(self.fillColor.gradientDesc)
      else:
        drawBoard.SetFillPaintType(amanith.G_COLOR_PAINT_TYPE)
        drawBoard.SetFillColor(*self.fillColor)
      drawBoard.SetFillEnabled(True)
    else:
      drawBoard.SetFillEnabled(False)

    if self.strokeWidth is not None:
      drawBoard.SetStrokeWidth(self.strokeWidth)
    
    if self.strokeOpacity is not None:
      drawBoard.SetStrokeOpacity(self.strokeOpacity)
      
    if self.fillOpacity is not None:
      drawBoard.SetFillOpacity(self.fillOpacity)

    if self.strokeLineJoin is not None:
      drawBoard.SetStrokeJoinStyle(self.strokeLineJoin)

class SvgTransform:
  """2D transformation matrix for SVG coordinate transformations.
  
  Supports translation, rotation, scaling, and arbitrary matrix transforms.
  Wraps a 3x3 homogeneous transformation matrix using NumPy.
  
  Attributes:
      matrix: 3x3 NumPy array representing the transformation matrix.
  """
  
  def __init__(self, baseTransform = None):
    """Initialize a transform, optionally copying from a base transform.
    
    Args:
        baseTransform: Optional SvgTransform to copy the matrix from.
    """
    self._gmatrix = amanith.GMatrix33()
    self.reset()
    
    if baseTransform:
      self.matrix = baseTransform.matrix.copy()

  def applyAttributes(self, attrs, key = "transform"):
    transform = attrs.get(key)
    if transform:
      m = re.match(r"translate\(\s*(.+?)\s*,(.+?)\s*\)", transform)
      if m:
        dx, dy = [float(c) for c in m.groups()]
        self.matrix[0, 2] += dx
        self.matrix[1, 2] += dy
      m = re.match(r"matrix\(\s*" + r"\s*,\s*".join(["(.+?)"] * 6) + r"\s*\)", transform)
      if m:
        e = [float(c) for c in m.groups()]
        e = [e[0], e[2], e[4], e[1], e[3], e[5], 0, 0, 1]
        m = reshape(e, (3, 3))
        self.matrix = dot(self.matrix, m)

  def transform(self, transform):
    """Concatenate another transform with this one.
    
    Args:
        transform: SvgTransform to multiply with this transform.
    """
    self.matrix = dot(self.matrix, transform.matrix)

  def reset(self):
    """Reset the transform to the identity matrix."""
    self.matrix = identity(3, float32)

  def translate(self, dx, dy):
    """Apply a translation to the transform.
    
    Args:
        dx: Translation in the X direction.
        dy: Translation in the Y direction.
    """
    m = zeros((3, 3))
    m[0, 2] = dx
    m[1, 2] = dy
    self.matrix += m

  def rotate(self, angle):
    """Apply a rotation to the transform.
    
    Args:
        angle: Rotation angle in radians.
    """
    m = identity(3, float32)
    s = sin(angle)
    c = cos(angle)
    m[0, 0] =  c
    m[0, 1] = -s
    m[1, 0] =  s
    m[1, 1] =  c
    self.matrix = dot(self.matrix, m)

  def scale(self, sx, sy):
    """Apply a scale transformation.
    
    Args:
        sx: Scale factor in the X direction.
        sy: Scale factor in the Y direction.
    """
    m = identity(3, float32)
    m[0, 0] = sx
    m[1, 1] = sy
    self.matrix = dot(self.matrix, m)

  def applyGL(self):
    # Interpret the 2D matrix as 3D
    m = self.matrix
    m = [m[0, 0], m[1, 0], 0.0, 0.0,
         m[0, 1], m[1, 1], 0.0, 0.0,
             0.0,     0.0, 1.0, 0.0,
         m[0, 2], m[1, 2], 0.0, 1.0]
    glMultMatrixf(m)

  def getGMatrix(self, m):
    f = float
    self._gmatrix.Set( \
      f(m[0, 0]), f(m[0, 1]), f(m[0, 2]), \
      f(m[1, 0]), f(m[1, 1]), f(m[1, 2]), \
      f(m[2, 0]), f(m[2, 1]), f(m[2, 2]))
    return self._gmatrix

  def apply(self, drawBoard):
    drawBoard.SetModelViewMatrix(self.getGMatrix(self.matrix))

class SvgHandler(sax.ContentHandler):
  """SAX content handler for parsing SVG XML documents.
  
  Processes SVG elements and converts them to drawing commands.
  Maintains stacks for styles, transforms, and context to handle
  nested SVG groups properly.
  
  Attributes:
      drawBoard: Amanith drawing board for rendering.
      styleStack: Stack of SvgRenderStyle for nested style inheritance.
      contextStack: Stack tracking the current parsing context.
      transformStack: Stack of SvgTransform for nested transforms.
      defs: Dictionary of defined gradients and patterns by ID.
      cache: SvgCache for caching rendered paths.
  """
  
  def __init__(self, drawBoard, cache):
    """Initialize the SVG handler.
    
    Args:
        drawBoard: Amanith GOpenGLBoard for rendering operations.
        cache: SvgCache instance for caching drawing commands.
    """
    self.drawBoard = drawBoard
    self.styleStack = [SvgRenderStyle()]
    self.contextStack = [None]
    self.transformStack = [SvgTransform()]
    self.defs = {}
    self.cache = cache
  
  def startElement(self, name, attrs):
    style = SvgRenderStyle(self.style())
    style.applyAttributes(attrs, self.defs)
    self.styleStack.append(style)
    
    transform = SvgTransform(self.transform())
    transform.applyAttributes(attrs)
    self.transformStack.append(transform)
    
    try:
      f = "start" + name.capitalize()
      #print f, self.transformStack
      #print len(self.styleStack)
      f = getattr(self, f)
    except AttributeError:
      return
    f(attrs)

  def endElement(self, name):
    try:
      f = "end" + name.capitalize()
      #print f, self.contextStack
      getattr(self, f)()
    except AttributeError:
      pass
    self.styleStack.pop()
    self.transformStack.pop()

  def startG(self, attrs):
    self.contextStack.append("g")

  def endG(self):
    self.contextStack.pop()

  def startDefs(self, attrs):
    self.contextStack.append("defs")

  def endDefs(self):
    self.contextStack.pop()

  def startMarker(self, attrs):
    self.contextStack.append("marker")

  def endMarker(self):
    self.contextStack.pop()

  def context(self):
    return self.contextStack[-1]

  def style(self):
    return self.styleStack[-1]

  def transform(self):
    return self.transformStack[-1]

  def startPath(self, attrs):
    if self.context() in ["g", None]:
      if "d" in attrs:
        self.style().apply(self.drawBoard, self.transform())
        self.transform().apply(self.drawBoard)
        d = str(attrs["d"])
        self.cache.addStroke(self.style(), self.transform(), self.drawBoard.DrawPaths(d))

  def createLinearGradient(self, attrs, keys):
    a = dict(attrs)
    if not "x1" in a or not "x2" in a or not "y1" in a or not "y2" in a:
      a["x1"] = a["y1"] = 0.0
      a["x2"] = a["y2"] = 1.0
    if "id" in a and "x1" in a and "x2" in a and "y1" in a and "y2" in a:
      transform = SvgTransform()
      if "gradientTransform" in a:
        transform.applyAttributes(a, key = "gradientTransform")
      x1, y1, x2, y2 = [float(a[k]) for k in ["x1", "y1", "x2", "y2"]]
      return a["id"], self.drawBoard.CreateLinearGradient((x1, y1), (x2, y2), keys), transform
    return None, None, None

  def createRadialGradient(self, attrs, keys):
    a = dict(attrs)
    if not "cx" in a or not "cy" in a or not "fx" in a or not "fy" in a:
      a["cx"] = a["cy"] = 0.0
      a["fx"] = a["fy"] = 1.0
    if "id" in a and "cx" in a and "cy" in a and "fx" in a and "fy" in a and "r" in a:
      transform = SvgTransform()
      if "gradientTransform" in a:
        transform.applyAttributes(a, key = "gradientTransform")
      cx, cy, fx, fy, r = [float(a[k]) for k in ["cx", "cy", "fx", "fy", "r"]]
      return a["id"], self.drawBoard.CreateRadialGradient((cx, cy), (fx, fy), r, keys), transform
    return None, None, None

  def startLineargradient(self, attrs):
    if self.context() == "defs":
      if "xlink:href" in attrs:
        id = attrs["xlink:href"][1:]
        if not id in self.defs:
          Log.warn("Linear gradient %s has not been defined." % id)
        else:
          keys = self.defs[id].gradientDesc.ColorKeys()
          id, grad, trans = self.createLinearGradient(attrs, keys)
          self.defs[id] = SvgGradient(grad, trans)
      else:
        self.contextStack.append("gradient")
        self.stops = []
        self.gradientAttrs = attrs
    
  def startRadialgradient(self, attrs):
    if self.context() == "defs":
      if "xlink:href" in attrs:
        id = attrs["xlink:href"][1:]
        if not id in self.defs:
          Log.warn("Radial gradient %s has not been defined." % id)
        else:
          keys = self.defs[id].gradientDesc.ColorKeys()
          id, grad, trans = self.createRadialGradient(attrs, keys)
          self.defs[id] = SvgGradient(grad, trans)
      else:
        self.contextStack.append("gradient")
        self.stops = []
        self.gradientAttrs = attrs

  def parseKeys(self, stops):
    keys = []
    for stop in self.stops:
      color, opacity, offset = None, None, None
      if "style" in stop:
        style =  self.style().parseStyle(stop["style"])
        if "stop-color" in style:
          color = self.style().parseColor(style["stop-color"])
        if "stop-opacity" in style:
          opacity = float(style["stop-opacity"])
      if "offset" in stop:
        offset = float(stop["offset"])
      if offset is not None and (color is not None or opacity is not None):
        if opacity is None: opacity = 1.0
        k = amanith.GKeyValue(offset, (color[0], color[1], color[2], opacity))
        keys.append(k)
    return keys
    
  def endLineargradient(self):
    if self.context() == "gradient":
      keys = self.parseKeys(self.stops)
      id, grad, trans = self.createLinearGradient(self.gradientAttrs, keys)
      del self.stops
      del self.gradientAttrs
      if id and grad:
        self.defs[id] = SvgGradient(grad, trans)
      self.contextStack.pop()
    
  def endRadialgradient(self):
    if self.context() == "gradient":
      keys = self.parseKeys(self.stops)
      id, grad, trans = self.createRadialGradient(self.gradientAttrs, keys)
      del self.stops
      del self.gradientAttrs
      if id and grad:
        self.defs[id] = SvgGradient(grad, trans)
      self.contextStack.pop()
    
  def startStop(self, attrs):
    if self.context() == "gradient":
      self.stops.append(attrs)
    
class SvgCache:
  """Caching system for optimized SVG rendering.
  
  Stores rendered SVG paths in a cache bank for efficient repeated
  drawing. Groups strokes by style to minimize state changes.
  
  Attributes:
      drawBoard: Amanith drawing board for rendering.
      displayList: List of (style, slot_ranges) tuples for cached paths.
      transforms: Dictionary mapping cache slots to their transforms.
      bank: Amanith cache bank for storing rendered geometry.
  """
  
  def __init__(self, drawBoard):
    """Initialize the SVG cache.
    
    Args:
        drawBoard: Amanith GOpenGLBoard for rendering operations.
    """
    self.drawBoard = drawBoard
    self.displayList = []
    self.transforms = {}
    self.bank = drawBoard.CreateCacheBank()

  def beginCaching(self):
    """Begin caching mode for recording drawing commands."""
    self.drawBoard.SetCacheBank(self.bank)
    self.drawBoard.SetTargetMode(amanith.G_CACHE_MODE)

  def endCaching(self):
    """End caching mode and return to normal rendering."""
    self.drawBoard.SetTargetMode(amanith.G_COLOR_MODE)
    self.drawBoard.SetCacheBank(None)

  def addStroke(self, style, transform, slot):
    """Add a stroke to the cache display list.
    
    Optimizes storage by grouping consecutive strokes with the same
    style into contiguous slot ranges.
    
    Args:
        style: SvgRenderStyle for the stroke.
        transform: SvgTransform for the stroke's coordinate space.
        slot: Cache slot number returned by DrawPaths.
    """
    if self.displayList:
      lastStyle = self.displayList[-1][0]
    else:
      lastStyle = None

    self.transforms[slot] = transform
    
    if lastStyle == style:
      lastSlotStart, lastSlotEnd = self.displayList[-1][1][-1]
      if lastSlotEnd == slot - 1:
        self.displayList[-1][1][-1] = (lastSlotStart, slot)
      else:
        self.displayList[-1][1].append((slot, slot))
    else:
      self.displayList.append((style, [(slot, slot)]))

  def draw(self, baseTransform):
    """Draw all cached strokes with a base transformation.
    
    Args:
        baseTransform: SvgTransform to apply to all cached geometry.
    """
    self.drawBoard.SetCacheBank(self.bank)
    for style, slotList in self.displayList:
      transform = SvgTransform(baseTransform)
      transform.transform(self.transforms[slotList[0][0]])
      transform.apply(self.drawBoard)
      style.apply(self.drawBoard, transform)
      for firstSlot, lastSlot in slotList:
        self.drawBoard.DrawCacheSlots(firstSlot, lastSlot)
    self.drawBoard.SetCacheBank(None)

    # eat any possible OpenGL errors -- we can't handle them anyway
    try:
      glMatrixMode(GL_MODELVIEW)
    except:
      pass

class SvgDrawing:
  """Main class for loading and rendering SVG images.
  
  Handles loading SVG files or data, with support for pre-rendered PNG
  textures for improved performance. Provides transformation and
  rendering capabilities.
  
  Attributes:
      svgData: Raw SVG XML data string (None if using texture).
      texture: Texture instance for bitmap rendering.
      context: SvgContext for rendering operations.
      cache: SvgCache for cached vector rendering.
      transform: SvgTransform for positioning and scaling.
  """
  
  def __init__(self, context, svgData):
    """Initialize an SVG drawing from file path or data.
    
    Supports loading from:
        - File path to .svg file (will use .png if available)
        - File path to .png file directly
        - File-like object containing SVG data
    
    Args:
        context: SvgContext for rendering operations.
        svgData: File path string or file-like object with SVG content.
    
    Raises:
        RuntimeError: If the file cannot be loaded or texture created.
    """
    self.svgData = None
    self.texture = None
    self.context = context
    self.cache = None
    self.transform = SvgTransform()

    # Detect the type of data passed in
    if isinstance(svgData, io.IOBase):
      self.svgData = svgData.read()
    elif type(svgData) == str:
      bitmapFile = svgData.replace(".svg", ".png")
      # Load PNG files directly
      if svgData.endswith(".png"):
        self.texture = Texture(svgData)
      # Check whether we have a prerendered bitmap version of the SVG file
      elif svgData.endswith(".svg") and os.path.exists(bitmapFile):
        Log.debug("Loading cached bitmap '%s' instead of '%s'." % (bitmapFile, svgData))
        self.texture = Texture(bitmapFile)
      else:
        if not haveAmanith:
          e = "PyAmanith support is deprecated and you are trying to load an SVG file."
          Log.error(e)
          raise RuntimeError(e)
        Log.debug("Loading SVG file '%s'." % (svgData))
        self.svgData = open(svgData).read()

    # Make sure we have a valid texture
    if not self.texture:
      if type(svgData) == str:
        e = "Unable to load texture for %s." % svgData
      else:
        e = "Unable to load texture for SVG file."
      Log.error(e)
      raise RuntimeError(e)

  def _cacheDrawing(self, drawBoard):
    self.cache.beginCaching()
    parser = sax.make_parser()
    sax.parseString(self.svgData, SvgHandler(drawBoard, self.cache))
    self.cache.endCaching()
    del self.svgData

  def convertToTexture(self, width, height):
    """Convert the SVG drawing to a texture for faster rendering.
    
    Note: This method is currently deprecated. SVG files should have
    pre-rendered PNG versions available.
    
    Args:
        width: Texture width in pixels.
        height: Texture height in pixels.
    
    Raises:
        RuntimeError: If no valid texture exists.
    """
    if self.texture:
      return

    e = "SVG drawing does not have a valid texture image."
    Log.error(e)
    raise RuntimeError(e)

    #try:
    #  self.texture = Texture()
    #  self.texture.bind()
    #  self.texture.prepareRenderTarget(width, height)
    #  self.texture.setAsRenderTarget()
    #  quality = self.context.getRenderingQuality()
    #  self.context.setRenderingQuality(HIGH_QUALITY)
    #  geometry = self.context.geometry
    #  self.context.setProjection((0, 0, width, height))
    #  glViewport(0, 0, width, height)
    #  self.context.clear()
    #  transform = SvgTransform()
    #  transform.translate(width / 2, height / 2)
    #  self._render(transform)
    #  self.texture.resetDefaultRenderTarget()
    #  self.context.setProjection(geometry)
    #  glViewport(*geometry)
    #  self.context.setRenderingQuality(quality)
    #except TextureException, e:
    #  Log.warn("Unable to convert SVG drawing to texture: %s" % str(e))

  def _getEffectiveTransform(self):
    transform = SvgTransform(self.transform)
    transform.transform(self.context.transform)
    return transform

  def _render(self, transform):
    glMatrixMode(GL_TEXTURE)
    glPushMatrix()
    glMatrixMode(GL_MODELVIEW)
    
    glPushAttrib(GL_ENABLE_BIT | GL_TEXTURE_BIT | GL_STENCIL_BUFFER_BIT | GL_TRANSFORM_BIT | GL_COLOR_BUFFER_BIT | GL_POLYGON_BIT | GL_CURRENT_BIT | GL_DEPTH_BUFFER_BIT)
    if not self.cache:
      self.cache = SvgCache(self.context.drawBoard)
      self._cacheDrawing(self.context.drawBoard)
    self.cache.draw(transform)
    glPopAttrib()

    glMatrixMode(GL_TEXTURE)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

  def draw(self, color = (1, 1, 1, 1)):
    """Render the SVG drawing to the screen.
    
    Applies the current transform and draws the image using either
    the cached texture or vector rendering.
    
    Args:
        color: RGBA color tuple (r, g, b, a) to modulate the image.
            Defaults to white with full opacity.
    """
    glMatrixMode(GL_TEXTURE)
    glPushMatrix()
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    self.context.setProjection()
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()

    transform = self._getEffectiveTransform()
    if self.texture:
      glLoadIdentity()
      transform.applyGL()

      glScalef(self.texture.pixelSize[0], self.texture.pixelSize[1], 1)
      glTranslatef(-.5, -.5, 0)
      glColor4f(*color)
      
      self.texture.bind()
      glEnable(GL_TEXTURE_2D)
      glBegin(GL_TRIANGLE_STRIP)
      glTexCoord2f(0.0, 1.0)
      glVertex2f(0.0, 1.0)
      glTexCoord2f(1.0, 1.0)
      glVertex2f(1.0, 1.0)
      glTexCoord2f(0.0, 0.0)
      glVertex2f(0.0, 0.0)
      glTexCoord2f(1.0, 0.0)
      glVertex2f(1.0, 0.0)
      glEnd()
      glDisable(GL_TEXTURE_2D)
    else:
      self._render(transform)
    glMatrixMode(GL_TEXTURE)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
