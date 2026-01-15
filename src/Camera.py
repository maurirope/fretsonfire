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

"""Camera module for 3D scene rendering.

This module provides a Camera class that manages the view transformation
for 3D rendering using OpenGL. The camera defines the viewpoint from which
the scene is rendered, including the camera position, target look-at point,
and up direction vector.
"""

from OpenGL.GLU import *


class Camera:
    """A 3D camera for scene rendering using OpenGL.

    The Camera class encapsulates the view transformation parameters needed
    to render a 3D scene from a specific viewpoint. It uses the gluLookAt
    function to set up the view matrix.

    Attributes:
        origin: A tuple (x, y, z) representing the camera's position in world space.
        target: A tuple (x, y, z) representing the point the camera is looking at.
        up: A tuple (x, y, z) representing the camera's up direction vector.
    """

    def __init__(self):
        """Initialize the camera with default position, target, and up vector."""
        # Camera origin vector
        self.origin = (10.0, 0.0, 10.0)
        # Camera target vector
        self.target = (0.0, 0.0, 0.0)
        # Camera up vector
        self.up     = (0.0, 1.0, 0.0)

    def apply(self):
        """Apply the camera transformation to the OpenGL modelview matrix.

        Configures the view matrix using gluLookAt based on the camera's
        origin, target, and up vector. This should be called after loading
        the identity matrix and before rendering scene objects.

        Returns:
            None
        """
        gluLookAt(self.origin[0], self.origin[1], self.origin[2],
                  self.target[0], self.target[1], self.target[2],
                  self.up[0],     self.up[1],     self.up[2])

