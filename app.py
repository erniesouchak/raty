#!/usr/bin/env python3
"""
Raty - Loan Tracker Backend
Uruchomienie: python3 app.py
Domyślnie działa na porcie 8765
"""

import json
import os
import tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading

DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')
ARCHIVE_FILE = os.path.join(os.path.dirname(__file__), 'archive.json')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
PORT = 8765

# Serwer jest wielowątkowy — każdy odczyt-modyfikacja-zapis plików danych
# musi być pod tą blokadą (nigdy nie trzymaj jej podczas I/O sieciowego).
_data_lock = threading.Lock()


def _atomic_write(path, obj):
    directory = os.path.dirname(path) or '.'
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix='.tmp-', suffix='.json')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"loans": []}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"loans": []}


def save_data(data):
    _atomic_write(DATA_FILE, data)


def load_archive():
    if not os.path.exists(ARCHIVE_FILE):
        return []
    try:
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            archived = json.load(f)
            return archived if isinstance(archived, list) else []
    except Exception:
        return []


def save_archive(archived):
    _atomic_write(ARCHIVE_FILE, archived)


class Handler(BaseHTTPRequestHandler):
    timeout = 30  # zrywa połączenie, które milczy >30 s

    def log_message(self, format, *args):
        pass  # cicho

    def send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path, mime):
        try:
            with open(path, 'rb') as f:
                data = f.read()
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', len(data))
            # Cache static assets
            if mime != 'text/html':
                self.send_header('Cache-Control', 'public, max-age=86400')
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API
        if path == '/api/loans':
            with _data_lock:
                data = load_data()
                archived = load_archive()
            self.send_json(200, {
                'loans': data.get('loans', []),
                'archivedLoans': archived,
            })
            return

        # Static files
        if path == '/' or path == '/index.html':
            self.send_file(os.path.join(STATIC_DIR, 'index.html'), 'text/html; charset=utf-8')
        elif path == '/manifest.json':
            self.send_file(os.path.join(STATIC_DIR, 'manifest.json'), 'application/json')
        elif path == '/sw.js':
            self.send_file(os.path.join(STATIC_DIR, 'sw.js'), 'application/javascript')
        elif path == '/icon-192v2.png':
            self.send_file(os.path.join(STATIC_DIR, 'icon-192v2.png'), 'image/png')
        elif path == '/icon-512v2.png':
            self.send_file(os.path.join(STATIC_DIR, 'icon-512v2.png'), 'image/png')
        elif path == '/icon-1024v2.png':
            self.send_file(os.path.join(STATIC_DIR, 'icon-1024v2.png'), 'image/png')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            length = int(self.headers.get('Content-Length', 0))
        except ValueError:
            length = -1
        if length < 0:
            self.send_json(400, {'error': 'invalid content-length'})
            return
        body = self.rfile.read(length) if length else b'{}'
        try:
            payload = json.loads(body)
        except Exception:
            self.send_json(400, {'error': 'invalid json'})
            return

        if path == '/api/loans':
            # Zapisz cały stan (frontend wysyła pełną listę aktywnych kredytów).
            # Klucz archivedLoans z payloadu jest ignorowany — archiwum żyje
            # wyłącznie w archive.json i jest zmieniane tylko przez dedykowane
            # endpointy poniżej.
            if 'loans' not in payload:
                self.send_json(400, {'error': 'missing loans'})
                return
            with _data_lock:
                archived_ids = {a.get('id') for a in load_archive()}
                loans = [l for l in payload['loans'] if l.get('id') not in archived_ids]
                save_data({'loans': loans})
            self.send_json(200, {'ok': True})

        elif path == '/api/archive':
            loan = payload.get('loan')
            if not loan or not loan.get('id'):
                self.send_json(400, {'error': 'missing loan'})
                return
            with _data_lock:
                archived = load_archive()
                archived = [a for a in archived if a.get('id') != loan['id']]
                archived.append(loan)
                save_archive(archived)

                data = load_data()
                data['loans'] = [l for l in data.get('loans', []) if l.get('id') != loan['id']]
                save_data(data)

            self.send_json(200, {'ok': True})

        elif path == '/api/unarchive':
            loan_id = payload.get('id')
            if not loan_id:
                self.send_json(400, {'error': 'missing id'})
                return
            with _data_lock:
                archived = load_archive()
                loan = next((a for a in archived if a.get('id') == loan_id), None)
                if loan is not None:
                    archived = [a for a in archived if a.get('id') != loan_id]
                    save_archive(archived)

                    data = load_data()
                    loans = [l for l in data.get('loans', []) if l.get('id') != loan_id]
                    loans.append(loan)
                    data['loans'] = loans
                    save_data(data)
            if loan is None:
                self.send_json(404, {'error': 'not found'})
                return

            self.send_json(200, {'ok': True, 'loan': loan})

        else:
            self.send_json(404, {'error': 'not found'})


def migrate_archive():
    """Jednorazowa migracja: przenieś archivedLoans z data.json do archive.json."""
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return
    if not isinstance(data, dict) or 'archivedLoans' not in data:
        return

    old_archived = data.get('archivedLoans') or []
    archived = load_archive()
    existing_ids = {a.get('id') for a in archived}
    for loan in old_archived:
        if loan.get('id') not in existing_ids:
            archived.append(loan)
            existing_ids.add(loan.get('id'))
    save_archive(archived)

    save_data({'loans': data.get('loans', [])})
    print(f"  Migracja: przeniesiono {len(old_archived)} archiwalnych wpisów do {ARCHIVE_FILE}")


def main():
    migrate_archive()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f"✓ Raty działa na http://0.0.0.0:{PORT}")
    print(f"  Dane zapisywane do: {DATA_FILE}")
    print("  Ctrl+C aby zatrzymać\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nZatrzymano.")


if __name__ == '__main__':
    main()
