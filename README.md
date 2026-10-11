# Raty — harmonogram kredytów ratalnych

Prosta aplikacja webowa do śledzenia spłat kredytów. Działa jako PWA — na telefonie wygląda i zachowuje się jak natywna apka.

## Funkcje

- Dodawanie kredytów z harmonogramem rat
- Odhaczanie zapłaconych rat
- Nadpłaty ze skracaniem okresu kredytowania
- Notatki przy każdej racie
- Dashboard z podsumowaniem (zadłużenie, zapłacono, pozostało, najbliższa rata)
- Synchronizacja danych między urządzeniami przez backend
- Działa offline (service worker)

---

## Wymagania

- Python 3.9+
- Żadnych dodatkowych bibliotek — tylko standardowa biblioteka Pythona

---

## Struktura plików

```
raty/
├── app.py          ← serwer HTTP (uruchamiasz to)
├── data.json       ← aktywne kredyty (tworzy się automatycznie)
├── archive.json    ← archiwum kredytów (tworzy się automatycznie)
├── README.md
└── static/
    ├── index.html
    ├── manifest.json
    ├── sw.js
    ├── icon-192v2.png
    ├── icon-512v2.png
    └── icon-1024v2.png
```

---

## Uruchomienie

```bash
python3 /ścieżka/do/raty/app.py
```

Domyślnie działa na porcie **8765**. Zmień stałą `PORT` w `app.py` jeśli potrzebujesz innego.

Aplikacja dostępna pod `http://localhost:8765` lub `http://IP_MASZYNY:8765`.

---

## Autostart (systemd, Linux)

Utwórz plik serwisu:

```bash
sudo nano /etc/systemd/system/raty.service
```

Wklej:

```ini
[Unit]
Description=Raty
After=network.target

[Service]
ExecStart=/bin/python3 /home/UŻYTKOWNIK/raty/app.py
WorkingDirectory=/home/UŻYTKOWNIK/raty
Restart=always
User=UŻYTKOWNIK

[Install]
WantedBy=multi-user.target
```

Włącz i uruchom:

```bash
sudo systemctl enable raty
sudo systemctl start raty
```

---

## Dostęp zdalny

Aplikacja działa lokalnie — żeby mieć do niej dostęp spoza sieci domowej potrzebujesz VPN.

### Tailscale (zalecane)

Działa za NAT i double NAT bez przekierowania portów na routerze — idealne dla większości domowych konfiguracji w Polsce (INEA, UPC, Vectra i inne z CG-NAT).

**Instalacja na serwerze (Linux/Raspberry Pi):**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --advertise-routes=192.168.1.0/24
```

Podmień `192.168.1.0/24` na swój lokalny zakres sieci.

W panelu Tailscale (`login.tailscale.com/admin/machines`) zatwierdź trasę subnet.

**Na pozostałych urządzeniach:**

Zainstaluj aplikację Tailscale (iOS, Android, Windows, macOS) i zaloguj się tym samym kontem. Po połączeniu VPN wchodzisz na aplikację po lokalnym IP serwera.

### WireGuard (alternatywa)

Wymaga publicznego IP lub przekierowania portu UDP na routerze. Działa jeśli masz bezpośrednie publiczne IP (tryb bridge u providera).

Instalacja przez PiVPN:

```bash
curl -L https://install.pivpn.io | bash
```

---

## PWA — instalacja na telefonie

Aplikacja musi być serwowana przez HTTP/HTTPS (nie otwierana jako plik lokalny).

**iOS (Safari):**
1. Otwórz stronę w Safari
2. Ikona udostępniania → **Dodaj do ekranu głównego**

**Android (Chrome):**
1. Otwórz stronę w Chrome
2. Menu → **Dodaj do ekranu głównego**

**Windows/macOS (Chrome/Edge):**
- Ikona instalacji (⊕) w pasku adresu

---

## Dane

Dane zapisywane są obok `app.py`: aktywne kredyty w `data.json`, zarchiwizowane w `archive.json`. Oba pliki są w `.gitignore`. Format JSON — czytelny i edytowalny ręcznie. Skopiuj oba pliki jako backup.
