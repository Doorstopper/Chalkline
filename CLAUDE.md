# CLAUDE.md

## What this is

Chalkline is a single-file HTML PWA for tagging and telestrating youth soccer footage.

- **`index.html` is the entire app** — all markup, styles, and logic live in this one file.
- **`sw.js`** is a cache-first service worker.
- Deployed via **GitHub Pages from the root of this repo**.

## Critical deploy rule

The `CACHE` version string in `sw.js` **must be bumped on every deploy**. The service worker is cache-first, so if the version string is unchanged, phones will serve stale cached copies of the app instead of the new deploy. Bump it whenever `index.html` (or any cached asset) changes.

## "Deploy" means (routine)

When the user says **"deploy"**, run this routine:

1. **Bump the cache version** in `sw.js` — increment the `CACHE` string
   (`chalkline-v1` → `chalkline-v2`, etc.). This is mandatory; without it phones
   serve the stale cached app.
2. **Commit** all pending changes with a sensible, specific message describing
   what changed in this deploy.
3. **Push** to `origin` (`main`). GitHub Pages serves from the repo root, so the
   push is the deploy — the live site updates within a couple of minutes.

The cache bump is non-negotiable and is part of every deploy, even if `sw.js`
itself wasn't otherwise touched.

## Single source of truth

`index.html` is the **only** copy of the app. There is no `chalkline.html` — it
was eliminated. The same `index.html` serves both roles:

- **Hosted:** deployed to GitHub Pages and installed to phones as a PWA.
- **Local:** opened straight off disk via a desktop shortcut. Service-worker
  registration is guarded to `http(s)` (see `index.html`), so it simply skips on
  `file://` and the app runs fine as a local file.

The desktop shortcut is created by `Create Chalkline shortcut.cmd`, which points
at the local `index.html` in this repo folder. Never fork the app into a second
HTML file again — edit `index.html` only.

## App structure

- **Studio tab** — the app. Load a match, tag as you watch, telestrate, export.
- **Sideline tab** — **retired** (v110). The phone-first live-capture view was
  removed from the UI: the tab button and routing are gone and the app always
  opens in Studio. The `#sideline` `<section>` and its JS are kept dormant in the
  file (hidden) so shared code still resolves — do not delete them piecemeal, or
  the many `$('#sideline-element')` handlers throw at load. Pad editing, Save,
  Clear and Sync were surfaced in Studio when Sideline was retired.

## Known constraints & gotchas

- **iOS Photo Library picker stalls on long videos.** Users must use **"Choose Files"** rather than the Photo Library picker.
- **HEVC won't decode in some browsers.** There is a **black-frame probe** that detects this and warns the user.
- Studio is designed laptop-first; Sideline is designed phone-first. Keep layout/interaction assumptions aligned with the target device for each tab.

## Repo layout

- `index.html` — the app (deployed)
- `chalkline.html` — local desktop-shortcut copy (no manifest/SW)
- `sw.js` — cache-first service worker (bump `CACHE` on every deploy)
- `manifest.webmanifest` — PWA manifest
- `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` — app icons
- `Create Chalkline shortcut.cmd` — makes a Desktop shortcut to the local `index.html`
- `README-hosting.md` — hosting + install notes
