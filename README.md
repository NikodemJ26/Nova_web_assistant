# Asystent Nowa – Projekt hobbystyczny

**Asystent Nowa** to polski asystent głosowy z nowoczesnym interfejsem webowym. Pozwala na obsługę codziennych zadań za pomocą mowy i panelu www.  
Projekt powstał z pasji do nowych technologii i jest rozwijany hobbystycznie – kod tworzę sam, ucząc się programowania na bieżąco.

---

## Funkcje projektu

- **Rozpoznawanie mowy (STT)** – obsługa komend głosowych w języku polskim (Vosk)
- **Synteza mowy (TTS)** – odpowiedzi asystenta generowane przez ElevenLabs
- **Panel konwersacji** – historia rozmowy z asystentem
- **Notatki** – dodawanie, odczytywanie i usuwanie notatek (głosowo i przez GUI, także z klawiaturą ekranową)
- **Budziki** – ustawianie, aktywacja i zarządzanie budzikami
- **Przypomnienia** – dodawanie, przeglądanie i usuwanie przypomnień w GUI
- **Panel ustawień** – zmiana miasta, adresu MAC komputera i innych parametrów bez edycji plików
- **Pogoda** – aktualna prognoza dla wybranego miasta (OpenWeather)
- **Wake on LAN** – zdalne włączanie komputera w sieci lokalnej
- **Monitor systemu** – podgląd obciążenia CPU i RAM
- **Instrukcja obsługi** – panel z opisem dostępnych komend i funkcji
- **Powiadomienia systemowe** – szybkie komunikaty o sukcesach i błędach
- **Lepsza obsługa błędów** – czytelne komunikaty w GUI i backendzie

---

## Jak działa?

- **Backend** (Python, Flask): obsługuje rozpoznawanie mowy, syntezę mowy, logikę komend, API do notatek, budzików, przypomnień, pogody i ustawień.
- **Frontend** (HTML, Alpine.js, Tailwind): interfejs webowy z panelami do rozmowy, notatek, budzików, przypomnień, pogody, systemu i ustawień.
- **Socket.IO**: komunikacja w czasie rzeczywistym (np. aktualizacja rozmowy, status nasłuchiwania).
- **Pliki JSON**: dane notatek, budzików, przypomnień i ustawień zapisywane są lokalnie.

---

## Instalacja i uruchomienie

### Wymagania

- Python 3.10+
- Node.js (do ewentualnej obsługi frontendowej)
- Klucze API do ElevenLabs i OpenWeather (opcjonalnie `.env`)

### Instalacja zależności

```bash
pip install -r requirements.txt
```

### Uruchom backend

```bash
python backend/app.py
```

### Otwórz stronę

Przejdź do [http://localhost:5000](http://localhost:5000) w przeglądarce.

---

## Przykładowe komendy głosowe

- „Nowa” – aktywuj asystenta
- „Jaka jest pogoda?” – sprawdź pogodę
- „Zapisz notatkę kupić mleko” – dodaj notatkę
- „Pokaż notatki” – odczytaj zapisane notatki
- „Włącz komputer” – wyślij Wake on LAN
- „Stop” – zakończ nasłuchiwanie

---

## Status projektu

> **Projekt jest hobbystyczny i w ciągłym rozwoju. Tworzę go sam, nie mam dużej wiedzy programistycznej – traktuję go jako naukę i zabawę.  
> Kod może zawierać błędy, a funkcje są stale rozbudowywane i poprawiane.  
> Jeśli masz pomysł, chcesz pomóc lub zgłosić błąd – śmiało napisz!**

---

## Licencja

Projekt udostępniony jest na zasadach open source – możesz korzystać, uczyć się i