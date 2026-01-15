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
Song selection scene for Frets on Fire.

This module implements the song choosing interface where players browse
and select songs from their library. It handles:

- Song library browsing with folder navigation
- Song preview and metadata display
- Difficulty level selection
- Persistence of last selected song in configuration

The scene serves as the entry point before gameplay, transitioning to
GuitarScene once a valid song and difficulty are chosen.
"""

from Scene import SceneServer, SceneClient
import Player
import Dialogs
import Song
import Config
from Language import _

# save chosen song into config file
Config.define("game", "selected_library",  str, "")
Config.define("game", "selected_song",     str, "")


class SongChoosingScene:
  """
  Base class for song selection scene functionality.
  
  This empty base class provides a common type for both server and client
  variants of the song choosing scene. In the single-player architecture,
  only the Client variant is actively used.
  """
  pass


class SongChoosingSceneServer(SongChoosingScene, SceneServer):
  """
  Server-side song choosing scene stub.
  
  This class exists for architectural compatibility but is not used
  in single-player mode.
  """
  pass


class SongChoosingSceneClient(SongChoosingScene, SceneClient):
  """
  Client-side song selection scene implementation.
  
  Presents the song library browser dialog and difficulty selection,
  then transitions to GuitarScene for gameplay.
  
  Attributes:
      wizardStarted: Flag indicating if the selection wizard has begun.
      libraryName: Currently selected song library/folder path.
      songName: Currently selected song identifier.
  """
  
  """
  Client-side song selection scene implementation.
  
  Presents the song library browser dialog and difficulty selection,
  then transitions to GuitarScene for gameplay.
  
  Attributes:
      wizardStarted: Flag indicating if the selection wizard has begun.
      libraryName: Currently selected song library/folder path.
      songName: Currently selected song identifier.
  """
  
  def createClient(self, libraryName = None, songName = None):
    """
    Initialize the song choosing scene client.
    
    Args:
        libraryName: Optional library/folder name to pre-select.
            If None, uses the last selected library from config.
        songName: Optional song name to pre-select.
            If None, the song browser dialog will be shown.
    """
    self.wizardStarted = False
    self.libraryName   = libraryName
    self.songName      = songName

  def run(self, ticks):
    """
    Process one frame of the song choosing scene.
    
    On the first frame, launches the song selection wizard which displays
    the library browser and difficulty selection dialogs. Once a valid
    song and difficulty are chosen, transitions to GuitarScene.
    
    Args:
        ticks: Time elapsed since last frame in milliseconds.
    """
    SceneClient.run(self, ticks)

    if not self.wizardStarted:
      self.wizardStarted = True

      if not self.songName:
        while True:
          self.libraryName, self.songName = \
            Dialogs.chooseSong(self.engine, \
                               selectedLibrary = Config.get("game", "selected_library"),
                               selectedSong    = Config.get("game", "selected_song"))
        
          if not self.songName:
            self.session.finishGame()
            return

          Config.set("game", "selected_library", self.libraryName)
          Config.set("game", "selected_song",    self.songName)
          
          info = Song.loadSongInfo(self.engine, self.songName, library = self.libraryName)
          
          # Check if song has any difficulties
          if not info.difficulties:
            Dialogs.showMessage(self.engine, _("This song has no playable notes."))
            continue
          
          d = Dialogs.chooseItem(self.engine, info.difficulties,
                                 _("Choose a difficulty:"), selected = self.player.difficulty)
          if d:
            self.player.difficulty = d
            break
      else:
        info = Song.loadSongInfo(self.engine, self.songName, library = self.libraryName)

      # Make sure the difficulty we chose is available
      if not info.difficulties:
        Dialogs.showMessage(self.engine, _("This song has no playable notes."))
        self.session.finishGame()
        return
        
      if not self.player.difficulty in info.difficulties:
        self.player.difficulty = info.difficulties[0]
        
      self.session.deleteScene(self)
      self.session.createScene("GuitarScene", libraryName = self.libraryName, songName = self.songName)
