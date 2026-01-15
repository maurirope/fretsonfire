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
Main menu screen for Frets on Fire.

This module provides the main menu interface that appears when the game
starts. It displays animated background graphics and provides access to
game modes, settings, editor, credits, and exit options.

Classes:
    MainMenu: The main menu background layer with animated visuals.
"""

from OpenGL.GL import *
import math

from View import BackgroundLayer
from Menu import Menu
from Editor import Editor, Importer, GHImporter
from Credits import Credits
from Svg import SvgDrawing
from Language import _
from SinglePlayer import SinglePlayerSession
import Dialogs
import Config
import Log
import Audio
import Settings
import Song

class MainMenu(BackgroundLayer):
  """
  Main menu background layer with animated graphics.

  Displays the game's main menu with animated keyboard background,
  logo, and character graphics. Manages navigation to game modes,
  settings, editor, and other screens.

  Attributes:
      engine: Game engine instance.
      time (float): Animation timer for visual effects.
      nextLayer: Layer to push after menu closes.
      visibility (float): Current fade visibility (0.0 to 1.0).
      songName (str, optional): Song to auto-start if specified.
      gameStarted (bool): True if a game session was started.
      song: Background music audio object.
      background: Keyboard background SVG drawing.
      guy: Character pose SVG drawing.
      logo: Game logo SVG drawing.
      menu: The Menu instance for navigation.
  """

  def __init__(self, engine, songName = None):
    """
    Initialize the main menu.

    Args:
        engine: Game engine instance.
        songName: Optional song name to auto-start after menu shows.
    """
    self.engine              = engine
    self.time                = 0.0
    self.nextLayer           = None
    self.visibility          = 0.0
    self.songName            = songName
    self.gameStarted         = False
    self.song                = None
    
    self.engine.loadSvgDrawing(self, "background", "keyboard.svg")
    self.engine.loadSvgDrawing(self, "guy",        "pose.svg")
    self.engine.loadSvgDrawing(self, "logo",       "logo.svg")
    
    # Try to load and play menu music, but don't crash if mixer is not ready
    try:
      self.song = Audio.Sound(self.engine.resource.fileName("menu.ogg"))
      self.song.setVolume(self.engine.config.get("audio", "songvol"))
      self.song.play(-1)
    except Exception as e:
      Log.warn("Could not play menu music: %s" % e)
      self.song = None

    editorMenu = Menu(self.engine, [
      (_("Edit Existing Song"),            self.startEditor),
      (_("Import New Song"),               self.startImporter),
      (_("Import Guitar Hero(tm) Songs"),  self.startGHImporter),
    ])
    
    settingsMenu = Settings.SettingsMenu(self.engine)
    
    mainMenu = [
      (_("Play Game"),   self.newGame),
      (_("Tutorial"),    self.showTutorial),
      (_("Song Editor"), editorMenu),
      (_("Settings >"),  settingsMenu),
      (_("Credits"),     self.showCredits),
      (_("Quit"),        self.quit),
    ]
    self.menu = Menu(self.engine, mainMenu, onClose = lambda: self.engine.view.popLayer(self))

  def shown(self):
    """
    Called when the main menu becomes visible.

    Pushes the navigation menu layer and auto-starts a game if
    a song name was specified at initialization.
    """
    self.engine.view.pushLayer(self.menu)

    if self.songName:
      self.newGame(self.songName)
    
  def hidden(self):
    """
    Called when the main menu is hidden.

    Cleans up the menu layer, fades out music, and either launches
    the next layer or quits the game if no game was started.
    """
    # Only pop menu if it's still in the layers
    if self.menu in self.engine.view.layers:
      self.engine.view.popLayer(self.menu)

    if self.song:
      self.song.fadeout(1000)
    
    if self.nextLayer:
      self.engine.view.pushLayer(self.nextLayer())
      self.nextLayer = None
    elif not self.gameStarted:
      self.engine.quit()

  def quit(self):
    """Exit the main menu and quit the game."""
    self.engine.view.popLayer(self.menu)

  def launchLayer(self, layerFunc):
    """
    Schedule a layer to be launched after the menu closes.

    Args:
        layerFunc: Factory function that creates the layer to launch.
    """
    if not self.nextLayer:
      self.nextLayer = layerFunc
      self.engine.view.popAllLayers()

  def _startGame(self, songName=None, libraryName=None):
    """Start a single-player game session."""
    try:
      # Mark that a game has started so hidden() doesn't quit
      self.gameStarted = True
      
      # Pop the menu layers before starting the game
      # This ensures Menu doesn't intercept game key events
      self.engine.view.popLayer(self.menu)
      self.engine.view.popLayer(self)
      
      # Create single-player session
      session = SinglePlayerSession(self.engine)
      session.createPlayer(_("Player"))
      
      # Start the game with optional song
      if songName:
        session.startGame(libraryName=libraryName or Song.DEFAULT_LIBRARY, songName=songName)
      else:
        session.startGame()
        
    except Exception as e:
      import traceback
      traceback.print_exc()
      Dialogs.showMessage(self.engine, str(e))

  def showTutorial(self):
    """Start the tutorial."""
    self._startGame(songName="tutorial", libraryName=Song.DEFAULT_LIBRARY)

  def newGame(self, songName=None):
    """Start a new single-player game."""
    if songName:
      self._startGame(songName=songName)
    else:
      self._startGame()

  def startEditor(self):
    """Launch the song editor for editing existing songs."""
    self.launchLayer(lambda: Editor(self.engine))

  def startImporter(self):
    """Launch the song importer for importing new songs."""
    self.launchLayer(lambda: Importer(self.engine))

  def startGHImporter(self):
    """Launch the Guitar Hero song importer."""
    self.launchLayer(lambda: GHImporter(self.engine))

  def showCredits(self):
    """Display the game credits screen."""
    self.launchLayer(lambda: Credits(self.engine))

  def run(self, ticks):
    """
    Update menu animation state.

    Args:
        ticks: Time elapsed since last update in milliseconds.
    """
    self.time += ticks / 50.0
    
  def render(self, visibility, topMost):
    """
    Render the main menu background with OpenGL.

    Draws animated keyboard background, game logo, and character
    graphics with smooth motion effects.

    Args:
        visibility: Fade-in/out factor from 0.0 to 1.0.
        topMost: True if this is the topmost visible layer.
    """
    self.visibility = visibility
    v = 1.0 - ((1 - visibility) ** 2)
      
    t = self.time / 100
    w, h, = self.engine.view.geometry[2:4]
    r = .5
    self.background.transform.reset()
    self.background.transform.translate((1 - v) * 2 * w + w / 2 + math.cos(t / 2) * w / 2 * r, h / 2 + math.sin(t) * h / 2 * r)
    self.background.transform.rotate(-t)
    self.background.transform.scale(math.sin(t / 8) + 2, math.sin(t / 8) + 2)
    self.background.draw()

    self.logo.transform.reset()
    self.logo.transform.translate(.5 * w, .8 * h + (1 - v) * h * 2 * 0)
    f1 = math.sin(t * 16) * .025
    f2 = math.cos(t * 17) * .025
    self.logo.transform.scale(1 + f1 + (1 - v) ** 3, -1 + f2 + (1 - v) ** 3)
    self.logo.draw()
    
    self.guy.transform.reset()
    self.guy.transform.translate(.75 * w + (1 - v) * 2 * w, .35 * h)
    self.guy.transform.scale(-.9, .9)
    self.guy.transform.rotate(math.pi)
    self.guy.draw()
