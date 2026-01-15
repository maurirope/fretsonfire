#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#####################################################################
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
Frets on Fire - Main Entry Point
================================

This is the main executable for Frets on Fire, a free music video game
inspired by Guitar Hero. Players use keyboard keys to simulate playing
a guitar in time with music.

Usage:
    python FretsOnFire.py [options]
    
Options:
    -v, --verbose       Enable verbose logging output
    -p, --play SONG     Start playing the specified song immediately

The game will load the configuration, initialize the game engine, and
display the main menu. The engine runs in a loop until the player quits
or requests a restart.

Controls:
    F1-F5       Fret keys (guitar neck buttons)
    Enter       Pick/strum
    Escape      Pause game / Cancel in menus
    Arrow keys  Menu navigation
"""
import sys
import os
import getopt
import codecs
import encodings.iso8859_1
import encodings.utf_8

# Register text encodings for internationalization support
codecs.register(lambda encoding: encodings.iso8859_1.getregentry())
codecs.register(lambda encoding: encodings.utf_8.getregentry())
assert codecs.lookup("iso-8859-1")
assert codecs.lookup("utf-8")

from GameEngine import GameEngine
from MainMenu import MainMenu
import Log
import Config
import Version

# Command-line usage information
USAGE = """
Frets on Fire - A Guitar Hero style music game

Usage: %(prog)s [options]

Options:
  -v, --verbose         Enable verbose logging
  -p, --play SONG       Start playing the specified song immediately
  -h, --help            Show this help message

Examples:
  %(prog)s                  Start the game normally
  %(prog)s -v               Start with verbose logging
  %(prog)s -p tutorial      Start playing the tutorial song
""" % {"prog": sys.argv[0]}


def parse_arguments():
    """
    Parse command-line arguments.
    
    Returns:
        tuple: (songName, verbose) - song to play (or None) and verbose flag
    """
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vp:h", ["verbose", "play=", "help"])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(1)

    songName = None
    verbose = False
    
    for opt, arg in opts:
        if opt in ["--verbose", "-v"]:
            verbose = True
        elif opt in ["--play", "-p"]:
            songName = arg
        elif opt in ["--help", "-h"]:
            print(USAGE)
            sys.exit(0)
    
    return songName, verbose


def main():
    """
    Main entry point for Frets on Fire.
    
    Initializes the game engine and runs the main game loop.
    Handles restart requests and graceful shutdown.
    """
    songName, verbose = parse_arguments()
    
    if verbose:
        Log.quiet = False

    while True:
        # Load configuration and initialize engine
        config = Config.load(Version.appName() + ".ini", setAsDefault=True)
        engine = GameEngine(config)
        menu = MainMenu(engine, songName=songName)
        engine.setStartupLayer(menu)

        # Run the main game loop
        try:
            while engine.run():
                pass
        except KeyboardInterrupt:
            Log.notice("Interrupted by user.")

        # Handle restart request
        if engine.restartRequested:
            Log.notice("Restarting game...")
            _handle_restart()
            break
        else:
            break
    
    engine.quit()


def _handle_restart():
    """
    Handle game restart by re-executing the process.
    
    This is used when settings change that require a full restart
    (e.g., video mode changes).
    """
    try:
        if hasattr(sys, "frozen"):
            # Running from frozen executable
            if os.name == "nt":
                os.execl("FretsOnFire.exe", "FretsOnFire.exe", *sys.argv[1:])
            elif sys.platform == "darwin":
                # Exit code 100 tells launcher script to restart
                sys.exit(100)
            else:
                os.execl("./FretsOnFire", "./FretsOnFire", *sys.argv[1:])
        else:
            # Running from Python source
            python = sys.executable
            os.execl(python, python, "FretsOnFire.py", *sys.argv[1:])
    except Exception as e:
        Log.warn("Restart failed: %s" % e)
        raise


if __name__ == "__main__":
    main()
