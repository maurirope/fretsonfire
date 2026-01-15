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
SVG to PNG conversion utility for Frets on Fire.

This script recursively walks through the current directory tree and converts
all SVG (Scalable Vector Graphics) files to PNG format using Inkscape. It is
used to generate rasterized game assets from vector source files.

Usage:
    cd data/  # Navigate to directory containing SVG files
    python ../src/svg2png.py

Behavior:
    - Recursively finds all *.svg files in the current directory tree
    - Converts each SVG to PNG with the same base filename
    - Uses Inkscape's command-line interface for conversion
    - Exports only the drawing area (-D flag)
    - Uses black background with full transparency

Requirements:
    - Inkscape must be installed and available in the system PATH
"""

import os, fnmatch

for root, dirs, files in os.walk("."):
  for svg in fnmatch.filter(files, "*.svg"):
    svg = os.path.join(root, svg)
    print(svg, os.system("inkscape -e '%s' -D '%s' -b black -y 0.0" % (svg.replace(".svg", ".png"), svg)))
