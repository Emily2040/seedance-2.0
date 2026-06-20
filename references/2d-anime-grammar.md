# 2D / Anime Grammar — direct the medium, not a camera rig

*Seedance 2.0 renders stylized 2D and anime motion well, but live-action grammar degrades it: lens, depth-of-field, and sensor vocabulary pulls outputs toward photorealism or a fake tilt-shift look. Direct 2D work in animation-production language instead. Labels: [field] = practitioner-reported · [heuristic] = default to test. Craft guidance compiled 2026-06-11; contains no platform-availability claims.*

## Core rule [field]

Name the medium first and keep every sentence inside the animation process: "hand-drawn 2D animation, cel-shaded characters over a painted background." Never use lens, bokeh, depth-of-field, focal-length, or camera-body vocabulary in a 2D prompt — it summons photoreal rendering.

## Layer grammar [field]

2D scenes read as stacked artwork layers, and the model responds to layer language:

- **Cel over painted background:** crisp cel-shaded subjects over a soft gouache or watercolor painted background.
- **Background scroll / multiplane depth:** "the painted background scrolls past" or "foreground silhouettes slide faster than the distant skyline" for parallax.
- **Held background, animated subject:** declare what stays still — held frames are a feature of the medium, not a failure.

## Motion grammar [field]

- **Burst animation (sakuga) vs held frames:** alternate high-effort fully animated bursts with held poses: "a burst of fluid full animation as she turns, then a held frame on her expression."
- **Timing:** "animated on twos" for classic cel cadence; "on ones" only for the showcase move. [heuristic]
- **Impact frames:** "a single high-contrast impact frame on the hit."
- **Speed lines and smears:** "speed lines streak the background during the dash," "her arm smears across the swing."
- **Follow-through:** hair, cloth, and coat tails keep settling after the body stops.

## Camera in 2D [field]

The "camera" is a rostrum over artwork: pan across the painted background, slow push-in on a held face, vertical tilt down the tower artwork. One motivated move per shot still applies. Avoid dolly, handheld shake, and lens-breathing realism wording.

## Light and color [field]

Light is drawn, not rendered: "hard two-tone cel shadow," "rim light as a clean shape along the jaw," "specular drawn as a white wedge in the eye." Name palette and finish: "limited palette, warm paper texture," "flat color with painted light bloom."

## Sound for 2D [heuristic]

Stylized sound reads better than realistic foley: a whoosh on the smear, a sharp sting on the impact frame, room tone dropping out on the held frame.

## Style safety [field]

Describe technique, era, and palette — never a studio, franchise, or living artist. "1990s hand-painted TV-anime look with grainy film texture" is safe grammar; named-studio or franchise style requests route through `[skill:seedance-copyright]` and `[skill:seedance-style]`.

## Failure → fix [field]

| Symptom | Fix |
|---|---|
| Output drifts photoreal or 3D-CG | remove lens and depth-of-field words; lead with "hand-drawn 2D cel animation"; name the painted background |
| Motion feels floaty or rotoscoped | ask for snappy bursts "on twos," held frames between beats, smears on fast arcs |
| Faces melt during fast action | put the speed into lines, smears, and background scroll instead of facial detail; cut to a held impact frame |
| Style flickers between shots | repeat the exact medium line in every shot of a multi-shot prompt; keep one palette phrase constant |

## Sequence Boundary [heuristic]

For connected 2D clips, preserve character sheets, palette, line weight, layer roles, screen direction, and open motion. Use observed final layout from the accepted clip as the next opening layout. Do not switch to photographic lens or sensor language when writing continuation prompts.
