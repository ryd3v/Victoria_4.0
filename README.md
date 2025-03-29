# OpenAI-Powered Voice Assistant Victoria

## Overview
This project is a **PyQt6-based AI-powered voice assistant** that allows users to interact using voice commands. It integrates OpenAI's API for intelligent responses and supports audio recording using `pygame` and `scipy.io.wavfile`.

## Features
- **Graphical User Interface (GUI)** built with PyQt6
- **Voice input support** using `pygame`
- **AI-driven responses** via OpenAI API
- **Environment variable management** with `dotenv`
- **Audio recording and processing** with `scipy.io.wavfile`
- **Customizable UI themes and icons**

## Installation
### Prerequisites
Ensure you have Python installed (recommended: Python 3.9+). Then, install dependencies:
```sh
pip install -r requirements.txt
```

### Environment Variables
Create a `.key` file in the project directory and set your OpenAI API key:
```env
OPENAI_API_KEY=your_api_key_here
```

## Usage
Run the application with:
```sh
python main.py
```

## File Structure
```
.
├── main.py               # Main application script
├── audio_recorder.py     # Handles audio recording
├── assets/               # Icons and images
├── .env                  # API keys (not included in repo)
├── requirements.txt      # Dependencies
```

## Contributing
Feel free to submit issues and pull requests!

## License
This project is licensed under the MIT License.

