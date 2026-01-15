#!/usr/bin/python
# -*- coding: utf-8 -*-
#####################################################################
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
Test runner script for Frets on Fire.

This module discovers and runs all unit tests in the project. It automatically
finds all files matching the pattern '*Test.py' in the source tree and executes
their test cases using Python's unittest framework.

Usage:
    python TestAll.py         Run all standard unit tests
    python TestAll.py -i      Run interactive tests (tests ending in 'TestInteractive')

The test runner loads the default configuration before executing tests and
reports results with verbose output.
"""

import sys
import os
import unittest
import Config

tests = []

for root, dirs, files in os.walk("."):
  for f in files:
    f = os.path.join(root, f)
    if f.endswith("Test.py"):
      m = os.path.basename(f).replace(".py", "")
      d = os.path.dirname(f)
      sys.path.append(d)
      tests.append(__import__(m))

suite = unittest.TestSuite()

if "-i" in sys.argv:
  suffix = "TestInteractive"
else:
  suffix = "Test"

for test in tests:
  for item in dir(test):
    if item.endswith(suffix):
      suite.addTest(unittest.makeSuite(test.__dict__[item]))
  
Config.load(setAsDefault = True)
unittest.TextTestRunner(verbosity = 2).run(suite)
