# The Seat Beside You — production pack

An original 60-second first-love short, 12 shots × 5 seconds, 9:16, photorealistic Korean youth-drama aesthetic. Both fictional protagonists are 18-year-old final-year students. Romance stays innocent: glances, a mistaken invitation, a returned sketchbook, and a shared walk.

`episode.json` is the full script, subtitle timeline, locked character descriptions, detailed still-image prompts, motion prompts and per-shot review checklist. The first four shots establish the crush; shots 5–6 introduce the misunderstanding; shots 7–8 reveal the truth; shots 9–12 resolve it. Captions tell the story without paid speech or lip-sync generation.

## Character consistency before video generation

1. Create and approve a front portrait, three-quarter portrait and full-length uniform reference for each character from the locked descriptions. No real student photos are needed.
2. Create 12 portrait first-frame images using the image prompts and those same references in an image generator that explicitly supports image references. Save the approved PNGs as `film/frames/01.png` through `12.png`, each at 720×1280, below 5 MB. Check identities and uniforms side by side before approval. Blank note/envelope text is intentional; story text comes from captions.
3. Gen-4 Turbo animates each approved first frame. It does not receive an invented multi-character reference parameter. Prompt repetition and seeds do not guarantee identical faces; the approved frames and human review are essential. These frames are missing today; no paid generation has occurred.

## Music and subtitles

The CLI composes a quiet original synthesized piano-like instrumental locally, no downloaded or copyrighted recordings. It adds fade-in/out and burns the English script into the final 720×1280 H.264/AAC MP4. SRT is also exported. No voiceover, paid TTS or paid music service is required. This is a music-led subtitled film.

## Budget proposal — requires approval, not authorization

Illustrative only, **not a verified current provider quote**: if Gen-4 Turbo costs USD $0.05 per generated second, 60 seconds costs USD $3.00, or CAD $4.83 at USD/CAD 1.40 with 15% margin. Reserve CAD $5 for reference/keyframe images and CAD $8.17 for uncertainty within the $18 ceiling. There are no automatic video retries. If actual image or video pricing differs, revise the quote before approval. Purchased minimum credit bundles may cost more than episode consumption; this must also be approved separately.

The CLI requires an explicit current per-second USD price, price-source string, incurred image costs and image file hashes to create a quote. All costs already incurred for this film count against $18. Do not mark reference/keyframe costs zero unless they were genuinely free. Keep all retries inside the same production directory. No OpenAI image integration or paid reference generation is silently included.

## Commands

From the repository root, with dependencies installed:

```bash
# Free editing test only; never the final AI deliverable:
.venv/bin/python -m drama_factory.film mock --output outputs/film-test
# After preparing and approving all 12 actual keyframes, quote only:
.venv/bin/python -m drama_factory.film quote --usd-per-second 0.05 --rate 1.40 --margin 0.15 --prior-cad 5 --price-source 'REPLACE with verified provider pricing URL and date' --output outputs/film-real
# AFTER explicit user approval of that exact quote, key securely in .env:
.venv/bin/python -m drama_factory.film generate --output outputs/film-real --approve-quote QUOTE_SHA256
# Assemble downloaded shots after reviewing them; rerunning generation resumes polling.
.venv/bin/python -m drama_factory.film assemble --output outputs/film-real
```

Use `.venv\Scripts\python.exe` instead on Windows. Set `RUNWAY_API_KEY` securely in `.env`; never send it in chat or commit it. Runway API network access must be allowed by environment settings before paid use. Generated media download hosts may also need allowing after their exact URLs are returned.

The quote hash binds the script, input frame hashes, CAD rate, margins and prior costs. A local lock prevents concurrent runs. A persisted reservation is written before each POST; task IDs are stored immediately. An ambiguous submission is **never retried automatically**: stop and reconcile it with Runway. Poll/download errors can resume the same task, without paying for a new generation. Failed paid tasks retain their reservation. No claim of exactly-once remote submission or exact actual billing is made; costs are conservative committed estimates until reconciled against provider billing. Keep the ledger; do not delete it to retry.

## Verified API architecture

Official Runway SDK sources were inspected for `POST https://api.dev.runwayml.com/v1/image_to_video`, `GET /v1/tasks/{id}`, `Authorization: Bearer …`, `X-Runway-Version: 2024-11-06`, model `gen4_turbo`, `promptImage` data URI, `promptText`, `duration`, and vertical `ratio: 720:1280`.

Sources: https://github.com/runwayml/sdk-python/blob/main/src/runwayml/resources/image_to_video.py and https://github.com/runwayml/sdk-python/blob/main/src/runwayml/types/image_to_video_create_params.py and https://github.com/runwayml/sdk-python/blob/main/src/runwayml/_client.py . Live account permissions, current pricing and successful paid generation remain unverified. Kling is not integrated in this first film workflow.
