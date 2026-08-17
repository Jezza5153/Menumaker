#!/usr/bin/env python3
# De Tafelaar - menukaart, lokaal draaiend. Meerdere kaarten naast elkaar.
import http.server, socketserver, json, threading, shutil, subprocess, os, re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs

HOME = Path.home()
D = HOME / 'Tafelaar'
KAARTEN = D / 'kaarten'
BACKUPS = D / 'backups'
for p in (D, KAARTEN, BACKUPS, D / 'pdf'):
    p.mkdir(exist_ok=True)
HTML = D / 'menukaart.html'
POORT = 8765

# oude opzet met een enkel menu.json overzetten
oud = D / 'menu.json'
if oud.exists() and not (KAARTEN / 'diner.json').exists():
    shutil.move(str(oud), str(KAARTEN / 'diner.json'))
    print('menu.json is nu kaarten/diner.json')

INSTF = D / 'instellingen.json'

# eenmalig: de dieetinstellingen uit een kaart halen en gedeeld opslaan
if not INSTF.exists():
    for f in sorted(KAARTEN.glob('*.json')):
        try:
            d = json.loads(f.read_text('utf-8'))
        except Exception:
            continue
        if d.get('leg'):
            INSTF.write_text(json.dumps({'leg': d['leg'], 'letters': bool(d.get('letters'))},
                                        ensure_ascii=False, indent=2), 'utf-8')
            print('dieetinstellingen overgenomen uit', f.stem)
            break

s = HTML.read_text(encoding='utf-8')
lock = threading.Lock()
VEILIG = re.compile(r'^[a-z0-9][a-z0-9-]{0,40}$')


def pad_van(naam):
    naam = (naam or 'diner').lower()
    if not VEILIG.match(naam):
        naam = 'diner'
    return KAARTEN / (naam + '.json')


def lijst():
    return sorted(p.stem for p in KAARTEN.glob('*.json'))


def html_voor(naam):
    # Chrome bepaalt het papierformaat bij het inlezen; javascript is te laat.
    mode = 'a5'
    try:
        mode = json.loads(pad_van(naam).read_text('utf-8')).get('print', 'a5')
    except Exception:
        pass
    regel = ('@page{size:A4 landscape;margin:0}' if mode == 'a4'
             else '@page{size:154mm 216mm;margin:0}' if mode == 'druk'
             else '@page{size:A5;margin:0}')
    oud = '<style id="pagerule">@page{size:A5;margin:0}</style>'
    return s.replace(oud, '<style id="pagerule">' + regel + '</style>', 1).encode('utf-8')


BROWSERS = [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    str(HOME) + '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/Applications/Brave Browser.app/Contents/MacOS/Brave Browser',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
]


def naar_voren(pad):
    # steeds hetzelfde bestand openen: Voorvertoning ververst dan het venster
    # dat al openstaat, in plaats van er elke keer een nieuw bij te maken
    import time
    dicht = ('tell application "Preview"\n'
             '  repeat with w in (every window)\n'
             '    if name of w is "' + pad.name + '" then close w\n'
             '  end repeat\n'
             'end tell')
    subprocess.run(['osascript', '-e', dicht], capture_output=True)
    time.sleep(0.3)
    subprocess.run(['open', '-a', 'Preview', str(pad)], capture_output=True)
    time.sleep(0.6)
    subprocess.run(['osascript', '-e', 'tell application "Preview" to activate'],
                   capture_output=True)


def maak_pdf(naam):
    """Laat de browser buiten beeld printen: geen printvenster, geen schaling."""
    exe = next((b for b in BROWSERS if os.path.exists(b)), None)
    if not exe:
        return None, 'geen Chrome gevonden'
    stempel = datetime.now().strftime('%Y-%m-%d_%H-%M')
    uit = D / 'pdf' / f'{naam}_{stempel}.pdf'
    cmd = [exe, '--headless=new', '--disable-gpu', '--no-pdf-header-footer',
           '--virtual-time-budget=6000', f'--print-to-pdf={uit}',
           f'http://127.0.0.1:{POORT}/?kaart={naam}']
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=120)
    except Exception:
        return None, 'browser reageerde niet op tijd'
    if not uit.exists() or uit.stat().st_size < 1000:
        return None, (r.stderr.decode()[-200:] or 'lege pdf')
    for f in sorted((D / 'pdf').glob('*.pdf'))[:-30]:
        f.unlink(missing_ok=True)
    laatste = D / (naam + '-laatste.pdf')
    shutil.copy2(uit, laatste)
    naar_voren(laatste)
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

    def vraag(self):
        u = urlparse(self.path)
        return u.path, parse_qs(u.query).get('kaart', ['diner'])[0]

    def do_GET(self):
        pad, naam = self.vraag()
        if pad in ('/', '/index.html'):
            return self.send(200, html_voor(naam), 'text/html; charset=utf-8')
        if pad == '/api/instellingen':
            with lock:
                if INSTF.exists():
                    return self.send(200, INSTF.read_bytes())
            return self.send(404, b'{}')
        if pad == '/api/kaarten':
            return self.send(200, json.dumps({'kaarten': lijst()}).encode())
        if pad == '/api/menu':
            with lock:
                f = pad_van(naam)
                if f.exists():
                    return self.send(200, f.read_bytes())
            return self.send(404, b'{}')
        self.send(404, b'{}')

    def do_POST(self):
        pad, naam = self.vraag()
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n) if n else b''

        if pad == '/api/pdf':
            try:
                naam = json.loads(raw).get('kaart', naam)
            except Exception:
                pass
            if not VEILIG.match(naam or ''):
                naam = 'diner'
            uit, fout = maak_pdf(naam)
            if fout:
                return self.send(500, json.dumps({'fout': fout}).encode())
            return self.send(200, json.dumps({'ok': True, 'pad': uit.name}).encode())

        if pad == '/api/instellingen':
            try:
                data = json.loads(raw)
            except Exception:
                return self.send(400, b'{}')
            with lock:
                tmp = INSTF.with_suffix('.tmp')
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
                tmp.replace(INSTF)
            return self.send(200, b'{"ok":true}')

        if pad != '/api/menu':
            return self.send(404, b'{}')
        try:
            data = json.loads(raw)
        except Exception:
            return self.send(400, b'{}')
        with lock:
            f = pad_van(naam)
            if f.exists():
                stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                shutil.copy2(f, BACKUPS / f'{f.stem}_{stamp}.json')
                for oudje in sorted(BACKUPS.glob(f'{f.stem}_*.json'))[:-40]:
                    oudje.unlink()
            tmp = f.with_suffix('.tmp')
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')
            tmp.replace(f)
        self.send(200, b'{"ok":true}')

    def log_message(self, *a):
        pass


socketserver.ThreadingTCPServer.allow_reuse_address = True
socketserver.ThreadingTCPServer.daemon_threads = True
with socketserver.ThreadingTCPServer(('127.0.0.1', POORT), H) as srv:
    print(f'draait op http://localhost:{POORT}/  kaarten: {", ".join(lijst()) or "nog geen"}')
    srv.serve_forever()
