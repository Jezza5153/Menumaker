import { put, list } from '@vercel/blob';

const KEY = 'menu.json';
const MAX_BACKUPS = 60;

function heeftOpslag() {
  return Boolean(process.env.BLOB_READ_WRITE_TOKEN);
}

async function huidigeUrl() {
  const { blobs } = await list({ prefix: KEY, limit: 1 });
  return blobs.length ? blobs[0].url : null;
}

export default async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');

  if (!heeftOpslag()) {
    // Zonder Blob-opslag draait de editor gewoon door, maar bewaart hij
    // alleen in de browser. Zie README voor het aanzetten.
    return res.status(501).json({ fout: 'geen opslag ingesteld' });
  }

  if (req.method === 'GET') {
    try {
      const url = await huidigeUrl();
      if (!url) return res.status(404).json({});
      const r = await fetch(url, { cache: 'no-store' });
      if (!r.ok) return res.status(404).json({});
      return res.status(200).json(await r.json());
    } catch (e) {
      return res.status(404).json({});
    }
  }

  if (req.method === 'POST') {
    const sleutel = process.env.EDIT_PASSWORD;
    if (sleutel && req.headers['x-tafelaar-key'] !== sleutel) {
      return res.status(401).json({ fout: 'sleutel onjuist' });
    }

    const body = typeof req.body === 'string' ? req.body : JSON.stringify(req.body);
    try {
      JSON.parse(body);
    } catch {
      return res.status(400).json({ fout: 'onleesbare inhoud' });
    }

    const opties = {
      access: 'public',
      contentType: 'application/json',
      addRandomSuffix: false,
      allowOverwrite: true,
    };

    // eerst de reservekopie, dan pas overschrijven
    const stempel = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    await put(`backups/menu_${stempel}.json`, body, opties);
    await put(KEY, body, opties);

    // oude kopieen opruimen
    try {
      const { blobs } = await list({ prefix: 'backups/' });
      const oud = blobs
        .sort((a, b) => new Date(a.uploadedAt) - new Date(b.uploadedAt))
        .slice(0, Math.max(0, blobs.length - MAX_BACKUPS));
      if (oud.length) {
        const { del } = await import('@vercel/blob');
        await del(oud.map((b) => b.url));
      }
    } catch {
      // opruimen is bijzaak, nooit de bewaaractie laten mislukken
    }

    return res.status(200).json({ ok: true });
  }

  return res.status(405).json({ fout: 'methode niet toegestaan' });
}
