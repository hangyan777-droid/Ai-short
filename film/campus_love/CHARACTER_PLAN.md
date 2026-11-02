# Haruto and Aoi — character references only

No images have been generated, and no paid requests have been sent. The attached comparison image guides the natural dark hair, white school clothing, quiet expressions and soft daylight. The six prompts create original fictional characters; they do not request exact real-person faces. Neutral backgrounds make reusable reference images more reliable than a finished film scene.

## API selected

Runway developer API, model `gen4_image`, `POST /v1/text_to_image`, 720×1280 PNG output. Official SDK documentation supports up to three `referenceImages`; our side/full images use the accepted front portrait as `@identity`. This checks the documented contract, not live account access or current prices.

Official schema: https://github.com/runwayml/sdk-python/blob/main/src/runwayml/types/text_to_image_create_params.py

## Planning cost, not a verified paid quote

The pricing page still returned HTTP 403 during the read-only check. The model's current price cannot be confirmed here. At the **illustrative** price USD $0.08 per image, USD/CAD 1.40, and 15% tax/fee margin:

| Stage | Images | Estimated CAD (rounded upward per request) |
| --- | ---: | ---: |
| Haruto + Aoi front portraits | 2 | $0.26 |
| Both side and full-body views, after face approval | 4 | $0.52 |
| Six-image reference set | 6 | **$0.78** |
| Optional two-image retry allowance | 2 | $0.26 |
| Planning total including that allowance | 8 | **$1.04** |

All reference charges count toward the episode's CAD $18 cap. Retry allowance is not permission to retry. Minimum credit purchases/account funding may cost more than image consumption. Verify the actual price and funding requirement before approving payment; do not mark the example pricing verified just to bypass the block.

## One key only

Use a **Runway developer API key**. An OpenAI key, ChatGPT subscription, Kling key, or ordinary Runway account login is not needed for these image calls.

1. Open https://docs.dev.runwayml.com/ and follow its developer-console/API-key instructions. Confirm API credits/billing and the current image price.
2. In the cloud environment's secure settings, supply the secret named `RUNWAY_API_KEY`. Review/save and publish the environment changes as required by that interface. No key value belongs in chat.
3. Alternatively, open a local `.env` file in the repository and enter `RUNWAY_API_KEY=your_actual_key` privately. `.env` is ignored by Git. Do not overwrite an existing `.env`, share it, or commit it.
4. No key automatically authorizes a charge. Paid submission also requires verified pricing, your explicit approval and the exact quote hash.

## Recommended two-stage review

The following commands are dry runs unless `--execute` is explicitly added. On Windows replace `.venv/bin/python` with `.venv\Scripts\python.exe`.

First quote only two front portraits:

```bash
.venv/bin/python -m drama_factory.film characters --episode 1 --views front
```

After current pricing has been verified in ignored `film/campus_love/pricing.local.json`, add `--pricing film/campus_love/pricing.local.json` and repeat the dry run. Review the new quote. Only after the owner explicitly approves that precise spend, run the identical command with `--execute --approve-quote APPROVED_HASH`.

We will then show these actual images here for review:

- `assets/characters/haruto/front.png`
- `assets/characters/aoi/front.png`

Check whether you like the faces and whether they look natural, Japanese, age-appropriate and consistent with the intended movie. You can say “approve Haruto's face” or request specific changes. No replacement image will be purchased without separate cost approval. After your visual approval, record it:

```bash
.venv/bin/python -m drama_factory.film approve --episode 1 --asset portrait --character haruto
.venv/bin/python -m drama_factory.film approve --episode 1 --asset portrait --character aoi
```

Then quote the remaining four views, which use those approved faces:

```bash
.venv/bin/python -m drama_factory.film characters --episode 1 --views side full
```

Again, use the verified pricing file, review the quote, and obtain explicit spending approval before adding execution flags. The scoped side/full command is blocked until both front portraits have been visually approved. Runway does not guarantee perfect likeness across views; review face shape, nose/profile, hairline, eyes, outfit, body proportions, hands and shoes.

Once all six exist, make a local six-image review sheet:

```bash
.venv/bin/python -m drama_factory.film character-sheet --episode 1
```

It saves `outputs/episode_01/character_review.jpg`. We can display that image here; no web dashboard is involved. After you approve the complete set:

```bash
.venv/bin/python -m drama_factory.film approve --episode 1 --asset characters
```

This records content hashes in SQLite and writes `assets/characters/APPROVED.json`. PNG files are stored in the permanent Character Bible folders as soon as generated, but remain **unapproved candidates** until review. The approval marker locks the accepted identities for reuse. Back up the folders, approval manifest and `outputs/episode_01/campus.sqlite3`; generated PNGs and the approval manifest are intentionally ignored by Git.

No keyframes, video shots, narration or full episode will be generated in this character stage.

## Six API-ready prompts

### Haruto — front

Photorealistic Japanese live-action coming-of-age film reference. Fictional person, not a celebrity likeness. Natural skin pores, soft window daylight, restrained warm color, quiet expression. No anime, idol styling, beauty filter, skin smoothing, logos or text. Haruto Sato, a fictional 17-year-old Japanese schoolboy. Soft black layered hair with a natural fringe, dark-brown eyes, natural youthful facial proportions, slim build, gentle slightly shy expression. White short-sleeve school shirt, navy straight-leg trousers, plain white sneakers; no accessories. Front-facing head-and-shoulders portrait, eye-level 85mm-style lens, both ears where visible, hair fully in frame, pale neutral background, relaxed closed mouth. Recognizable natural face, simple framing, vertical 9:16.

Reference input: None: create an original fictional face.

### Haruto — side

Photorealistic Japanese live-action coming-of-age film reference. Fictional person, not a celebrity likeness. Natural skin pores, soft window daylight, restrained warm color, quiet expression. No anime, idol styling, beauty filter, skin smoothing, logos or text. Haruto Sato, a fictional 17-year-old Japanese schoolboy. Soft black layered hair with a natural fringe, dark-brown eyes, natural youthful facial proportions, slim build, gentle slightly shy expression. White short-sleeve school shirt, navy straight-leg trousers, plain white sneakers; no accessories. Use @identity as the identity reference: the same face, hairline, age and outfit. True left-side profile, head and shoulders, eye-level lens, nose and ear silhouette clear, pale neutral background, relaxed closed mouth, vertical 9:16.

Reference input: assets/characters/haruto/front.png

### Haruto — full

Photorealistic Japanese live-action coming-of-age film reference. Fictional person, not a celebrity likeness. Natural skin pores, soft window daylight, restrained warm color, quiet expression. No anime, idol styling, beauty filter, skin smoothing, logos or text. Haruto Sato, a fictional 17-year-old Japanese schoolboy. Soft black layered hair with a natural fringe, dark-brown eyes, natural youthful facial proportions, slim build, gentle slightly shy expression. White short-sleeve school shirt, navy straight-leg trousers, plain white sneakers; no accessories. Use @identity as the identity reference: the same face, hair, age and outfit. Head-to-toe front-facing standing reference, eye-level 50mm-style lens, ordinary school posture, arms at sides with hands visible, both shoes fully in frame, pale neutral background, vertical 9:16.

Reference input: assets/characters/haruto/front.png

### Aoi — front

Photorealistic Japanese live-action coming-of-age film reference. Fictional person, not a celebrity likeness. Natural skin pores, soft window daylight, restrained warm color, quiet expression. No anime, idol styling, beauty filter, skin smoothing, logos or text. Aoi Nakamura, a fictional 17-year-old Japanese schoolgirl. Straight dark hair with soft bangs, dark-brown eyes, natural youthful facial proportions, no visible makeup, warm observant expression. White school blouse, loose ivory knit cardigan, navy knee-length pleated skirt, white socks, brown loafers. Front-facing head-and-shoulders portrait, eye-level 85mm-style lens, both ears where visible, hair fully in frame, pale neutral background, relaxed closed mouth. Recognizable natural face, simple framing, vertical 9:16.

Reference input: None: create an original fictional face.

### Aoi — side

Photorealistic Japanese live-action coming-of-age film reference. Fictional person, not a celebrity likeness. Natural skin pores, soft window daylight, restrained warm color, quiet expression. No anime, idol styling, beauty filter, skin smoothing, logos or text. Aoi Nakamura, a fictional 17-year-old Japanese schoolgirl. Straight dark hair with soft bangs, dark-brown eyes, natural youthful facial proportions, no visible makeup, warm observant expression. White school blouse, loose ivory knit cardigan, navy knee-length pleated skirt, white socks, brown loafers. Use @identity as the identity reference: the same face, hairline, age and outfit. True left-side profile, head and shoulders, eye-level lens, nose and ear silhouette clear, pale neutral background, relaxed closed mouth, vertical 9:16.

Reference input: assets/characters/aoi/front.png

### Aoi — full

Photorealistic Japanese live-action coming-of-age film reference. Fictional person, not a celebrity likeness. Natural skin pores, soft window daylight, restrained warm color, quiet expression. No anime, idol styling, beauty filter, skin smoothing, logos or text. Aoi Nakamura, a fictional 17-year-old Japanese schoolgirl. Straight dark hair with soft bangs, dark-brown eyes, natural youthful facial proportions, no visible makeup, warm observant expression. White school blouse, loose ivory knit cardigan, navy knee-length pleated skirt, white socks, brown loafers. Use @identity as the identity reference: the same face, hair, age and outfit. Head-to-toe front-facing standing reference, eye-level 50mm-style lens, ordinary school posture, arms at sides with hands visible, both shoes fully in frame, pale neutral background, vertical 9:16.

Reference input: assets/characters/aoi/front.png
