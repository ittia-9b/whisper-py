#!/bin/bash

# Whisper Py Setup Script
# This script automates the setup process for the Whisper Py application.

# Function to print messages
log() {
    echo "[INFO] $1"
}

error_exit() {
    echo "[ERROR] $1" >&2
    exit 1
}

# --- Pre-flight Checks ---
log "Starting Whisper Py setup..."

# Check for Python 3.8+
log "Checking for Python 3.8+..."
if ! command -v python3 &> /dev/null; then
    error_exit "Python 3 is not installed. Please install Python 3.8 or higher."
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_PYTHON_VERSION="3.8"
if [ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON_VERSION" ]; then 
    error_exit "Python version $PYTHON_VERSION found, but $REQUIRED_PYTHON_VERSION or higher is required."
fi
log "Python version $PYTHON_VERSION found."

# Check for pip
log "Checking for pip..."
if ! python3 -m pip --version &> /dev/null; then
    error_exit "pip for Python 3 is not installed. Please ensure pip is installed for your Python 3 distribution."
fi
log "pip found."

# Get Project Directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log "Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR" || error_exit "Could not change to project directory."

# --- Virtual Environment Setup ---
log "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv || error_exit "Failed to create virtual environment."
    log "Virtual environment created."
else
    log "Virtual environment 'venv' already exists."
fi

# Activate virtual environment (for this script's context)
source "$PROJECT_DIR/venv/bin/activate" || error_exit "Failed to activate virtual environment."
log "Virtual environment activated."

# --- Install Python Dependencies ---
log "Installing Python dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt || error_exit "Failed to install Python dependencies."
log "Python dependencies installed successfully."

# --- Install System Dependencies (Debian/Ubuntu specific for Qt) ---
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [[ "$ID" == "ubuntu" || "$ID" == "debian" ]]; then
        log "Detected Ubuntu/Debian. Checking for Qt system dependencies..."
        QT_DEPS="libxcb-xinerama0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxcb-xkb1 libxkbcommon-x11-0"
        PACKAGES_TO_INSTALL=""
        for pkg in $QT_DEPS; do
            if ! dpkg -s "$pkg" &> /dev/null; then
                PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $pkg"
            fi
        done

        if [ -n "$PACKAGES_TO_INSTALL" ]; then
            log "The following Qt system dependencies are missing: $PACKAGES_TO_INSTALL"
            read -p "Do you want to install them using sudo apt-get install? (y/N): " -n 1 -r
            echo # Move to a new line
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                sudo apt-get update || error_exit "Failed to run apt-get update."
                sudo apt-get install -y $PACKAGES_TO_INSTALL || error_exit "Failed to install Qt system dependencies."
                log "Qt system dependencies installed successfully."
            else
                log "Skipping installation of Qt system dependencies. The application might not run correctly."
            fi
        else
            log "Required Qt system dependencies are already installed."
        fi
    else
        log "Skipping automatic system dependency installation for non-Debian/Ubuntu system. Please ensure Qt dependencies are met manually."
    fi
else
    log "Cannot determine OS type. Skipping automatic system dependency installation."
fi

# --- API Key Setup ---
log "Setting up OpenAI API key..."
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    log "'.env' file not found. Copying from '.env.example'..."
    cp .env.example .env || error_exit "Failed to copy .env.example to .env"
fi

if [ -f ".env" ]; then
    if grep -q "your_openai_api_key_here" .env || ! grep -q "OPENAI_API_KEY=" .env; then
        read -p "Please enter your OpenAI API key: " OPENAI_API_KEY
        # Escape special characters in API key for sed
        ESCAPED_API_KEY=$(printf '%s\n' "$OPENAI_API_KEY" | sed 's/[&\/\\|]/\\&/g')
        if grep -q "OPENAI_API_KEY=" .env; then 
            sed -i "s/^OPENAI_API_KEY=.*/OPENAI_API_KEY=$ESCAPED_API_KEY/" .env || error_exit "Failed to update API key in .env"
        else
            echo "OPENAI_API_KEY=$ESCAPED_API_KEY" >> .env || error_exit "Failed to add API key to .env"
        fi
        log "OpenAI API key saved to .env file."
    else
        log "OpenAI API key already configured in .env file."
    fi
else
    log "'.env' file not found and '.env.example' is missing. Please create a '.env' file with your OPENAI_API_KEY."
fi

# --- Desktop Integration ---
log "Setting up desktop integration..."

# Make launch-whisper.sh executable
if [ -f "launch-whisper.sh" ]; then
    chmod +x launch-whisper.sh || error_exit "Failed to make launch-whisper.sh executable."
    log "'launch-whisper.sh' is now executable."
else
    log "'launch-whisper.sh' not found. Skipping this step."
fi

# Create .desktop file
DESKTOP_FILE_DIR="$HOME/.local/share/applications"
DESKTOP_FILE_PATH="$DESKTOP_FILE_DIR/whisper-py.desktop"

mkdir -p "$DESKTOP_FILE_DIR" # Ensure directory exists

log "Creating desktop entry at $DESKTOP_FILE_PATH..."

cat << EOF > "$DESKTOP_FILE_PATH"
[Desktop Entry]
Type=Application
Name=Whisper Py Voice Typing
Comment=Voice-to-text system tray app using OpenAI Whisper
Exec=$PROJECT_DIR/launch-whisper.sh
Icon=$PROJECT_DIR/mic2-white.png
Terminal=false
Categories=Utility;AudioVideo;Audio;
Keywords=whisper;speech;text;transcription;voice typing;
StartupNotify=true
EOF

if [ $? -eq 0 ]; then
    log "Desktop entry created successfully."
    # Update desktop database
    log "Updating desktop database..."
    update-desktop-database "$DESKTOP_FILE_DIR" || log "Failed to update desktop database. You may need to run 'update-desktop-database $DESKTOP_FILE_DIR' manually."
    log "Desktop database updated."
else
    error_exit "Failed to create desktop entry file."
fi

log "Setup complete!"
log "To run the application, you can now find 'Whisper Py Voice Typing' in your applications menu, or run '$PROJECT_DIR/launch-whisper.sh' directly."
log "If you didn't set up your API key, the app will prompt you or you can edit the .env file."
