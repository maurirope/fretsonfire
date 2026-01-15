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
Logging utilities for Frets on Fire.

This module provides a simple logging system with support for different
log levels (debug, notice, warn, error). Log messages are written to both
the console (when verbose mode is enabled) and a log file.

Features:
    - Color-coded console output on POSIX systems (Linux/macOS)
    - Automatic log file creation in the user's writable resource path
    - Quiet mode by default; enable verbose with -v command line flag
    - Four log levels: debug, notice, warn, error

Module-level functions:
    - debug(msg): Log debug-level messages (blue)
    - notice(msg): Log informational notices (green)
    - warn(msg): Log warning messages (yellow)
    - error(msg): Log error messages (red)

Example usage:
    >>> import Log
    >>> Log.notice("Application started")
    >>> Log.debug("Loading configuration...")
    >>> Log.warn("Config file not found, using defaults")
    >>> Log.error("Failed to initialize audio")
"""

import sys
import os
import Resource

quiet = True
logFile = open(os.path.join(Resource.getWritableResourcePath(), "fretsonfire.log"), "w")
encoding = "utf-8"

if "-v" in sys.argv:
  quiet = False
  
if os.name == "posix":
  labels = {
    "warn":   "\033[1;33m(W)\033[0m",
    "debug":  "\033[1;34m(D)\033[0m",
    "notice": "\033[1;32m(N)\033[0m",
    "error":  "\033[1;31m(E)\033[0m",
  }
else:
  labels = {
    "warn":   "(W)",
    "debug":  "(D)",
    "notice": "(N)",
    "error":  "(E)",
  }

def log(cls, msg):
  """Write a log message with the specified classification.
  
  Outputs the message to the log file, and optionally to the console
  if verbose mode is enabled (-v flag). Messages are prefixed with
  a classification label.
  
  Args:
      cls: Log classification - one of 'debug', 'notice', 'warn', 'error'.
      msg: The message to log. Will be converted to string if needed.
  """
  msg = str(msg)
  if not quiet:
    print(labels[cls] + " " + msg)
  print(labels[cls] + " " + msg, file=logFile)


def warn(msg):
  """Log a warning message.
  
  Args:
      msg: The warning message to log.
  """
  log("warn", msg)


def debug(msg):
  """Log a debug message.
  
  Args:
      msg: The debug message to log.
  """
  log("debug", msg)


def notice(msg):
  """Log an informational notice.
  
  Args:
      msg: The notice message to log.
  """
  log("notice", msg)


def error(msg):
  """Log an error message.
  
  Args:
      msg: The error message to log.
  """
  log("error", msg)
