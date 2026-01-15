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
Configuration management module for Frets on Fire.

This module provides a flexible configuration system that allows defining,
loading, reading, and writing configuration options. It uses INI-style
configuration files with a prototype-based system for defining valid options
with their types, defaults, and descriptions.

Key components:
    - Option: A prototype configuration key definition
    - Config: A configuration registry for managing settings
    - define(): Define new configuration options with type validation
    - load(): Load configuration from file
    - get()/set(): Global configuration access functions

Example usage:
    >>> define("audio", "volume", float, default=0.8, text="Master volume")
    >>> config = load("settings.ini", setAsDefault=True)
    >>> volume = get("audio", "volume")
"""

from configparser import ConfigParser
import Log
import Resource
import os

encoding  = "iso-8859-1"
config    = None
prototype = {}

class Option:
  """A prototype configuration key.
  
  Represents a configuration option definition with its type, default value,
  description text, and available options for selection.
  
  Attributes:
      type: The Python type for this option (e.g., str, int, float, bool).
      default: The default value if not specified in config file.
      text: Human-readable description of this option.
      options: List or dict of valid values for this option.
  """
  
  def __init__(self, **args):
    """Initialize an Option with arbitrary keyword arguments.
    
    Args:
        **args: Keyword arguments that become attributes of this Option.
            Common keys: type, default, text, options.
    """
    for key, value in list(args.items()):
      setattr(self, key, value)
      
def define(section, option, type, default = None, text = None, options = None, prototype = prototype):
  """Define a configuration key in the prototype.
  
  Registers a new configuration option with its type, default value,
  and optional constraints. This must be called before the option
  can be used with get() or set().
  
  Args:
      section: Section name in the configuration file (e.g., "audio").
      option: Option name within the section (e.g., "volume").
      type: Python type for the value (e.g., str, int, float, bool).
      default: Default value when the option is not in the config file.
      text: Human-readable description for UI display.
      options: Valid values - either a list [val1, val2] or a dict
          mapping values to descriptions {True: 'Yes', False: 'No'}.
      prototype: Configuration prototype dict to add this option to.
          Defaults to the global prototype.
  """
  if not section in prototype:
    prototype[section] = {}
    
  if type == bool and not options:
    options = [True, False]
    
  prototype[section][option] = Option(type = type, default = default, text = text, options = options)

def load(fileName = None, setAsDefault = False):
  """Load a configuration file with the default prototype.
  
  Creates a new Config instance from the specified file. If the file
  doesn't exist at the given path, it will look in the writable
  resource path.
  
  Args:
      fileName: Path to the configuration file. If None, uses defaults only.
      setAsDefault: If True and no global config exists, set this as
          the global configuration accessible via get()/set().
  
  Returns:
      Config: The loaded configuration instance.
  """
  global config
  c = Config(prototype, fileName)
  if setAsDefault and not config:
    config = c
  return c

class Config:
  """A configuration registry for managing application settings.
  
  Provides methods to read and write configuration values with type
  validation based on a prototype definition. Configuration is persisted
  to an INI-style file.
  
  Attributes:
      prototype: Dict mapping section -> option -> Option definitions.
      config: The underlying ConfigParser instance.
      fileName: Path to the configuration file.
  """
  
  def __init__(self, prototype, fileName = None):
    """Initialize a Config instance.
    
    Args:
        prototype: Dict mapping section names to option definitions.
            Each option definition is an Option instance with type and default.
        fileName: Path to the configuration file. If the file doesn't exist
            at the given path, looks in the writable resource directory.
    """
    self.prototype = prototype

    # read configuration
    self.config = ConfigParser()

    if fileName:
      if not os.path.isfile(fileName):
        path = Resource.getWritableResourcePath()
        fileName = os.path.join(path, fileName)
      self.config.read(fileName)
  
    self.fileName  = fileName
  
    # fix the defaults and non-existing keys
    for section, options in list(prototype.items()):
      if not self.config.has_section(section):
        self.config.add_section(section)
      for option in list(options.keys()):
        type    = options[option].type
        default = options[option].default
        if not self.config.has_option(section, option):
          self.config.set(section, option, str(default))
    
  def get(self, section, option):
    """Read a configuration value.
    
    Retrieves the value for the specified option, converting it to the
    appropriate type as defined in the prototype. Boolean values accept
    various string representations (1, true, yes, on).
    
    Args:
        section: Section name (e.g., "audio").
        option: Option name within the section (e.g., "volume").
    
    Returns:
        The configuration value, converted to its defined type.
        Returns the default value if the option is not set.
    
    Warns:
        Logs a warning if the key is not defined in the prototype.
    """
    try:
      type    = self.prototype[section][option].type
      default = self.prototype[section][option].default
    except KeyError:
      Log.warn("Config key %s.%s not defined while reading." % (section, option))
      type, default = str, None
  
    value = self.config.has_option(section, option) and self.config.get(section, option) or default
    if type == bool:
      value = str(value).lower()
      if value in ("1", "true", "yes", "on"):
        value = True
      else:
        value = False
    else:
      value = type(value)
      
    #Log.debug("%s.%s = %s" % (section, option, value))
    return value

  def set(self, section, option, value):
    """Set a configuration value and persist to file.
    
    Updates the configuration value and immediately writes the entire
    configuration to the file. Creates the section if it doesn't exist.
    
    Args:
        section: Section name (e.g., "audio").
        option: Option name within the section (e.g., "volume").
        value: New value to set. Will be converted to string for storage.
    
    Warns:
        Logs a warning if the key is not defined in the prototype.
    """
    try:
      prototype[section][option]
    except KeyError:
      Log.warn("Config key %s.%s not defined while writing." % (section, option))
    
    if not self.config.has_section(section):
      self.config.add_section(section)

    if type(value) == str:
      value = value
    else:
      value = str(value)

    self.config.set(section, option, value)
    
    f = open(self.fileName, "w")
    self.config.write(f)
    f.close()

def get(section, option):
  """Read a value from the global configuration.
  
  Convenience function to access the default global configuration
  instance. Requires that load() was called with setAsDefault=True.
  
  Args:
      section: Section name (e.g., "audio").
      option: Option name within the section (e.g., "volume").
  
  Returns:
      The configuration value, converted to its defined type.
  
  Raises:
      AttributeError: If no global configuration has been loaded.
  """
  global config
  return config.get(section, option)
  
def set(section, option, value):
  """Write a value to the global configuration.
  
  Convenience function to modify the default global configuration
  instance. Requires that load() was called with setAsDefault=True.
  
  Args:
      section: Section name (e.g., "audio").
      option: Option name within the section (e.g., "volume").
      value: New value to set.
  
  Raises:
      AttributeError: If no global configuration has been loaded.
  """
  global config
  config.set(section, option, value)
