# Music Finder

A small web app for searching and downloading audio that the source/provider exposes for download.

## Run
```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```
Open http://127.0.0.1:8000

## Important
This app does not bypass DRM, paywalls, protected playback, or provider restrictions. Commercial songs may appear as source links but are not converted into MP3 unless the provider exposes an authorized/downloadable file.

Sources currently wired:
- Internet Archive audio items
- Audius public catalog/stream resolution

For a large authorized downloadable catalog, Jamendo can be added with a developer client_id; its API explicitly exposes whether a track is downloadable.
