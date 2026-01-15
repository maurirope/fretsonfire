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
Resource and asset management module.

This module provides classes for managing game resources and assets,
including asynchronous loading capabilities. It handles locating files
across multiple data paths, managing read-only vs. writable resource
locations, and thread-based background loading.

Classes:
    Loader: A threaded resource loader that loads assets in the background.
    Resource: A task-based resource manager that coordinates asset loading
        and provides file path resolution.

Functions:
    getWritableResourcePath: Returns the platform-specific path for
        writable application configuration and data.
"""

import os
from queue import Queue, Empty
from threading import Thread, BoundedSemaphore
import time
import shutil
import stat

from Task import Task
import Log
import Version

class Loader(Thread):
  """
  A threaded resource loader for asynchronous asset loading.

  This class extends Thread to load game resources in the background,
  preventing the main game loop from blocking during potentially slow
  I/O operations. It supports cancellation, timing, and callback
  notification when loading completes.

  Attributes:
      semaphore (BoundedSemaphore): Controls concurrent loading operations.
      target: The object to attach the loaded resource to.
      name (str): The attribute name for the loaded resource.
      function (callable): The function that performs the actual loading.
      resultQueue (Queue): Queue for communicating completion to main thread.
      result: The loaded resource, or None if not yet loaded.
      onLoad (callable): Optional callback invoked after successful load.
      exception (tuple): Exception info if loading failed, None otherwise.
      time (float): Time in seconds taken to load the resource.
      canceled (bool): Whether this load operation was canceled.
  """

  def __init__(self, target, name, function, resultQueue, loaderSemaphore, onLoad = None):
    """
    Initialize a new Loader thread.

    Args:
        target: The object to attach the loaded resource to as an attribute.
        name (str): The attribute name to assign the loaded resource to.
        function (callable): A callable that performs the loading and returns
            the loaded resource.
        resultQueue (Queue): A queue to put this loader into when complete.
        loaderSemaphore (BoundedSemaphore): A semaphore to limit concurrent
            loading operations.
        onLoad (callable, optional): A callback function invoked with the
            loaded result after successful loading. Defaults to None.
    """
    Thread.__init__(self)
    self.semaphore   = loaderSemaphore
    self.target      = target
    self.name        = name
    self.function    = function
    self.resultQueue = resultQueue
    self.result      = None
    self.onLoad      = onLoad
    self.exception   = None
    self.time        = 0.0
    self.canceled    = False
    if target and name:
      setattr(target, name, None)

  def run(self):
    """
    Execute the loading operation in a separate thread.

    Acquires the semaphore, optionally lowers process priority on POSIX
    systems, performs the load, and signals completion via the result queue.
    """
    self.semaphore.acquire()
    # Reduce priority on posix
    if os.name == "posix":
      os.nice(5)
    self.load()
    self.semaphore.release()
    self.resultQueue.put(self)

  def __str__(self):
    """
    Return a string representation of this loader.

    Returns:
        str: A description including function name, resource name,
            and cancellation status.
    """
    return "%s(%s) %s" % (self.function.__name__, self.name, self.canceled and "(canceled)" or "")

  def cancel(self):
    """
    Cancel this loading operation.

    Sets the canceled flag to prevent the result from being applied
    when finish() is called.
    """
    self.canceled = True

  def load(self):
    """
    Perform the actual resource loading.

    Calls the loading function and records the time taken. Any exceptions
    are captured and stored for later re-raising in finish().
    """
    try:
      start = time.time()
      self.result = self.function()
      self.time = time.time() - start
    except:
      import sys
      self.exception = sys.exc_info()

  def finish(self):
    """
    Finalize the loading operation and apply the result.

    Logs the loading time, re-raises any exceptions that occurred during
    loading, assigns the result to the target object, and invokes the
    onLoad callback if provided.

    Returns:
        The loaded resource, or None if the operation was canceled.

    Raises:
        Exception: Re-raises any exception that occurred during loading.
    """
    if self.canceled:
      return
    
    Log.notice("Loaded %s.%s in %.3f seconds" % (self.target.__class__.__name__, self.name, self.time))
    
    if self.exception:
      raise self.exception[0](self.exception[1]).with_traceback(self.exception[2])
    if self.target and self.name:
      setattr(self.target, self.name, self.result)
    if self.onLoad:
      self.onLoad(self.result)
    return self.result

  def __call__(self):
    """
    Wait for loading to complete and return the result.

    Blocks until the loader thread finishes, then returns the loaded
    resource.

    Returns:
        The loaded resource.
    """
    self.join()
    return self.result

class Resource(Task):
  """
  A task-based resource manager for loading and locating game assets.

  This class manages data paths for locating resources, handles the
  distinction between read-only and writable resource locations, and
  coordinates asynchronous loading of game assets using Loader threads.
  It extends Task to integrate with the game's task scheduling system.

  Attributes:
      resultQueue (Queue): Queue for receiving completed loader threads.
      dataPaths (list[str]): List of paths to search for resources, in
          priority order (first path has highest priority).
      loaderSemaphore (BoundedSemaphore): Limits concurrent load operations.
      loaders (list[Loader]): Currently active loader threads.
  """

  def __init__(self, dataPath = os.path.join("..", "data")):
    """
    Initialize the Resource manager.

    Args:
        dataPath (str, optional): The primary data directory path.
            Defaults to "../data" relative to the current directory.
    """
    self.resultQueue = Queue()
    self.dataPaths = [dataPath]
    self.loaderSemaphore = BoundedSemaphore(value = 1)
    self.loaders = []

  def addDataPath(self, path):
    """
    Add a data path to search for resources.

    The path is added at highest priority (searched first).

    Args:
        path (str): The directory path to add.
    """
    if not path in self.dataPaths:
      self.dataPaths = [path] + self.dataPaths

  def removeDataPath(self, path):
    """
    Remove a data path from the search list.

    Args:
        path (str): The directory path to remove.
    """
    if path in self.dataPaths:
      self.dataPaths.remove(path)

  def fileName(self, *name, **args):
    """
    Resolve a resource filename to its full path.

    Searches through data paths to find the requested file. For writable
    files, copies read-only resources to a writable location if needed.

    Args:
        *name: Path components to join (e.g., "sounds", "click.ogg").
        **args: Optional keyword arguments:
            writable (bool): If True, returns a writable path, copying
                the file from read-only location if necessary.

    Returns:
        str: The full path to the resource file.
    """
    if not args.get("writable", False):
      for dataPath in self.dataPaths:
        readOnlyPath = os.path.join(dataPath, *name)
        # If the requested file is in the read-write path and not in the
        # read-only path, use the existing read-write one.
        if os.path.isfile(readOnlyPath):
          return readOnlyPath
        readWritePath = os.path.join(getWritableResourcePath(), *name)
        if os.path.isfile(readWritePath):
          return readWritePath
      return readOnlyPath
    else:
      readOnlyPath = os.path.join(self.dataPaths[-1], *name)
      try:
        # First see if we can write to the original file
        if os.access(readOnlyPath, os.W_OK):
          return readOnlyPath
        # If the original file does not exist, see if we can write to its directory
        if not os.path.isfile(readOnlyPath) and os.access(os.path.dirname(readOnlyPath), os.W_OK):
          return readOnlyPath
      except:
        raise
      
      # If the resource exists in the read-only path, make a copy to the
      # read-write path.
      readWritePath = os.path.join(getWritableResourcePath(), *name)
      if not os.path.isfile(readWritePath) and os.path.isfile(readOnlyPath):
        Log.notice("Copying '%s' to writable data directory." % "/".join(name))
        try:
          os.makedirs(os.path.dirname(readWritePath))
        except:
          pass
        shutil.copy(readOnlyPath, readWritePath)
        self.makeWritable(readWritePath)
      # Create directories if needed
      if not os.path.isdir(readWritePath) and os.path.isdir(readOnlyPath):
        Log.notice("Creating writable directory '%s'." % "/".join(name))
        os.makedirs(readWritePath)
        self.makeWritable(readWritePath)
      return readWritePath

  def makeWritable(self, path):
    """
    Set file permissions to make a path writable.

    Args:
        path (str): The file or directory path to make writable.
    """
    os.chmod(path, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
  
  def load(self, target = None, name = None, function = lambda: None, synch = False, onLoad = None):
    """
    Load a resource either synchronously or asynchronously.

    Creates a Loader to execute the loading function. For synchronous
    loading, blocks until complete. For asynchronous loading, starts
    a background thread and returns immediately.

    Args:
        target: The object to attach the loaded resource to.
        name (str): The attribute name to assign the resource to.
        function (callable): A callable that performs the loading and
            returns the loaded resource.
        synch (bool, optional): If True, load synchronously (blocking).
            Defaults to False (asynchronous).
        onLoad (callable, optional): Callback invoked with the loaded
            resource after successful loading.

    Returns:
        For synchronous loading: The loaded resource.
        For asynchronous loading: The Loader instance.
    """
    Log.notice("Loading %s.%s %s" % (target.__class__.__name__, name, synch and "synchronously" or "asynchronously"))
    l = Loader(target, name, function, self.resultQueue, self.loaderSemaphore, onLoad = onLoad)
    if synch:
      l.load()
      return l.finish()
    else:
      self.loaders.append(l)
      l.start()
      return l

  def run(self, ticks):
    """
    Process completed loading operations.

    Called by the task scheduler to check for and finalize any
    completed asynchronous load operations.

    Args:
        ticks: The current tick count (unused, required by Task interface).
    """
    try:
      loader = self.resultQueue.get_nowait()
      loader.finish()
      self.loaders.remove(loader)
    except Empty:
      pass

def getWritableResourcePath():
  """
  Get the platform-specific writable resource path.

  Returns the path to a directory where the application can store
  configuration files and writable data. On POSIX systems, this is
  ~/.appname; on Windows, it's in APPDATA.

  Returns:
      str: The path to the writable resource directory. The directory
          is created if it doesn't exist.
  """
  path = "."
  appname = Version.appName()
  if os.name == "posix":
    path = os.path.expanduser("~/." + appname)
  elif os.name == "nt":
    try:
      path = os.path.join(os.environ["APPDATA"], appname)
    except:
      pass
  try:
    os.mkdir(path)
  except:
    pass
  return path
