import os
import sys
import time
import threading
import traceback
import json
import random
import datetime
import difflib
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import psutil

# Import asystenta głosowego
try:
    from assistant import VoiceAssistant
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from assistant import VoiceAssistant

# Wczytaj zmienne środowiskowe
load_dotenv()

# Ścieżki i konfiguracja aplikacji
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_PATH = os.path.abspath(os.path.join(BASE_DIR, '../frontend/public'))

app = Flask(__name__, static_folder=FRONTEND_PATH, static_url_path='/')
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicjalizacja asystenta
assistant = VoiceAssistant(socketio)
assistant_active = True
is_listening = False
force_listen = False

# Globalne zmienne dla budzików i przypomnień
alarms = []
reminders = []
SETTINGS_FILE = "settings.json"

# Funkcja do aktualizacji konwersacji w GUI
def update_conversation(speaker, text):
    timestamp = time.strftime("%H:%M:%S")
    entry = {"speaker": speaker, "text": text, "timestamp": timestamp}
    socketio.emit('conversation_update', entry)

# Funkcje do obsługi budzików i przypomnień
def load_alarms():
    """Wczytaj budziki z pliku JSON."""
    global alarms
    try:
        if os.path.exists("alarms.json"):
            with open("alarms.json", "r", encoding="utf-8") as f:
                alarms = json.load(f)
        else:
            alarms = []
    except Exception as e:
        print(f"Błąd ładowania budzików: {e}")
        alarms = []

def save_alarms():
    """Zapisz budziki do pliku JSON."""
    try:
        with open("alarms.json", "w", encoding="utf-8") as f:
            json.dump(alarms, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Błąd zapisu budzików: {e}")

def load_reminders():
    """Wczytaj przypomnienia z pliku JSON."""
    global reminders
    try:
        if os.path.exists("reminders.json"):
            with open("reminders.json", "r", encoding="utf-8") as f:
                reminders = json.load(f)
        else:
            reminders = []
    except Exception as e:
        print(f"Błąd ładowania przypomnień: {e}")
        reminders = []

def save_reminders():
    """Zapisz przypomnienia do pliku JSON."""
    try:
        with open("reminders.json", "w", encoding="utf-8") as f:
            json.dump(reminders, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Błąd zapisu przypomnień: {e}")

# Funkcja do porównywania podobieństwa tekstów
def is_similar(a, b, threshold=0.8):
    """Sprawdź, czy dwa teksty są podobne."""
    if not a or not b:
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() > threshold

# Endpointy API
@app.route('/')
def index():
    """Serwuj plik index.html."""
    return send_from_directory(FRONTEND_PATH, 'index.html')

@app.route('/api/weather')
def weather_api():
    """Zwróć dane pogodowe."""
    city = request.args.get('city', os.getenv("DEFAULT_CITY", "Szczecin"))
    weather = assistant.get_weather(city)
    return jsonify(weather)

@app.route('/api/system')
def system_api():
    """Zwróć statystyki systemowe (CPU, RAM)."""
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    return jsonify({"cpu": cpu, "ram": ram})

# Endpointy do zarządzania notatkami
@app.route('/api/notes', methods=['GET'])
def get_notes_api():
    notes = assistant.get_notes()
    return jsonify(notes)

@app.route('/api/notes', methods=['POST'])
def add_note_api():
    data = request.get_json()
    content = data.get('content', '').strip()
    if not content:
        return jsonify({"message": "Notatka nie może być pusta!"}), 400
    msg = assistant.save_note(content)
    return jsonify({"message": msg})

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note_api(note_id):
    msg = assistant.delete_note(note_id)
    return jsonify({"message": msg})

# Endpointy do zarządzania budzikami
@app.route('/api/alarms', methods=['GET'])
def get_alarms_api():
    load_alarms()
    return jsonify(alarms)

@app.route('/api/alarms', methods=['POST'])
def add_alarm_api():
    data = request.get_json()
    if not data or 'time' not in data:
        return jsonify({"error": "Brak czasu budzika"}), 400
    
    # Przetwórz czas na format HH:MM, jeśli przyszedł w innym formacie (np. datetime-local)
    # Zakładamy, że 'time' może być w formacie 'YYYY-MM-DDTHH:MM'
    alarm_time = data['time']
    if 'T' in alarm_time and len(alarm_time) > 16: # Sprawdzamy, czy to pełna data-czas
        alarm_time = alarm_time[11:16] # Wycinamy tylko HH:MM

    alarm_id = int(time.time()) + random.randint(1, 1000)
    alarm = {
        "id": alarm_id,
        "time": alarm_time,
        "label": data.get('label', ''),
        "active": True
    }
    load_alarms()
    alarms.append(alarm)
    save_alarms()
    return jsonify({"message": "Budzik dodany!"})

@app.route('/api/alarms/<int:alarm_id>', methods=['DELETE'])
def delete_alarm_api(alarm_id):
    load_alarms()
    alarms[:] = [a for a in alarms if a['id'] != alarm_id]
    save_alarms()
    return jsonify({"message": "Budzik usunięty!"})

@app.route('/api/alarms/<int:alarm_id>/toggle', methods=['PUT'])
def toggle_alarm_api(alarm_id):
    data = request.get_json()
    load_alarms()
    for alarm in alarms:
        if alarm['id'] == alarm_id:
            alarm['active'] = data.get('active', True)
    save_alarms()
    return jsonify({"message": "Status budzika zmieniony!"})

# Endpointy do zarządzania przypomnieniami
@app.route('/api/reminders', methods=['GET'])
def get_reminders_api():
    load_reminders()
    return jsonify(reminders)

@app.route('/api/reminders', methods=['POST'])
def add_reminder_api():
    data = request.get_json()
    if not data or 'time' not in data or 'content' not in data:
        return jsonify({"error": "Brak danych przypomnienia"}), 400

    reminder_time = data['time']
    if 'T' in reminder_time and len(reminder_time) > 16:
        reminder_time = reminder_time[11:16]

    reminder_id = int(time.time()) + random.randint(1, 1000)
    reminder = {
        "id": reminder_id,
        "time": reminder_time,
        "content": data['content'],
        "active": True,
        "timestamp": datetime.datetime.now().isoformat() # Dodaj timestamp dla wyświetlania
    }
    load_reminders()
    reminders.append(reminder)
    save_reminders()
    return jsonify({"message": "Przypomnienie dodane!"})

@app.route('/api/reminders/<int:reminder_id>', methods=['DELETE'])
def delete_reminder_api(reminder_id):
    load_reminders()
    reminders[:] = [r for r in reminders if r['id'] != reminder_id]
    save_reminders()
    return jsonify({"message": "Przypomnienie usunięte!"})

@app.route('/api/reminders/<int:reminder_id>/toggle', methods=['PUT'])
def toggle_reminder_api(reminder_id):
    data = request.get_json()
    load_reminders()
    for reminder in reminders:
        if reminder['id'] == reminder_id:
            reminder['active'] = data.get('active', True)
    save_reminders()
    return jsonify({"message": "Status przypomnienia zmieniony!"})

# Nowe endpointy do zarządzania ustawieniami
@app.route('/api/settings', methods=['GET'])
def get_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"city": "Szczecin", "mac": ""})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.get_json()
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return jsonify({"message": "Ustawienia zapisane!"})

# Obsługa Socket.IO
@socketio.on('start_listening')
def handle_start_listening():
    """Rozpocznij nasłuchiwanie."""
    global is_listening, force_listen
    is_listening = True
    force_listen = True
    update_conversation("System", "Rozpoczynam nasłuchiwanie.")
    socketio.emit('listening_status', {"status": True})
    assistant.tts_speak("Słucham?")

@socketio.on('stop_listening')
def handle_stop_listening():
    """Zatrzymaj nasłuchiwanie."""
    global is_listening
    is_listening = False
    update_conversation("System", "Zatrzymano nasłuchiwanie.")
    socketio.emit('listening_status', {"status": False})
    assistant.tts_speak("Do usłyszenia!")

@socketio.on('start_voice_note')
def handle_start_voice_note():
    update_conversation("System", "Powiedz treść notatki...")
    assistant.tts_speak("Powiedz treść notatki...")
    note_text = assistant.speech_to_text(timeout=15)
    if note_text:
        socketio.emit('voice_note_text', note_text)
    else:
        socketio.emit('voice_note_text', "Nie rozpoznano notatki.")

@socketio.on('read_notes')
def handle_read_notes():
    notes = assistant.get_notes()
    if not notes:
        assistant.tts_speak("Nie masz jeszcze żadnych notatek.")
        return

    text = "Oto Twoje notatki: "
    for i, note in enumerate(notes, 1):
        text += f"Notatka {i}: {note['content']}. "

    assistant.tts_speak(text)

# Wątek asystenta
def assistant_thread_function():
    """Główna pętla asystenta."""
    global is_listening, force_listen
    print("Wątek asystenta uruchomiony.")
    assistant.tts_speak("Jestem gotowa do działania")
    last_command = None
    last_response = None

    while assistant_active:
        try:
            if force_listen:
                command = ""  # Wymusza wejście do pętli aktywnego nasłuchiwania
                force_listen = False  # Reset flagi po pierwszym wejściu
            else:
                print("Nasłuchiwanie słowa aktywującego...")
                command = assistant.speech_to_text(timeout=10)
                print(f"Po nasłuchiwaniu: {command}")

            wake_words = [w.strip() for w in os.getenv("WAKE_WORD", "nowa").split(",")]
            if command and any(wake_word in command for wake_word in wake_words):
                print(f"Aktywowano: {command}")
                update_conversation("Użytkownik", command)
                is_listening = True
                socketio.emit('listening_status', {"status": True})
                assistant.reset_recognition_time()
                assistant.tts_speak("Tak, słucham?")
                update_conversation("Nowa", "Tak, słucham?")
            elif not is_listening and command:
                print(f"Nieaktywowana komenda: {command}")
                continue

            while assistant_active and is_listening:
                print("Nasłuchiwanie komendy użytkownika...")
                while assistant.is_speaking:
                    time.sleep(0.1)
                command = assistant.speech_to_text(timeout=30)

                if command is None or command == "":
                    if time.time() - assistant.last_recognition_time > 15:
                        print("Brak komendy, kończę nasłuchiwanie.")
                        is_listening = False
                        socketio.emit('listening_status', {"status": False})
                        assistant.tts_speak("Do usłyszenia!")
                        break
                    continue

                if command == last_command or is_similar(command, last_command) or (last_response and command in last_response):
                    print("Zignorowano powtórzoną lub echem komendę.")
                    continue
                last_command = command

                print(f"Pytanie: {command}")
                response = assistant.run_ai(command)
                last_response = response
                print(f"Odpowiedź: {response}")
                update_conversation("Nowa", response)
                assistant.tts_speak(response)

        except Exception as e:
            print(f"Błąd w głównej pętli: {e}")
            traceback.print_exc()
            time.sleep(1)

def alarm_checker():
    while True:
        now = datetime.datetime.now().strftime("%H:%M")
        load_alarms()
        for alarm in alarms:
            if alarm['active'] and alarm['time'] == now:
                socketio.emit('alarm_triggered', alarm)
                assistant.tts_speak(f"Czas na budzik: {alarm.get('label', '') or alarm['time']}")
                alarm['active'] = False # Wyłącz alarm po aktywacji
                save_alarms()
        time.sleep(30) # Sprawdzaj co 30 sekund

def reminder_checker():
    while True:
        now = datetime.datetime.now().strftime("%H:%M")
        load_reminders()
        for reminder in reminders:
            if reminder['active'] and reminder['time'] == now:
                socketio.emit('reminder_triggered', reminder)
                assistant.tts_speak(f"Przypomnienie: {reminder['content']}")
                reminder['active'] = False # Wyłącz przypomnienie po aktywacji
                save_reminders()
        time.sleep(30) # Sprawdzaj co 30 sekund

def system_stats_emitter(): # Nowa funkcja do wysyłania statystyk
    while True:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        socketio.emit('system_stats', {"cpu": cpu, "ram": ram})
        time.sleep(2) # Wysyłaj co 2 sekundy

if __name__ == "__main__":
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or os.environ.get('FLASK_ENV') == 'development':
        print("Uruchamianie serwera w głównym procesie (lub w trybie deweloperskim Flask)...")
        alarm_thread = threading.Thread(target=alarm_checker, daemon=True)
        alarm_thread.start()

        reminder_thread = threading.Thread(target=reminder_checker, daemon=True)
        reminder_thread.start()

        assistant_thread = threading.Thread(target=assistant_thread_function, daemon=True)
        assistant_thread.start()

        system_stats_thread = threading.Thread(target=system_stats_emitter, daemon=True) # Uruchom wątek statystyk
        system_stats_thread.start()

        global assistant_thread_instance
        assistant_thread_instance = assistant_thread
    else:
        print("Proces przeładowania Flask - wątki nie będą uruchamiane.")

    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("Zamykanie serwera...")
        assistant_active = False
        if 'assistant_thread_instance' in globals() and assistant_thread_instance.is_alive():
            assistant_thread_instance.join(timeout=2.0)
        sys.exit(0)
    except Exception as e:
        print(f"Krytyczny błąd serwera: {e}")
        traceback.print_exc()
        sys.exit(1)