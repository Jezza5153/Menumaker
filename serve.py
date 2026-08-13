#!/usr/bin/env python3
# De Tafelaar - menukaart, lokaal draaiend
import http.server, socketserver, json, threading, webbrowser, shutil, time
from pathlib import Path
from datetime import datetime

HOME = Path.home()
D = HOME / 'Tafelaar'
D.mkdir(exist_ok=True)
(D / 'backups').mkdir(exist_ok=True)
MENU = D / 'menu.json'
HTML = D / 'menukaart.html'

# nieuwste gedownloade editor ophalen en klaarzetten
cands = list((HOME / 'Downloads').glob('tafelaar-menukaart*.html'))
cands += list((HOME / 'Downloads').glob('tafelaar-menu-editor*.html'))
if cands:
    src = max(cands, key=lambda p: p.stat().st_mtime)
    if not HTML.exists() or src.stat().st_mtime > HTML.stat().st_mtime:
        shutil.copy2(src, HTML)

s = HTML.read_text(encoding='utf-8')

def html_voor_mode():
    # Chrome bepaalt het papierformaat bij het inlezen; javascript is te laat.
    mode = 'a5'
    try:
        mode = json.loads(MENU.read_text('utf-8')).get('print', 'a5')
    except Exception:
        pass
    regel = '@page{size:A4 landscape;margin:0}' if mode == 'a4' else '@page{size:A5;margin:0}'
    oud = '<style id="pagerule">@page{size:A5;margin:0}</style>'
    nieuw = '<style id="pagerule">' + regel + '</style>'
    return s.replace(oud, nieuw, 1).encode('utf-8')

BODY = s.encode('utf-8')
lock = threading.Lock()

import subprocess, os

BROWSERS = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    str(HOME) + '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
]

def maak_pdf():
    """Laat de browser buiten beeld printen: geen printvenster, geen schaling."""
    (D / 'pdf').mkdir(exist_ok=True)
    exe = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not exe:
        return None, 'geen Chrome gevonden'
    stempel = datetime.now().strftime('%Y-%m-%d_%H-%M')
    uit = D / 'pdf' / ('menukaart_' + stempel + '.pdf')
    cmd = [exe, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
           '--virtual-time-budget=6000',
           '--print-to-pdf=' + str(uit), 'http://127.0.0.1:8765/']
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=90)
    except Exception:
        return None, 'browser reageerde niet op tijd'
    if not uit.exists() or uit.stat().st_size < 1000:
        return None, (r.stderr.decode()[-200:] or 'lege pdf')
    for f in sorted((D / 'pdf').glob('menukaart_*.pdf'))[:-20]:
        f.unlink(missing_ok=True)
    subprocess.run(['open', str(uit)])
    return uit, None



class H(http.server.BaseHTTPRequestHandler):
    def send(self, code, body=b'', ctype='application/json; charset=utf-8'):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            return self.send(200, html_voor_mode(), 'text/html; charset=utf-8')
        if self.path == '/api/menu':
            with lock:
                if MENU.exists():
                    return self.send(200, MENU.read_bytes())
            return self.send(404, b'{}')
        self.send(404, b'{}')

    def do_POST(self):
        if self.path == '/api/pdf':
            pad, fout = maak_pdf()
            if fout:
                return self.send(500, json.dumps({'fout': fout}).encode())
            return self.send(200, json.dumps({'ok': True, 'pad': pad.name}).encode())
        if self.path != '/api/menu':
            return self.send(404, b'{}')
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n)
        try:
            data = json.loads(raw)
        except Exception:
            return self.send(400, b'{}')
        with lock:
            if MENU.exists():
                stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                shutil.copy2(MENU, D / 'backups' / ('menu_' + stamp + '.json'))
                old = sorted((D / 'backups').glob('menu_*.json'))
                for f in old[:-40]:
                    f.unlink()
            tmp = MENU.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
            tmp.replace(MENU)
        self.send(200, b'{"ok":true}')

    def log_message(self, *a):
        pass

socketserver.ThreadingTCPServer.allow_reuse_address = True
socketserver.ThreadingTCPServer.daemon_threads = True
with socketserver.ThreadingTCPServer(('127.0.0.1', 8765), H) as srv:
    print('draait op http://localhost:8765/  map: ' + str(D))
    srv.serve_forever()
