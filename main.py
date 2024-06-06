import os
import sys
import json
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QSize
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtGui import QTextOption
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QDialog,
    QLabel,
)
from PyQt6.QtWidgets import QHBoxLayout
from dotenv import load_dotenv
from openai import OpenAI
import pygame
from scipy.io.wavfile import write

from audio_recorder import AudioRecorder

BG_COLOR = "#171717"
INPUT_BG = "#212121"
BUTTON_BG = "#383838"
PLACEHOLDER_COLOR = "#909090"
HOVER_BG = "#2563eb"
TEXT_COLOR = "#ececec"

MIC_PATH = os.path.join(os.path.dirname(__file__), "mic.png")
STOP_PATH = os.path.join(os.path.dirname(__file__), "stop.png")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")
HISTORY_ICON_PATH = os.path.join(os.path.dirname(__file__), "history.png")

KEY_PATH = os.path.join(os.path.dirname(__file__), "key")
ICON_SIZE = QSize(32, 32)

SYSTEM_VOICE = "shimmer"
SYSTEM_MESSAGE = """Your name is Victoria, and my name is Ryan. You are an intelligent, friendly, and highly knowledgeable assistant. You should provide accurate, concise, and helpful responses to a wide array of questions, and from time to time, you can have a little humor, let's say 10%. When a question is about general knowledge, technical information, personal advice, or any other topic, ensure your response is clear and concise."""


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

        self.setWindowTitle("Victoria")
        self.setGeometry(100, 100, 500, 800)
        self.setStyleSheet("background-color: #09090b;")
        app.setStyle("Fusion")

        self.history_file_path = os.path.join(os.path.dirname(__file__), "history.json")

        # Input box
        self.input_text = QTextEdit()
        self.input_text.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.input_text.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.input_text.setPlaceholderText("How can I help you today?")
        self.input_text.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self.input_text.setMaximumWidth(950)
        self.input_text.setFixedHeight(60)
        self.input_text.setStyleSheet(
            f"QTextEdit {{border-radius: 5px; background-color: {INPUT_BG};}}"
        )
        text_font = QFont("Roboto", 12)
        self.input_text.setFont(text_font)
        self.input_text.keyPressEvent = self.custom_key_event

        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setStyleSheet(
            f"""QPushButton {{
                                            background-color: {BUTTON_BG};
                                            color: {TEXT_COLOR};
                                            border-radius: 8px;
                                            padding: 10px;
                                            font-size: 16px;
                                            font-weight: bold;
                                        }}QPushButton:hover {{
                                            background-color: {HOVER_BG};
                                        }}"""
        )

        # Output box
        self.output_text = QTextEdit()
        self.output_text.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.output_text.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.output_text.setStyleSheet(
            f"QTextEdit {{border-radius: 5px; background-color: {INPUT_BG}; color: {TEXT_COLOR};}}"
        )
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
        self.record_button.setIcon(QIcon(MIC_PATH))

        self.record_button.setIconSize(ICON_SIZE)
        self.record_button.setFixedSize(ICON_SIZE)
        self.record_button.setStyleSheet(
            "QPushButton { border: none; }"
            "QPushButton::menu-indicator { image: none; }"
        )
        self.layout.addWidget(self.record_button)
        self.record_button.clicked.connect(self.toggle_record)

        # Stop Button
        self.stop_button = QPushButton()
        self.stop_button.setIcon(QIcon(STOP_PATH))
        self.stop_button.setIconSize(ICON_SIZE)
        self.stop_button.setFixedSize(ICON_SIZE)
        self.stop_button.setStyleSheet(
            "QPushButton { border: none; }"
            "QPushButton::menu-indicator { image: none; }"
        )
        self.stop_button.clicked.connect(self.stop_audio)
        self.layout.addWidget(self.stop_button)

        # View History Button
        self.view_history_button = QPushButton()
        self.view_history_button.setIcon(QIcon(HISTORY_ICON_PATH))
        self.view_history_button.setIconSize(ICON_SIZE)
        self.view_history_button.setFixedSize(ICON_SIZE)
        self.view_history_button.setStyleSheet(
            "QPushButton { border: none; }"
            "QPushButton::menu-indicator { image: none; }"
        )
        self.view_history_button.clicked.connect(self.view_history)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.send_button)
        buttons_layout.addWidget(self.view_history_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.record_button)
        self.layout.addLayout(buttons_layout)

        self.setLayout(self.layout)

        load_dotenv(dotenv_path=KEY_PATH)
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.MODEL = "gpt-4o"

        self.audio_dir = os.path.join(os.path.dirname(__file__), "audio_files")
        os.makedirs(self.audio_dir, exist_ok=True)
        self.output_audio_path = os.path.join(self.audio_dir, "output.mp3")
        self.response_counter = 1

        app.aboutToQuit.connect(self.cleanup)

    def stop_audio(self):
        pygame.mixer.music.stop()

    def fetch_response(self, question):
        completion = self.create_chat_completion(question)
        res_text = completion.choices[0].message.content
        return res_text

    def send_button_clicked(self):
        self.input_text.append('<font color="#60a5fa" size="13px">Thinking...</font>')
        user_input = self.input_text.toPlainText()

        if user_input.lower() != "quit":
            self.worker = Worker(self.fetch_response, user_input)
            self.worker.finished.connect(self.handle_response)
            self.worker.start()

    def handle_response(self, response_text):
        if hasattr(self, "play_worker") and self.play_worker.isRunning():
            self.play_worker.stop()
        self.output_text.append(f"{response_text}\n")
        self.write_to_history(self.input_text.toPlainText(), response_text)
        self.play_worker = Worker(self.play_response_sound, response_text)
        self.play_worker.start()
        self.input_text.clear()

    def play_response_sound(self, text):
        output_file = f"output_{self.response_counter}.mp3"
        output_path = os.path.join(self.audio_dir, output_file)
        self.response_counter += 1

        audio_response = self.client.audio.speech.create(
            model="tts-1-hd", voice=SYSTEM_VOICE, input=text, response_format="mp3"
        )
        with open(output_path, "wb") as f:
            f.write(audio_response.content)

        pygame.mixer.music.load(output_path)
        pygame.mixer.music.play()
        pygame.mixer.music.set_volume(1.0)
        self.playback_timer.start(100)

    def check_audio_playback(self):
        if not pygame.mixer.music.get_busy():
            self.playback_timer.stop()

    def handle_error(self, e):
        error_message = f"Error: {str(e)}"
        self.output_text.append(f"{error_message}")

    def custom_key_event(self, event):
        if (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() == Qt.KeyboardModifier.ShiftModifier
        ):
            self.input_text.insertPlainText("\n")
        elif event.key() == Qt.Key.Key_Return:
            self.send_button_clicked()
        else:
            QTextEdit.keyPressEvent(self.input_text, event)

    # Recording functions
    def toggle_record(self):
        if not self.audio_recorder.is_recording:
            self.input_text.append('<font color="#dc2626" size="13px">🔴</font>')
            self.audio_recorder.start_recording()
        else:
            self.worker = Worker(self.stop_recording_and_process_audio)
            self.worker.finished.connect(self.start_playback)
            self.worker.error.connect(self.handle_error)
            self.worker.start()
            self.input_text.clear()
            self.input_text.append(
                '<font color="#fa5252" size="13px">Thinking...</font>'
            )

    def stop_recording_and_process_audio(self):
        try:
            audio_data = self.audio_recorder.stop_recording()
            user_audio_file_path = os.path.join(self.audio_dir, "user.wav")
            write(user_audio_file_path, self.audio_recorder.sample_rate, audio_data)
            with open(user_audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file
                )
            text = transcript.text

            chat_response = self.create_chat_completion(text)
            response_text = chat_response.choices[0].message.content
            self.output_text.append(f"{response_text}\n")
            self.write_to_history(text, response_text)

            audio_response = self.client.audio.speech.create(
                model="tts-1-hd",
                voice=SYSTEM_VOICE,
                input=response_text,
                response_format="mp3",
            )
            voice_response_file_path = os.path.join(
                self.audio_dir, f"voice_response_{self.response_counter}.mp3"
            )
            self.response_counter += 1

            with open(voice_response_file_path, "wb") as f:
                f.write(audio_response.content)

            pygame.mixer.music.load(voice_response_file_path)
            pygame.mixer.music.play()
            pygame.mixer.music.set_volume(1.0)

        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.output_text.append(f"{error_message}")

    def start_playback(self, output_file):
        try:
            self.input_text.clear()
            self.play_worker = Worker(self.play_response_sound, output_file)
            self.play_worker.error.connect(self.handle_error)
            self.play_worker.start()
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.output_text.append(f"{error_message}")

    def delete_audio_file(self, file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.output_text.append(f"{error_message}")

    def cleanup(self):
        try:
            for filename in os.listdir(self.audio_dir):
                if (
                    filename.startswith("output_")
                    and filename.endswith(".mp3")
                    or filename == "user.wav"
                    or filename.startswith("voice_response_")
                    and filename.endswith(".mp3")
                ):
                    file_path = os.path.join(self.audio_dir, filename)
                    os.remove(file_path)
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.output_text.append(f"{error_message}")

    def create_chat_completion(self, prompt):
        return self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": prompt},
            ],
        )

    def write_to_history(self, user_input, response):
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "response": response,
        }
        if os.path.exists(self.history_file_path):
            with open(self.history_file_path, "r", encoding="utf-8") as file:
                history_data = json.load(file)
        else:
            history_data = []

        history_data.append(history_entry)
        with open(self.history_file_path, "w", encoding="utf-8") as file:
            json.dump(history_data, file, indent=4)

    def view_history(self):
        history_dialog = QDialog(self)
        history_dialog.setWindowTitle("Chat History")
        history_dialog.setGeometry(200, 200, 600, 400)
        history_text_edit = QTextEdit()
        history_text_edit.setReadOnly(True)

        history_font = QFont("Roboto", 12)
        history_text_edit.setFont(history_font)
        history_text_edit.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        try:
            with open("history.json", "r") as file:
                history_data = json.load(file)
                history_text = ""
                for entry in history_data:
                    history_text += f"Timestamp: {entry['timestamp']}\n"
                    history_text += f"User Input: {entry['user_input']}\n"
                    history_text += f"Response: {entry['response']}\n\n"
                history_text_edit.setPlainText(history_text)
        except Exception as e:
            history_text_edit.setPlainText(f"Failed to load history: {e}")

        clear_history_button = QPushButton("Clear History")
        clear_history_button.setStyleSheet(
            f"""QPushButton {{
                background-color: {BUTTON_BG};
                color: {TEXT_COLOR};
                border-radius: 8px;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }}QPushButton:hover {{
                background-color: {HOVER_BG};
            }}"""
        )
        clear_history_button.clicked.connect(self.clear_history)

        dialog_layout = QVBoxLayout()
        dialog_layout.addWidget(history_text_edit)
        dialog_layout.addWidget(clear_history_button)
        history_dialog.setLayout(dialog_layout)

        history_dialog.exec()

    def clear_history(self):
        with open("history.json", "w") as file:
            json.dump([], file)
        confirmation_dialog = QDialog(self)
        confirmation_dialog.setWindowTitle("Confirmation")
        confirmation_dialog.setGeometry(200, 200, 200, 100)
        confirmation_layout = QVBoxLayout()
        confirmation_label = QLabel("History cleared successfully.")
        confirmation_layout.addWidget(confirmation_label)
        confirmation_dialog.setLayout(confirmation_layout)
        confirmation_dialog.exec()


app = QApplication(sys.argv)
app_icon = QIcon(LOGO_PATH)
window = MainWindow()
window.setWindowIcon(app_icon)
window.show()
sys.exit(app.exec())
