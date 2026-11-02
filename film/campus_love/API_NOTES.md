# API contract checks and pricing status

Read-only official SDK sources were inspected during implementation. No image, video or speech requests were submitted to real providers.

## Runway

- Base URL: `https://api.dev.runwayml.com/v1`
- Authentication: `Authorization: Bearer …`; version header `X-Runway-Version: 2024-11-06`.
- Images: `POST /text_to_image`, model `gen4_image`, `promptText`, `ratio: 720:1280`, optional `referenceImages` with `uri` and `tag`; up to three references. Tags use letters/digits/underscores, 3–16 characters. The adapter uses PNG data URIs below 5 MB.
- Video: `POST /image_to_video`, model `gen4_turbo`, `promptImage`, `promptText`, `duration`, `ratio: 720:1280`.
- Optional video model: the current SDK schema includes **`kling3.0_standard`**, with `audio: false` supported. The adapter sends that flag explicitly for the no-audio path. It does not send `audio` to Gen-4 Turbo. Live account/model availability and permitted five-second duration still need verification before any submission.
- Polling: `GET /tasks/{id}`; save IDs before polling. Handle `SUCCEEDED`, `FAILED`, `CANCELED`/`CANCELLED`, queued/running states, and bounded transient polling errors.
- Download task outputs with a fresh unauthenticated client; never forward API credentials to asset hosts. Redirects are deliberately not followed; inspect and allow the exact legitimate asset destination before resuming.
- No undocumented idempotency parameter is invented. Unknown POST outcomes are held for investigation, not retried. A crash after submission but before storing its task ID cannot be automatically resolved safely.

Sources:

- https://github.com/runwayml/sdk-python/blob/main/src/runwayml/types/text_to_image_create_params.py
- https://github.com/runwayml/sdk-python/blob/main/src/runwayml/resources/text_to_image.py
- https://github.com/runwayml/sdk-python/blob/main/src/runwayml/types/image_to_video_create_params.py
- https://github.com/runwayml/sdk-python/blob/main/src/runwayml/resources/tasks.py
- https://github.com/runwayml/sdk-python/blob/main/src/runwayml/_client.py

## Japanese speech

OpenAI adapter: `POST https://api.openai.com/v1/audio/speech`, `model: tts-1`, `input`, configurable supported `voice`, `response_format: wav`. Haruto defaults to `alloy`; Aoi to `nova`. Narration/dialogue is Japanese text. These are generic synthetic voices, not guaranteed age-specific or actor-grade performances. There is no lip synchronization claim. Dialogue is treated as remembered/off-camera audio and faces are prompted not to speak.

Source: https://github.com/openai/openai-python/blob/main/src/openai/types/audio/speech_create_params.py . Test Japanese diction, pronunciation and emotional delivery before accepting the real film. OpenAI is the implemented TTS provider; other vendors need an adapter and verified pricing before they can be selected. `TTS_PROVIDER` rejects unsupported providers rather than guessing an API.

## Pricing and model verification are still required

The official Runway pricing page returned HTTP 403 in this environment. The reason was not established; this is not evidence of missing API credentials. Therefore **the checked-in pricing file is illustrative and unverified**, not a current price promise. Before paid use, verify official prices, model access, requested duration/resolution, tax and FX:

- https://docs.dev.runwayml.com/guides/pricing/
- https://docs.dev.runwayml.com/api/
- https://openai.com/api/pricing/

Copy `pricing.example.json` to ignored `pricing.local.json`, set real unit prices/rate/margin, add official sources, and only then set `verified_at` to the UTC verification timestamp and `capabilities_verified` to true. Verification expires after seven days. Every paid task rechecks it; every request reserves a conservative CAD amount first. Japanese TTS quoting uses UTF-8 byte length as a conservative character-count allowance.

The SDK schema checks validate field names, not current prices, successful live generation, exact actual charges, or character consistency. Operator-confirmed prices plus local reservations enforce the configured CAD cap; unexpected provider billing must still be reconciled. A provider-side account spending limit is recommended where supported. Do not assume an API-credit purchase minimum is covered by per-episode consumption estimates.
