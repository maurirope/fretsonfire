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
Core Engine Module
==================

This module provides the main task scheduler that drives the game.
The Engine class manages a collection of tasks that are run each frame,
handling timing, pausing, and garbage collection.

Architecture:
    - Tasks can be "synchronized" (run with fixed timesteps for physics/logic)
    - Or "frame tasks" (run once per frame for rendering)
    - The Timer class provides frame timing and tick generation

Example:
    engine = Engine(fps=60, tickrate=1.0)
    engine.addTask(myGameLogic, synchronized=True)
    engine.addTask(myRenderer, synchronized=False)
    while engine.run():
        pass
"""

import gc

import Object
from Timer import Timer
from Task import Task


class Engine:
    """
    Main task scheduler and game loop controller.
    
    The Engine manages two types of tasks:
    - Synchronized tasks: Run with fixed timesteps for consistent game logic
    - Frame tasks: Run once per frame for rendering and input processing
    
    Attributes:
        tasks (list): Synchronized tasks running with fixed timesteps
        frameTasks (list): Tasks running once per frame
        timer (Timer): Timing controller for frame rate management
        paused (list): Currently paused tasks
        running (bool): Whether the engine is running
    """
    
    def __init__(self, fps=60, tickrate=1.0):
        """
        Initialize the engine.
        
        Args:
            fps (int): Target frames per second (default: 60)
            tickrate (float): Game speed multiplier (default: 1.0)
        """
        self.tasks = []
        self.frameTasks = []
        self.timer = Timer(fps=fps, tickrate=tickrate)
        self.currentTask = None
        self.paused = []
        self.running = True

    def quit(self):
        """Stop all tasks and shut down the engine."""
        for t in list(self.tasks + self.frameTasks):
            self.removeTask(t)
        self.running = False

    def addTask(self, task, synchronized=True):
        """
        Add a task to the engine.
        
        Args:
            task (Task): The task to add
            synchronized (bool): If True, task runs with fixed timesteps.
                               If False, task runs once per frame.
        """
        if synchronized:
            queue = self.tasks
        else:
            queue = self.frameTasks
        
        if task not in queue:
            queue.append(task)
            task.started()

    def removeTask(self, task):
        """
        Remove a task from the engine.
        
        Args:
            task (Task): The task to remove
        """
        queues = self._getTaskQueues(task)
        for q in queues:
            q.remove(task)
        if queues:
            task.stopped()

    def _getTaskQueues(self, task):
        """Get all queues containing the specified task."""
        queues = []
        for queue in [self.tasks, self.frameTasks]:
            if task in queue:
                queues.append(queue)
        return queues

    def pauseTask(self, task):
        """
        Pause a task (it won't run until resumed).
        
        Args:
            task (Task): The task to pause
        """
        self.paused.append(task)

    def resumeTask(self, task):
        """
        Resume a paused task.
        
        Args:
            task (Task): The task to resume
        """
        self.paused.remove(task)
    
    def enableGarbageCollection(self, enabled):
        """
        Enable or disable Python garbage collection.
        
        Disabling GC can prevent stuttering during gameplay but will
        increase memory usage. Re-enable after loading screens.
        
        Args:
            enabled (bool): Whether to enable garbage collection
        """
        if enabled:
            gc.enable()
        else:
            gc.disable()
      
    def collectGarbage(self):
        """Force an immediate garbage collection run."""
        gc.collect()

    def boostBackgroundThreads(self, boost):
        """
        Adjust scheduling priority for background threads.
        
        When boost is True, background threads (like resource loading)
        get more CPU time. When False, the main thread has priority.
        
        Args:
            boost (bool): True to boost background threads
        """
        self.timer.highPriority = not bool(boost)

    def _runTask(self, task, ticks=0):
        """Run a single task if it's not paused."""
        if task not in self.paused:
            self.currentTask = task
            task.run(ticks)
            self.currentTask = None

    def run(self):
        """
        Run one cycle of the game loop.
        
        Executes all frame tasks once, then runs synchronized tasks
        for each tick generated by the timer.
        
        Returns:
            bool: True if the engine should continue, False if it should stop
        """
        if not self.frameTasks and not self.tasks:
            return False
        
        # Run frame tasks (once per frame)
        for task in self.frameTasks:
            self._runTask(task)
        
        # Run synchronized tasks (once per tick)
        for ticks in self.timer.advanceFrame():
            for task in self.tasks:
                self._runTask(task, ticks)
        
        return True
