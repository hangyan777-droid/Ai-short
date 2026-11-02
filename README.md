# The Seat Beside You — AI romance film production

The project now focuses on producing **one real, cinematic, 60-second Korean youth-romance short**, not building an app. The earlier dashboard/backend are paused; their instructions are archived in `docs/APP_ARCHIVE.md`.

## Start here

Read [the production plan](film/PRODUCTION.md). The full original script, two locked character descriptions, twelve detailed still-image prompts, motion prompts and subtitle timeline are in [film/episode.json](film/episode.json).

The film is vertical 9:16, twelve 5-second shots, with an innocent high-school first-love plot. Both fictional protagonists are 18. The intended look is photorealistic with warm spring light, stylish uniforms and natural acting. Approved reference portraits and shot keyframes are required to preserve identity; they are not yet created.

## Install

Requires Python 3.11+, FFmpeg/ffprobe with libx264 and the subtitles/libass filter, and a usable font. Ubuntu: `sudo apt-get install ffmpeg fonts-dejavu-core`. Windows: install Python and FFmpeg, reopen PowerShell, then run:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m drama_factory.film mock --output outputs/film-test
```

On Linux/macOS:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m drama_factory.film mock --output outputs/film-test
```

This free test checks editing, burned-in subtitles, an original synthesized music score, and 720×1280 H.264/AAC output. **`PIPELINE_TEST.mp4` is only a technical test, never the final AI film.**

## Paid production is approval-gated

No paid calls have been made. Do not provide keys in chat. Before production, prepare and approve the 12 actual 720×1280 PNG keyframes, verify current Runway pricing, account funding and prior image costs, and obtain user approval of the complete estimate within CAD $18. Then configure `RUNWAY_API_KEY` securely in `.env`.

The CLI supports `quote`, `generate`, and `assemble`; exact commands and known prerequisites are in the production plan. It uses verified Runway image-to-video and task endpoints, saves task IDs and conservative reservations, resumes polling, and refuses automatic paid resubmission after an ambiguous request. Separate HTTP clients keep API authorization out of asset downloads. Retain the production ledger across failures; it is not an actual-billing reconciliation system.

Reference/keyframe creation and paid video generation still need key access, pricing approval, live API validation, and human quality review. Neither a working mock nor a successful API response proves the cinematic quality or character consistency of the final film. No automatic retries, upscaling, paid speech, music subscription, or web server is needed for this film workflow.

## Tests

```bash
.venv/bin/python -m pytest tests/test_film.py tests/test_workflow.py -q
```

Tests use local inputs and stubbed API transports; they never spend credits. Legacy application tests remain available but are outside the active production direction.
