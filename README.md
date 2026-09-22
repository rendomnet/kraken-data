# kraken-data

Static platform catalogues for [Kraken](https://github.com/rendomnet/tauri-app), served over CDN.

## What lives here

One folder per platform. Each holds a `catalogue.json` and the artwork it references.

| Platform | Catalogue |
| --- | --- |
| Battle.net | [`battlenet/catalogue.json`](battlenet/catalogue.json) |

## How Kraken reads it

```
https://cdn.jsdelivr.net/gh/rendomnet/kraken-data@main/<platform>/catalogue.json
```

**These URLs are permanent.** Shipped releases of Kraken request them forever, including versions from years ago. This repository must therefore stay public and keep its name. Do not rename it, make it private, or move the folder layout.

jsDelivr caches `@main` for up to 12 hours, so an edit reaches users within hours rather than instantly.

## Catalogue format

```jsonc
{
  "version": 1,                 // schema version
  "updatedAt": "2026-09-22T00:00:00Z",
  "artBase": "https://cdn.jsdelivr.net/gh/rendomnet/kraken-data@main/<platform>/art",
  "games": [
    {
      "productCode": "Fen",     // stable identity — never change it
      "name": "Diablo IV",
      "segment": "diablo-4",    // news feed slug; omit when the title has no feed
      "launchUri": "battlenet://Fen",
      "launchArgs": "--exec=\"launch Fen\"",
      "art": { "portrait": "...", "landscape": "...", "hero": "...", "logo": "..." },
      "meta": { "developer": "...", "publisher": "...", "releaseDate": "YYYY-MM-DD", "genres": ["..."] }
    }
  ]
}
```

`art` paths are relative to `artBase`. Install state is never stored here — Kraken determines that on the user's machine.

## Editing

Kraken skips malformed entries rather than failing the whole load, and ships a bundled copy of each catalogue as a fallback, so a bad edit degrades rather than breaks. CI still validates every catalogue on push — keep it green.

Changing a `productCode` orphans that game in every existing install. Add a new entry instead.
