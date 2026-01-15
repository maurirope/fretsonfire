# -*- coding: utf-8 -*-
"""
MIDI File Reading and Writing Module.

This is the MXM Python Midi Package, bundled with Frets on Fire for MIDI
file parsing and generation. It provides classes for reading and writing
Standard MIDI Files (SMF), with event-based parsing and generation.

Key Classes:
    MidiInFile: Read and parse MIDI files with event callbacks.
    MidiOutFile: Write MIDI files with a stream-based interface.
    MidiInStream: Low-level MIDI input stream handling.
    MidiOutStream: Low-level MIDI output stream handling.
    MidiToText: Utility to convert MIDI events to text representation.

Originally from: http://www.mxm.dk/products/public/pythonmidi
Modified for Python 3 compatibility (2026).
"""

from .MidiOutStream import MidiOutStream
from .MidiOutFile import MidiOutFile
from .MidiInStream import MidiInStream
from .MidiInFile import MidiInFile
from .MidiToText import MidiToText
