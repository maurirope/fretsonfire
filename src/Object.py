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
Object serialization and manager module for Frets on Fire.

This module provides a framework for managing game objects with support for:
- Object serialization and deserialization using pickle
- Centralized object lifecycle management (creation, modification, deletion)
- Change tracking and synchronization for networked multiplayer
- Message-based event system for inter-object communication

The module implements a publish-subscribe pattern where objects can emit
messages and other objects can connect callbacks to handle those messages.
"""

import pickle
from io import StringIO

class Serializer(pickle.Pickler):
  """
  Custom pickle serializer that handles persistent object references.
  
  Objects with an 'id' attribute are stored by reference rather than
  by value, allowing them to be properly restored through the Manager.
  """
  
  def persistent_id(self, obj):
    """Return the persistent ID for an object if it has one.
    
    Args:
        obj: The object to get the persistent ID for.
        
    Returns:
        The object's id attribute if present, None otherwise.
    """
    return getattr(obj, "id", None)


class Unserializer(pickle.Unpickler):
  """
  Custom pickle deserializer that resolves persistent object references.
  
  Works with a Manager instance to restore object references by looking
  up objects by their persistent IDs.
  
  Attributes:
      manager: The Manager instance used to resolve object references.
  """
  
  def __init__(self, manager, data):
    """Initialize the unserializer.
    
    Args:
        manager: The Manager instance for object lookup.
        data: The serialized data stream to read from.
    """
    pickle.Unpickler.__init__(self, data)
    self.manager = manager
    
  def persistent_load(self, id):
    """Load a persistent object reference by ID.
    
    Args:
        id: The persistent ID of the object to load.
        
    Returns:
        The object with the given ID, or None if not found.
    """
    return self.manager.getObject(id)

def serialize(data):
  """Serialize data to a string using pickle with persistent object references.
  
  Args:
      data: The data to serialize (can contain Object instances).
      
  Returns:
      A string containing the serialized data.
  """
  file = StringIO()
  Serializer(file, protocol = 2).dump(data)
  return file.getvalue()


def unserialize(manager, data):
  """Deserialize data from a string, resolving object references.
  
  Args:
      manager: The Manager instance to use for resolving object references.
      data: The serialized string data to deserialize.
      
  Returns:
      The deserialized data with object references resolved.
  """
  return Unserializer(manager, StringIO(data)).load()

class Manager:
  """
  Central manager for tracking and synchronizing game objects.
  
  The Manager maintains a registry of all managed objects and tracks
  their lifecycle events (creation, modification, deletion). It provides
  serialization of changes for network synchronization in multiplayer games.
  
  Attributes:
      MSG_CREATE: Message type constant for object creation.
      MSG_CHANGE: Message type constant for object modification.
      MSG_DELETE: Message type constant for object deletion.
      id: Unique identifier for this manager instance.
      objects: Dictionary mapping object IDs to object instances.
  """
  
  MSG_CREATE = 0
  MSG_CHANGE = 1
  MSG_DELETE = 2
  
  def __init__(self, id = 0):
    """Initialize the manager.
    
    Args:
        id: Unique identifier for this manager (default 0).
    """
    self.id = id
    self.reset()

  def setId(self, id):
    """Set the manager's unique identifier.
    
    Args:
        id: The new identifier for this manager.
    """
    self.id = id

  def reset(self):
    """Reset the manager to its initial state, clearing all tracked objects."""
    self.objects = {}
    self.__creationData = {}
    self.__created = []
    self.__changed = []
    self.__deleted = []
    self.__idCounter = 0

  def createObject(self, instance, *args, **kwargs):
    """Register a new object with the manager.
    
    Args:
        instance: The object instance to register.
        *args: Positional arguments used to create the object.
        **kwargs: Keyword arguments used to create the object.
        
    Returns:
        The globally unique ID assigned to the object.
    """
    self.__idCounter += 1
    id = self.globalObjectId(self.__idCounter)
    self.objects[id] = instance
    self.__creationData[id] = (instance.__class__, args, kwargs)
    self.__created.append(instance)
    return id

  def setChanged(self, obj):
    """Mark an object as changed for synchronization.
    
    Args:
        obj: The object that has been modified.
    """
    if not obj in self.__changed:
      self.__changed.append(obj)

  def deleteObject(self, obj):
    """Remove an object from the manager's registry.
    
    Args:
        obj: The object to delete (must have an 'id' attribute).
    """
    del self.objects[obj.id]
    del self.__creationData[obj.id]
    if obj in self.__created: self.__created.remove(obj)
    self.__deleted.append(obj.id)

  def getObject(self, id):
    """Retrieve an object by its ID.
    
    Args:
        id: The unique identifier of the object.
        
    Returns:
        The object with the given ID, or None if not found.
    """
    return self.objects.get(id, None)

  def getChanges(self, everything = False):
    """Get all pending changes as serialized data for synchronization.
    
    Args:
        everything: If True, return all objects and their full state.
                   If False, return only changes since last call.
                   
    Returns:
        A list of serialized change messages.
    """
    data = []
    if everything:
      data += [(self.MSG_CREATE, [(id, data) for id, data in list(self.__creationData.items())])]
      data += [(self.MSG_CHANGE, [(o.id, o.getChanges(everything = True)) for o in list(self.objects.values())])]
    else:
      if self.__created: data += [(self.MSG_CREATE, [(o.id, self.__creationData[o.id]) for o in self.__created])]
      if self.__changed: data += [(self.MSG_CHANGE, [(o.id, o.getChanges()) for o in self.__changed])]
      if self.__deleted: data += [(self.MSG_DELETE, self.__deleted)]
      self.__created = []
      self.__changed = []
      self.__deleted = []
    return [serialize(d) for d in data]

  def globalObjectId(self, objId):
    """Generate a globally unique object ID.
    
    Args:
        objId: The local object ID counter value.
        
    Returns:
        A globally unique ID combining manager ID and object ID.
    """
    return (self.id << 20) + objId

  def applyChanges(self, managerId, data):
    """Apply changes received from another manager (for network sync).
    
    Args:
        managerId: The ID of the manager that sent the changes.
        data: A list of serialized change messages to apply.
        
    Raises:
        Exception: Re-raises any exception encountered during processing.
    """
    for d in data:
      try:
        msg, data = unserialize(self, d)
        if msg == self.MSG_CREATE:
          for id, data in data:
            objectClass, args, kwargs = data
            self.__creationData[id] = data
            self.objects[id] = objectClass(id = id, manager = self, *args, **kwargs)
        elif msg == self.MSG_CHANGE:
          for id, data in data:
            if data: self.objects[id].applyChanges(data)
        elif msg == self.MSG_DELETE:
          id = data
          del self.__creationData[id]
          del self.objects[id]
      except Exception as e:
        print("Exception %s while processing incoming changes from manager %s." % (str(e), managerId))
        raise


def enableGlobalManager():
  """Enable the global manager instance for convenient access.
  
  Creates a module-level 'manager' variable that can be used as
  a default manager for Object instances.
  """
  global manager
  manager = Manager()

class Message:
  """
  Base class for messages used in the object event system.
  
  Messages are used for publish-subscribe communication between objects.
  Each message class is automatically assigned a unique numeric ID.
  
  Attributes:
      classes: Class-level dictionary mapping message classes to IDs.
      id: Unique identifier for this message type.
  """
  
  classes = {}
  
  def __init__(self):
    """Initialize the message and register its class if new."""
    if not self.__class__ in self.classes:
      self.classes[self.__class__] = len(self.classes)
    self.id = self.classes[self.__class__]


class ObjectCreated(Message):
  """Message emitted when an object is created."""
  pass    


class ObjectDeleted(Message):
  """Message emitted when an object is deleted.
  
  Attributes:
      object: Reference to the object being deleted.
  """
  
  def __init__(self, obj):
    """Initialize the deletion message.
    
    Args:
        obj: The object that is being deleted.
    """
    self.object = obj

class Object(object):
  """
  Base class for managed game objects with serialization and messaging support.
  
  Objects inheriting from this class are automatically registered with a Manager
  and support change tracking for network synchronization. They can also emit
  and receive messages for event-driven communication.
  
  Attributes:
      manager: The Manager instance that manages this object.
      id: Unique identifier assigned by the manager.
  """
  
  def __init__(self, id = None, manager = None, *args, **kwargs):
    """Initialize a managed object.
    
    Args:
        id: Pre-assigned ID (used when recreating from serialized data).
        manager: The Manager instance to register with.
        *args: Additional positional arguments for subclasses.
        **kwargs: Additional keyword arguments for subclasses.
    """
    self.__modified = {}
    self.__messages = []
    self.__messageMap = {}
    self.__shared = []
    #if not manager: manager = globals()["manager"]
    self.manager = manager
    self.id = id or manager.createObject(self, *args, **kwargs)

  def share(self, *attr):
    """Mark attributes as shared for network synchronization.
    
    Args:
        *attr: Names of attributes to share across the network.
    """
    [(self.__shared.append(str(a)), self.__modified.__setitem__(a, self.__dict__[a])) for a in attr]

  def __setattr__(self, attr, value):
    """Override attribute setting to track changes to shared attributes.
    
    Args:
        attr: The attribute name being set.
        value: The new value for the attribute.
    """
    if attr in getattr(self, "_Object__shared", {}):
      self.__modified[attr] = value
      self.manager.setChanged(self)
    object.__setattr__(self, attr, value)

  def delete(self):
    """Delete this object, emitting an ObjectDeleted message."""
    self.emit(ObjectDeleted(self))
    self.manager.deleteObject(self)

  def getChanges(self, everything = False):
    """Get pending changes for this object.
    
    Args:
        everything: If True, return all shared attributes.
                   If False, return only modified attributes.
                   
    Returns:
        A dictionary of changed attributes and their values.
    """
    if self.__messages:
      self.__modified["_Object__messages"] = self.__messages
    
    self.__processMessages()

    if everything:
      return dict([(k, getattr(self, k)) for k in self.__shared])

    if self.__modified:
      (data, self.__modified) = (self.__modified, {})
      return data

  def applyChanges(self, data):
    """Apply received changes to this object.
    
    Args:
        data: Dictionary of attribute names and values to apply.
    """
    self.__dict__.update(data)
    self.__processMessages()
    
  def emit(self, message):
    """Emit a message to be processed by connected callbacks.
    
    Args:
        message: The Message instance to emit.
    """
    self.__messages.append(message)

  def connect(self, messageClass, callback):
    """Connect a callback to a message type.
    
    Args:
        messageClass: The Message subclass to listen for.
        callback: Function to call when the message is emitted.
    """
    if not messageClass in self.__messageMap:
      self.__messageMap[messageClass] = []
    self.__messageMap[messageClass].append(callback)

  def disconnect(self, messageClass, callback):
    """Disconnect a callback from a message type.
    
    Args:
        messageClass: The Message subclass to stop listening for.
        callback: The callback function to remove.
    """
    if messageClass in self.__messageMap:
      self.__messageMap[messageClass].remove(callback)

  def __processMessages(self):
    """Process all pending messages, calling registered callbacks."""
    for m in self.__messages:
      if m.__class__ in self.__messageMap:
        for c in self.__messageMap[m.__class__]:
          c(m)
    self.__messages = []
