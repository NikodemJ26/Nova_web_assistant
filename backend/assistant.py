# assistant.py
import os
import sys
import time
import json
import queue
import requests
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import random
import traceback
import io
import soundfile as sf
from wakeonlan import send_magic_packet
import datetime
# import pyttsx3

class VoiceAssistant:
    def __init__(self, socketio=None):
        self.q = queue.Queue()
        self.is_speaking = False
        self.recording_enabled = True
        self.socketio = socketio
        self.last_recognition_time = 0
        self.recognition_cooldown = 0.5
        self.listening_start_time = 0
        self.active_session = False

        self.vosk_model_path = os.getenv(
            "VOSK_MODEL_PATH",
            os.path.join(os.path.dirname(__file__), "..", "models", "vosk", "pl")
        )
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4azwk8qx opposing")
        self.wake_word = os.getenv("WAKE_WORD", "nowa")
        self.end_words = os.getenv("END_WORDS", "stop,koniec,zakończ,wyjdź").split(",")
        self.sample_rate = 16000
        self.blocksize = 8000
        self.default_city = os.getenv("DEFAULT_CITY", "Szczecin")
        self.computer_mac = os.getenv("COMPUTER_MAC")
        self.broadcast_address = os.getenv("BROADCAST_ADDRESS", "192.168.1.255")
        self.notes_file = os.getenv(
            "NOTES_FILE",
            os.path.join(os.path.dirname(__file__), "..", "notes.json")
        )

        try:
            self.model_vosk = Model(self.vosk_model_path)
            print("Model VOSK załadowany.")
        except Exception as e:
            print(f"Błąd ładowania modelu VOSK: {e}")
            self.model_vosk = None

        if self.elevenlabs_api_key and self.elevenlabs_voice_id:
            self.tts_model_loaded = True
            print("Eleven Labs gotowy do użycia.")
        else:
            self.tts_model_loaded = False
            print("Brak klucza API Eleven Labs lub ID głosu. TTS będzie niedostępny.")

    # --- STT: Speech to Text ---
    def audio_callback(self, indata, frames, time_, status):
        if not self.recording_enabled or self.is_speaking:
            return
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def clear_queue(self):
        while not self.q.empty():
            self.q.get()

    def speech_to_text(self, timeout=10):
        """Prosty, zoptymalizowany STT z Vosk"""
        if not self.model_vosk:
            print("Brak modelu Vosk!")
            return ""
        self.clear_queue()
        recognizer = KaldiRecognizer(self.model_vosk, self.sample_rate)
        print("Rozpoczynam nasłuchiwanie...")
        try:
            with sd.RawInputStream(samplerate=self.sample_rate, blocksize=self.blocksize, dtype='int16', channels=1, callback=self.audio_callback):
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        data = self.q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            print(f"Rozpoznano: {text}")
                            self.last_recognition_time = time.time()
                            return text
                print("Timeout nasłuchiwania.")
                return ""
        except Exception as e:
            print(f"Błąd STT: {e}")
            return ""

    # --- TTS: Text to Speech (Eleven Labs) ---
    def tts_speak(self, text):
        """Generowanie i odtwarzanie mowy za pomocą Eleven Labs."""
        if not self.tts_model_loaded or not self.elevenlabs_api_key or not self.elevenlabs_voice_id:
            print("Eleven Labs nie jest skonfigurowany.")
            return

        try:
            self.is_speaking = True
            self.recording_enabled = False  # wycisz mikrofon

            headers = {
                "Accept": "audio/wav",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key
            }
            data = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"

            response = requests.post(url, headers=headers, json=data, stream=True, timeout=10)
            response.raise_for_status()

            audio_data, sample_rate = sf.read(io.BytesIO(response.content), dtype='float32')

            sd.play(audio_data, samplerate=sample_rate)
            sd.wait()

        except requests.exceptions.RequestException as req_err:
            print(f"Błąd zapytania do Eleven Labs: {req_err}")
            if hasattr(req_err, 'response') and req_err.response is not None:
                print(f"Odpowiedź serwera: {req_err.response.text}")
            traceback.print_exc()
        except Exception as e:
            print(f"Błąd TTS (Eleven Labs): {e}")
            traceback.print_exc()
        finally:
            self.is_speaking = False
            self.recording_enabled = True  # przywróć mikrofon


    def reset_recognition_time(self):
        self.last_recognition_time = time.time() # Resetuj czas, aby sesja nie wygasła
        self.active_session = True

    # --- Funkcje komend ---
    def get_weather(self, city):
        try:
            if city:
                query_city = city
            else:
                query_city = self.default_city # Użyj domyślnego miasta z pliku .env

            url = f"http://api.openweathermap.org/data/2.5/weather?q={query_city}&appid={self.openweather_api_key}&units=metric&lang=pl"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get('cod') != 200:
                error_msg = data.get('message', 'nieznany błąd')
                return {"error": f"Błąd pogody: {error_msg}"}
            icon_code = data['weather'][0]['icon']
            description = data['weather'][0]['description']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            wind_speed = data['wind']['speed']
            return {
                "city": data['name'],
                "icon": icon_code,
                "description": description.capitalize(),
                "temp": temp,
                "feels_like": feels_like,
                "humidity": humidity,
                "wind_speed": wind_speed
            }
        except Exception as e:
            print(f"Błąd pogody: {e}")
            return {"error": "Przepraszam, problem z pobraniem pogody"}

    def wake_computer(self):
        if not self.computer_mac:
            return "Brak adresu MAC komputera do włączenia w pliku .env."
        try:
            send_magic_packet(self.computer_mac, ip_address=self.broadcast_address)
            return "Wysłałam komendę włączenia komputera."
        except Exception as e:
            print(f"Błąd WoL: {e}")
            return "Nie udało się wysłać komendy włączenia komputera."

    def save_note(self, content):
        try:
            notes = []
            if os.path.exists(self.notes_file):
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    try:
                        notes = json.load(f)
                    except Exception:
                        notes = []
            # Unikalny ID na bazie czasu i losowej liczby
            note_id = int(datetime.datetime.now().timestamp() * 1000) + random.randint(1, 999)
            note = {
                "id": note_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "content": content
            }
            notes.append(note)
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
            return "Notatka została zapisana."
        except Exception as e:
            print(f"Błąd zapisu notatki: {e}")
            return "Nie udało się zapisać notatki."

    def get_notes(self):
        try:
            if os.path.exists(self.notes_file):
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Błąd odczytu notatek: {e}")
            return []

    def delete_note(self, note_id):
        try:
            notes = []
            if os.path.exists(self.notes_file):
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    notes = json.load(f)
            notes = [n for n in notes if n["id"] != note_id]
            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump(notes, f, indent=2, ensure_ascii=False)
            return "Notatka usunięta."
        except Exception as e:
            print(f"Błąd usuwania notatki: {e}")
            return "Nie udało się usunąć notatki."

    def run_ai(self, prompt):
        # Notatki
        if "zapisz notatkę" in prompt.lower() or "zrób notatkę" in prompt.lower():
            content = prompt.lower().replace("zapisz notatkę", "").replace("zrób notatkę", "").strip()
            if not content:
                return "Co mam zapisać w notatce?"
            return self.save_note(content)
        if "pokaż notatki" in prompt.lower() or "wyświetl notatki" in prompt.lower():
            notes = self.get_notes()
            if not notes:
                return "Nie masz jeszcze żadnych notatek."
            return "Oto Twoje notatki: " + ", ".join([note['content'] for note in notes])
        # Pogoda
        weather_triggers = ["pogod", "temperatur", "deszcz", "słońc", "śnieg", "wilgotność", "wiatr"]
        if any(trigger in prompt.lower() for trigger in weather_triggers):
            city_name = None
            if "w" in prompt.lower():
                parts = prompt.lower().split("w")
                if len(parts) > 1:
                    city_name = parts[1].strip().split(" ")[0].capitalize()
            
            weather_info = self.get_weather(city_name)
            if "error" in weather_info:
                return weather_info["error"]
            return (f"Aktualna pogoda w {weather_info['city']}: "
                    f"{weather_info['description']}, "
                    f"temperatura: {weather_info['temp']}°C "
                    f"(odczuwalna {weather_info['feels_like']}°C), "
                    f"wilgotność: {weather_info['humidity']}%, "
                    f"wiatr: {weather_info['wind_speed']} km/h")
        # Funkcja Wake on LAN
        wake_triggers = ["włącz komputer", "uruchom komputer", "włącz pc", "włącz pecet"]
        if any(trigger in prompt.lower() for trigger in wake_triggers):
            return self.wake_computer()
        # Zakończ sesję
        if any(end in prompt.lower() for end in self.end_words):
            self.active_session = False
            return "Kończę nasłuchiwanie. Miłego dnia!"
        # AI
        try:
            headers = {"Authorization": f"Bearer {self.openrouter_api_key}", "Content-Type": "application/json"}
            payload = {
                "model": "openai/gpt-oss-20b:free",
                "messages": [
                    {"role": "system", "content": "Jesteś pomocnym asystentem głosowym o imieniu Nowa. Odpowiadaj żywo, naturalnie i krótko oraz rozmownie, zawsze po polsku. Zakaz emotek i znaków specjalnych. nie używaj **."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 400
            }
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Błąd w komunikacji z AI: {e}"