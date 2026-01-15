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
Main game engine module for Frets on Fire.

This module contains the GameEngine class, which is the central coordinator
for all game subsystems. It initializes and manages:

- Video: OpenGL rendering and display management
- Audio: Sound playback and music streaming
- Input: Keyboard, mouse, and gamepad handling
- Resources: Asset loading and caching
- View: Scene/layer stack and rendering pipeline
- Configuration: Game settings and preferences
- Mods/Themes: Visual customization support

The GameEngine extends the base Engine class to provide game-specific
functionality including fullscreen toggling, debug mode, and the main
game loop with loading screen support.

Typical usage:
    engine = GameEngine(config)
    engine.setStartupLayer(MainMenu(engine))
    while engine.run():
        pass
    engine.quit()
"""

from OpenGL.GL import *
import pygame
import os
import sys

from Engine import Engine, Task
from Video import Video
from Audio import Audio
from View import View
from Input import Input, KeyListener, SystemEventListener
from Resource import Resource
from Data import Data
# Server and Session removed - single player only
# from Server import Server
# from Session import ClientSession
from Svg import SvgContext, SvgDrawing, LOW_QUALITY, NORMAL_QUALITY, HIGH_QUALITY
from Debug import DebugLayer
from Language import _
# import Network
import Log
import Config
import Dialogs
import Theme
import Version
import Mod

# define configuration keys
Config.define("engine", "tickrate",     float, 1.0)
Config.define("engine", "highpriority", bool,  True)
Config.define("game",   "uploadscores", bool,  False, text = _("Upload Highscores"),    options = {False: _("No"), True: _("Yes")})
Config.define("game",   "uploadurl",    str,   "http://fretsonfire.sourceforge.net/play")
Config.define("game",   "leftymode",    bool,  False, text = _("Lefty mode"),           options = {False: _("No"), True: _("Yes")})
Config.define("game",   "tapping",      bool,  True,  text = _("Tappable notes"),       options = {False: _("No"), True: _("Yes")})
Config.define("game",   "compactlist",  bool,  False, text = _("Compact song list"),    options = {False: _("No"), True: _("Yes")})
Config.define("game",   "autopreview",  bool,  True,  text = _("Song auto preview"),    options = {False: _("No"), True: _("Yes")})
Config.define("game",   "artistsort",   bool,  False, text = _("Sort by artist"),       options = {False: _("No"), True: _("Yes")})
Config.define("video",  "fullscreen",   bool,  False, text = _("Fullscreen Mode"),      options = {False: _("No"), True: _("Yes")})
Config.define("video",  "multisamples", int,   4,     text = _("Antialiasing Quality"), options = {0: _("None"), 2: _("2x"), 4: _("4x"), 6: _("6x"), 8: _("8x")})
Config.define("video",  "resolution",   str,   "640x480")
Config.define("video",  "fps",          int,   80,    text = _("Frames per Second"), options = dict([(n, n) for n in range(1, 120)]))
#Config.define("opengl", "svgquality",   int,   NORMAL_QUALITY,  text = _("SVG Quality"), options = {LOW_QUALITY: _("Low"), NORMAL_QUALITY: _("Normal"), HIGH_QUALITY: _("High")})
Config.define("audio",  "frequency",    int,   44100, text = _("Sample Frequency"), options = [8000, 11025, 22050, 32000, 44100, 48000])
Config.define("audio",  "bits",         int,   16,    text = _("Sample Bits"), options = [16, 8])
Config.define("audio",  "stereo",       bool,  True)
Config.define("audio",  "buffersize",   int,   2048,  text = _("Buffer Size"), options = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536])
Config.define("audio",  "delay",        int,   100,   text = _("A/V delay"), options = dict([(n, n) for n in range(0, 301)]))
Config.define("audio",  "screwupvol", float,   0.25,  text = _("Screw Up Sounds"), options = {0.0: _("Off"), .25: _("Quiet"), .5: _("Loud"), 1.0: _("Painful")})
Config.define("audio",  "guitarvol",  float,    1.0,  text = _("Guitar Volume"),   options = dict([(n / 100.0, "%02d/10" % (n / 9)) for n in range(0, 110, 10)]))
Config.define("audio",  "songvol",    float,    1.0,  text = _("Song Volume"),     options = dict([(n / 100.0, "%02d/10" % (n / 9)) for n in range(0, 110, 10)]))
Config.define("audio",  "rhythmvol",  float,    1.0,  text = _("Rhythm Volume"),   options = dict([(n / 100.0, "%02d/10" % (n / 9)) for n in range(0, 110, 10)]))
Config.define("video",  "fontscale",  float,    1.0,  text = _("Text scale"),      options = dict([(n / 100.0, "%3d%%" % n) for n in range(50, 260, 10)]))

class FullScreenSwitcher(KeyListener):
  """
  A keyboard listener that handles special built-in key combinations.

  Provides global keyboard shortcuts for:
  - Alt+Enter: Toggle fullscreen mode
  - Alt+D: Toggle debug mode
  - Alt+G: Dump garbage collector info (debug mode only)

  Attributes:
      engine: Reference to the GameEngine instance.
      altStatus: Tracks whether Alt key is currently pressed.
  """

  def __init__(self, engine):
    """Initialize the fullscreen switcher.

    Args:
        engine: The GameEngine instance to control.
    """
    self.engine = engine
    self.altStatus = False
  
  def keyPressed(self, key, str):
    """Handle key press events for global shortcuts.

    Args:
        key: The pygame key code that was pressed.
        str: The string representation of the key (unused).

    Returns:
        True if the key event was handled, None otherwise.
    """
    if key == pygame.K_LALT:
      self.altStatus = True
    elif key == pygame.K_RETURN and self.altStatus:
      if not self.engine.toggleFullscreen():
        Log.error("Unable to toggle fullscreen mode.")
      return True
    elif key == pygame.K_d and self.altStatus:
      self.engine.setDebugModeEnabled(not self.engine.isDebugModeEnabled())
      return True
    elif key == pygame.K_g and self.altStatus and self.engine.isDebugModeEnabled():
      self.engine.debugLayer.gcDump()
      return True

  def keyReleased(self, key):
    """Handle key release events.

    Args:
        key: The pygame key code that was released.
    """
    if key == pygame.K_LALT:
      self.altStatus = False
      
class SystemEventHandler(SystemEventListener):
  """
  A system event listener that handles window and application events.

  Responds to system-level events including:
  - Screen resize: Updates viewport and SVG context geometry
  - Restart requests: Triggers full game restart
  - Quit: Initiates graceful shutdown

  Attributes:
      engine: Reference to the GameEngine instance.
  """

  def __init__(self, engine):
    """Initialize the system event handler.

    Args:
        engine: The GameEngine instance to control.
    """
    self.engine = engine

  def screenResized(self, size):
    """Handle window resize events.

    Args:
        size: Tuple of (width, height) in pixels.
    """
    self.engine.resizeScreen(size[0], size[1])

  def restartRequested(self):
    """Handle restart request events."""
    self.engine.restart()

  def quit(self):
    """Handle quit events."""
    self.engine.quit()

class GameEngine(Engine):
  """
  The main game engine that coordinates all game subsystems.

  GameEngine is the central hub of the application, responsible for
  initializing and managing all major subsystems. It extends the base
  Engine class to provide game-specific functionality.

  Attributes:
      config: Configuration manager for game settings.
      title: Window title string.
      restartRequested: Flag indicating a pending restart.
      handlingException: Flag to prevent recursive exception handling.
      video: Video subsystem for display and OpenGL management.
      audio: Audio subsystem for sound and music playback.
      input: Input subsystem for keyboard/mouse/gamepad handling.
      view: View manager for scene/layer rendering.
      resource: Resource manager for async asset loading.
      data: Data loader for game assets (fonts, images, sounds).
      svg: SVG rendering context for vector graphics.
      server: Deprecated - always None (single-player only).
      sessions: List of active game sessions.
      mainloop: Current main loop function (loading or main).
      debugLayer: Debug overlay layer (None if disabled).
      startupLayer: Layer to show after loading completes.
      loadingScreenShown: Flag tracking loading screen display.
  """

  def __init__(self, config=None):
    """Initialize the game engine and all subsystems.

    Args:
        config: Optional Config instance. If None, loads from default
            configuration file.
    """

    if not config:
      config = Config.load()
      
    self.config  = config
    
    fps          = self.config.get("video", "fps")
    tickrate     = self.config.get("engine", "tickrate")
    Engine.__init__(self, fps = fps, tickrate = tickrate)
    
    pygame.init()
    
    self.title             = _("Frets on Fire")
    self.restartRequested  = False
    self.handlingException = False
    self.video             = Video(self.title)
    self.audio             = Audio()

    Log.debug("Initializing audio.")
    frequency    = self.config.get("audio", "frequency")
    bits         = self.config.get("audio", "bits")
    stereo       = self.config.get("audio", "stereo")
    bufferSize   = self.config.get("audio", "buffersize")
    
    self.audio.pre_open(frequency = frequency, bits = bits, stereo = stereo, bufferSize = bufferSize)
    pygame.init()
    self.audio.open(frequency = frequency, bits = bits, stereo = stereo, bufferSize = bufferSize)

    Log.debug("Initializing video.")
    width, height = [int(s) for s in self.config.get("video", "resolution").split("x")]
    fullscreen    = self.config.get("video", "fullscreen")
    multisamples  = self.config.get("video", "multisamples")
    self.video.setMode((width, height), fullscreen = fullscreen, multisamples = multisamples)

    # Enable the high priority timer if configured
    if self.config.get("engine", "highpriority"):
      Log.debug("Enabling high priority timer.")
      self.timer.highPriority = True

    viewport = glGetIntegerv(GL_VIEWPORT)
    h = viewport[3] - viewport[1]
    w = viewport[2] - viewport[0]
    geometry = (0, 0, w, h)
    self.svg = SvgContext(geometry)
    self.svg.setRenderingQuality(self.config.get("opengl", "svgquality"))
    glViewport(int(viewport[0]), int(viewport[1]), int(viewport[2]), int(viewport[3]))

    self.input     = Input()
    self.view      = View(self, geometry)
    self.resizeScreen(w, h)

    self.resource  = Resource(Version.dataPath())
    self.server    = None
    self.sessions  = []
    self.mainloop  = self.loading
    
    # Load game modifications
    Mod.init(self)
    theme = Config.load(self.resource.fileName("theme.ini"))
    Theme.open(theme)

    # Make sure we are using the new upload URL
    if self.config.get("game", "uploadurl").startswith("http://kempele.fi"):
      self.config.set("game", "uploadurl", "http://fretsonfire.sourceforge.net/play")

    self.addTask(self.audio, synchronized = False)
    self.addTask(self.input, synchronized = False)
    self.addTask(self.view)
    self.addTask(self.resource, synchronized = False)
    self.data = Data(self.resource, self.svg)
    
    self.input.addKeyListener(FullScreenSwitcher(self), priority = True)
    self.input.addSystemEventListener(SystemEventHandler(self))

    self.debugLayer         = None
    self.startupLayer       = None
    self.loadingScreenShown = False

    Log.debug("Ready.")

  def setStartupLayer(self, startupLayer):
    """Set the layer to display after resources are loaded.

    This layer (typically the MainMenu) is pushed onto the view
    stack once all essential resources have been loaded.

    Args:
        startupLayer: A Layer instance to display at startup.
    """
    self.startupLayer = startupLayer

  def isDebugModeEnabled(self):
    """Check if debug mode is currently enabled.

    Returns:
        True if debug layer is active, False otherwise.
    """
    return bool(self.debugLayer)

  def setDebugModeEnabled(self, enabled):
    """Enable or disable the debug overlay layer.

    Args:
        enabled: True to show debug layer, False to hide.
    """
    if enabled:
      self.debugLayer = DebugLayer(self)
    else:
      self.debugLayer = None
    
  def toggleFullscreen(self):
    """Toggle between fullscreen and windowed display modes.

    On Windows, toggling fullscreen requires a full game restart
    due to OpenGL context/texture limitations.

    Returns:
        True on success (always returns True, may trigger restart).
    """
    if not self.video.toggleFullscreen():
      # on windows, the fullscreen toggle kills our textures, se we must restart the whole game
      self.input.broadcastSystemEvent("restartRequested")
      self.config.set("video", "fullscreen", not self.video.fullscreen)
      return True
    self.config.set("video", "fullscreen", self.video.fullscreen)
    return True
    
  def restart(self):
    """Request a full game restart.

    Sets the restart flag and broadcasts a restart event. If a restart
    is already pending, calls Engine.quit() directly as a workaround
    for audio cleanup issues.
    """
    if not self.restartRequested:
      self.restartRequested = True
      self.input.broadcastSystemEvent("restartRequested")
    else:
        # evilynux - With self.audio.close(), calling self.quit() results in
        #            a crash. Calling the parent directly as a workaround.
        Engine.quit(self)

  def quit(self):
    """Shut down the game engine and release all resources.

    Closes the audio subsystem and calls the parent Engine.quit()
    to stop all tasks and clean up.
    """
    self.audio.close()
    Engine.quit(self)

  def resizeScreen(self, width, height):
    """Resize the game screen and update rendering contexts.

    Updates both the View and SVG context geometry to match
    the new screen dimensions.

    Args:
        width: New width in pixels.
        height: New height in pixels.
    """
    self.view.setGeometry((0, 0, width, height))
    self.svg.setGeometry((0, 0, width, height))
    
  def isServerRunning(self):
    """Check if game server is running.

    Note:
        Server functionality has been removed. This always returns False.

    Returns:
        False (single-player mode only).
    """
    # Server removed - single player only
    return False

  def startServer(self):
    """Start the game server - not available in single player mode."""
    Log.warn("Server functionality removed - single player mode only")
    pass

  def connect(self, host):
    """Connect to a game server (deprecated).

    Note:
        Network functionality has been removed for single-player mode.

    Args:
        host: Server hostname (ignored).

    Returns:
        None (always).
    """
    Log.warn("Network functionality removed - single player mode only")
    return None

  def stopServer(self):
    """Stop the game server - not available in single player mode."""
    pass

  def disconnect(self, session):
    """Disconnect a session (deprecated).

    Note:
        Network functionality has been removed for single-player mode.

    Args:
        session: Session to disconnect (ignored).
    """
    pass

  def loadSvgDrawing(self, target, name, fileName, textureSize=None):
    """Load an SVG drawing synchronously.

    Loads an SVG file from the data directory and optionally renders
    it to a texture of specified size.

    Args:
        target: Object that will own the drawing. The drawing is
            assigned as an attribute on this object.
        name: Attribute name to assign the drawing to on target.
        fileName: Name of the SVG file in the data directory.
        textureSize: Optional tuple (width, height) to render the SVG
            to a texture. If None, uses native SVG rendering.

    Returns:
        SvgDrawing instance ready for rendering.
    """
    return self.data.loadSvgDrawing(target, name, fileName, textureSize)

  def loading(self):
    """Loading state main loop.

    Handles the initial loading phase where essential resources are
    loaded before the game can start. Once resources are loaded,
    shows the loading screen and transitions to the main loop.

    Returns:
        True if engine should continue running, False to quit.
    """
    done = Engine.run(self)
    self.clearScreen()
    
    if self.data.essentialResourcesLoaded():
      if not self.loadingScreenShown:
        self.loadingScreenShown = True
        Dialogs.showLoadingScreen(self, self.data.resourcesLoaded)
        if self.startupLayer:
          self.view.pushLayer(self.startupLayer)
        self.mainloop = self.main
      self.view.render()
    self.video.flip()
    return done

  def clearScreen(self):
    """Clear the screen with the theme's background color."""
    self.svg.clear(*Theme.backgroundColor)

  def main(self):
    """Main game state loop.

    The primary game loop that runs after loading is complete.
    Handles task execution, view rendering, debug overlay,
    and screen buffer flipping.

    Returns:
        True if engine should continue running, False to quit.
    """
    # Tune the scheduler priority so that transitions are as smooth as possible
    if self.view.isTransitionInProgress():
      self.boostBackgroundThreads(False)
    else:
      self.boostBackgroundThreads(True)
    
    done = Engine.run(self)
    self.clearScreen()
    self.view.render()
    if self.debugLayer:
      self.debugLayer.render(1.0, True)
    self.video.flip()
    return done

  def run(self):
    """Execute one iteration of the game loop.

    Delegates to the current mainloop function (loading or main)
    and handles any exceptions by displaying an error dialog.

    Returns:
        True if engine should continue running, False to quit.

    Raises:
        KeyboardInterrupt: Exits immediately.
        SystemExit: Exits immediately.
    """
    try:
      return self.mainloop()
    except KeyboardInterrupt:
      sys.exit(0)
    except SystemExit:
      sys.exit(0)
    except Exception as e:
      def clearMatrixStack(stack):
        try:
          glMatrixMode(stack)
          for i in range(16):
            glPopMatrix()
        except:
          pass

      if self.handlingException:
        # A recursive exception is fatal as we can't reliably reset the GL state
        sys.exit(1)

      self.handlingException = True
      Log.error("%s: %s" % (e.__class__, e))
      import traceback
      traceback.print_exc()

      clearMatrixStack(GL_PROJECTION)
      clearMatrixStack(GL_MODELVIEW)
      
      Dialogs.showMessage(self, str(e))
      self.handlingException = False
      return True
