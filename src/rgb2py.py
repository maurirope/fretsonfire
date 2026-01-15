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
Color table generator utility for Frets on Fire.

This script parses the X11 RGB color definition file (/etc/X11/rgb.txt) and
generates a Python dictionary mapping color names to normalized RGB tuples.
The output can be redirected to create a Python module with named color
constants for use in the game's graphics system.

Usage:
    python rgb2py.py > SvgColors.py

Output format:
    colors = {
        "colorname": (r, g, b),  # Values normalized to 0.0-1.0 range
        ...
    }

Note:
    Requires the X11 rgb.txt file to be present on the system.
    Typically found at /etc/X11/rgb.txt on Linux systems.
"""

import re

f = open("/etc/X11/rgb.txt")

print("colors = {")
for l in f.readlines():
  if l.startswith("!"): continue
  c = re.split("[ \t]+", l.strip())
  rgb, names = list(map(int, c[:3])), c[3:]
  rgb = [float(c) / 255.0 for c in rgb]
  for n in names:
    print('  %-24s: (%.2f, %.2f, %.2f),' % ('"%s"' % n.lower(), rgb[0], rgb[1], rgb[2]))
print("}")
