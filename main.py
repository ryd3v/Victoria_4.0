import os
import sys

from PyQt6.QtCore import QThread, pyqtSignal, QSize
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtGui import QTextOption
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit
from PyQt6.QtWidgets import QHBoxLayout
from dotenv import load_dotenv
from openai import OpenAI
import pygame
from scipy.io.wavfile import write

from audio_recorder import AudioRecorder

mic_path = os.path.join(os.path.dirname(__file__), 'mic.png')
stop_path = os.path.join(os.path.dirname(__file__), 'stop.png')
logo_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
key = os.path.join(os.path.dirname(__file__), 'key')


class Worker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(Exception)

    def __init__(self, func, *args, **kwargs):
        super(Worker, self).__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.running = True
    
    def stop(self):
        self.running = False
        pygame.mixer.music.stop()

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            if self.running:
                self.finished.emit(result)
        except Exception as e:
            pass

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        pygame.init()
        pygame.mixer.init()

        self.setWindowTitle('Victoria')
        self.setGeometry(100, 100, 500, 800)
        self.setStyleSheet("background-color: #09090b;")
        app.setStyle("Fusion")

        # Input box
        self.input_text = QTextEdit()
        self.input_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.input_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.input_text.setPlaceholderText("Ask your question...")
        self.input_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.input_text.setMaximumWidth(950)
        self.input_text.setFixedHeight(50)
        self.input_text.setStyleSheet("QTextEdit {border-radius: 5px; background-color: #18181b;}")
        text_font = QFont("Roboto", 12)
        self.input_text.setFont(text_font)
        self.input_text.keyPressEvent = self.custom_key_event

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setStyleSheet("""QPushButton {
                                            background-color: #27272a;
                                            color: #f4f4f5;
                                            border-radius: 8px;
                                            padding: 10px;
                                            font-size: 16px;
                                            font-weight: bold;
                                        }QPushButton:hover {
                                            background-color: #3b82f6;
                                        }""")

        self.output_text = QTextEdit()
        self.output_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.output_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.output_text.setStyleSheet("QTextEdit {border-radius: 5px; background-color: #18181b; color: #0ea5e9;}")
        output_font = QFont("Roboto", 12)
        self.output_text.setFont(output_font)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.input_text)

        self.layout.addWidget(self.output_text)
        self.layout.addWidget(self.send_button)
        self.setLayout(self.layout)

        self.output_text.setReadOnly(True)
        self.send_button.clicked.connect(self.send_button_clicked)

        # Recorder Button
        self.audio_recorder = AudioRecorder()
        self.record_button = QPushButton()
        self.record_button.setIcon(QIcon(mic_path))
        icon_size = QSize(32, 32)
        self.record_button.setIconSize(icon_size)
        self.record_button.setFixedSize(icon_size)
        self.record_button.setStyleSheet("QPushButton { border: none; }"
                                         "QPushButton::menu-indicator { image: none; }")
        self.layout.addWidget(self.record_button)
        self.record_button.clicked.connect(self.toggle_record)

        # Stop Button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(QIcon(stop_path))
        icon_size = QSize(32,32)
        self.stop_button.setIconSize(icon_size)
        self.stop_button.setFixedSize(icon_size)
        self.stop_button.setStyleSheet("QPushButton { border: none; }"
                                         "QPushButton::menu-indicator { image: none; }")
        self.stop_button.clicked.connect(self.stop_audio)
        self.layout.addWidget(self.stop_button)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.record_button)
        self.layout.addLayout(buttons_layout)

        self.setLayout(self.layout)

        load_dotenv(dotenv_path=key)
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.MODEL = 'gpt-4-turbo'

        self.audio_dir = os.path.join(os.path.dirname(__file__), 'audio_files')
        os.makedirs(self.audio_dir, exist_ok=True)
        self.output_audio_path = os.path.join(self.audio_dir, 'output.mp3')
        self.response_counter = 1

        app.aboutToQuit.connect(self.cleanup)

    def stop_audio(self):
        pygame.mixer.music.stop()

    def fetch_response(self, question):
        completion = self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system",
                 "content": "Your name is Victoria, and you are a personal assistant to Ryan the user"},
                {"role": "user", "content": question}
            ]
        )
        res_text = completion.choices[0].message.content
        return res_text

    def send_button_clicked(self):
        self.input_text.append('<font color="#0ea5e9" size="13px">Thinking...</font>')
        user_input = self.input_text.toPlainText()

        if user_input.lower() != 'quit':
            self.worker = Worker(self.fetch_response, user_input)
            self.worker.finished.connect(self.handle_response)
            self.worker.start()

    def handle_response(self, response_text):
        if hasattr(self, 'play_worker') and self.play_worker.isRunning():
            self.play_worker.stop()
        self.output_text.append(f"{response_text}\n")
        self.play_worker = Worker(self.play_response_sound, response_text)
        self.play_worker.start()
        self.input_text.clear()

    def play_response_sound(self, text):
            output_file = f"output_{self.response_counter}.mp3"
            output_path = os.path.join(self.audio_dir, output_file)
            self.response_counter += 1

            audio_response = self.client.audio.speech.create(
                model="tts-1-hd",
                voice="nova",
                input=text,
                response_format="mp3"
            )
            with open(output_path, 'wb') as f:
                f.write(audio_response.content)

            pygame.mixer.music.load(output_path)
            pygame.mixer.music.play()
            self.playback_timer.start(100)

    def check_audio_playback(self):
        if not pygame.mixer.music.get_busy():
            self.playback_timer.stop()

    def handle_error(self, e):
        error_message = f"Error: {str(e)}"
        self.output_text.append(f'{error_message}')

    def custom_key_event(self, event):
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.input_text.insertPlainText("\n")
        elif event.key() == Qt.Key.Key_Return:
            self.send_button_clicked()
        else:
            QTextEdit.keyPressEvent(self.input_text, event)

    # Recording functions
    def toggle_record(self):
        if not self.audio_recorder.is_recording:
            self.input_text.append('<font color="#fa5252" size="12px">🔴</font>')
            self.audio_recorder.start_recording()
        else:
            self.worker = Worker(self.stop_recording_and_process_audio)
            self.worker.finished.connect(self.start_playback)
            self.worker.error.connect(self.handle_error)
            self.worker.start()
            self.input_text.clear()
            self.input_text.append('<font color="#fa5252" size="13px">Thinking...</font>')

    def stop_recording_and_process_audio(self):
        try:
            audio_data = self.audio_recorder.stop_recording()
            user_audio_file_path = os.path.join(self.audio_dir, 'user.wav')
            write(user_audio_file_path, self.audio_recorder.sample_rate, audio_data)
            with open(user_audio_file_path, 'rb') as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            text = transcript.text

            chat_response = self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "Your name is Victoria, and you are a personal assistant to Ryan the user"},
                    {"role": "user", "content": text}
                ]
            )
            response_text = chat_response.choices[0].message.content
            self.output_text.append(f"{response_text}\n")

            audio_response = self.client.audio.speech.create(
                model="tts-1-hd",
                voice="nova",
                input=response_text,
                response_format="mp3"
            )
            voice_response_file_path = os.path.join(self.audio_dir, f'voice_response_{self.response_counter}.mp3')
            self.response_counter += 1

            with open(voice_response_file_path, 'wb') as f:
                f.write(audio_response.content)

            pygame.mixer.music.load(voice_response_file_path)
            pygame.mixer.music.play()

        except Exception as e:
           error_message = f"Error: {str(e)}"
           self.output_text.append(f'{error_message}')

    def start_playback(self, output_file):
        try:
            self.input_text.clear()
            self.play_worker = Worker(self.play_response_sound, output_file)
            self.play_worker.error.connect(self.handle_error)
            self.play_worker.start()
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.output_text.append(f'{error_message}')

    def delete_audio_file(self, file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.output_text.append(f'{error_message}')

    def cleanup(self):
        print("Running cleanup...")
        try:
            for filename in os.listdir(self.audio_dir):
                if filename.startswith("output_") and filename.endswith(".mp3") or \
                filename == 'user.wav' or \
                filename.startswith("voice_response_") and filename.endswith(".mp3"):
                    file_path = os.path.join(self.audio_dir, filename)
                    print(f"Attempting to delete: {file_path}")
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.output_text.append(f'{error_message}')


app = QApplication(sys.argv)
app_icon = QIcon(logo_path)
window = MainWindow()
window.setWindowIcon(app_icon)
window.show()
sys.exit(app.exec())