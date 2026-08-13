#!/usr/bin/env python3
"""Bouwt de twee varianten uit shell.html + img/.

    menukaart.html      voor de lokale server (serve.py)
    public/index.html   voor Vercel

De vier beelden (kaft en drie achterkanten) staan apart in img/ zodat de
code klein blijft. Draai dit na elke wijziging in shell.html.
"""
from pathlib import Path

D = Path(__file__).resolve().parent
IMG = D / 'img'
SHELL = D / 'shell.html'

def met_beelden():
    s = SHELL.read_text('utf-8')
    for i in range(1, 5):
        s = s.replace('__IMG%d__' % i, (IMG / ('%d.b64' % i)).read_text())
    return s

def voor_vercel(s):
    # de sleutel meesturen bij het bewaren
    s = s.replace(
        "const r=await fetch('/api/menu',{method:'POST',headers:{'Content-Type':'application/json'},body});",
        "const r=await fetch('/api/menu',{method:'POST',headers:{'Content-Type':'application/json',"
        "'x-tafelaar-key':(localStorage.getItem('tafelaar-key')||'')},body});", 1)
    # om een sleutel vragen als de server erom vraagt
    s = s.replace(
        "    if(!r.ok) throw 0;\n    lastSaved=body;",
        "    if(r.status===401){ const k=prompt('Sleutel om te mogen bewaren:');\n"
        "      if(k){ localStorage.setItem('tafelaar-key',k); return push(); }\n"
        "      return say('Geen sleutel, niet bewaard','err'); }\n"
        "    if(!r.ok) throw 0;\n    lastSaved=body;", 1)
    # terugval op de browser als er op de server geen opslag is ingesteld
    s = s.replace(
        "  }catch{ say('Nieuw document','ok'); }\n}",
        "  }catch{}\n"
        "  const b=localStorage.getItem('tafelaar-menu');\n"
        "  if(b){ try{ const d=JSON.parse(b);\n"
        "    if(d&&d.s){ m=d; lastSaved=b; return say('Geladen uit deze browser','ok'); } }catch{} }\n"
        "  say('Nieuw document','ok');\n}", 1)
    s = s.replace(
        "  }catch{ say('Bewaren mislukt','err'); }\n}",
        "  }catch{\n"
        "    try{ localStorage.setItem('tafelaar-menu',body); lastSaved=body;\n"
        "      say('Bewaard in deze browser','ok'); }\n"
        "    catch{ say('Bewaren mislukt','err'); }\n  }\n}", 1)

    # de pdf-knop werkt alleen lokaal, want daar draait een browser
    s = s.replace("document.getElementById('pdf').onclick=async()=>{",
        "if(!['localhost','127.0.0.1'].includes(location.hostname))"
        " document.getElementById('pdf').hidden=true;\n"
        "document.getElementById('pdf').onclick=async()=>{", 1)
    return s

s = met_beelden()
(D / 'menukaart.html').write_text(s, 'utf-8')
(D / 'public').mkdir(exist_ok=True)
(D / 'public' / 'index.html').write_text(voor_vercel(s), 'utf-8')
print('menukaart.html en public/index.html gebouwd:', len(s) // 1024, 'KB')
