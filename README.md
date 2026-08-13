# Menumaker

Menukaart-editor voor restaurant De Tafelaar. Acht pagina's A5, opgebouwd op de
maatvoering die uit de originele Illustrator-PDF is gemeten — kader, vlakken,
kleuren en korpsgroottes staan in `maatvoering.md`.

## Wat het doet

Links een formulier met alle gerechten, rechts een live weergave van de kaart.
In de bewerkstand sleep je vlakken en losse gerechten, met uitlijnhulp en een
regelraster. Printen kan als losse A5's of als twee kaarten op een liggende A4,
met de juiste volgorde voor dubbelzijdig drukwerk.

## Lokaal draaien

```bash
python3 bouw.py     # bouwt menukaart.html en public/index.html
python3 serve.py    # http://localhost:8765
```

Je werk komt in `menu.json` naast het script, met een reservekopie per
bewaaractie in `backups/`. De knop **PDF maken** laat Chrome buiten beeld
printen en opent het resultaat — geen printvenster, dus geen schaling.

## Op Vercel

```bash
npx vercel
```

Zet in het dashboard onder **Storage** een Blob-store aan; Vercel voegt
`BLOB_READ_WRITE_TOKEN` zelf toe. Zonder die store werkt de editor gewoon,
maar bewaart hij alleen in de browser waarin je werkt.

Wil je niet dat iedereen met de link je kaart kan wijzigen, zet dan
`EDIT_PASSWORD` als omgevingsvariabele. De editor vraagt er dan één keer om.

## Opbouw

```
shell.html          de editor, zonder de beelden
img/1..4.b64        kaft en drie achterkanten, uit de originele PDF
bouw.py             plakt die samen tot de twee varianten
serve.py            lokale server: opslaan, reservekopieen, PDF maken
install.py          bouwt en herstart de server in een keer
api/menu.js         opslaan en laden op Vercel
maatvoering.md      alle gemeten waarden van het origineel
```

`menukaart.html` en `public/index.html` worden gegenereerd; bewerk `shell.html`.

## Fonts

Het origineel gebruikt Goudy Old Style en Bernard MT Condensed. Dat zijn
betaalde fonts en die zitten hier niet in. In plaats daarvan staan Sorts Mill
Goudy (een directe Goudy-revival) en Bevan, horizontaal versmald naar 84% als
benadering van Bernard. Heb je de echte fonts op je machine, zet ze dan vooraan
in de font-stack in `shell.html`.
