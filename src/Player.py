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
Player module for Frets on Fire.

This module provides player control management and input mapping for the game.
It defines control constants (directional keys, action keys, fret keys), handles
keyboard input mapping through the Controls class, and manages player state
(score, streak, difficulty) through the Player class.

Control constants use bit flags for efficient state checking:
    - LEFT, RIGHT, UP, DOWN: Navigation controls
    - ACTION1, ACTION2: Pick/strum controls  
    - KEY1-KEY5: Fret button controls
    - CANCEL: Menu cancel/escape control

Example:
    >>> from Player import Player, Controls
    >>> player = Player(game_engine, "Player1")
    >>> player.difficulty = Song.MEDIUM_DIFFICULTY
    >>> player.addScore(100)
"""

import pygame
import Config
import Song
from Language import _

LEFT    = 0x1
RIGHT   = 0x2
UP      = 0x4
DOWN    = 0x8
ACTION1 = 0x10
ACTION2 = 0x20
KEY1    = 0x40
KEY2    = 0x80
KEY3    = 0x100
KEY4    = 0x200
KEY5    = 0x400
CANCEL  = 0x800

SCORE_MULTIPLIER = [0, 10, 20, 30]

# define configuration keys
Config.define("player", "key_left",     str, "K_LEFT",   text = _("Move left"))
Config.define("player", "key_right",    str, "K_RIGHT",  text = _("Move right"))
Config.define("player", "key_up",       str, "K_UP",     text = _("Move up"))
Config.define("player", "key_down",     str, "K_DOWN",   text = _("Move down"))
Config.define("player", "key_action1",  str, "K_RETURN", text = _("Pick"))
Config.define("player", "key_action2",  str, "K_RSHIFT", text = _("Secondary Pick"))
Config.define("player", "key_1",        str, "K_F1",     text = _("Fret #1"))
Config.define("player", "key_2",        str, "K_F2",     text = _("Fret #2"))
Config.define("player", "key_3",        str, "K_F3",     text = _("Fret #3"))
Config.define("player", "key_4",        str, "K_F4",     text = _("Fret #4"))
Config.define("player", "key_5",        str, "K_F5",     text = _("Fret #5"))
Config.define("player", "key_cancel",   str, "K_ESCAPE", text = _("Cancel"))
Config.define("player", "name",         str, "")
Config.define("player", "difficulty",   int, Song.EASY_DIFFICULTY)

class Controls:
    """
    Manages keyboard-to-game-control mapping and input state tracking.
    
    This class maps physical keyboard keys (configured via Config) to logical
    game controls (LEFT, RIGHT, KEY1-KEY5, etc.). It tracks which controls are
    currently active using bit flags and supports multiple keys being held
    simultaneously.
    
    Attributes:
        flags (int): Bit flags representing currently active controls.
            Each control constant (LEFT, RIGHT, etc.) corresponds to a bit.
        controlMapping (dict): Maps pygame key codes to control constants.
        heldKeys (dict): Tracks which physical keys are held for each control,
            enabling proper release detection when multiple keys map to
            the same control.
    
    Example:
        >>> controls = Controls()
        >>> controls.keyPressed(pygame.K_LEFT)
        >>> if controls.getState(LEFT):
        ...     print("Moving left")
    """
    
    def __init__(self):
        """
        Initialize controls by loading key mappings from configuration.
        
        Reads key bindings from the [player] section of the config file
        and creates the control mapping dictionary. Each key binding can
        be either a pygame key constant name (e.g., 'K_LEFT') or a numeric
        key code.
        """
        def keycode(name):
            """Convert a config key name to a pygame keycode."""
            k = Config.get("player", name)
            try:
                return int(k)
            except:
                return getattr(pygame, k)
        
        self.flags = 0
        self.controlMapping = {
      keycode("key_left"):      LEFT,
      keycode("key_right"):     RIGHT,
      keycode("key_up"):        UP,
      keycode("key_down"):      DOWN,
      keycode("key_action1"):   ACTION1,
      keycode("key_action2"):   ACTION2,
      keycode("key_1"):         KEY1,
      keycode("key_2"):         KEY2,
      keycode("key_3"):         KEY3,
      keycode("key_4"):         KEY4,
      keycode("key_5"):         KEY5,
      keycode("key_cancel"):    CANCEL,
    }
    
        # Multiple key support
        self.heldKeys = {}

    def getMapping(self, key):
        """
        Get the control constant mapped to a physical key.
        
        Args:
            key: pygame key code to look up.
        
        Returns:
            The control constant (e.g., LEFT, KEY1) if mapped,
            None if the key is not mapped to any control.
        """
        return self.controlMapping.get(key)

    def keyPressed(self, key):
        """
        Handle a key press event.
        
        Activates the corresponding control and tracks the key in heldKeys
        for proper release handling when multiple keys map to the same control.
        
        Args:
            key: pygame key code that was pressed.
        
        Returns:
            The control constant that was activated, or None if the key
            is not mapped to any control.
        """
        c = self.getMapping(key)
        if c:
            self.toggle(c, True)
            if c in self.heldKeys and not key in self.heldKeys[c]:
                self.heldKeys[c].append(key)
            return c
        return None

    def keyReleased(self, key):
        """
        Handle a key release event.
        
        Only deactivates a control when all physical keys mapped to it
        have been released (supports multiple keys for the same control).
        
        Args:
            key: pygame key code that was released.
        
        Returns:
            The control constant that was deactivated, or None if the key
            is not mapped or other keys for this control are still held.
        """
        c = self.getMapping(key)
        if c:
            if c in self.heldKeys:
                if key in self.heldKeys[c]:
                    self.heldKeys[c].remove(key)
                    if not self.heldKeys[c]:
                        self.toggle(c, False)
                        return c
                return None
            self.toggle(c, False)
            return c
        return None

    def toggle(self, control, state):
        """
        Set or clear a control's active state.
        
        Args:
            control: Control constant (bit flag) to modify.
            state: True to activate, False to deactivate.
        
        Returns:
            bool: True if the control state changed, False otherwise.
        """
        prevState = self.flags
        if state:
            self.flags |= control
            return not prevState & control
        else:
            self.flags &= ~control
            return prevState & control

    def getState(self, control):
        """
        Check if a control is currently active.
        
        Args:
            control: Control constant (bit flag) to check.
        
        Returns:
            int: Non-zero if active, zero if inactive.
        """
        return self.flags & control

class Player(object):
    """
    Represents a player in the game with score tracking and input controls.
    
    The Player class manages all player-specific state including score,
    note streak, difficulty settings, and input controls. Player settings
    like name and difficulty are persisted via the Config module.
    
    Attributes:
        owner: Reference to the game engine that owns this player.
        controls (Controls): Input control handler for this player.
        score (int): Current accumulated score.
        notesHit (int): Total number of notes successfully hit.
        longestStreak (int): Best consecutive note streak achieved.
        cheating (bool): Whether cheat mode is active.
    
    Properties:
        name (str): Player name (persisted to config).
        streak (int): Current consecutive note streak.
        difficulty: Current difficulty setting (Song.Difficulty object).
    """
    
    def __init__(self, owner, name):
        """
        Initialize a new player.
        
        Args:
            owner: The game engine or scene that owns this player.
            name: Initial player name (note: actual name is loaded from config).
        """
        self.owner = owner
        self.controls = Controls()
        self.reset()
    
    def reset(self):
        """
        Reset player state for a new game.
        
        Clears score, streak, notes hit counter, and cheating flag.
        Does not reset persistent settings like name or difficulty.
        """
        self.score = 0
        self._streak = 0
        self.notesHit = 0
        self.longestStreak = 0
        self.cheating = False
    
    def getName(self):
        """
        Get the player's name from configuration.
        
        Returns:
            str: The player's configured name.
        """
        return Config.get("player", "name")
    
    def setName(self, name):
        """
        Set the player's name in configuration.
        
        Args:
            name (str): The new player name to save.
        """
        Config.set("player", "name", name)
    
    name = property(getName, setName)
    
    def getStreak(self):
        """
        Get the current note streak.
        
        Returns:
            int: Current consecutive notes hit without missing.
        """
        return self._streak
    
    def setStreak(self, value):
        """
        Set the current note streak and update longest streak record.
        
        Args:
            value (int): New streak value.
        """
        self._streak = value
        self.longestStreak = max(self._streak, self.longestStreak)
    
    streak = property(getStreak, setStreak)
    
    def getDifficulty(self):
        """
        Get the current difficulty setting.
        
        Returns:
            Song.Difficulty: The difficulty object for current setting.
        """
        return Song.difficulties.get(Config.get("player", "difficulty"))
    
    def setDifficulty(self, difficulty):
        """
        Set the difficulty level.
        
        Args:
            difficulty (Song.Difficulty): The difficulty to set.
        """
        Config.set("player", "difficulty", difficulty.id)
    
    difficulty = property(getDifficulty, setDifficulty)
    
    def addScore(self, score):
        """
        Add points to the player's score with multiplier applied.
        
        The score is multiplied based on current streak before adding.
        Higher streaks yield higher multipliers (1x to 4x).
        
        Args:
            score (int): Base score value to add.
        """
        self.score += score * self.getScoreMultiplier()
    
    def getScoreMultiplier(self):
        """
        Calculate the score multiplier based on current streak.
        
        Multipliers increase at streak thresholds:
        - 0-9 notes: 1x multiplier
        - 10-19 notes: 2x multiplier  
        - 20-29 notes: 3x multiplier
        - 30+ notes: 4x multiplier
        
        Returns:
            int: Current score multiplier (1-4).
        """
        try:
            return SCORE_MULTIPLIER.index((self.streak / 10) * 10) + 1
        except ValueError:
            return len(SCORE_MULTIPLIER)
