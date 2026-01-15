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
Timer module for Frets on Fire.

This module provides frame timing and synchronization for the game loop.
The Timer class maintains a consistent frame rate by controlling when
frames advance, and provides FPS estimation for performance monitoring.

The timer supports:
    - Configurable target frame rate
    - Adjustable tick rate for slow-motion or fast-forward effects
    - High-priority mode for more accurate timing
    - Real-time FPS estimation

Example:
    >>> timer = Timer(fps=60, tickrate=1.0)
    >>> while running:
    ...     ticks = timer.advanceFrame()
    ...     update_game(ticks[0])
    ...     render()
    ...     print(f"FPS: {timer.fpsEstimate:.1f}")
"""

import pygame
import time


class Timer(object):
    """
    Frame timer for controlling game loop timing and measuring FPS.
    
    The Timer ensures consistent frame pacing by waiting until enough
    time has elapsed before allowing the next frame to proceed. It also
    tracks actual performance through FPS estimation.
    
    Attributes:
        fps (int): Target frames per second.
        timestep (float): Milliseconds per frame (1000 / fps).
        tickrate (float): Time scaling factor (1.0 = normal speed).
        ticks (int): Current time in scaled milliseconds.
        frame (int): Total frames rendered since timer creation.
        fpsEstimate (float): Estimated current FPS based on recent frames.
        highPriority (bool): If True, busy-waits for precise timing.
            If False, yields CPU time while waiting.
    
    Example:
        >>> timer = Timer(fps=60)
        >>> timer.highPriority = True  # For more accurate timing
        >>> delta = timer.advanceFrame()[0]  # Wait for next frame
    """
    
    def __init__(self, fps=60, tickrate=1.0):
        """
        Initialize the timer with target framerate and tick rate.
        
        Args:
            fps (int): Target frames per second. Defaults to 60.
            tickrate (float): Time scaling multiplier. Values less than 1.0
                create slow-motion, values greater than 1.0 speed up time.
                Defaults to 1.0 (normal speed).
        """
        self.fps = fps
        self.timestep = 1000.0 / fps
        self.tickrate = tickrate
        self.ticks = self.getTime()
        self.frame = 0
        self.fpsEstimate = 0
        self.fpsEstimateStartTick = self.ticks
        self.fpsEstimateStartFrame = self.frame
        self.highPriority = False

    def getTime(self):
        """
        Get the current time in scaled milliseconds.
        
        Returns:
            int: Current pygame time multiplied by the tick rate.
        """
        return int(pygame.time.get_ticks() * self.tickrate)

    time = property(getTime)

    def advanceFrame(self):
        """
        Wait for the next frame and return timing information.
        
        Blocks until enough time has elapsed for the next frame according
        to the target FPS. Updates the FPS estimate periodically.
        
        In high-priority mode, uses busy-waiting for precise timing.
        Otherwise, yields CPU time with pygame.time.wait(0).
        
        Returns:
            list: A single-element list containing the elapsed time in
                milliseconds since the last frame, capped at 16x the
                timestep to prevent physics explosions after long pauses.
        
        Note:
            The return value is capped to prevent very large delta times
            that could cause issues with physics or animation calculations
            (e.g., after the game window loses focus).
        """
        while True:
            ticks = self.getTime()
            diff = ticks - self.ticks
            if diff >= self.timestep:
                break
            if not self.highPriority:
                pygame.time.wait(0)

        self.ticks = ticks
        self.frame += 1

        if ticks > self.fpsEstimateStartTick + 250:
            n = self.frame - self.fpsEstimateStartFrame
            self.fpsEstimate = 1000.0 * n / (ticks - self.fpsEstimateStartTick)
            self.fpsEstimateStartTick = ticks
            self.fpsEstimateStartFrame = self.frame

        return [min(diff, self.timestep * 16)]
