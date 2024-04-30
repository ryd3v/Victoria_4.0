import sounddevice as sd
import numpy as np


class AudioRecorder:
    def __init__(self, sample_rate=48000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.recording_buffer = []
        self.stream = None

    def start_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.recording_buffer = []
            self.stream = sd.InputStream(callback=self.audio_callback, samplerate=self.sample_rate,
                                         channels=self.channels)
            self.stream.start()

    def stop_recording(self):
        if self.is_recording:
            self.stream.stop()
            self.stream.close()
            self.is_recording = False
            recording = np.concatenate(self.recording_buffer, axis=0)
            self.recording_buffer = []
            return recording

    def audio_callback(self, indata, frames, time, status):
        if self.is_recording:
            self.recording_buffer.append(indata.copy())
