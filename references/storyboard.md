  if json.seg exists and len > 0:
    for each s in json.seg:
      line = s.t + ": " + s.act
      if s.cam: line += " Camera: " + s.cam
      if s.sfx: line += " SFX: " + join(s.sfx, " + ")
      out.append(line)
  else:
    out.append( json.shot.act )

  // BLOCK 4: Global camera (always present for L2+)
  if json.shot.cam: out.append( "Camera: " + json.shot.cam )

  // BLOCK 5: Light
  if json.shot.light: out.append( "Light: " + json.shot.light )

  // BLOCK 6: Style (join array, max 3)
  if json.shot.style: out.append( join(json.shot.style, ", ") )

  // BLOCK 7: Sound
  snd_parts = []
  if json.shot.snd.amb: snd_parts.append(json.shot.snd.amb)
  for sfx in json.shot.snd.sfx: snd_parts.append(sfx)
  if json.shot.snd.mx: snd_parts.append(json.shot.snd.mx)
  if snd_parts: out.append( "Sound: " + join(snd_parts, ". ") )

  // BLOCK 8: Lock constraints
  if json.lock: out.append( join(json.lock, ", ") )

  // BLOCK 9: Exit
  if json.exit: out.append( json.exit )

  return join(out, "\n")
```

---

### Budget Triage (When Compiled Prompt Is Too Long)

Cut in this strict order. Never skip ahead.

| Cut order | What to remove | Never remove |
|-----------|---------------|--------------|
| 1st | `shot.style` entries beyond first token | `shot.subj` |
| 2nd | `shot.snd.mx` description detail | `shot.act` |
| 3rd | Segment-level `cam` overrides | Global `shot.cam` |
| 4th | `shot.snd.sfx` entries beyond primary | All `seg[].act` |
| 5th | `shot.light` reduced to source only | `lock` array |
| 6th | `ref.bg`, `ref.style` (describe in text) | `ref.char` |

If the compiled prompt is still too long after all 6 cuts: **switch to Level 1 — delete `seg`, replace `shot.act` with one sentence, remove all `ref` except `ref.char`.**

---

## Module 02: Quad-Modal Protocol

### Universal Rules

- One prompt = one clip. Treat it as a shot or short sequence, not a screenplay.
- Prefer one hero subject per shot; two max if interaction is essential.
- If dialogue is present, plan around it — dialogue timing sets shot timing.
- Avoid dense on-screen text; if needed, keep to 1–3 words and accept imperfect typography.

### T2V (Text to Video)

**Best for:** Original worlds, atmosphere, controlled camera/light, scenarios where the model has domain knowledge.

- For known domains (food, brands, sports, common activities): use Level 1–2. Trust the model's built-in knowledge.
- For novel/unusual content: use Level 3–4 with explicit structure.
- Put SUBJECT + ACTION first (the subject anchor).
- Specify camera + timing explicitly.
- Keep environment precise but short.

**Common failures:** generic backgrounds, camera drift, adjective mush.  
**Fix:** shorten, add a named light source, lock camera, reduce adjectives.

### I2V (Image to Video)

**Best for:** Character/environment anchoring, product demos, bringing illustrations to life.

- Use `@Image1 as the first frame` for strong stability.
- Add `@Image2 as the last frame` for maximum control (motion-in-between).
- Describe only the change from the starting image — don't rewrite the entire scene.
- The first frame is your most important creative decision (see Module 06B).

**Common failures:** identity drift, costume drift, background warping.  
**Fix:** `"@Image1's character as the subject, wearing the outfit from @Image1."` Reduce motion. Lock camera.

### V2V (Video to Video)

**Best for:** Camera path transfer, action choreography transfer, style transformation.

**Two distinct operations:**
1. **Reference mode:** `"参考@Video1的运镜"` → generate new content using the reference's technique.
2. **Edit mode:** `"将@Video1中的人物换成..."` → modify the reference directly.

- Explicitly state what to keep and what to change.
- Limit changes to 1–2 per generation. Too many changes = loss of structure.

**Common failures:** change bleeds into everything, loss of structure.  
