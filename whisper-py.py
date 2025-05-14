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
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject, QThread
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
            api_key = os.getenv("OPENAI_API_KEY")
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
        
        # Set up system tray menu
        menu = QtWidgets.QMenu(parent)
        action_record = menu.addAction('Record && Transcribe (Right Alt)')
        action_record.triggered.connect(self.start_transcription)
        action_quit = menu.addAction('Quit')
        action_quit.triggered.connect(self.quit_application)
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
        
        # Use QMetaObject.invokeMethod with a slot
        QtCore.QMetaObject.invokeMethod(self.worker, 'run', QtCore.Qt.QueuedConnection)
        
    def transcription_finished(self):
        """Handle completion of transcription"""
        self.is_transcribing = False
        
        # Disconnect to prevent multiple connections
        self.worker.signals.finished.disconnect(self.transcription_finished)
        
    def handle_error(self, error_msg):
        """Handle errors from the worker thread"""
        print(f"Error: {error_msg}")
        self.is_transcribing = False
        
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
        return
    audio_data = np.concatenate(frames, axis=0)
    audio_length = (datetime.datetime.now() - recording_state['start_time']).total_seconds()
    # Set audio for worker and trigger transcription
    tray.worker.set_audio(audio_data, audio_length)
    tray.start_transcription()

def hotkey_listener():
    """Background thread to listen for hotkeys and control recording"""
    COMBO = {pynput_keyboard.Key.alt_r}
    current = set()

    def on_press(key):
        if key in COMBO and not recording_state['is_recording']:
            current.add(key)
            start_recording()

    def on_release(key):
        if key in current:
            current.remove(key)
            stop_recording_and_transcribe()

    with pynput_keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()




def main():
    """Main application entry point"""
    global tray
    
    # Create application
    app = QtWidgets.QApplication(sys.argv)
    
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
    
    # Start hotkey listener in a thread
    threading.Thread(target=hotkey_listener, daemon=True).start()
    
    # Start Qt event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
