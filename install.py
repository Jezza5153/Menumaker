#!/usr/bin/env python3
# Zet de beelden apart en bouwt menukaart.html op uit een kleine romp.
# Zo hoeft er bij een update alleen nog code over de lijn, geen plaatjes.
import base64
import gzip
import re
import subprocess
import sys
import time
from pathlib import Path

D = Path.home() / 'Tafelaar'
IMG = D / 'img'
IMG.mkdir(parents=True, exist_ok=True)
HTML = D / 'menukaart.html'
SHELL = D / 'shell.html'

# 1. beelden eenmalig uit de bestaande kaart halen
if not (IMG / '1.b64').exists():
    if not HTML.exists():
        sys.exit('menukaart.html ontbreekt')
    blobs = re.findall(r'data:image/png;base64,([A-Za-z0-9+/=]+)', HTML.read_text('utf-8'))
    if len(blobs) != 4:
        sys.exit('verwachtte 4 beelden, vond %d' % len(blobs))
    for i, b in enumerate(blobs, 1):
        (IMG / ('%d.b64' % i)).write_text(b)
    print('beelden bewaard:', [len(b) // 1024 for b in blobs], 'KB')

# 2. nieuwe romp uitpakken (staat naast dit script als shell.gz)
gz = D / 'shell.gz'
if gz.exists():
    SHELL.write_text(gzip.decompress(gz.read_bytes()).decode('utf-8'), 'utf-8')
    gz.unlink()

# 3. romp + beelden samenvoegen tot de echte kaart
s = SHELL.read_text('utf-8')
for i in range(1, 5):
    s = s.replace('__IMG%d__' % i, (IMG / ('%d.b64' % i)).read_text())
HTML.write_text(s, 'utf-8')
print('menukaart.html opgebouwd:', len(s) // 1024, 'KB')

# 4. server herstarten
subprocess.run(['pkill', '-f', 'Tafelaar/serve.py'], capture_output=True)
time.sleep(0.7)
subprocess.Popen(['python3', str(D / 'serve.py')],
                 cwd=str(D),
                 stdout=open(D / 'log.txt', 'w'),
                 stderr=subprocess.STDOUT,
                 start_new_session=True)
time.sleep(1.5)
print('server herstart op http://localhost:8765/')
