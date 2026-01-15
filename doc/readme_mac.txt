Readme for building and running Frets on Fire on macOS
=======================================================

********************************************************************************
1. Requirements
********************************************************************************

- Python 3.8 or later (install from python.org or Homebrew)
- pip for package installation
- Xcode command line tools: xcode-select --install
- OpenGL support (built-in on macOS)

********************************************************************************
2. Installation
********************************************************************************

1. Install Python 3.8+ if not already installed:

   # Using Homebrew (recommended)
   brew install python3

   # Or download from python.org

2. Install dependencies:

   pip3 install pygame pyopengl pillow numpy

3. Clone the repository:

   git clone https://github.com/skyostil/fretsonfire.git
   cd fretsonfire/src

4. Run the game:

   python3 FretsOnFire.py

********************************************************************************
3. Troubleshooting
********************************************************************************

OpenGL Issues:
- Ensure you have the latest macOS updates
- Some Macs may need to run in compatibility mode

Audio Issues:
- Check System Preferences > Sound for output device
- pygame requires SDL audio support

Permission Issues:
- The game may need permission to access the microphone/input devices
- Grant permissions in System Preferences > Security & Privacy

********************************************************************************
4. Help
********************************************************************************

- Visit the Frets on Fire GitHub repository for issues and updates
- https://github.com/skyostil/fretsonfire

