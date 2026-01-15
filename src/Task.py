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
Task module for Frets on Fire.

This module provides the base Task class, which represents a unit of work
that can be scheduled and executed by the game engine. Tasks are the
fundamental building blocks of the game loop, handling everything from
input processing to rendering.

The game engine maintains a list of active tasks and calls their run()
method each frame with timing information. Tasks can be dynamically
added and removed during gameplay.

Example:
    >>> class MyTask(Task):
    ...     def __init__(self, name):
    ...         Task.__init__(self)
    ...         self.name = name
    ...     
    ...     def started(self):
    ...         print(f"{self.name} started")
    ...     
    ...     def run(self, ticks):
    ...         # Process one frame of work
    ...         pass
    ...     
    ...     def stopped(self):
    ...         print(f"{self.name} stopped")
"""


class Task:
    """
    Base class for scheduled tasks in the game engine.
    
    Tasks are units of work that run each frame during the game loop.
    Subclass this to create custom tasks for input handling, game logic,
    rendering, etc.
    
    Lifecycle:
        1. Task is created
        2. Task is added to engine via Engine.addTask()
        3. started() is called once
        4. run(ticks) is called each frame
        5. Task is removed via Engine.removeTask()
        6. stopped() is called once
    
    Attributes:
        None by default. Subclasses may add their own attributes.
    
    Example:
        >>> class UpdateTask(Task):
        ...     def run(self, ticks):
        ...         for entity in self.entities:
        ...             entity.update(ticks)
    """
    
    def __init__(self):
        """
        Initialize a new task.
        
        Subclasses should call Task.__init__(self) in their constructors.
        """
        pass
    
    def started(self):
        """
        Called when the task is added to the game engine.
        
        Override this method to perform initialization that requires
        the task to be active (e.g., registering event listeners).
        """
        pass
    
    def stopped(self):
        """
        Called when the task is removed from the game engine.
        
        Override this method to perform cleanup (e.g., unregistering
        event listeners, releasing resources).
        """
        pass
    
    def run(self, ticks):
        """
        Execute one frame of the task's work.
        
        This method is called each frame by the game engine while the
        task is active. Implement the task's main logic here.
        
        Args:
            ticks: Timing information from the game timer, typically
                a list containing the elapsed time since the last frame
                in milliseconds.
        """
        pass
