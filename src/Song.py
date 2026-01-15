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
Song and music data management module for Frets on Fire.

This module handles all aspects of song loading, storage, and playback control.
It provides functionality for:

- Loading and parsing MIDI note files for guitar tracks
- Managing song metadata (artist, name, delay, highscores) via INI files
- Handling multiple difficulty levels (Supaeasy, Easy, Medium, Amazing)
- Tracking note events with timing, length, and special attributes
- Supporting tappable note detection based on timing rules
- Managing audio tracks (song, guitar, rhythm) and their synchronization
- Reading/writing song scripts for text and picture events

Difficulty Levels:
    AMAZING_DIFFICULTY (0): Hardest difficulty with all notes
    MEDIUM_DIFFICULTY (1): Moderate difficulty
    EASY_DIFFICULTY (2): Easier gameplay
    SUPAEASY_DIFFICULTY (3): Beginner-friendly difficulty

MIDI Note Mapping:
    Notes are mapped from MIDI pitch values to game fret positions (0-4)
    based on difficulty-specific pitch ranges defined in noteMap.

Typical usage::

    song = loadSong(engine, "mysong", library="songs")
    song.play()
    track = song.track  # Get current difficulty track
    events = track.getEvents(startTime, endTime)
"""

import midi
import Log
import Audio
from configparser import ConfigParser
import os
import re
import shutil
import Config
import hashlib
import binascii
import pickle
# import Cerealizer
import urllib.request, urllib.parse, urllib.error
import Version
import Theme
from Language import _
from functools import reduce

DEFAULT_LIBRARY         = "songs"

AMAZING_DIFFICULTY      = 0
MEDIUM_DIFFICULTY       = 1
EASY_DIFFICULTY         = 2
SUPAEASY_DIFFICULTY     = 3

class Difficulty:
  """
  Represents a game difficulty level.

  Difficulty levels determine which notes are included in gameplay
  and map to specific MIDI pitch ranges in the note file.

  Attributes:
      id: Integer identifier for the difficulty (0=Amazing, 1=Medium,
          2=Easy, 3=Supaeasy).
      text: Localized display name for the difficulty level.
  """

  def __init__(self, id, text):
    """Initialize a Difficulty instance.

    Args:
        id: Integer identifier for this difficulty level.
        text: Human-readable name for display.
    """
    self.id   = id
    self.text = text
    
  def __str__(self):
    return self.text

  def __repr__(self):
    return self.text

difficulties = {
  SUPAEASY_DIFFICULTY: Difficulty(SUPAEASY_DIFFICULTY, _("Supaeasy")),
  EASY_DIFFICULTY:     Difficulty(EASY_DIFFICULTY,     _("Easy")),
  MEDIUM_DIFFICULTY:   Difficulty(MEDIUM_DIFFICULTY,   _("Medium")),
  AMAZING_DIFFICULTY:  Difficulty(AMAZING_DIFFICULTY,  _("Amazing")),
}

class SongInfo(object):
  """
  Container for song metadata loaded from a song.ini file.

  Manages all song information including name, artist, highscores,
  delay settings, and available difficulties. Highscores are stored
  with SHA1 hash verification to prevent tampering.

  Attributes:
      songName: Directory name of the song (used as identifier).
      fileName: Full path to the song.ini file.
      info: ConfigParser instance for reading/writing INI data.
      highScores: Dictionary mapping Difficulty to list of (score, stars, name) tuples.
      tutorial: Boolean property indicating if this is a tutorial song.
      name: Song title from metadata.
      artist: Artist name from metadata.
      delay: Audio delay offset in milliseconds.
      difficulties: List of available Difficulty objects for this song.
      cassetteColor: Theme color for the song's cassette representation.
  """

  def __init__(self, infoFileName):
    """Initialize SongInfo from a song.ini file.

    Args:
        infoFileName: Path to the song.ini configuration file.
    """
    self.songName      = os.path.basename(os.path.dirname(infoFileName))
    self.fileName      = infoFileName
    self.info          = ConfigParser()
    self._difficulties = None

    try:
      self.info.read(infoFileName)
    except:
      pass
      
    # Read highscores and verify their hashes.
    # There ain't no security like security throught obscurity :)
    self.highScores = {}
    
    scores = self._get("scores", str, "")
    if scores:
      try:
        scores = pickle.loads(binascii.unhexlify(scores))
        for difficulty in list(scores.keys()):
          try:
            difficulty = difficulties[difficulty]
          except KeyError:
            continue
          for score, stars, name, hash in scores[difficulty.id]:
            if self.getScoreHash(difficulty, score, stars, name) == hash:
              self.addHighscore(difficulty, score, stars, name)
            else:
              Log.warn("Weak hack attempt detected. Better luck next time.")
      except Exception as e:
        # Could not load old scores (likely old serialization format)
        Log.warn("Could not load saved scores: %s" % str(e))

  def _set(self, attr, value):
    if not self.info.has_section("song"):
      self.info.add_section("song")
    # In Python 3, configparser requires string values
    if not isinstance(value, str):
      value = str(value)
    self.info.set("song", attr, value)
    
  def getObfuscatedScores(self):
    s = {}
    for difficulty in list(self.highScores.keys()):
      s[difficulty.id] = [(score, stars, name, self.getScoreHash(difficulty, score, stars, name)) for score, stars, name in self.highScores[difficulty]]
    return binascii.hexlify(pickle.dumps(s))

  def save(self):
    self._set("scores", self.getObfuscatedScores())
    
    f = open(self.fileName, "w")
    self.info.write(f)
    f.close()
    
  def _get(self, attr, type = None, default = ""):
    try:
      v = self.info.get("song", attr)
    except:
      v = default
    if v is not None and type:
      v = type(v)
    return v

  def getDifficulties(self):
    """Get available difficulty levels for this song.

    Parses the MIDI note file to determine which difficulties have notes.
    Tutorial songs only return MEDIUM_DIFFICULTY. Results are cached
    after first call.

    Returns:
        List of Difficulty objects available for this song, sorted by
        difficulty ID in descending order (hardest first).
    """
    # Tutorials only have the medium difficulty
    if self.tutorial:
      return [difficulties[MEDIUM_DIFFICULTY]]

    if self._difficulties is not None:
      return self._difficulties

    # See which difficulties are available
    try:
      noteFileName = os.path.join(os.path.dirname(self.fileName), "notes.mid")
      info = MidiInfoReader()
      midiIn = midi.MidiInFile(info, noteFileName)
      try:
        midiIn.read()
      except MidiInfoReader.Done:
        pass
      info.difficulties.sort(key=lambda x: x.id, reverse=True)
      self._difficulties = info.difficulties
    except:
      self._difficulties = list(difficulties.values())
    
    # If no difficulties found (empty MIDI), return all difficulties as fallback
    if not self._difficulties:
      self._difficulties = list(difficulties.values())
    
    return self._difficulties

  def getName(self):
    return self._get("name")

  def setName(self, value):
    self._set("name", value)

  def getArtist(self):
    return self._get("artist")

  def getCassetteColor(self):
    c = self._get("cassettecolor")
    if c:
      return Theme.hexToColor(c)
  
  def setCassetteColor(self, color):
    self._set("cassettecolor", Theme.colorToHex(color))
  
  def setArtist(self, value):
    self._set("artist", value)
    
  def getScoreHash(self, difficulty, score, stars, name):
    return hashlib.sha1(("%d%d%d%s" % (difficulty.id, score, stars, name)).encode('utf-8')).hexdigest()
    
  def getDelay(self):
    return self._get("delay", int, 0)
    
  def setDelay(self, value):
    return self._set("delay", value)
    
  def getHighscores(self, difficulty):
    try:
      return self.highScores[difficulty]
    except KeyError:
      return []

  def uploadHighscores(self, url, songHash):
    try:
      d = {
        "songName": self.songName,
        "songHash": songHash,
        "scores":   self.getObfuscatedScores(),
        "version":  Version.version()
      }
      data = urllib.request.urlopen(url + "?" + urllib.parse.urlencode(d)).read()
      Log.debug("Score upload result: %s" % data)
      if ";" in data:
        fields = data.split(";")
      else:
        fields = [data, "0"]
      return (fields[0] == "True", int(fields[1]))
    except Exception as e:
      Log.error(e)
      return (False, 0)
  
  def addHighscore(self, difficulty, score, stars, name):
    """Add a new highscore entry for the given difficulty.

    Maintains a sorted list of top 5 scores per difficulty.

    Args:
        difficulty: Difficulty object for this score.
        score: Integer score value.
        stars: Integer star rating (0-5).
        name: Player name string.

    Returns:
        Integer position (0-4) if score made top 5, -1 otherwise.
    """
    if not difficulty in self.highScores:
      self.highScores[difficulty] = []
    self.highScores[difficulty].append((score, stars, name))
    # Sort by score descending (Python 3 uses key= instead of cmp=)
    self.highScores[difficulty].sort(key=lambda x: -x[0])
    self.highScores[difficulty] = self.highScores[difficulty][:5]
    for i, scores in enumerate(self.highScores[difficulty]):
      _score, _stars, _name = scores
      if _score == score and _stars == stars and _name == name:
        return i
    return -1

  def isTutorial(self):
    return self._get("tutorial", int, 0) == 1
    
  name          = property(getName, setName)
  artist        = property(getArtist, setArtist)
  delay         = property(getDelay, setDelay)
  tutorial      = property(isTutorial)
  difficulties  = property(getDifficulties)
  cassetteColor = property(getCassetteColor, setCassetteColor)

class LibraryInfo(object):
  def __init__(self, libraryName, infoFileName):
    self.libraryName   = libraryName
    self.fileName      = infoFileName
    self.info          = ConfigParser()
    self.songCount     = 0

    try:
      self.info.read(infoFileName)
    except:
      pass

    # Set a default name
    if not self.name:
      self.name = os.path.basename(os.path.dirname(self.fileName))

    # Count the available songs
    libraryRoot = os.path.dirname(self.fileName)
    for name in os.listdir(libraryRoot):
      if not os.path.isdir(os.path.join(libraryRoot, name)) or name.startswith("."):
        continue
      if os.path.isfile(os.path.join(libraryRoot, name, "song.ini")):
        self.songCount += 1

  def _set(self, attr, value):
    if not self.info.has_section("library"):
      self.info.add_section("library")
    if type(value) == str:
      value = value.encode(Config.encoding)
    else:
      value = str(value)
    self.info.set("library", attr, value)
    
  def save(self):
    f = open(self.fileName, "w")
    self.info.write(f)
    f.close()
    
  def _get(self, attr, type = None, default = ""):
    try:
      v = self.info.get("library", attr)
    except:
      v = default
    if v is not None and type:
      v = type(v)
    return v

  def getName(self):
    return self._get("name")

  def setName(self, value):
    self._set("name", value)

  def getColor(self):
    c = self._get("color")
    if c:
      return Theme.hexToColor(c)
  
  def setColor(self, color):
    self._set("color", Theme.colorToHex(color))
    
    
  name          = property(getName, setName)
  color         = property(getColor, setColor)

class Event:
  """
  Base class for all timed events in a song track.

  Events represent things that happen at specific times during playback,
  such as notes, tempo changes, text displays, or picture overlays.

  Attributes:
      length: Duration of the event in milliseconds.
  """

  def __init__(self, length):
    """Initialize an Event with the given duration.

    Args:
        length: Duration in milliseconds.
    """
    self.length = length

class Note(Event):
  """
  Represents a playable note in a guitar track.

  Notes correspond to fret buttons the player must press. They have
  timing, duration, and can be marked as special (star power) or
  tappable (hammer-on/pull-off).

  Attributes:
      number: Fret number (0-4) corresponding to guitar buttons.
      length: Duration the note is held in milliseconds.
      played: Boolean indicating if the note has been successfully hit.
      special: Boolean for star power notes (MIDI velocity 127).
      tappable: Boolean for hammer-on/pull-off notes (set by Track.update).
  """

  def __init__(self, number, length, special = False, tappable = False):
    """Initialize a Note event.

    Args:
        number: Fret number (0-4).
        length: Note duration in milliseconds.
        special: Whether this is a star power note.
        tappable: Whether this note can be tapped (usually set later).
    """
    Event.__init__(self, length)
    self.number   = number
    self.played   = False
    self.special  = special
    self.tappable = tappable
    
  def __repr__(self):
    return "<#%d>" % self.number

class Tempo(Event):
  def __init__(self, bpm):
    Event.__init__(self, 0)
    self.bpm = bpm
    
  def __repr__(self):
    return "<%d bpm>" % self.bpm

class TextEvent(Event):
  def __init__(self, text, length):
    Event.__init__(self, length)
    self.text = text

  def __repr__(self):
    return "<%s>" % self.text

class PictureEvent(Event):
  def __init__(self, fileName, length):
    Event.__init__(self, length)
    self.fileName = fileName
    
class Track:
  """
  Container for events at a specific difficulty level.

  Tracks store notes and other events with efficient time-based retrieval
  using a granular bucket system. Each track corresponds to one difficulty.

  Attributes:
      granularity: Time bucket size in milliseconds for event indexing.
      events: List of event buckets for fast time-range queries.
      allEvents: List of all (time, event) tuples in insertion order.
  """

  granularity = 50
  
  def __init__(self):
    """Initialize an empty Track."""
    self.events = []
    self.allEvents = []

  def addEvent(self, time, event):
    """Add an event to the track at the specified time.

    Events are indexed into time buckets based on granularity for
    efficient range queries. Long events span multiple buckets.

    Args:
        time: Start time in milliseconds.
        event: Event object to add (Note, Tempo, TextEvent, etc.).
    """
    for t in range(int(time / self.granularity), int((time + event.length) / self.granularity) + 1):
      if len(self.events) < t + 1:
        n = t + 1 - len(self.events)
        n *= 8
        self.events = self.events + [[] for n in range(n)]
      self.events[t].append((time - (t * self.granularity), event))
    self.allEvents.append((time, event))

  def removeEvent(self, time, event):
    for t in range(int(time / self.granularity), int((time + event.length) / self.granularity) + 1):
      e = (time - (t * self.granularity), event)
      if t < len(self.events) and e in self.events[t]:
        self.events[t].remove(e)
    if (time, event) in self.allEvents:
      self.allEvents.remove((time, event))

  def getEvents(self, startTime, endTime):
    """Retrieve all events within a time range.

    Uses the granular bucket index for efficient lookups.

    Args:
        startTime: Start of time range in milliseconds.
        endTime: End of time range in milliseconds.

    Returns:
        Set of (time, event) tuples for events active in the range.
    """
    t1, t2 = [int(x) for x in [startTime / self.granularity, endTime / self.granularity]]
    if t1 > t2:
      t1, t2 = t2, t1

    events = set()
    for t in range(max(t1, 0), min(len(self.events), t2)):
      for diff, event in self.events[t]:
        time = (self.granularity * t) + diff
        events.add((time, event))
    return events

  def getAllEvents(self):
    return self.allEvents

  def reset(self):
    for eventList in self.events:
      for time, event in eventList:
        if isinstance(event, Note):
          event.played = False

  def update(self):
    """Update track state, marking tappable notes.

    Analyzes all notes to determine which can be played as hammer-ons
    or pull-offs (tappable). A note is tappable if:
    
    1. It is not the first note of the track
    2. The previous note is different from this one
    3. The previous note is not a chord (single note only)
    4. The previous note ends within 161 ticks of this note's start

    This method should be called after all notes are loaded.
    """
    # Determine which notes are tappable. The rules are:
    #  1. Not the first note of the track
    #  2. Previous note not the same as this one
    #  3. Previous note not a chord
    #  4. Previous note ends at most 161 ticks before this one
    bpm             = None
    ticksPerBeat    = 480
    tickThreshold   = 161
    prevNotes       = []
    currentNotes    = []
    currentTicks    = 0.0
    prevTicks       = 0.0
    epsilon         = 1e-3

    def beatsToTicks(time):
      return (time * bpm * ticksPerBeat) / 60000.0

    if not self.allEvents:
      return

    for time, event in self.allEvents + [self.allEvents[-1]]:
      if isinstance(event, Tempo):
        bpm = event.bpm
      elif isinstance(event, Note):
        # All notes are initially not tappable
        event.tappable = False
        ticks = beatsToTicks(time)
        
        # Part of chord?
        if ticks < currentTicks + epsilon:
          currentNotes.append(event)
          continue
        
        """
        for i in range(5):
          if i in [n.number for n in prevNotes]:
            print " # ",
          else:
            print " . ",
        print " | ",
        for i in range(5):
          if i in [n.number for n in currentNotes]:
            print " # ",
          else:
            print " . ",
        print
        """

        # Previous note not a chord?
        if len(prevNotes) == 1:
          # Previous note ended recently enough?
          prevEndTicks = prevTicks + beatsToTicks(prevNotes[0].length)
          if currentTicks - prevEndTicks <= tickThreshold:
            for note in currentNotes:
              # Are any current notes the same as the previous one?
              if note.number == prevNotes[0].number:
                break
            else:
              # If all the notes are different, mark the current notes tappable
              for note in currentNotes:
                note.tappable = True

        # Set the current notes as the previous notes
        prevNotes    = currentNotes
        prevTicks    = currentTicks
        currentNotes = [event]
        currentTicks = ticks

class Song(object):
  """
  Main song class managing audio playback and note tracks.

  Coordinates loading of audio files (song, guitar, rhythm tracks),
  MIDI note data, and script events. Provides playback control and
  timing synchronization for gameplay.

  Attributes:
      engine: Game engine reference for resource access.
      info: SongInfo object with metadata.
      tracks: List of Track objects, one per difficulty level.
      difficulty: Currently selected Difficulty object.
      bpm: Beats per minute for timing calculations.
      period: Milliseconds per beat (60000 / bpm).
      music: Main Audio.Music object for song playback.
      guitarTrack: Optional Audio.StreamingSound for guitar audio.
      rhythmTrack: Optional Audio.StreamingSound for rhythm/bass audio.
      noteFileName: Path to the MIDI notes file.
      track: Property returning the Track for current difficulty.
  """

  def __init__(self, engine, infoFileName, songTrackName, guitarTrackName, rhythmTrackName, noteFileName, scriptFileName = None):
    """Initialize a Song from audio and note files.

    Args:
        engine: Game engine instance.
        infoFileName: Path to song.ini file.
        songTrackName: Path to main song audio file.
        guitarTrackName: Path to guitar audio file (optional).
        rhythmTrackName: Path to rhythm audio file (optional).
        noteFileName: Path to MIDI notes file.
        scriptFileName: Path to script.txt for text/picture events (optional).
    """
    self.engine        = engine
    self.info          = SongInfo(infoFileName)
    self.tracks        = [Track() for t in range(len(difficulties))]
    self.difficulty    = difficulties[AMAZING_DIFFICULTY]
    self._playing      = False
    self.start         = 0.0
    self.noteFileName  = noteFileName
    self.bpm           = None
    self.period        = 0

    # load the tracks
    if songTrackName:
      self.music       = Audio.Music(songTrackName)

    self.guitarTrack = None
    self.rhythmTrack = None

    try:
      if guitarTrackName:
        self.guitarTrack = Audio.StreamingSound(self.engine, self.engine.audio.getChannel(1), guitarTrackName)
    except Exception as e:
      Log.warn("Unable to load guitar track: %s" % e)

    try:
      if rhythmTrackName:
        self.rhythmTrack = Audio.StreamingSound(self.engine, self.engine.audio.getChannel(2), rhythmTrackName)
    except Exception as e:
      Log.warn("Unable to load rhythm track: %s" % e)
	
    # load the notes
    if noteFileName:
      midiIn = midi.MidiInFile(MidiReader(self), noteFileName)
      midiIn.read()

    # load the script
    if scriptFileName and os.path.isfile(scriptFileName):
      scriptReader = ScriptReader(self, open(scriptFileName))
      scriptReader.read()

    # update all note tracks
    for track in self.tracks:
      track.update()

  def getHash(self):
    h = hashlib.sha1()
    f = open(self.noteFileName, "rb")
    bs = 1024
    while True:
      data = f.read(bs)
      if not data: break
      h.update(data)
    return h.hexdigest()
  
  def setBpm(self, bpm):
    self.bpm    = bpm
    self.period = 60000.0 / self.bpm

  def save(self):
    self.info.save()
    f = open(self.noteFileName + ".tmp", "wb")
    midiOut = MidiWriter(self, midi.MidiOutFile(f))
    midiOut.write()
    f.close()

    # Rename the output file after it has been succesfully written
    shutil.move(self.noteFileName + ".tmp", self.noteFileName)

  def play(self, start = 0.0):
    """Start playing the song from the specified position.

    Args:
        start: Start position in milliseconds. Note: guitar and rhythm
               tracks only support starting from 0.0.
    """
    self.start = start
    self.music.play(0, start / 1000.0)
    if self.guitarTrack:
      assert start == 0.0
      self.guitarTrack.play()
    if self.rhythmTrack:
      assert start == 0.0
      self.rhythmTrack.play()
    self._playing = True

  def pause(self):
    self.music.pause()
    self.engine.audio.pause()

  def unpause(self):
    self.music.unpause()
    self.engine.audio.unpause()

  def setGuitarVolume(self, volume):
    if not self.rhythmTrack:
      volume = max(.1, volume)
    if self.guitarTrack:
      self.guitarTrack.setVolume(volume)
    else:
      self.music.setVolume(volume)

  def setRhythmVolume(self, volume):
    if self.rhythmTrack:
      self.rhythmTrack.setVolume(volume)
  
  def setBackgroundVolume(self, volume):
    self.music.setVolume(volume)
  
  def stop(self):
    """Stop playback and reset all tracks.

    Resets played state of all notes and rewinds audio to beginning.
    """
    for track in self.tracks:
      track.reset()
      
    self.music.stop()
    self.music.rewind()
    if self.guitarTrack:
      self.guitarTrack.stop()
    if self.rhythmTrack:
      self.rhythmTrack.stop()
    self._playing = False

  def fadeout(self, time):
    for track in self.tracks:
      track.reset()
      
    self.music.fadeout(time)
    if self.guitarTrack:
      self.guitarTrack.fadeout(time)
    if self.rhythmTrack:
      self.rhythmTrack.fadeout(time)
    self._playing = False

  def getPosition(self):
    if not self._playing:
      pos = 0.0
    else:
      pos = self.music.getPosition()
    if pos < 0.0:
      pos = 0.0
    return pos + self.start

  def isPlaying(self):
    return self._playing and self.music.isPlaying()

  def getBeat(self):
    return self.getPosition() / self.period

  def update(self, ticks):
    pass

  def getTrack(self):
    return self.tracks[self.difficulty.id]

  track = property(getTrack)

noteMap = {     # difficulty, note
  0x60: (AMAZING_DIFFICULTY,  0),
  0x61: (AMAZING_DIFFICULTY,  1),
  0x62: (AMAZING_DIFFICULTY,  2),
  0x63: (AMAZING_DIFFICULTY,  3),
  0x64: (AMAZING_DIFFICULTY,  4),
  0x54: (MEDIUM_DIFFICULTY,   0),
  0x55: (MEDIUM_DIFFICULTY,   1),
  0x56: (MEDIUM_DIFFICULTY,   2),
  0x57: (MEDIUM_DIFFICULTY,   3),
  0x58: (MEDIUM_DIFFICULTY,   4),
  0x48: (EASY_DIFFICULTY,     0),
  0x49: (EASY_DIFFICULTY,     1),
  0x4a: (EASY_DIFFICULTY,     2),
  0x4b: (EASY_DIFFICULTY,     3),
  0x4c: (EASY_DIFFICULTY,     4),
  0x3c: (SUPAEASY_DIFFICULTY, 0),
  0x3d: (SUPAEASY_DIFFICULTY, 1),
  0x3e: (SUPAEASY_DIFFICULTY, 2),
  0x3f: (SUPAEASY_DIFFICULTY, 3),
  0x40: (SUPAEASY_DIFFICULTY, 4),
}

reverseNoteMap = dict([(v, k) for k, v in list(noteMap.items())])

class MidiWriter:
  """
  Writes song note data to a MIDI file.

  Converts internal Note events back to MIDI format for saving
  edited songs. Handles tempo and note timing conversions.

  Attributes:
      song: Song object to write.
      out: midi.MidiOutFile output stream.
      ticksPerBeat: MIDI time resolution (default 480).
  """

  def __init__(self, song, out):
    """Initialize MidiWriter for the given song.

    Args:
        song: Song object containing tracks to write.
        out: midi.MidiOutFile instance for output.
    """
    self.song         = song
    self.out          = out
    self.ticksPerBeat = 480

  def midiTime(self, time):
    return int(self.song.bpm * self.ticksPerBeat * time / 60000.0)

  def write(self):
    self.out.header(division = self.ticksPerBeat)
    self.out.start_of_track()
    self.out.update_time(0)
    if self.song.bpm:
      self.out.tempo(int(60.0 * 10.0**6 / self.song.bpm))
    else:
      self.out.tempo(int(60.0 * 10.0**6 / 122.0))

    # Collect all events
    events = [list(zip([difficulty] * len(track.getAllEvents()), track.getAllEvents())) for difficulty, track in enumerate(self.song.tracks)]
    events = reduce(lambda a, b: a + b, events)
    # Sort by time ascending (Python 3 uses key= instead of cmp=)
    events.sort(key=lambda x: x[1][0])
    heldNotes = []

    for difficulty, event in events:
      time, event = event
      if isinstance(event, Note):
        time = self.midiTime(time)

        # Turn of any held notes that were active before this point in time
        for note, endTime in list(heldNotes):
          if endTime <= time:
            self.out.update_time(endTime, relative = 0)
            self.out.note_off(0, note)
            heldNotes.remove((note, endTime))

        note = reverseNoteMap[(difficulty, event.number)]
        self.out.update_time(time, relative = 0)
        self.out.note_on(0, note, event.special and 127 or 100)
        heldNotes.append((note, time + self.midiTime(event.length)))
        # Sort by endTime ascending (Python 3 uses key= instead of cmp=)
        heldNotes.sort(key=lambda x: x[1])

    # Turn of any remaining notes
    for note, endTime in heldNotes:
      self.out.update_time(endTime, relative = 0)
      self.out.note_off(0, note)
      
    self.out.update_time(0)
    self.out.end_of_track()
    self.out.eof()
    self.out.write()

class ScriptReader:
  def __init__(self, song, scriptFile):
    self.song = song
    self.file = scriptFile

  def read(self):
    for line in self.file:
      if line.startswith("#"): continue
      time, length, type, data = re.split("[\t ]+", line.strip(), 3)
      time   = float(time)
      length = float(length)

      if type == "text":
        event = TextEvent(data, length)
      elif type == "pic":
        event = PictureEvent(data, length)
      else:
        continue

      for track in self.song.tracks:
        track.addEvent(time, event)

class MidiReader(midi.MidiOutStream):
  """
  Parses MIDI files to extract note and tempo data.

  Extends midi.MidiOutStream to receive MIDI events and convert them
  to game Note objects. Handles tempo changes and note timing with
  proper BPM scaling.

  Attributes:
      song: Song object to populate with parsed events.
      heldNotes: Dict tracking currently held notes for note-off matching.
      velocity: Dict storing note velocities for special note detection.
      ticksPerBeat: MIDI time resolution from file header.
      tempoMarkers: List of (tick, bpm) tuples for tempo changes.
  """

  def __init__(self, song):
    """Initialize MidiReader for the given song.

    Args:
        song: Song object to populate with parsed MIDI data.
    """
    midi.MidiOutStream.__init__(self)
    self.song = song
    self.heldNotes = {}
    self.velocity  = {}
    self.ticksPerBeat = 480
    self.tempoMarkers = []

  def addEvent(self, track, event, time = None):
    if time is None:
      time = self.abs_time()
    assert time >= 0
    if track is None:
      for t in self.song.tracks:
        t.addEvent(time, event)
    elif track < len(self.song.tracks):
      self.song.tracks[track].addEvent(time, event)

  def abs_time(self):
    def ticksToBeats(ticks, bpm):
      return (60000.0 * ticks) / (bpm * self.ticksPerBeat)
      
    if self.song.bpm:
      currentTime = midi.MidiOutStream.abs_time(self)

      # Find out the current scaled time.
      # Yeah, this is reeally slow, but fast enough :)
      scaledTime      = 0.0
      tempoMarkerTime = 0.0
      currentBpm      = self.song.bpm
      for i, marker in enumerate(self.tempoMarkers):
        time, bpm = marker
        if time > currentTime:
          break
        scaledTime += ticksToBeats(time - tempoMarkerTime, currentBpm)
        tempoMarkerTime, currentBpm = time, bpm
      return scaledTime + ticksToBeats(currentTime - tempoMarkerTime, currentBpm)
    return 0.0

  def header(self, format, nTracks, division):
    self.ticksPerBeat = division
    
  def tempo(self, value):
    bpm = 60.0 * 10.0**6 / value
    self.tempoMarkers.append((midi.MidiOutStream.abs_time(self), bpm))
    if not self.song.bpm:
      self.song.setBpm(bpm)
    self.addEvent(None, Tempo(bpm))

  def note_on(self, channel, note, velocity):
    if self.get_current_track() > 1: return
    self.velocity[note] = velocity
    self.heldNotes[(self.get_current_track(), channel, note)] = self.abs_time()

  def note_off(self, channel, note, velocity):
    if self.get_current_track() > 1: return
    try:
      startTime = self.heldNotes[(self.get_current_track(), channel, note)]
      endTime   = self.abs_time()
      del self.heldNotes[(self.get_current_track(), channel, note)]
      if note in noteMap:
        track, number = noteMap[note]
        self.addEvent(track, Note(number, endTime - startTime, special = self.velocity[note] == 127), time = startTime)
      else:
        #Log.warn("MIDI note 0x%x at %d does not map to any game note." % (note, self.abs_time()))
        pass
    except KeyError:
      Log.warn("MIDI note 0x%x on channel %d ending at %d was never started." % (note, channel, self.abs_time()))
      
class MidiInfoReader(midi.MidiOutStream):
  """
  Quick MIDI scanner to detect available difficulty levels.

  Reads just enough of a MIDI file to determine which difficulties
  have notes, then raises Done exception for early termination.

  Attributes:
      difficulties: List of Difficulty objects found in the MIDI file.

  Raises:
      MidiInfoReader.Done: Raised when all difficulties are found
          to allow early exit from MIDI parsing.
  """

  # We exit via this exception so that we don't need to read the whole file in
  class Done: pass
  
  def __init__(self):
    """Initialize the MidiInfoReader."""
    midi.MidiOutStream.__init__(self)
    self.difficulties = []

  def note_on(self, channel, note, velocity):
    try:
      track, number = noteMap[note]
      diff = difficulties[track]
      if not diff in self.difficulties:
        self.difficulties.append(diff)
        if len(self.difficulties) == len(difficulties):
          raise MidiInfoReader.Done
    except KeyError:
      pass

def loadSong(engine, name, library = DEFAULT_LIBRARY, seekable = False, playbackOnly = False, notesOnly = False):
  """Load a complete song with audio and note data.

  Args:
      engine: Game engine instance for resource access.
      name: Song directory name.
      library: Library path containing the song (default: "songs").
      seekable: If True, combines guitar into song track for seeking.
      playbackOnly: If True, skips loading note data.
      notesOnly: Currently unused.

  Returns:
      Song object ready for playback.
  """
  guitarFile = engine.resource.fileName(library, name, "guitar.ogg")
  songFile   = engine.resource.fileName(library, name, "song.ogg")
  rhythmFile = engine.resource.fileName(library, name, "rhythm.ogg")
  noteFile   = engine.resource.fileName(library, name, "notes.mid", writable = True)
  infoFile   = engine.resource.fileName(library, name, "song.ini", writable = True)
  scriptFile = engine.resource.fileName(library, name, "script.txt")
  
  if seekable:
    if os.path.isfile(guitarFile) and os.path.isfile(songFile):
      # TODO: perform mixing here
      songFile   = guitarFile
      guitarFile = None
    else:
      songFile   = guitarFile
      guitarFile = None
      
  if not os.path.isfile(songFile):
    songFile   = guitarFile
    guitarFile = None
  
  if not os.path.isfile(rhythmFile):
    rhythmFile = None
  
  if playbackOnly:
    noteFile = None
  
  song       = Song(engine, infoFile, songFile, guitarFile, rhythmFile, noteFile, scriptFile)
  return song

def loadSongInfo(engine, name, library = DEFAULT_LIBRARY):
  infoFile   = engine.resource.fileName(library, name, "song.ini", writable = True)
  return SongInfo(infoFile)
  
def createSong(engine, name, guitarTrackName, backgroundTrackName, rhythmTrackName = None, library = DEFAULT_LIBRARY):
  """Create a new song from audio files.

  Creates the song directory structure and copies audio files.
  Initializes an empty MIDI notes file.

  Args:
      engine: Game engine instance for resource access.
      name: Name for the new song (used as directory name).
      guitarTrackName: Path to source guitar audio file.
      backgroundTrackName: Path to source background audio file (optional).
      rhythmTrackName: Path to source rhythm audio file (optional).
      library: Library path for the new song (default: "songs").

  Returns:
      Song object for the newly created song.
  """
  path = os.path.abspath(engine.resource.fileName(library, name, writable = True))
  os.makedirs(path)
  
  guitarFile = engine.resource.fileName(library, name, "guitar.ogg", writable = True)
  songFile   = engine.resource.fileName(library, name, "song.ogg",   writable = True)
  noteFile   = engine.resource.fileName(library, name, "notes.mid",  writable = True)
  infoFile   = engine.resource.fileName(library, name, "song.ini",   writable = True)
  
  shutil.copy(guitarTrackName, guitarFile)
  
  if backgroundTrackName:
    shutil.copy(backgroundTrackName, songFile)
  else:
    songFile   = guitarFile
    guitarFile = None

  if rhythmTrackName:
    rhythmFile = engine.resource.fileName(library, name, "rhythm.ogg", writable = True)
    shutil.copy(rhythmTrackName, rhythmFile)
  else:
    rhythmFile = None
    
  f = open(noteFile, "wb")
  m = midi.MidiOutFile(f)
  m.header()
  m.start_of_track()
  m.update_time(0)
  m.end_of_track()
  m.eof()
  m.write()
  f.close()

  song = Song(engine, infoFile, songFile, guitarFile, rhythmFile, noteFile)
  song.info.name = name
  song.save()
  
  return song

def getDefaultLibrary(engine):
  return LibraryInfo(DEFAULT_LIBRARY, engine.resource.fileName(DEFAULT_LIBRARY, "library.ini"))

def getAvailableLibraries(engine, library = DEFAULT_LIBRARY):
  # Search for libraries in both the read-write and read-only directories
  songRoots    = [engine.resource.fileName(library),
                  engine.resource.fileName(library, writable = True)]
  libraries    = []
  libraryRoots = []
  
  for songRoot in songRoots:
    for libraryRoot in os.listdir(songRoot):
      libraryRoot = os.path.join(songRoot, libraryRoot)
      if not os.path.isdir(libraryRoot):
        continue
      for name in os.listdir(libraryRoot):
        # If the directory has at least one song under it or a file called "library.ini", add it
        if os.path.isfile(os.path.join(libraryRoot, name, "song.ini")) or \
           name == "library.ini":
          if not libraryRoot in libraryRoots:
            libName = library + os.path.join(libraryRoot.replace(songRoot, ""))
            libraries.append(LibraryInfo(libName, os.path.join(libraryRoot, "library.ini")))
            libraryRoots.append(libraryRoot)
            break
  libraries.sort(key=lambda x: x.name)
  return libraries

def getAvailableSongs(engine, library = DEFAULT_LIBRARY, includeTutorials = False):
  """Get list of available songs in a library.

  Searches both read-only and writable resource directories.

  Args:
      engine: Game engine instance for resource access.
      library: Library path to search (default: "songs").
      includeTutorials: If True, includes tutorial songs in results.

  Returns:
      List of SongInfo objects sorted by name.
  """
  # Search for songs in both the read-write and read-only directories
  songRoots = [engine.resource.fileName(library), engine.resource.fileName(library, writable = True)]
  names = []
  for songRoot in songRoots:
    for name in os.listdir(songRoot):
      if not os.path.isfile(os.path.join(songRoot, name, "song.ini")) or name.startswith("."):
        continue
      if not name in names:
        names.append(name)

  songs = [SongInfo(engine.resource.fileName(library, name, "song.ini", writable = True)) for name in names]
  if not includeTutorials:
    songs = [song for song in songs if not song.tutorial]
  songs.sort(key=lambda x: x.name)
  return songs
