# CAMPUS LOVE

**The goal is a real Japanese live-action-style romance short film, not a website.** FastAPI and Streamlit work is paused. This is a command-line production workflow for one 60-second, 720×1280 vertical film, with Japanese voice-over and simplified Chinese subtitles.

Episode 01: **《那年夏天，她坐在我前面》** / **あの夏、君は僕の前の席にいた。**

Haruto has a quiet crush on Aoi, the girl sitting in front of him. Borrowing an eraser becomes a summer memory; a graduation note reveals her feelings. Their romance stays innocent. Both are original fictional 17-year-old Japanese students, with natural faces and ordinary school clothing; no celebrity imitation, anime or idol styling.

## What exists now

- [Screenplay, Character Bible and twelve detailed shot prompts](film/campus_love/PRODUCTION.md).
- Editable [storyboard source](film/campus_love/episode_01.json), Japanese voice lines, Chinese subtitles, locations, camera motion and continuity notes.
- Permanent `assets/characters/haruto/` and `assets/characters/aoi/` folders. Text Bibles exist; actual portraits await permission to generate.
- Documented Runway reference-image and image-to-video adapters, optional Kling no-audio request fields, Japanese OpenAI TTS adapter, SQLite job/budget state, human approval gates and resumable task polling.
- Local FFmpeg assembly with original synthesized music, procedural ambience, timed voice slots, Chinese captions, Japanese message overlays, opening title and final fade.
- A technical test render is **not** the real film. No paid media or genuine Japanese speech has been generated yet.

## Install — Windows beginner instructions

Install Python 3.11+ and FFmpeg (including ffprobe, libx264 and libass/subtitles). On Windows you can use `winget install Python.Python.3.12` and `winget install Gyan.FFmpeg`, then reopen PowerShell. Install a Chinese/Japanese-capable font such as Noto Sans CJK JP and SC for reliable captions.

From the downloaded/cloned repository:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe -m drama_factory.film preproduce --episode 1
.venv\Scripts\python.exe -m drama_factory.film test-shot --episode 1 --shot 1
```

On Linux/macOS replace `.venv\Scripts\python.exe` with `.venv/bin/python`. On Ubuntu install `ffmpeg fonts-noto-cjk`; on macOS install FFmpeg and suitable CJK fonts. No web server is needed.

## Three production modes

All commands run from the repository root. The default episode directory is `outputs/episode_01/`. `--output` can change it, but **keep one permanent real-production directory and its database for this episode**; never start over in another directory to bypass incurred costs.

### 1. Preproduction — completely local

```bash
python -m drama_factory.film preproduce --episode 1
```

Creates `storyboard.json`, readable `PRODUCTION.md`, budget estimate and cost report. Edit the output storyboard before approving any media. Repeating preproduction preserves your edited storyboard and refreshes the readable plan. Once assets are paid for, changing story/profile inputs invalidates approvals and is not a free regeneration.

### 2. Test shot — dry-run first

```bash
python -m drama_factory.film test-shot --episode 1 --shot 1
```

This always defaults to a dry run. It prints the price, missing prerequisites and a quote hash; it does not send any provider requests. To make one real five-second shot, first complete the character/keyframe steps below, verify prices, configure credentials, and obtain explicit user approval of the exact quote. Then append `--execute --approve-quote HASH` and use the same verified pricing file.

After generating it, inspect face consistency, hands, school uniforms, camera movement and motion quality. Record acceptance:

```bash
python -m drama_factory.film approve --episode 1 --asset test-shot --shot 1
```

This accepts a real, unchanged API clip only. Mock video cannot satisfy this gate. The first real test must be shot 1; other shots can be individually tested later, but do not replace the first-shot full-production gate.

### 3. Full production — dry-run first, then approved execution

```bash
python -m drama_factory.film produce --episode 1
```

It reports remaining tasks and cumulative costs. Execution requires approved characters, approved keyframes, an approved real test shot, current pricing, credentials and an approved quote hash. It resumes the successful test instead of paying for it again. Once authorized with `--execute --approve-quote HASH`, Japanese speech is generated and checked before the remaining video shots, followed by automatic assembly.

The final real output will be:

```text
outputs/episode_01/final_9x16.mp4
```

Also retained: keyframes, individual clips, voice files, original score, ambience, ASS/SRT subtitles, SQLite state, quotes, `cost_report.json`, `render_manifest.json` and `rendering.log`. For editorial-only fixes after completed media generation, run `python -m drama_factory.film edit --episode 1`; this sends no provider requests. Human review is still required before publishing.

## Preparing characters and keyframes

These actions also default to dry runs and require separately approved quote hashes before paid execution:

```bash
python -m drama_factory.film characters --episode 1
# After verified price + explicit approval, rerun with --pricing ... --execute --approve-quote HASH.
# Review front, side and full-body images for BOTH characters, then:
python -m drama_factory.film approve --episode 1 --asset characters
python -m drama_factory.film keyframes --episode 1
# After approval and generation, review the test keyframe:
python -m drama_factory.film approve --episode 1 --asset keyframe --shot 1
# Review all twelve frames before full production:
python -m drama_factory.film approve --episode 1 --asset keyframes
```

Front portraits are created once. Side/full references use those same generated fronts; human approval happens before shot images are generated. Keyframes use the approved faces plus a wardrobe reference, within Runway's three-reference limit. Reference fingerprints and file hashes bind approvals; changes invalidate them. Completed unchanged assets are reused, never blindly overwritten. Character consistency is not guaranteed: every shot starts flagged for human review in the storyboard.

Keep reference PNGs under `assets/characters/<name>/{front,side,full}.png` permanently. They are ignored by Git to avoid accidentally committing generated binary media; back them up with the SQLite production state. Copying untracked external paid assets into these folders is not an accounting import: do not do so without recording their cost/provenance. An automatic external-asset import tool is not included in this milestone.

## Credentials and exact paid authorization

1. Use the official [Runway developer documentation](https://docs.dev.runwayml.com/) to open its developer console and create an API key. API billing/credits may be separate from a consumer Runway subscription.
2. For narration, create an API key in the [OpenAI platform](https://platform.openai.com/api-keys) with appropriate billing access.
3. Put `RUNWAY_API_KEY` and `OPENAI_API_KEY` in your local ignored `.env`, or configure them securely in the cloud environment. Never paste them into chat or commit them. Keep `.env` even after copying a new template. Merely setting a key does not authorize spending.
4. Copy `film/campus_love/pricing.example.json` to ignored `film/campus_love/pricing.local.json`. Confirm official per-model prices, five-second/720p support and account access; enter current FX/tax margin, verification sources and UTC timestamp. Set `capabilities_verified` true only after checking. [API contract details](film/campus_love/API_NOTES.md).
5. Use `--pricing film/campus_love/pricing.local.json` on the dry run. Resolve blockers, rerun it, review its exact CAD total and obtain explicit user approval. Each stage needs approval of its own quote. Never execute using the hash of an earlier, blocked or changed plan.
6. Only then rerun the identical command with `--execute --approve-quote THE_HASH_PRINTED_BY_THAT_DRY_RUN`. The code checks that the quote still matches all inputs.

Example, **only after approval**:

```bash
python -m drama_factory.film test-shot --episode 1 --shot 1 --pricing film/campus_love/pricing.local.json --execute --approve-quote APPROVED_HASH
```

Cloud networking must allow `api.dev.runwayml.com` and `api.openai.com`; Runway's exact output-host destinations may need to be added when known. Do not disable TLS verification or bypass a policy denial.

## Budget and recovery

The checked-in prices are illustrative, **not a current provider quote**. At USD $0.05/video-second, $0.08/image, USD/CAD 1.40 and 15% tax margin, the rounded estimates are:

| Scope | CAD |
| --- | ---: |
| One 5-second Gen-4 Turbo video, existing approved inputs | $0.41 |
| Six character references | $0.78 |
| Twelve keyframes | $1.56 |
| Twelve video shots | $4.92 |
| Japanese narration, conservatively quoted | $0.11 |
| Base episode | **$7.37** |
| With two video retries, two image retries and audio allowance | **$8.49** |

These exclude minimum credit-package purchases; approval must distinguish account funding from this film's consumption. Default pricing is intentionally unverified, so it blocks paid execution. The conservative allowance is not authorization to regenerate shots. Premium Kling unit pricing is also only an editable placeholder, not a verified quote. Change a shot's model in the storyboard, then recalculate and obtain a new approval before production.

SQLite reserves the full per-request estimated CAD charge **before** submission and checks the $18 cumulative cap. Unknown actual costs keep their reservations. No expensive request is automatically retried. A submitted task ID is reused after polling/download failures. Ambiguous submission outcomes require checking provider history; do not delete a request or lock/database to force another submission.

When verified provider billing is available, record actual CAD cost and release any unused reservation:

```bash
python -m drama_factory.film reconcile --episode 1 --request-id video:01 --actual-cad 0.40 --billing-source "Verified provider invoice and conversion record"
```

Only confirmed complete/failed requests can reconcile. Actual billing above the cap is recorded truthfully and stops further production; software estimates cannot force a provider to honor stale or incorrect prices. Unknown POST outcomes need investigation before reconciliation. A stale `production.lock` can be removed only after confirming its producer process has stopped. Run one producer per episode and retain all billing state.

## Free pipeline check and tests

```bash
python -m drama_factory.film render-test --episode 1 --output outputs/episode_01_pipeline_test
python -m pytest -q
```

The free render writes `pipeline_test_9x16.mp4`, **not** `final_9x16.mp4`, and marks it visibly as a test. It contains colored footage and timing tones instead of Japanese speech. It exercises the real FFmpeg edit, Chinese captions, Japanese overlays, original music, procedural rain/cicada/footstep ambience, voice slots and exact duration without calling any paid service. Mock output cannot be promoted into a real final render.

Tests cover provider payloads using stubbed HTTP, the reference→keyframe→one-shot→approval→remaining-shots sequence, saved-task reuse, cost reservations/reconciliation, stale pricing, missing approvals, quote hashes, subtitle content, and legacy behavior. Legacy web files remain for history; do not start a dashboard or API server for this production workflow.
