document.addEventListener('alpine:init', () => {
    Alpine.data('app', () => ({
        listening: false,
        conversation: [],
        weather: {
            city: "Ładowanie...",
            icon: "☀️",
            description: "",
            temp: "--",
            feels_like: "--",
            humidity: "--",
            wind_speed: "--"
        },
        system: {
            cpu: 0,
            ram: 0
        },
        notes: [],
        alarms: [],
        reminders: [],
        newAlarmTime: "",
        newAlarmLabel: "",
        newReminderTime: "",
        newReminderContent: "",
        showNotesModal: false,
        showAlarmsModal: false,
        showRemindersModal: false,
        showHelpModal: false, // Dodane
        addingNote: false,
        newNoteText: '',
        status: "Połączono",
        settings: {
            city: "",
            mac: ""
        },
        showSettingsModal: false,
        notification: { show: false, text: '', type: 'success' },

        init() {
            // Połączenie z WebSocket
            this.socket = io();
            
            // Nasłuchiwanie aktualizacji konwersacji
            this.socket.on('conversation_update', (message) => {
                this.conversation.push(message);
                // Auto-przewijanie
                setTimeout(() => {
                    const container = document.querySelector('.conversation-container');
                    container.scrollTop = container.scrollHeight;
                }, 100);
            });
            
            // Nasłuchiwanie statusu nasłuchiwania
            this.socket.on('listening_status', (data) => {
                this.listening = data.status;
            });

            // Nasłuchiwanie rozpoznanego tekstu notatki
            this.socket.on('voice_note_text', (text) => {
                if (this.addingNote) {
                    this.newNoteText = text;
                }
            });
            
            // Nasłuchiwanie alarmów
            this.socket.on('alarm_triggered', (alarm) => {
                this.conversation.push({
                    speaker: "System",
                    text: `Budzik: ${alarm.label || alarm.time}`,
                    timestamp: new Date().toLocaleTimeString()
                });
            });
            
            // Pobierz początkową pogodę
            this.refreshWeather();
            
            // Pobierz notatki
            this.loadNotes();
            
            // Pobierz budziki
            this.loadAlarms();
            
            // Pobierz przypomnienia
            this.loadReminders();
            
            // Uruchom monitor systemu
            this.startSystemMonitor();

            // Pobierz ustawienia
            this.loadSettings();
        },
        
        toggleListening() {
            this.listening = !this.listening;
            if (this.listening) {
                this.socket.emit('start_listening');
            } else {
                this.socket.emit('stop_listening');
            }
        },
        
        refreshWeather() {
            fetch('/api/weather')
                .then(response => response.json())
                .then(data => {
                    this.weather = data;
                    // Aktualizuj ikonę
                    const icons = {
                        "01d": "☀️", "01n": "🌙", "02d": "⛅", "02n": "☁️",
                        "03d": "☁️", "03n": "☁️", "04d": "☁️", "04n": "☁️",
                        "09d": "🌧️", "09n": "🌧️", "10d": "🌦️", "10n": "🌧️",
                        "11d": "⛈️", "11n": "⛈️", "13d": "❄️", "13n": "❄️",
                        "50d": "🌫️", "50n": "🌫️"
                    };
                    this.weather.icon = icons[data.icon] || "☀️";
                });
        },
        
        startSystemMonitor() {
            setInterval(() => {
                fetch('/api/system')
                    .then(response => response.json())
                    .then(data => {
                        this.system = data;
                    });
            }, 2000);
        },
        
        wakeComputer() {
            fetch('/api/wake', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    this.conversation.push({
                        speaker: "System",
                        text: data.message,
                        timestamp: new Date().toLocaleTimeString()
                    });
                });
        },
        
        startAddingNote() {
            this.addingNote = true;
            this.newNoteText = '';
            this.socket.emit('start_voice_note');
        },
        
        cancelAddingNote() {
            this.addingNote = false;
            this.newNoteText = '';
        },
        
        saveNewNote() {
            if (!this.newNoteText.trim()) {
                alert('Notatka nie może być pusta!');
                return;
            }

            fetch('/api/notes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: this.newNoteText })
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    this.conversation.push({
                        speaker: "System",
                        text: data.message,
                        timestamp: new Date().toLocaleTimeString()
                    });
                    this.addingNote = false;
                    this.loadNotes(); // Odświeżenie listy notatek
                }
            });
        },
        
        readNotes() {
            this.socket.emit('read_notes');
        },
        
        loadNotes() {
            fetch('/api/notes')
                .then(response => response.json())
                .then(data => {
                    this.notes = data;
                })
                .catch(error => console.error("Błąd ładowania notatek:", error));
        },
        
        deleteNote(noteId) {
            if (confirm("Czy na pewno chcesz usunąć tę notatkę?")) {
                fetch(`/api/notes/${noteId}`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    this.conversation.push({
                        speaker: "System",
                        text: data.message,
                        timestamp: new Date().toLocaleTimeString()
                    });
                    this.loadNotes();
                });
            }
        },
        
        loadAlarms() {
            fetch('/api/alarms')
                .then(response => response.json())
                .then(data => {
                    this.alarms = data;
                });
        },
        
        addAlarm() {
            if (!this.newAlarmTime) {
                alert("Podaj czas budzika");
                return;
            }
            
            fetch('/api/alarms', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    time: this.newAlarmTime,
                    label: this.newAlarmLabel
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    this.loadAlarms();
                    this.newAlarmTime = "";
                    this.newAlarmLabel = "";
                    this.conversation.push({
                        speaker: "System",
                        text: data.message,
                        timestamp: new Date().toLocaleTimeString()
                    });
                }
            });
        },
        
        deleteAlarm(alarmId) {
            if (confirm("Czy na pewno chcesz usunąć ten budzik?")) {
                fetch(`/api/alarms/${alarmId}`, {
                    method: 'DELETE'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message) {
                        this.loadAlarms();
                        this.conversation.push({
                            speaker: "System",
                            text: data.message,
                            timestamp: new Date().toLocaleTimeString()
                        });
                    }
                });
            }
        },
        
        toggleAlarm(alarmId, active) {
            fetch(`/api/alarms/${alarmId}/toggle`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ active: active })
            })
            .then(response => response.json())
            .then(data => {
                if (data.message) {
                    this.loadAlarms();
                }
            });
        },
        
        loadReminders() {
            fetch('/api/reminders')
                .then(r => r.json())
                .then(data => { this.reminders = data; });
        },
        addReminder() {
            if (!this.newReminderTime || !this.newReminderContent) {
                this.showNotification("Podaj czas i treść przypomnienia!", "error");
                return;
            }
            fetch('/api/reminders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    time: this.newReminderTime,
                    content: this.newReminderContent
                })
            })
            .then(r => r.json())
            .then(data => {
                this.showNotification(data.message || "Przypomnienie dodane!", "success");
                this.loadReminders();
                this.newReminderTime = "";
                this.newReminderContent = "";
            });
        },
        deleteReminder(reminderId) {
            fetch(`/api/reminders/${reminderId}`, { method: 'DELETE' })
                .then(r => r.json())
                .then(data => {
                    this.showNotification(data.message || "Przypomnienie usunięte!", "success");
                    this.loadReminders();
                });
        },
        saveSettings() {
            fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.settings)
            })
            .then(r => r.json())
            .then(data => {
                this.showSettingsModal = false;
                this.status = "Ustawienia zapisane!";
            });
        },
        showNotification(text, type = 'success') {
            this.notification.text = text;
            this.notification.type = type;
            this.notification.show = true;
            setTimeout(() => { this.notification.show = false; }, 3000);
        },
    }));
});