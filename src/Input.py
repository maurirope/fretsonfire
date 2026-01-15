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
Input handling module for Frets on Fire.

This module provides unified input handling for keyboard, mouse, and joystick
devices. It uses a listener-based event system where components can register
to receive input events.

The module includes:
    - KeyListener: Interface for keyboard event handlers
    - MouseListener: Interface for mouse event handlers  
    - SystemEventListener: Interface for system events (quit, resize, etc.)
    - Input: Main input processor that polls pygame events and dispatches
      them to registered listeners

Joystick inputs are encoded as virtual key codes and dispatched through
the key listener system for unified input handling.

Example:
    >>> class MyScene(KeyListener):
    ...     def keyPressed(self, key, unicode):
    ...         if key == pygame.K_RETURN:
    ...             self.startGame()
    ...         return True  # Event consumed
    ...     def keyReleased(self, key):
    ...         return False  # Let other listeners handle it
    >>> 
    >>> input_handler = Input()
    >>> input_handler.addKeyListener(my_scene)
"""

import pygame
import Log
import Audio

from Task import Task
from Player import Controls

class KeyListener:
    """
    Interface for keyboard event listeners.
    
    Implement this interface to receive keyboard events from the Input system.
    Methods should return True if the event was consumed and should not be
    passed to other listeners, False otherwise.
    """
    
    def keyPressed(self, key, str):
        """
        Called when a key is pressed.
        
        Args:
            key: pygame key code or encoded joystick button.
            str: Unicode character for the key, or '\\x00' for non-character keys.
        
        Returns:
            bool: True if event was consumed, False to pass to other listeners.
        """
        pass
    
    def keyReleased(self, key):
        """
        Called when a key is released.
        
        Args:
            key: pygame key code or encoded joystick button.
        
        Returns:
            bool: True if event was consumed, False to pass to other listeners.
        """
        pass

class MouseListener:
    """
    Interface for mouse event listeners.
    
    Implement this interface to receive mouse events from the Input system.
    Methods should return True if the event was consumed and should not be
    passed to other listeners, False otherwise.
    """
    
    def mouseButtonPressed(self, button, pos):
        """
        Called when a mouse button is pressed.
        
        Args:
            button (int): Mouse button number (1=left, 2=middle, 3=right).
            pos (tuple): (x, y) position of the mouse cursor.
        
        Returns:
            bool: True if event was consumed, False to pass to other listeners.
        """
        pass
    
    def mouseButtonReleased(self, button, pos):
        """
        Called when a mouse button is released.
        
        Args:
            button (int): Mouse button number (1=left, 2=middle, 3=right).
            pos (tuple): (x, y) position of the mouse cursor.
        
        Returns:
            bool: True if event was consumed, False to pass to other listeners.
        """
        pass
    
    def mouseMoved(self, pos, rel):
        """
        Called when the mouse is moved.
        
        Args:
            pos (tuple): (x, y) current position of the mouse cursor.
            rel (tuple): (dx, dy) relative movement since last event.
        
        Returns:
            bool: True if event was consumed, False to pass to other listeners.
        """
        pass
    
class SystemEventListener:
    """
    Interface for system event listeners.
    
    Implement this interface to receive system-level events like window
    resize, application quit requests, and music playback completion.
    """
    
    def screenResized(self, size):
        """
        Called when the window is resized.
        
        Args:
            size (tuple): (width, height) new window dimensions.
        """
        pass
    
    def restartRequested(self):
        """
        Called when an application restart is requested.
        """
        pass
    
    def musicFinished(self):
        """
        Called when background music playback completes.
        """
        pass
    
    def quit(self):
        """
        Called when the application should terminate.
        """
        pass


# Custom pygame event for music playback completion
MusicFinished = pygame.USEREVENT

# Compatibility shim for Python 2 (reversed() was added in Python 2.4)
try:
    reversed
except NameError:
    def reversed(seq):
        """Return a reversed copy of a sequence."""
        seq = seq[:]
        seq.reverse()
        return seq

class Input(Task):
    """
    Central input handler that processes and dispatches all input events.
    
    This class polls pygame for keyboard, mouse, and joystick events and
    dispatches them to registered listeners. It runs as a Task in the game
    engine's main loop.
    
    Joystick inputs (buttons, axes, hats) are encoded as virtual key codes
    so they can be handled uniformly with keyboard input through KeyListeners.
    
    Attributes:
        mouse: pygame mouse module reference for cursor control.
        mouseListeners (list): Registered MouseListener instances.
        keyListeners (list): Registered KeyListener instances (normal priority).
        priorityKeyListeners (list): Registered KeyListener instances (high priority).
        systemListeners (list): Registered SystemEventListener instances.
        controls (Controls): Player control state tracker.
        joysticks (list): Initialized pygame joystick objects.
        joystickAxes (dict): Current axis states per joystick.
        joystickHats (dict): Current hat states per joystick.
    
    Example:
        >>> input_handler = Input()
        >>> input_handler.addKeyListener(my_scene)
        >>> input_handler.addSystemEventListener(game_engine)
    """
    
    def __init__(self):
        """
        Initialize the input system.
        
        Sets up pygame input subsystems, initializes all connected joysticks,
        configures music end events, and installs custom key name handling
        for joystick inputs.
        """
        Task.__init__(self)
        self.mouse = pygame.mouse
        self.mouseListeners = []
        self.keyListeners = []
        self.systemListeners = []
        self.priorityKeyListeners = []
        self.controls = Controls()
        self.disableKeyRepeat()

        # Initialize joysticks
        pygame.joystick.init()
        self.joystickAxes = {}
        self.joystickHats = {}

        self.joysticks = [pygame.joystick.Joystick(id) for id in range(pygame.joystick.get_count())]
        for j in self.joysticks:
            j.init()
            self.joystickAxes[j.get_id()] = [0] * j.get_numaxes()
            self.joystickHats[j.get_id()] = [(0, 0)] * j.get_numhats()
        Log.debug("%d joysticks found." % (len(self.joysticks)))

        # Enable music events
        Audio.Music.setEndEvent(MusicFinished)

        # Custom key names
        self.getSystemKeyName = pygame.key.name
        pygame.key.name = self.getKeyName

    def reloadControls(self):
        """
        Reload control mappings from configuration.
        
        Call this after key bindings have been changed in settings.
        """
        self.controls = Controls()

    def disableKeyRepeat(self):
        """
        Disable keyboard auto-repeat.
        
        When disabled, holding a key only generates a single keyPressed event.
        Useful during gameplay.
        """
        pygame.key.set_repeat(0, 0)

    def enableKeyRepeat(self):
        """
        Enable keyboard auto-repeat for menu navigation.
        
        When enabled, holding a key generates repeated keyPressed events
        (300ms delay, then every 30ms). Useful for text input and menus.
        """
        pygame.key.set_repeat(300, 30)

    def addMouseListener(self, listener):
        """
        Register a mouse event listener.
        
        Args:
            listener (MouseListener): Object implementing MouseListener interface.
        """
        if not listener in self.mouseListeners:
            self.mouseListeners.append(listener)

    def removeMouseListener(self, listener):
        """
        Unregister a mouse event listener.
        
        Args:
            listener (MouseListener): Previously registered listener to remove.
        """
        if listener in self.mouseListeners:
            self.mouseListeners.remove(listener)

    def addKeyListener(self, listener, priority=False):
        """
        Register a keyboard event listener.
        
        Priority listeners receive events before normal listeners and can
        consume events to prevent them from reaching normal listeners.
        
        Args:
            listener (KeyListener): Object implementing KeyListener interface.
            priority (bool): If True, register as high-priority listener.
        """
        if priority:
            if not listener in self.priorityKeyListeners:
                self.priorityKeyListeners.append(listener)
        else:
            if not listener in self.keyListeners:
                self.keyListeners.append(listener)

    def removeKeyListener(self, listener):
        """
        Unregister a keyboard event listener.
        
        Removes the listener from both priority and normal listener lists.
        
        Args:
            listener (KeyListener): Previously registered listener to remove.
        """
        if listener in self.keyListeners:
            self.keyListeners.remove(listener)
        if listener in self.priorityKeyListeners:
            self.priorityKeyListeners.remove(listener)

    def addSystemEventListener(self, listener):
        """
        Register a system event listener.
        
        Args:
            listener (SystemEventListener): Object implementing SystemEventListener.
        """
        if not listener in self.systemListeners:
            self.systemListeners.append(listener)

    def removeSystemEventListener(self, listener):
        """
        Unregister a system event listener.
        
        Args:
            listener (SystemEventListener): Previously registered listener to remove.
        """
        if listener in self.systemListeners:
            self.systemListeners.remove(listener)
      
    def broadcastEvent(self, listeners, function, *args):
        """
        Broadcast an event to a list of listeners.
        
        Iterates through listeners in reverse order (most recently added first)
        and calls the specified method. Stops if a listener returns True
        (event consumed).
        
        Args:
            listeners (list): List of listener objects.
            function (str): Name of the method to call on each listener.
            *args: Arguments to pass to the listener method.
        
        Returns:
            bool: True if any listener consumed the event, False otherwise.
        """
        for l in reversed(listeners):
            if getattr(l, function)(*args):
                return True
        else:
            return False

    def broadcastSystemEvent(self, name, *args):
        """
        Broadcast a system event to all system listeners.
        
        Args:
            name (str): Name of the system event method to call.
            *args: Arguments to pass to the event method.
        
        Returns:
            bool: True if any listener consumed the event, False otherwise.
        """
        return self.broadcastEvent(self.systemListeners, name, *args)

    def encodeJoystickButton(self, joystick, button):
        """
        Encode a joystick button as a virtual key code.
        
        Args:
            joystick (int): Joystick ID.
            button (int): Button index.
        
        Returns:
            int: Virtual key code (0x10000 + joystick*256 + button).
        """
        return 0x10000 + (joystick << 8) + button

    def encodeJoystickAxis(self, joystick, axis, end):
        """
        Encode a joystick axis direction as a virtual key code.
        
        Args:
            joystick (int): Joystick ID.
            axis (int): Axis index.
            end (int): Direction - 0 for negative, 1 for positive.
        
        Returns:
            int: Virtual key code (0x20000 + joystick*256 + axis*16 + end).
        """
        return 0x20000 + (joystick << 8) + (axis << 4) + end

    def encodeJoystickHat(self, joystick, hat, pos):
        """
        Encode a joystick hat position as a virtual key code.
        
        Args:
            joystick (int): Joystick ID.
            hat (int): Hat index.
            pos (tuple): (x, y) hat position, each -1, 0, or 1.
        
        Returns:
            int: Virtual key code (0x30000 + joystick*256 + hat*16 + encoded_pos).
        """
        v = int((pos[1] + 1) * 3 + (pos[0] + 1))
        return 0x30000 + (joystick << 8) + (hat << 4) + v

    def decodeJoystickButton(self, id):
        """
        Decode a joystick button virtual key code.
        
        Args:
            id (int): Virtual key code from encodeJoystickButton.
        
        Returns:
            tuple: (joystick_id, button_index).
        """
        id -= 0x10000
        return (id >> 8, id & 0xff)

    def decodeJoystickAxis(self, id):
        """
        Decode a joystick axis virtual key code.
        
        Args:
            id (int): Virtual key code from encodeJoystickAxis.
        
        Returns:
            tuple: (joystick_id, axis_index, direction).
        """
        id -= 0x20000
        return (id >> 8, (id >> 4) & 0xf, id & 0xf)

    def decodeJoystickHat(self, id):
        """
        Decode a joystick hat virtual key code.
        
        Args:
            id (int): Virtual key code from encodeJoystickHat.
        
        Returns:
            tuple: (joystick_id, hat_index, (x, y) position).
        """
        id -= 0x30000
        v = id & 0xf
        x, y = (v % 3) - 1, (v / 3) - 1
        return (id >> 8, (id >> 4) & 0xf, (x, y))

    def getKeyName(self, id):
        """
        Get a human-readable name for a key or joystick input.
        
        Handles both regular pygame keys and encoded joystick inputs.
        
        Args:
            id (int): Key code or encoded joystick input.
        
        Returns:
            str: Human-readable name (e.g., 'Joy #1, axis 0 high').
        """
        if id >= 0x30000:
            joy, axis, pos = self.decodeJoystickHat(id)
            return "Joy #%d, hat %d %s" % (joy + 1, axis, pos)
        elif id >= 0x20000:
            joy, axis, end = self.decodeJoystickAxis(id)
            return "Joy #%d, axis %d %s" % (joy + 1, axis, (end == 1) and "high" or "low")
        elif id >= 0x10000:
            joy, but = self.decodeJoystickButton(id)
            return "Joy #%d, %s" % (joy + 1, chr(ord('A') + but))
        return self.getSystemKeyName(id)

    def run(self, ticks):
        """
        Process all pending input events.
        
        Called each frame by the game engine. Polls pygame for events and
        dispatches them to appropriate listeners (keyboard, mouse, system,
        and joystick events).
        
        Args:
            ticks: Frame timing information (unused, required by Task interface).
        """
        pygame.event.pump()
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if not self.broadcastEvent(self.priorityKeyListeners, "keyPressed", event.key, event.unicode):
                    self.broadcastEvent(self.keyListeners, "keyPressed", event.key, event.unicode)
            elif event.type == pygame.KEYUP:
                if not self.broadcastEvent(self.priorityKeyListeners, "keyReleased", event.key):
                    self.broadcastEvent(self.keyListeners, "keyReleased", event.key)
            elif event.type == pygame.MOUSEMOTION:
                self.broadcastEvent(self.mouseListeners, "mouseMoved", event.pos, event.rel)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.broadcastEvent(self.mouseListeners, "mouseButtonPressed", event.button, event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.broadcastEvent(self.mouseListeners, "mouseButtonReleased", event.button, event.pos)
            elif event.type == pygame.VIDEORESIZE:
                self.broadcastEvent(self.systemListeners, "screenResized", event.size)
            elif event.type == pygame.QUIT:
                self.broadcastEvent(self.systemListeners, "quit")
            elif event.type == MusicFinished:
                self.broadcastEvent(self.systemListeners, "musicFinished")
            elif event.type == pygame.JOYBUTTONDOWN:
                # Joystick buttons masquerade as keyboard events
                id = self.encodeJoystickButton(event.joy, event.button)
                if not self.broadcastEvent(self.priorityKeyListeners, "keyPressed", id, '\x00'):
                    self.broadcastEvent(self.keyListeners, "keyPressed", id, '\x00')
            elif event.type == pygame.JOYBUTTONUP:
                id = self.encodeJoystickButton(event.joy, event.button)
                if not self.broadcastEvent(self.priorityKeyListeners, "keyReleased", id):
                    self.broadcastEvent(self.keyListeners, "keyReleased", id)
            elif event.type == pygame.JOYAXISMOTION:
                try:
                    threshold = .8
                    state = self.joystickAxes[event.joy][event.axis]
                    keyEvent = None

                    if event.value > threshold and state != 1:
                        self.joystickAxes[event.joy][event.axis] = 1
                        keyEvent = "keyPressed"
                        args = (self.encodeJoystickAxis(event.joy, event.axis, 1), '\x00')
                        state = 1
                    elif event.value < -threshold and state != -1:
                        keyEvent = "keyPressed"
                        args = (self.encodeJoystickAxis(event.joy, event.axis, 0), '\x00')
                        state = -1
                    elif state != 0:
                        keyEvent = "keyReleased"
                        args = (self.encodeJoystickAxis(event.joy, event.axis, (state == 1) and 1 or 0), )
                        state = 0

                    if keyEvent:
                        self.joystickAxes[event.joy][event.axis] = state
                        if not self.broadcastEvent(self.priorityKeyListeners, keyEvent, *args):
                            self.broadcastEvent(self.keyListeners, keyEvent, *args)
                except KeyError:
                    pass
            elif event.type == pygame.JOYHATMOTION:
                try:
                    state = self.joystickHats[event.joy][event.hat]
                    keyEvent = None

                    if event.value != (0, 0) and state == (0, 0):
                        self.joystickHats[event.joy][event.hat] = event.value
                        keyEvent = "keyPressed"
                        args = (self.encodeJoystickHat(event.joy, event.hat, event.value), '\x00')
                        state = event.value
                    else:
                        keyEvent = "keyReleased"
                        args = (self.encodeJoystickHat(event.joy, event.hat, state), )
                        state = (0, 0)

                    if keyEvent:
                        self.joystickHats[event.joy][event.hat] = state
                        if not self.broadcastEvent(self.priorityKeyListeners, keyEvent, *args):
                            self.broadcastEvent(self.keyListeners, keyEvent, *args)
                except KeyError:
                    pass
