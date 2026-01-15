# Frets on Fire

[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)

Frets on Fire is a free, open-source music video game inspired by games like Guitar Hero. Play guitar with your keyboard as accurately as possible!

**Version 1.4.0** - Python 3 Port & Single-Player Refactor

## About This Version

This is a modernized port of the original Frets on Fire game:
- **Ported to Python 3** (3.8+, tested with 3.12)
- **Refactored to single-player only** (removed all networking/multiplayer code)
- **Updated dependencies** for modern systems
- **Bug fixes** for gameplay issues (pause, input handling, edge cases)

The original game was created by Unreal Voodoo (Sami Kyöstilä, Tommi Inkilä, Joonas Kerttula) in 2006-2008. This port preserves the original gameplay while making it run on current systems.

## Features

- Single-player guitar simulation
- Custom song support
- Built-in song editor
- Guitar Hero song importer
- Multiple difficulty levels
- Theme and mod support
- Cross-platform (Windows, Linux, macOS)

## Requirements

- Python 3.8 or later (tested with Python 3.12)
- pygame-ce (recommended: 2.5+) or pygame
- PyOpenGL
- Pillow
- NumPy

## Installation

1. Ensure Python 3.8+ is installed.
2. Install dependencies:
   ```bash
   pip install pygame-ce pyopengl pillow numpy
   ```
3. Clone the repository:
   ```bash
   git clone https://github.com/skyostil/fretsonfire.git
   cd fretsonfire/src
   ```
4. Run the game:
   ```bash
   python FretsOnFire.py
   ```

## Gameplay

- Use **F1-F5** keys for frets
- **Enter** for pick/strum
- **Escape** to pause
- **Arrow keys** for menus
- See readme.txt for detailed controls

## Development

Frets on Fire is open source! Contributions welcome.

- Report issues on GitHub
- Python 3.8+ required
- Use virtualenv for development

## Version History

- **1.4.0** (2026): Python 3 port, single-player refactor, modern dependencies
- **1.3.110**: Last Python 2 version, removed SVG runtime support
- See changelog.txt for full history

## License

GNU General Public License v2.0

## Credits

**Python 3 Port & Modernization:**
- Mauricio Rosell Pena (2026)

**Original Game (2006-2008):**
- Sami Kyöstilä - Game Design, Programming
- Tommi Inkilä - Music, Sound Effects  
- Joonas Kerttula - Graphics