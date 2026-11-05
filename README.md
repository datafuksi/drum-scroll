# Drum Scroll

Auto-scrolling drum notation for the iPad. Press play, the lines scroll in time with the song.

## Run it
**Same Wi-Fi as the laptop:** `python serve.py` in this folder, then open the printed
`http://192.168.x.x:8765` in Safari on the iPad. Share > Add to Home Screen for a full-screen app.
Needs internet on the iPad for the YouTube video (Timer mode works without).

**Anywhere:** the private Artifact link (see chat) works without the laptop.

## How it syncs
Each song = list of strips + the video timestamp where each strip starts (`songs.js`).
Scroll position is a smooth curve through those timestamps, driven by the embedded YouTube
player's clock, so pause / seek / slow-down all keep the notes in sync.
Settings (gear): Video vs Timer mode, speed, per-song Sync nudge, reading-line height, cursor.
Double-tap a strip to jump to it. Drag the page = pause follow until "Follow song".

## Adding / fixing songs
Edit `SONGS` / `TIMES` in `build.py`, run `python build.py`.
Summer of '69 has no timestamps, only tempo (138 bpm) and bar numbers; use Sync to line up
the bar where the drums enter (bar 14).
