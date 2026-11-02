# AI Short Drama Factory

A Python + Streamlit prototype for 60-second school romance episodes. It runs entirely locally without API keys or paid credits.

## Start

Requires Python 3.11+ and FFmpeg (including ffprobe and libx264) on PATH. On Ubuntu install FFmpeg with `sudo apt-get update && sudo apt-get install -y ffmpeg`.

```bash
cd /workspace/Ai-short
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# Optional: copy .env.example to .env; no key is needed for mock mode.
.venv/bin/streamlit run app.py --server.headless true
```

Open the Streamlit address printed in your terminal when running locally. Edit the premise and reusable male/female character profiles, then click **Generate Episode**. Profiles persist across Streamlit reruns in the current session and are exported with every storyboard. Defaults live in `drama_factory/core.py`.

Each unique `outputs/<episode-id>/` directory contains a storyboard with character descriptions, six 10-second scene clips, captions, a budget report, and the assembled portrait MP4. The MP4 contains H.264 video, silent AAC audio, and a selectable subtitle track; captions can also be downloaded as SRT. Some browser players do not show embedded subtitles: use the storyboard or enable subtitles in a compatible player.

## What works now

- Deterministic six-beat romance planning incorporating your premise and character names.
- Real FFmpeg rendering and assembly of a 60-second, 360×640 mock video.
- Dashboard previews and downloads; mock spend is CAD $0.00.
- Decimal-based budget checks reject invalid, negative, nonfinite and over-CAD-$18 totals.
- Provider protocol, episode preflight cost authorization, and disabled Runway adapter boundary.

Mock output is colored placeholder footage, not generated cinematic imagery, narration or music. The template is intentionally deterministic; the premise is included in scene prompts rather than interpreted by an LLM. Generated files remain on disk until manually deleted.

## Runway integration architecture

`drama_factory/providers.py` defines scene quoting and clip generation interfaces. `RunwayProvider` deliberately raises `NotImplementedError`; no HTTP SDK or paid endpoint is invoked. `.env.example` documents the future key name only. Setting a key does not enable paid generation.

Before enabling real calls, implement a separately reviewed adapter using current official Runway documentation: choose model and supported durations, provision reference character assets, price all scenes in CAD with an explicit exchange rate and tax/retry buffer, reserve the entire episode budget before submission, persist task IDs for idempotency, poll with bounded retries, download and validate media, and reconcile charges. API billing cannot be guaranteed by an estimate alone; use provider/account spending controls as well. The mock release cannot spend credits.

## Tests

```bash
.venv/bin/python -m pytest -q
```

Tests exercise story planning, invalid inputs, the CAD limit and cumulative quotes, disabled paid generation, dashboard interaction, and actual FFmpeg output including full video decoding, duration, resolution and stream validation. No API credentials are required.
