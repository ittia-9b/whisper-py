import sounddevice as sd
import numpy as np
import scipy.io.wavfile
import os
import openai
from dotenv import load_dotenv
import threading
import sys
import json
import datetime
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QThread, QSettings
from pynput import keyboard as pynput_keyboard
import pyautogui

load_dotenv()

fs = 16000  # sampling rate

# Global state for recording
recording_state = {
    'is_recording': False,
    'recording_buffer': None,
    'frames': [],
    'start_time': None,
    'stream': None
}


# Signal definitions
class WorkerSignals(QObject):
    # Define signals
    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(str)
    notification = pyqtSignal(str, str)
    
# Worker thread for transcription
class TranscriptionWorker(QObject):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.audio_data = None  # Will be set before run()
        self.audio_length = 0
    
    def set_audio(self, audio_data, audio_length):
        self.audio_data = audio_data
        self.audio_length = audio_length
    
    @pyqtSlot()
    def run(self):
        """Transcribe the provided audio data from buffer"""
        self.signals.started.emit()
        if self.audio_data is None:
            self.signals.error.emit("No audio data provided.")
            self.signals.finished.emit()
            return
        self.signals.notification.emit("Whisper", f"Transcribing {self.audio_length:.2f} seconds...")
        print(f"Transcribing {self.audio_length:.2f} seconds...")
        filename = "temp.wav"
        try:
            scipy.io.wavfile.write(filename, fs, self.audio_data)
            settings = QSettings()
            api_key = settings.value("openai/api_key", os.getenv("OPENAI_API_KEY", ""))
            client = openai.OpenAI(api_key=api_key)
            with open(filename, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                result = transcript.text
                self.signals.notification.emit("Whisper Result", result)
                print(f"Transcription: {result}")
                self.save_transcription(result)
        except Exception as e:
            self.signals.error.emit(str(e))
            self.signals.notification.emit("Whisper Error", str(e))
            print(f"Transcription error: {e}")
        finally:
            if os.path.exists(filename):
                os.remove(filename)
            self.signals.finished.emit()
    
    def save_transcription(self, text):
        """Save transcription to history file"""
        history_file = "transcription_history.json"
        history = []
        
        # Load existing history if file exists
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except json.JSONDecodeError:
                # If file is corrupted, start with empty history
                history = []
        
        # Add new transcription with timestamp
        history.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "text": text
        })
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

# Main application class
class TrayApp(QtWidgets.QSystemTrayIcon):
    def __init__(self, icon, parent=None):
        super().__init__(icon, parent)
        self.parent = parent
        self.setToolTip('Whisper Transcriber')
        
        # Icons for different states
        self.icons = {
            'idle': QtGui.QIcon('mic2-white.png'),
            'recording': QtGui.QIcon('mic2-red.png'),
            'processing': QtGui.QIcon('mic2-yellow.png')
        }
        
        # Set initial state
        self.update_icon('idle')
        
        # Set up system tray menu
        menu = QtWidgets.QMenu(parent)
        # Dynamic record action showing current hotkey
        self.action_record = menu.addAction("Record && Transcribe")
        self.action_record.setCheckable(True)
        self.action_record.triggered.connect(self.toggle_transcription)
        action_quit = menu.addAction('Quit')
        action_quit.triggered.connect(self.quit_application)
        action_settings = menu.addAction('Settings...')
        action_settings.triggered.connect(self.show_settings)
        action_history = menu.addAction('History...')
        action_history.triggered.connect(self.show_history)
        self.setContextMenu(menu)
        self.activated.connect(self.on_activated)
        
        # Set up thread and worker
        self.thread = QThread()
        self.worker = TranscriptionWorker()
        self.worker.moveToThread(self.thread)
        
        # Connect signals and slots
        self.worker.signals.notification.connect(self.show_notification)
        self.worker.signals.error.connect(self.handle_error)
        
        # Start the thread
        self.thread.start()
        
        # Flag to prevent multiple transcriptions at once
        self.is_transcribing = False
        
    def quit_application(self):
        """Clean up and quit"""
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        QtWidgets.QApplication.quit()

    def on_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            self.start_transcription()

    def start_transcription(self):
        """Start the transcription process"""
        if self.is_transcribing:
            # Prevent multiple simultaneous recordings
            self.show_notification("Whisper", "Already recording...")
            return
            
        self.is_transcribing = True
        
        # Connect signals for this specific run
        self.worker.signals.finished.connect(self.transcription_finished)
        
        # Update icon to processing state
        self.update_icon('processing')
        
        # Use QMetaObject.invokeMethod with a slot
        QtCore.QMetaObject.invokeMethod(self.worker, 'run', QtCore.Qt.QueuedConnection)
        
    def transcription_finished(self):
        """Handle completion of transcription"""
        self.is_transcribing = False
        
        # Disconnect to prevent multiple connections
        self.worker.signals.finished.disconnect(self.transcription_finished)
        
        # Reset icon to idle state
        self.update_icon('idle')
        
    def handle_error(self, error_msg):
        """Handle errors from the worker thread"""
        print(f"Error: {error_msg}")
        self.is_transcribing = False
        
        # Reset icon to idle state on error
        self.update_icon('idle')
        
    def show_notification(self, title, message):
        """Show a system tray notification, copy transcription to clipboard, and auto-paste if appropriate"""
        self.showMessage(title, message, QtGui.QIcon(), 3000)
        # If this is a transcription result, copy to clipboard and auto-paste
        if title == "Whisper Result" and message.strip():
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(message)
            print("Transcription copied to clipboard.")
            try:
                pyautogui.hotkey('ctrl', 'v')
                print("Auto-paste triggered.")
            except Exception as e:
                print(f"Auto-paste failed: {e}")

    def show_settings(self, checked=False):
        """Show settings dialog"""
        dialog = SettingsDialog(self.parent)
        if dialog.exec_():
            # Refresh menu label when hotkey changes
            self.update_record_action()
    
    def show_history(self, checked=False):
        """Show transcription history dialog"""
        dialog = HistoryDialog(self.parent)
        dialog.exec_()
    
    def update_record_action(self):
        """Set the record menu item label to just 'Record && Transcribe'"""
        self.action_record.setText("Record && Transcribe")
        
    def update_icon(self, state):
        """Update the system tray icon based on current state
        
        Args:
            state (str): One of 'idle', 'recording', or 'processing'
        """
        if state in self.icons:
            self.setIcon(self.icons[state])
            status_text = {
                'idle': 'Whisper Transcriber - Ready',
                'recording': 'Whisper Transcriber - Recording',
                'processing': 'Whisper Transcriber - Processing'
            }.get(state, 'Whisper Transcriber')
            self.setToolTip(status_text)

    def toggle_transcription(self, checked=False):
        """Toggle recording/transcription from tray menu."""
        if not recording_state['is_recording']:
            start_recording()
            self.update_icon('recording')
        else:
            stop_recording_and_transcribe()
            # Processing icon will be set by start_transcription

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        layout = QtWidgets.QFormLayout(self)
        self.apiKeyEdit = QtWidgets.QLineEdit(self)
        settings = QSettings()
        from os import getenv
        self.apiKeyEdit.setText(settings.value("openai/api_key", getenv("OPENAI_API_KEY", "")))
        layout.addRow("OpenAI API Key:", self.apiKeyEdit)
        # Info label for hotkeys
        info = QtWidgets.QLabel(
            "<b>Hotkeys:</b> <br>"
            "<ul>"
            "<li>Alt + , (comma): Hold to record, release to finish/transcribe</li>"
            "<li>Alt + . (dot): Tap to toggle recording on/off</li>"
            "<li>Alt + / (slash): Tap to cancel recording/transcription</li>"
            "</ul>"
            "These are not configurable."
        )
        info.setWordWrap(True)
        layout.addRow(info)
        btnBox = QtWidgets.QHBoxLayout()
        saveBtn = QtWidgets.QPushButton("Save", self)
        cancelBtn = QtWidgets.QPushButton("Cancel", self)
        btnBox.addWidget(saveBtn)
        btnBox.addWidget(cancelBtn)
        layout.addRow(btnBox)
        saveBtn.clicked.connect(self.save)
        cancelBtn.clicked.connect(self.reject)

    def save(self):
        """Save settings"""
        settings = QSettings()
        settings.setValue("openai/api_key", self.apiKeyEdit.text())
        self.accept()

# History viewer dialog
class HistoryDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transcription History")
        self.resize(700, 500)
        layout = QtWidgets.QVBoxLayout(self)
        scroll = QtWidgets.QScrollArea(self)
        scroll.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        vbox = QtWidgets.QVBoxLayout(container)

        try:
            with open('transcription_history.json', 'r') as f:
                history = json.load(f)
        except Exception:
            history = []

        for e in history:
            ts = e.get('timestamp', '')
            # Compact timestamp: YYYY-MM-DD HH:MM
            try:
                dt = datetime.datetime.fromisoformat(ts)
                ts_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                ts_str = ts[:16]
            text = e.get('text', '')
            entry_widget = QtWidgets.QWidget()
            hbox = QtWidgets.QHBoxLayout(entry_widget)
            label = QtWidgets.QLabel(f"<b>{ts_str}</b><br>{text}")
            label.setWordWrap(True)
            label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            hbox.addWidget(label)
            copy_btn = QtWidgets.QPushButton("Copy")
            copy_btn.setFixedWidth(60)
            copy_btn.clicked.connect(lambda _, t=text: QtWidgets.QApplication.clipboard().setText(t))
            hbox.addWidget(copy_btn)
            vbox.addWidget(entry_widget)
        vbox.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        btnClose = QtWidgets.QPushButton("Close", self)
        layout.addWidget(btnClose)
        btnClose.clicked.connect(self.accept)
        self.setLayout(layout)
        self.setMinimumSize(600, 400)
        self.setSizeGripEnabled(True)


def start_recording():
    if recording_state['is_recording']:
        return
    print("Recording started (hold hotkey)...")
    recording_state['is_recording'] = True
    recording_state['frames'] = []
    recording_state['start_time'] = datetime.datetime.now()
    # Start sounddevice InputStream
    def callback(indata, frames, time, status):
        if recording_state['is_recording']:
            recording_state['frames'].append(indata.copy())
    stream = sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=callback)
    recording_state['stream'] = stream
    stream.start()
    # Update icon color if tray exists
    if 'tray' in globals() and tray is not None:
        tray.update_icon('recording')

def stop_recording_and_transcribe():
    if not recording_state['is_recording']:
        return
    print("Recording stopped. Transcribing...")
    recording_state['is_recording'] = False
    stream = recording_state.get('stream')
    if stream:
        stream.stop()
        stream.close()
    frames = recording_state.get('frames', [])
    if not frames:
        print("No audio recorded.")
        # Reset to idle if no audio recorded
        if 'tray' in globals() and tray is not None:
            tray.update_icon('idle')
        return
    audio_data = np.concatenate(frames, axis=0)
    audio_length = (datetime.datetime.now() - recording_state['start_time']).total_seconds()
    # Set audio for worker and trigger transcription
    tray.worker.set_audio(audio_data, audio_length)
    tray.start_transcription()  # This will set the icon to 'processing' state

def hotkey_listener():
    """Background thread: supports Alt+Comma (hold), Alt+Dot (toggle), Alt+Slash (cancel) only."""
    from pynput.keyboard import Key, KeyCode
    pressed_mods = set()
    toggle_active = False
    def is_alt_mod():
        return Key.alt in pressed_mods
    def on_press(key):
        nonlocal toggle_active
        if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            pressed_mods.add(Key.ctrl)
        if key in (Key.alt, Key.alt_l, Key.alt_r):
            pressed_mods.add(Key.alt)
        if key in (Key.shift, Key.shift_l, Key.shift_r):
            pressed_mods.add(Key.shift)
        # Alt + , (comma): hold to record
        if is_alt_mod() and key == KeyCode.from_char(','):
            if not recording_state['is_recording']:
                start_recording()
        # Alt + . (dot): toggle
        if is_alt_mod() and key == KeyCode.from_char('.'):
            if not toggle_active:
                if not recording_state['is_recording']:
                    start_recording()
                toggle_active = True
            else:
                if recording_state['is_recording']:
                    stop_recording_and_transcribe()
                toggle_active = False
        # Alt + / (slash): cancel
        if is_alt_mod() and key == KeyCode.from_char('/'):
            if recording_state['is_recording']:
                print("Recording canceled.")
                recording_state['is_recording'] = False
                stream = recording_state.get('stream')
                if stream:
                    stream.stop()
                    stream.close()
                # Reset icon to idle state when canceling
                if 'tray' in globals() and tray is not None:
                    tray.update_icon('idle')
    def on_release(key):
        nonlocal toggle_active
        if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            pressed_mods.discard(Key.ctrl)
        if key in (Key.alt, Key.alt_l, Key.alt_r):
            pressed_mods.discard(Key.alt)
        if key in (Key.shift, Key.shift_l, Key.shift_r):
            pressed_mods.discard(Key.shift)
        # Alt + , (comma): release to finish
        if key == KeyCode.from_char(',') and is_alt_mod():
            if recording_state['is_recording']:
                stop_recording_and_transcribe()
        # Alt + . (dot): handled on press as toggle
        # Alt + / (slash): handled on press as cancel
    with pynput_keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


def main():
    """Main application entry point"""
    global tray
    
    # Create application
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Create parent widget to handle custom events
    parent_widget = QtWidgets.QWidget()
    
    # Override event handler to trigger transcription on hotkey
    original_event = parent_widget.event
    def custom_event(event):
        if event.type() == QtCore.QEvent.User:
            if tray:
                tray.start_transcription()
            return True
        return original_event(event)
    
    parent_widget.event = custom_event
    
    # Create system tray icon
    icon = QtGui.QIcon('mic2-white.png')
    tray = TrayApp(icon, parent_widget)
    tray.show()
    
    # Start hotkey listener
    threading.Thread(target=hotkey_listener, daemon=True).start()
    
    # Start Qt event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
