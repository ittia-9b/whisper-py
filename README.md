<p align="center">
  <img src="mic2-white.png" alt="Whisper Py Icon" height="96">
</p>

# Whisper Py Voice Typing

A hands-free, system tray speech-to-text app for Linux using the OpenAI Whisper API. Hold the hotkey, speak, and have your words transcribed and auto-pasted anywhere.

## Features

- **Hands-Free Operation**: Start/stop transcription with simple, fixed hotkeys.
- **Whisper API Powered**: Accurate transcription via OpenAI's Whisper API.
- **System Tray Integration**: Easy access menu and visual feedback.
  - **Dynamic Icon Color**: White (idle), Red (recording), Yellow (processing).
- **Clipboard & Auto-Paste**: Transcriptions are copied and optionally auto-pasted.
- **Local History**: Transcriptions saved locally to `transcription_history.json` (never committed to git).
- **Easy API Key Management**: Set up via `.env` file or in-app settings.
- **Privacy Focused**: Your API key and history stay on your device.

## Screenshots

<p align="center">
  <img src="system-tray-menu.png" alt="System Tray Menu" width="400"><br>
  <em>System Tray Menu</em>
</p>
<p align="center">
  <img src="api-key-settings-window.png" alt="API Key Settings Window" width="400"><br>
  <em>API Key Settings Window</em>
</p>
<p align="center">
  <img src="history-window.png" alt="Transcription History Window" width="400"><br>
  <em>Transcription History Window</em>
</p>

## Prerequisites

- **Linux Distribution**: Tested on Ubuntu, should work on most modern Linux distros.
- **Python**: Version 3.8 or higher.
- **pip**: Python package installer.
- **git**: For cloning the repository.
- **OpenAI API Key**: **Required for transcription.** Obtain one from [OpenAI Platform](https://platform.openai.com/account/api-keys). Note that usage of the Whisper API will incur costs on your OpenAI account.

## Quick Start / Recommended Setup

For the easiest setup, use the provided setup script. This will guide you through the process, including dependency installation and API key configuration.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/whisper-py.git # Replace with your actual repo URL
    cd whisper-py
    ```
2.  **Run the setup script:**
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    The script will check for dependencies, set up a virtual environment, install packages, and help you configure your API key and desktop launcher.

Once setup is complete, you can find "Whisper Py Voice Typing" in your application menu or run it directly using `./launch-whisper.sh`.

## Hotkeys

-   `Alt + ,` (comma): Hold to record, release to finish/transcribe.
-   `Alt + .` (dot): Tap to toggle recording on/off.
-   `Alt + /` (slash): Tap to cancel recording/transcription.

*These hotkeys are currently hardcoded for simplicity.*

## Manual Installation

If you prefer to install manually or the setup script doesn't work for your system:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/whisper-py.git # Replace with your actual repo URL
    cd whisper-py
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Install System Dependencies:**
    Whisper Py uses PyQt5 for its interface, which may require system-level libraries. 
    -   **For Debian/Ubuntu:**
        ```bash
        sudo apt-get update
        sudo apt-get install libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0
        ```
    -   **For other distributions (e.g., Fedora, Arch):** You may need to find equivalent packages. Look for Qt5 XCB platform plugin dependencies.

5.  **Set up your API key:**
    -   Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
    -   Edit the `.env` file and add your OpenAI API key:
        ```ini
        OPENAI_API_KEY=your_openai_api_key_here
        ```
    -   Alternatively, you can set your API key via the application's Settings menu after launching it.

6.  **Run the application:**
    ```bash
    python whisper-py.py
    ```

## Desktop Integration (Manual)

If you didn't use the `setup.sh` script or want to set up the desktop launcher manually:

1.  **Ensure `launch-whisper.sh` is executable:**
    ```bash
    chmod +x launch-whisper.sh
    ```
2.  **Create a desktop entry file:**
    Create `~/.local/share/applications/whisper-py.desktop` with the following content, **replacing `/absolute/path/to/` with the actual absolute path to the `whisper-py` directory on your system**:
    ```ini
    [Desktop Entry]
    Type=Application
    Name=Whisper Py Voice Typing
    Comment=Voice-to-text system tray app using OpenAI Whisper
    Exec=/absolute/path/to/whisper-py/launch-whisper.sh
    Icon=/absolute/path/to/whisper-py/mic2-white.png
    Terminal=false
    Categories=Utility;AudioVideo;Audio;
    Keywords=whisper;speech;text;transcription;voice typing;
    StartupNotify=true
    ```
    *Example:* If `whisper-py` is in `/home/user/projects/whisper-py`, then `Exec` would be `/home/user/projects/whisper-py/launch-whisper.sh`.

3.  **Update the desktop database:**
    ```bash
    update-desktop-database ~/.local/share/applications/
    ```

## Transcription History

-   All transcriptions are saved locally to `transcription_history.json`.
-   This file is automatically excluded from git by `.gitignore`.
-   The "History" dialog in the app allows you to view and copy past transcriptions.

## Troubleshooting

-   **Qt Platform Plugin Error (xcb):** This usually means missing system dependencies for Qt. See the "Install System Dependencies" section under Manual Installation.
-   **No Sound / Recording Issues:** Ensure your microphone is correctly configured in your Linux system settings and that `sounddevice` has access to it. Check `pavucontrol` (PulseAudio Volume Control) if you're using PulseAudio.
-   **API Key Errors:** Double-check that your API key is correctly entered in the `.env` file or the app's settings. Ensure the key is active and has a payment method configured on the OpenAI platform if you've exceeded free trial limits.
-   **`launch-whisper.sh` or `setup.sh` not running:** Make sure they are executable (`chmod +x <script_name>`).

## Customization

-   **Hotkeys**: Currently hardcoded in `whisper-py.py`. You can modify them there if desired.

## License

MIT
