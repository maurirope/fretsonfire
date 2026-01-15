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
Stage background effects and layer rendering module.

This module provides the Stage class and associated effect classes for
rendering dynamic background and foreground visuals during gameplay.
The stage consists of multiple graphical layers that can have various
animation effects attached to them, triggered by gameplay events like
beats, note picks, and misses.

Layers are defined in a configuration file (stage.ini) and can include
effects such as lighting changes, rotations, wiggles, and scaling that
respond to the music and player performance.
"""

from configparser import ConfigParser
from OpenGL.GL import *
import math
import Log
import Theme

class Layer(object):
  """
  A graphical stage layer that can have animation effects attached.
  
  Layers are the building blocks of stage visuals. Each layer contains
  a single texture/drawing that can be positioned, scaled, rotated, and
  colored. Multiple effects can be attached to animate these properties
  based on gameplay events.
  
  Attributes:
      stage: The parent Stage instance.
      drawing: The SvgDrawing texture for this layer.
      position (tuple): (x, y) position offset as fractions of screen size.
      angle (float): Rotation angle in radians.
      scale (tuple): (x, y) scale factors.
      color (tuple): RGBA color multiplier.
      srcBlending: OpenGL source blending mode.
      dstBlending: OpenGL destination blending mode.
      effects (list): List of Effect instances attached to this layer.
  """
  def __init__(self, stage, drawing):
    """
    Initialize a Layer.
    
    Args:
        stage: The containing Stage instance.
        drawing: SvgDrawing for this layer. Should be rendered to a texture
            for performance.
    """
    self.stage       = stage
    self.drawing     = drawing
    self.position    = (0.0, 0.0)
    self.angle       = 0.0
    self.scale       = (1.0, 1.0)
    self.color       = (1.0, 1.0, 1.0, 1.0)
    self.srcBlending = GL_SRC_ALPHA
    self.dstBlending = GL_ONE_MINUS_SRC_ALPHA
    self.effects     = []
  
  def render(self, visibility):
    """
    Render the layer with all its effects applied.
    
    Transforms the layer based on position, scale, angle, and any attached
    effects, then draws the texture with the current color and blending.
    
    Args:
        visibility: Opacity factor from 0.0 (invisible) to 1.0 (fully visible).
            Used for fade-in/fade-out transitions.
    """
    w, h, = self.stage.engine.view.geometry[2:4]
    v = 1.0 - visibility ** 2
    self.drawing.transform.reset()
    self.drawing.transform.translate(w / 2, h / 2)
    if v > .01:
      self.color = (self.color[0], self.color[1], self.color[2], visibility)
      if self.position[0] < -.25:
        self.drawing.transform.translate(-v * w, 0)
      elif self.position[0] > .25:
        self.drawing.transform.translate(v * w, 0)
    self.drawing.transform.scale(self.scale[0], -self.scale[1])
    self.drawing.transform.translate(self.position[0] * w / 2, -self.position[1] * h / 2)
    self.drawing.transform.rotate(self.angle)

    # Blend in all the effects
    for effect in self.effects:
      effect.apply()
    
    glBlendFunc(self.srcBlending, self.dstBlending)
    self.drawing.draw(color = self.color)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

class Effect(object):
  """
  Base class for animation effects that can be attached to a Layer.
  
  Effects modify layer properties (position, rotation, color, etc.) based
  on triggers from gameplay events. Subclasses implement the apply() method
  to define specific visual transformations.
  
  Attributes:
      layer: The Layer this effect is attached to.
      stage: The Stage instance (via layer.stage).
      intensity (float): Effect strength multiplier.
      trigger: Trigger function to call for effect timing.
      period (float): Duration of effect in milliseconds.
      delay (float): Delay before effect starts, in periods.
      triggerProf: Profile function for effect interpolation.
  """
  def __init__(self, layer, options):
    """
    Initialize an Effect.
    
    Args:
        layer: Layer to attach this effect to.
        options: Dictionary of effect options:
            intensity (float): Effect intensity multiplier. Default 1.0.
            trigger (str): Event trigger type - "none", "beat", "quarterbeat",
                "pick", or "miss". Default "none".
            period (float): Effect duration in ms. Default 500.0.
            delay (float): Delay in periods before effect. Default 0.0.
            profile (str): Interpolation profile - "step", "linstep",
                or "smoothstep". Default "linstep".
    """
    self.layer       = layer
    self.stage       = layer.stage
    self.intensity   = float(options.get("intensity", 1.0))
    self.trigger     = getattr(self, "trigger" + options.get("trigger", "none").capitalize())
    self.period      = float(options.get("period", 500.0))
    self.delay       = float(options.get("delay", 0.0))
    self.triggerProf = getattr(self, options.get("profile", "linstep"))

  def apply(self):
    """Apply this effect to the layer. Override in subclasses."""
    pass

  def triggerNone(self):
    """No-op trigger that always returns 0.0."""
    return 0.0

  def triggerBeat(self):
    """
    Calculate effect intensity based on beat timing.
    
    Returns:
        float: Effect intensity from 0.0 to intensity, decaying from beat.
    """
    if not self.stage.lastBeatPos:
      return 0.0
    t = self.stage.pos - self.delay * self.stage.beatPeriod - self.stage.lastBeatPos
    return self.intensity * (1.0 - self.triggerProf(0, self.stage.beatPeriod, t))

  def triggerQuarterbeat(self):
    """
    Calculate effect intensity based on quarter-beat timing.
    
    Returns:
        float: Effect intensity from 0.0 to intensity, decaying from quarter-beat.
    """
    if not self.stage.lastQuarterBeatPos:
      return 0.0
    t = self.stage.pos - self.delay * (self.stage.beatPeriod / 4) - self.stage.lastQuarterBeatPos
    return self.intensity * (1.0 - self.triggerProf(0, self.stage.beatPeriod / 4, t))

  def triggerPick(self):
    """
    Calculate effect intensity based on note pick timing.
    
    Returns:
        float: Effect intensity from 0.0 to intensity, decaying from pick.
    """
    if not self.stage.lastPickPos:
      return 0.0
    t = self.stage.pos - self.delay * self.period - self.stage.lastPickPos
    return self.intensity * (1.0 - self.triggerProf(0, self.period, t))

  def triggerMiss(self):
    """
    Calculate effect intensity based on missed note timing.
    
    Returns:
        float: Effect intensity from 0.0 to intensity, decaying from miss.
    """
    if not self.stage.lastMissPos:
      return 0.0
    t = self.stage.pos - self.delay * self.period - self.stage.lastMissPos
    return self.intensity * (1.0 - self.triggerProf(0, self.period, t))

  def step(self, threshold, x):
    """Step function: returns 1 if x > threshold, else 0."""
    return (x > threshold) and 1 or 0

  def linstep(self, min, max, x):
    """Linear interpolation from 0 to 1 between min and max."""
    if x < min:
      return 0
    if x > max:
      return 1
    return (x - min) / (max - min)

  def smoothstep(self, min, max, x):
    """Smooth (cubic) interpolation from 0 to 1 between min and max."""
    if x < min:
      return 0
    if x > max:
      return 1
    def f(x):
      return -2 * x**3 + 3*x**2
    return f((x - min) / (max - min))

  def sinstep(self, min, max, x):
    """Sinusoidal interpolation from 0 to 1 between min and max."""
    return math.cos(math.pi * (1.0 - self.linstep(min, max, x)))

  def getNoteColor(self, note):
    """
    Get interpolated fret color for a fractional note value.
    
    Args:
        note: Note number, can be fractional for color blending.
    
    Returns:
        tuple: RGB color values interpolated between fret colors.
    """
    if note >= len(Theme.fretColors) - 1:
      return Theme.fretColors[-1]
    elif note <= 0:
      return Theme.fretColors[0]
    f2  = note % 1.0
    f1  = 1.0 - f2
    c1 = Theme.fretColors[int(note)]
    c2 = Theme.fretColors[int(note) + 1]
    return (c1[0] * f1 + c2[0] * f2, \
            c1[1] * f1 + c2[1] * f2, \
            c1[2] * f1 + c2[2] * f2)

class LightEffect(Effect):
  """
  Effect that changes layer color based on played notes.
  
  The color is derived from the average note being played, creating
  a lighting effect that responds to the music.
  
  Attributes:
      lightNumber (int): Which note average to use for color.
      ambient (float): Base brightness level.
      contrast (float): Brightness variation from trigger.
  """
  def __init__(self, layer, options):
    """Initialize LightEffect with light_number, ambient, and contrast options."""
    Effect.__init__(self, layer, options)
    self.lightNumber = int(options.get("light_number", 0))
    self.ambient     = float(options.get("ambient", 0.5))
    self.contrast    = float(options.get("contrast", 0.5))

  def apply(self):
    if len(self.stage.averageNotes) < self.lightNumber + 2:
      self.layer.color = (0.0, 0.0, 0.0, 0.0)
      return

    t = self.trigger()
    t = self.ambient + self.contrast * t
    c = self.getNoteColor(self.stage.averageNotes[self.lightNumber])
    self.layer.color = (c[0] * t, c[1] * t, c[2] * t, self.intensity)

class RotateEffect(Effect):
  """
  Effect that rotates the layer based on a trigger.
  
  Attributes:
      angle (float): Maximum rotation angle in radians.
  """
  def __init__(self, layer, options):
    """Initialize RotateEffect with angle option (in degrees)."""
    Effect.__init__(self, layer, options)
    self.angle     = math.pi / 180.0 * float(options.get("angle",  45))

  def apply(self):
    if not self.stage.lastMissPos:
      return
    
    t = self.trigger()
    self.layer.drawing.transform.rotate(t * self.angle)

class WiggleEffect(Effect):
  """
  Effect that oscillates the layer position in a circular pattern.
  
  Attributes:
      freq (float): Oscillation frequency.
      xmag (float): Horizontal movement magnitude.
      ymag (float): Vertical movement magnitude.
  """
  def __init__(self, layer, options):
    """Initialize WiggleEffect with frequency, xmagnitude, ymagnitude options."""
    Effect.__init__(self, layer, options)
    self.freq     = float(options.get("frequency",  6))
    self.xmag     = float(options.get("xmagnitude", 0.1))
    self.ymag     = float(options.get("ymagnitude", 0.1))

  def apply(self):
    t = self.trigger()
    
    w, h = self.stage.engine.view.geometry[2:4]
    p = t * 2 * math.pi * self.freq
    s, c = t * math.sin(p), t * math.cos(p)
    self.layer.drawing.transform.translate(self.xmag * w * s, self.ymag * h * c)

class ScaleEffect(Effect):
  """
  Effect that scales the layer based on a trigger.
  
  Attributes:
      xmag (float): Horizontal scale magnitude.
      ymag (float): Vertical scale magnitude.
  """
  def __init__(self, layer, options):
    """Initialize ScaleEffect with xmagnitude, ymagnitude options."""
    Effect.__init__(self, layer, options)
    self.xmag     = float(options.get("xmagnitude", .1))
    self.ymag     = float(options.get("ymagnitude", .1))

  def apply(self):
    t = self.trigger()
    self.layer.drawing.transform.scale(1.0 + self.xmag * t, 1.0 + self.ymag * t)

class Stage(object):
  """
  Stage background manager for gameplay visuals.
  
  The Stage loads layer configurations from a file and manages the
  rendering of background and foreground layers with their effects.
  It tracks gameplay events (beats, picks, misses) to trigger effects.
  
  Attributes:
      scene: The parent GuitarScene.
      engine: The game engine instance.
      config: ConfigParser with stage configuration.
      backgroundLayers (list): Layers rendered behind the guitar.
      foregroundLayers (list): Layers rendered in front of the guitar.
      textures (dict): Cache of loaded textures by filename.
      pos (float): Current playback position in milliseconds.
      beatPeriod (float): Current beat duration in milliseconds.
      beat (int): Current beat number.
      quarterBeat (int): Current quarter-beat number.
      lastBeatPos: Position of the last beat event.
      lastPickPos: Position of the last successful note pick.
      lastMissPos: Position of the last missed note.
      averageNotes (list): Rolling average of played note values.
  """
  def __init__(self, guitarScene, configFileName):
    """
    Initialize the Stage from a configuration file.
    
    Args:
        guitarScene: The parent GuitarScene instance.
        configFileName: Path to the stage configuration file (e.g., stage.ini).
    """
    self.scene            = guitarScene
    self.engine           = guitarScene.engine
    self.config           = ConfigParser()
    self.backgroundLayers = []
    self.foregroundLayers = []
    self.textures         = {}
    self.reset()

    self.config.read(configFileName)

    # Build the layers
    for i in range(32):
      section = "layer%d" % i
      if self.config.has_section(section):
        def get(value, type = str, default = None):
          if self.config.has_option(section, value):
            return type(self.config.get(section, value))
          return default
        
        xres    = get("xres", int, 256)
        yres    = get("yres", int, 256)
        texture = get("texture")

        try:
          drawing = self.textures[texture]
        except KeyError:
          drawing = self.engine.loadSvgDrawing(self, None, texture, textureSize = (xres, yres))
          self.textures[texture] = drawing
          
        layer = Layer(self, drawing)

        layer.position    = (get("xpos",   float, 0.0), get("ypos",   float, 0.0))
        layer.scale       = (get("xscale", float, 1.0), get("yscale", float, 1.0))
        layer.angle       = math.pi * get("angle", float, 0.0) / 180.0
        layer.srcBlending = globals()["GL_%s" % get("src_blending", str, "src_alpha").upper()]
        layer.dstBlending = globals()["GL_%s" % get("dst_blending", str, "one_minus_src_alpha").upper()]
        layer.color       = (get("color_r", float, 1.0), get("color_g", float, 1.0), get("color_b", float, 1.0), get("color_a", float, 1.0))

        # Load any effects
        fxClasses = {
          "light":          LightEffect,
          "rotate":         RotateEffect,
          "wiggle":         WiggleEffect,
          "scale":          ScaleEffect,
        }
        
        for j in range(32):
          fxSection = "layer%d:fx%d" % (i, j)
          if self.config.has_section(fxSection):
            type = self.config.get(fxSection, "type")

            if not type in fxClasses:
              continue

            options = self.config.options(fxSection)
            options = dict([(opt, self.config.get(fxSection, opt)) for opt in options])

            fx = fxClasses[type](layer, options)
            layer.effects.append(fx)

        if get("foreground", int):
          self.foregroundLayers.append(layer)
        else:
          self.backgroundLayers.append(layer)

  def reset(self):
    """Reset all stage state for a new song."""
    self.lastBeatPos        = None
    self.lastQuarterBeatPos = None
    self.lastMissPos        = None
    self.lastPickPos        = None
    self.beat               = 0
    self.quarterBeat        = 0
    self.pos                = 0.0
    self.playedNotes        = []
    self.averageNotes       = [0.0]
    self.beatPeriod         = 0.0

  def triggerPick(self, pos, notes):
    """
    Record a successful note pick event.
    
    Args:
        pos: Current playback position in milliseconds.
        notes: List of note numbers that were picked.
    """
    if notes:
      self.lastPickPos      = pos
      self.playedNotes      = self.playedNotes[-3:] + [sum(notes) / float(len(notes))]
      self.averageNotes[-1] = sum(self.playedNotes) / float(len(self.playedNotes))

  def triggerMiss(self, pos):
    """
    Record a missed note event.
    
    Args:
        pos: Current playback position in milliseconds.
    """
    self.lastMissPos = pos

  def triggerQuarterBeat(self, pos, quarterBeat):
    """
    Record a quarter-beat event.
    
    Args:
        pos: Current playback position in milliseconds.
        quarterBeat: The quarter-beat number.
    """
    self.lastQuarterBeatPos = pos
    self.quarterBeat        = quarterBeat

  def triggerBeat(self, pos, beat):
    """
    Record a beat event.
    
    Args:
        pos: Current playback position in milliseconds.
        beat: The beat number.
    """
    self.lastBeatPos  = pos
    self.beat         = beat
    self.averageNotes = self.averageNotes[-4:] + self.averageNotes[-1:]

  def _renderLayers(self, layers, visibility):
    """
    Render a list of layers with orthogonal projection.
    
    Args:
        layers: List of Layer instances to render.
        visibility: Opacity factor from 0.0 to 1.0.
    """
    self.engine.view.setOrthogonalProjection(normalize = True)
    try:
      for layer in layers:
        layer.render(visibility)
    finally:
      self.engine.view.resetProjection()

  def run(self, pos, period):
    """
    Update stage state for the current frame.
    
    Tracks the current position and triggers beat events as they occur.
    
    Args:
        pos: Current playback position in milliseconds.
        period: Current beat period in milliseconds.
    """
    self.pos        = pos
    self.beatPeriod = period
    quarterBeat = int(4 * pos / period)

    if quarterBeat > self.quarterBeat:
      self.triggerQuarterBeat(pos, quarterBeat)

    beat = quarterBeat / 4

    if beat > self.beat:
      self.triggerBeat(pos, beat)

  def render(self, visibility):
    """
    Render the complete stage with background, guitar, and foreground.
    
    Args:
        visibility: Opacity factor from 0.0 to 1.0 for fade effects.
    """
    self._renderLayers(self.backgroundLayers, visibility)
    self.scene.renderGuitar()
    self._renderLayers(self.foregroundLayers, visibility)
