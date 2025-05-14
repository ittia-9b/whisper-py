# Whisper Py Voice Typing

A hands-free, system tray speech-to-text app for Linux (Ubuntu) using OpenAI Whisper API. Hold the hotkey, speak, and have your words transcribed and auto-pasted anywhere.

## Features
- Record as long as you hold the hotkey (default: Right Alt)
- Transcription via Whisper API
- Clipboard integration and auto-paste
- System tray icon and menu
- Transcription history saved locally
- Easy setup with your own OpenAI API key

## Installation

1. **Clone the repo:**
   ```bash
   git clone https://github.com/yourusername/whisper-py.git
   cd whisper-py
   ```
2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Set up your API key:**
   - Copy `.env.example` to `.env` and add your OpenAI API key.

5. **Run the app:**
   ```bash
   python whisper-py.py
   ```

## Optional: Desktop Launcher
To launch from your system menu like any app, see the [Desktop Integration](#desktop-integration) section below.

## Requirements
- Python 3.8+
- Ubuntu (tested), should work on most Linux distros
- OpenAI API key

## Desktop Integration
Want to launch from your system menu? Create a launcher:

1. **Create `launch-whisper.sh`** (already included):
   ```bash
   #!/bin/bash
   PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
   cd "$PROJECT_DIR"
   source "$PROJECT_DIR/venv/bin/activate"
   python "$PROJECT_DIR/whisper-py.py" 2>&1 | tee "$PROJECT_DIR/whisper-launch.log"
   ```
   Make it executable:
   ```bash
   chmod +x launch-whisper.sh
   ```
2. **Create a desktop entry:**
   Create `~/.local/share/applications/whisper-py.desktop` with:
   ```ini
   [Desktop Entry]
   Type=Application
   Name=Whisper Py Voice Typing
   Comment=Voice-to-text system tray app
   Exec=/absolute/path/to/launch-whisper.sh
   Icon=/absolute/path/to/mic2-white.png
   Terminal=false
   Categories=Utility;
   ```
   Replace `/absolute/path/to/` with your real paths.
3. **Update the desktop database:**
   ```bash
   update-desktop-database ~/.local/share/applications/
   ```

## Customization
- Change the hotkey in the code if you want.
- Swap icons: both dark and light (white) versions included.

## License
MIT
