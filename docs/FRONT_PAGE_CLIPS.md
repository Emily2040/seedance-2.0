# Front-page clips: the shooting brief

Status: seven prompts, seventh draft, written 2026-09-27; none of the current
prompts rendered yet. Clip 03 has three earlier takes (fourth, fifth and sixth
drafts), recorded at the end of this file; each is the reason the next draft
exists. The data behind this page and the README slates is
`data/front-page-clips.json`; the slates are built by
`scripts/build_clip_posters.py`, and `--check` keeps them in step.

## Why these clips exist

People share what they can see. The front page therefore shows Seedance 2.0
output made from prompts this skill wrote, in the languages the skill writes,
with the exact prompt beneath each clip and, above it, the kind of brief people
usually type. The difference is visible before it is explained. Nothing on the
page is a mock-up: a clip is either rendered from the published prompt or its
slate says it is not.

## How to render them

- Surface: Seedance 2.0, text to video, no reference assets. One generation per
  clip. No editing, colour work, sound replacement or upscaling afterwards.
- Settings live in the tool, not in the prompt: aspect ratio 16:9, the duration
  listed on each card (choose the nearest value the tool offers and note it),
  audio generation on, 720p or the tool's default. Clip 04 also carries the
  documented Chinese prose echo 时长：15秒, which is a reinforcement, not a
  control.
- Paste each prompt exactly as printed. Do not translate it, add quality words,
  or append a style name. Every prompt has passed the moderation pre-screen; if
  a surface still refuses one, note the exact message in the render record
  and do not retry with synonyms.
- One take is the default. If a take misses the review checklist, generate one
  more with the same prompt and settings; publish the better take and record
  both in the table at the end of this file. A third attempt is a decision the
  maintainer makes, not a default.
- Return the files by dragging them into a comment on the open pull request.
  GitHub converts each upload to a hosted asset URL that the README can embed;
  the session watching that pull request reads the URLs from the comment,
  replaces the slates, and writes the caption from the record below. Name the
  files as listed on each card so the mapping is unambiguous.

## What each caption will say

Once a clip is in place its caption states, in one line: the surface and model
line, the date, the duration and ratio actually set, and the take number if it
was not the first. Anything the take did not do that the prompt asked for is
written under it rather than hidden. That is the same rule the example cards
already follow.

## The seven clips

Each card gives the typical brief (what the clip would have been made from
without the skill), what the audience knows by shot two, the internal read the
skill used, the screen note, the prompt as written, the ladder rung from
`references/multishot-grammar.md` (reaction shots and inserts at half a beat),
and the review checklist for the returned take. Every scene is a complete
fifteen-second story cut like short-drama coverage; the gallery runs on the
Stretch rung on purpose, as the calibration the ladder's thresholds are waiting
for. Every prompt is directed for the model by
`references/direct-for-the-model.md`: one action per shot while everyone else
keeps their idle business, reactions as a plain feeling plus one physical
anchor, prop work as a hand, every line given a voice and eyes, an ending the
last frame can hold, and a lock line closing every shot that restates light,
identity, position and the camera side, with reactions as reverse angles and
every crossing of a room on screen. Each prompt was rendered from the floor plan
and shot table printed under it (`references/shot-table.md`) and passed
`scripts/shot_table_check.py`. Every prompt passed
`scripts/moderation_prescreen.py` with no finding before publication.

### Clip 01: By appointment only

- Language: English. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch: 4.5 beats (one insert at half), load 3, S = 2.0. File: `clip-01-by-appointment-only.mp4`.
- Typical brief: *rich woman disguised as poor gets humiliated at luxury store, plot twist, satisfying, cinematic, 4k*
- Premise on screen: Shot one is a soaked woman in work clothes stopped inside a
  boutique door by a voice that says appointment only; shot three is a phone
  call that says the new owner is standing in the shop.
- Internal read: Narrative lane. Turn: the person being kept out is the person
  who owns the door. POV: hers, so she never has to speak. Force: the manager's
  voice and the room's stillness. Visible suppressed behaviour: she sits on the
  display chaise instead of arguing. Non-transferable detail: wet bootprints
  across cream carpet, given their own insert so the ending is a frame the shot
  can hold (authored choice). Stock solution refused: no speech from her, no
  reveal card, no music.
- Screen: No cue words. Directed for the model: the refusal is spoken from just
  off frame so her shot has one action and no second face to sync; his turn is
  embarrassment with a swallow, hers is calm; the assistants keep glancing
  rather than freezing; every lock line says where she sits and where he stands.
  Draft seven fixes the geography: the master looks from the back of the shop
  toward the door, the counter is on the right, and every cut names its camera
  side.

> Shot 1. Wide shot from the back of a hushed luxury boutique looking toward the glass front door, on a rainy afternoon: cream carpet, glass shelves of shoes along the left wall, the counter on the right with two assistants in black behind it, one folding tissue paper, one glancing up at the door. A woman pushes the glass door open, steps inside dripping, and stops on the mat, water running off her sleeves. From just off frame right, by the counter, the manager's voice, polite and thin: "We're by appointment only, ma'am." She turns her head toward the voice, calm, almost amused, and says nothing. Light: soft grey daylight from the front window, warm spotlights on the shelves. The woman: thirties, dark hair tied back, white overalls stained with paint, tan work boots, standing just inside the door, facing into the shop. Camera at the back of the shop, facing the door.
>
> Shot 2. Cut to a medium shot from the counter side: she walks across the carpet to the white display chaise in the middle of the shop, sits down on it facing the counter, crosses one muddy boot over the other, and looks slowly along the shelves, unhurried. Behind her the two assistants exchange a glance. Same light: soft grey daylight from the front window, warm spotlights on the shelves. The woman: thirties, dark hair tied back, white overalls stained with paint, tan work boots, seated on the white chaise in the middle of the shop, facing the counter. Camera on the counter side.
>
> Shot 3. Cut to a close shot of the manager from the chaise side, standing by the counter, a phone at his ear, listening. Embarrassed, the polite smile fades and he swallows; then he says quietly: "Yes, sir. The new owner is... standing in the shop now." His eyes go past the camera to her, off frame, and stay there. Same light: soft grey daylight from the front window, warm spotlights on the shelves. The manager: fifties, grey suit, steel-rimmed glasses, standing by the counter, facing the chaise. Camera on the chaise side.
>
> Shot 4. Cut to a two-shot from behind the chaise, her shoulder in the foreground, the manager by the counter and the wall of shoes beyond him: she lifts one arm and points at a single pair of shoes on the wall; he walks from the counter to the wall and lifts that pair down with both hands, careful now. Same light: soft grey daylight from the front window, warm spotlights on the shelves. The woman: thirties, dark hair tied back, white overalls stained with paint, tan work boots, seated on the chaise, facing the counter. The manager: fifties, grey suit, steel-rimmed glasses, walking from the counter to the wall of shoes. Camera behind the chaise.
>
> Shot 5. Cut to a close insert of the cream carpet: a trail of wet bootprints from the door to the chaise, rain running down the glass door behind. Hold on the bootprints. Same light: soft grey daylight from the front window. Camera low over the carpet, facing the door.
>
> Sound: rain on the glass door, her boots on the carpet, the murmur of the phone line, his voice dropping; no music, no subtitles.

Floor plan: A boutique: the glass front door at one end, the counter along the
right wall, the wall of shoes opposite the door, the white chaise in the middle.
The manager starts by the counter; the assistants behind it. Grey daylight from
the front window, warm spots on the shelves.

| Shot | Camera | In frame | Eye-line | Action | Others | Light | Last frame |
|---|---|---|---|---|---|---|---|
| 1 | Back of the shop toward the front door; wide | Woman inside the door, facing in; two assistants behind the counter, right; manager off frame right | She turns her head to the voice on the right | She pushes the door open, steps in, stops on the mat; the manager's line from off frame; calm, almost amused, she says nothing | Assistants fold tissue paper, glance up | Grey daylight from the front window, warm spots on the shelves | Her on the mat, the door behind her |
| 2 | Counter side; medium | Woman crossing to the chaise, sitting on it facing the counter; assistants behind her | Along the shelves | Walks to the chaise, sits, crosses one muddy boot over the other, looks slowly along the shelves | Assistants exchange a glance | Same daylight and spots | Her on the chaise, boots crossed |
| 3 | Chaise side; close | Manager by the counter, facing the chaise | Past the lens to her, off frame | Embarrassed: the polite smile fades, he swallows; the phone line, quiet; his eyes go to her and stay | None in frame | Same | His face, eyes on her |
| 4 | Behind the chaise; two-shot | Her shoulder in the foreground facing the counter; manager walking from the counter to the wall of shoes | Hers to the wall; his to the shoes | She points at one pair; he walks to the wall and lifts it down with both hands, careful now | Assistants stay at the counter | Same | Him at the wall with the shoes in his hands |
| 5 | Low over the carpet toward the door; insert | Nobody | None | Hold on the wet bootprints from the door to the chaise, rain on the glass door | None | Same daylight | The bootprints |

Review: the refusal line is heard in shot one with only her on screen; the phone
line in shot three with only him on screen; she never speaks; she sits and looks
along the shelves in shot two, points in shot four, and he lifts the shoes down;
the assistants glance rather than freeze; the daylight, the two descriptions and
their positions hold across every cut; the clip ends on the insert of the
bootprints; no music; no subtitles.

### Clip 02: Hold the line

- Language: English. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch: 4 beats, load 3, S = 2.1. File: `clip-02-hold-the-line.mp4`.
- Typical brief: *epic storm at sea, fisherman fights giant wave, slow motion, dramatic music, 8k*
- Premise on screen: Shot two tells the audience what the rope is worth: an
  off-screen voice says it is only a boat, and his answer says whose boat.
- Internal read: Narrative lane. Turn: a boat about to be lost to a boat still
  there. Force: the sea, acting first. Stakes in frame: one rope. Hidden want:
  not to lose the last thing his father left. Visible suppressed behaviour: he
  answers without turning his head. Non-transferable detail: boots braced
  against a cleat while water sheets around them (authored choice). Stock
  solution refused: no slow motion, no music, no rescue.
- Screen: No cue words; water is the model's strongest material. The second
  voice stays off screen so only one face has to sync. Directed for the model:
  he strains rather than freezes, the answer is angry and close to tears, and
  the last shot is framed low with the bow behind him so the frame it ends on
  already contains him, the rope and the boat. Draft seven names the camera's
  side of the pier in every shot.

> Shot 1. Wide shot from the landward end of a wooden pier at night in a storm, looking out along it: a small fishing boat straining at a single mooring rope off the far end, its bow lifting and slamming with each swell, rain driven sideways through one sodium lamp, and behind the boat a wave building higher than the mast. At the far end of the pier a man leans back against the rope with both hands, boots sliding on the wet planks, holding on, his back to the camera. Light: one orange sodium lamp on its post at the end of the pier, black water beyond, nothing else. The man: forties, short beard streaked grey, yellow oilskin with the hood down, black rubber boots, at the end of the pier with the rope in both hands, facing the boat. Camera at the landward end.
>
> Shot 2. Cut to a medium shot at deck height from the side of the pier: the man has both hands on the rope, boots braced against a cleat, arms shaking with the strain, the rope creaking as the boat pulls. From the dark behind the camera, landward, a voice shouts over the wind: "Let it go, Tom! It's only a boat!" He hears it, keeps his eyes on the rope, and his grip tightens. Same light: one orange sodium lamp overhead, black water beyond. The man: forties, short beard streaked grey, yellow oilskin with the hood down, black rubber boots, braced at the cleat, facing the boat. Camera at his side.
>
> Shot 3. Cut to a close shot of his face from in front of him, the boat behind the camera: rain running off his brow, eyes on the rope, teeth clenched; without turning his head he shouts back over his shoulder, angry and close to tears: "It's my father's!" Same light: one orange sodium lamp overhead, black water beyond. The man: forties, short beard streaked grey, yellow oilskin with the hood down, braced at the cleat, facing the boat. Camera in front of him.
>
> Shot 4. Cut to a low angle from the pier planks in front of him, looking up at him with the boat's bow behind him: the wave breaks over the end of the pier and buries him in white water. When the water drains through the planks he is still there, bent double and coughing, both hands on the rope, the rope taut, the boat still there behind him. Hold on this frame as the next swell lifts the bow. Same light: one orange sodium lamp overhead, black water beyond. The man: forties, short beard streaked grey, yellow oilskin with the hood down, black rubber boots, still braced at the cleat, facing the boat. Camera low, in front of him.
>
> Sound: wind, the rope creaking, the two shouts, the wave's impact, water draining through the planks, his coughing. No music, no subtitles.

Floor plan: A wooden pier running out into black water at night; one sodium lamp
on a post at the far end; the boat moored off the far end on a single rope, its
bow toward the pier; a wave building beyond it. The man is at the far end with
the rope in both hands, facing the boat; the second voice is landward, behind
the camera, never seen.

| Shot | Camera | In frame | Eye-line | Action | Others | Light | Last frame |
|---|---|---|---|---|---|---|---|
| 1 | Landward end of the pier looking out; wide | Man at the far end, back to camera, facing the boat | The boat | He leans back against the rope, boots sliding on the wet planks, holding on | None | One orange sodium lamp at the pier end, black water | The wave building behind the boat |
| 2 | His side, deck height; medium | Man braced at the cleat, facing the boat | The rope | Holds, arms shaking; the shout from landward behind the camera; his grip tightens | The voice, unseen | Same lamp | Him braced, rope taut |
| 3 | In front of him, boat behind the camera; close | His face, facing the boat | The rope; he shouts over his shoulder | The answer, angry and close to tears, without turning his head | None | Same lamp | His face, rain running off his brow |
| 4 | Low on the planks in front of him, bow behind him | Man at the cleat, boat behind | The rope | The wave breaks over him; it drains; he is still there, bent double, coughing, rope taut | None | Same lamp | Him bent over the rope, the boat behind, the next swell lifting the bow |

Review: the off-screen shout and his answer are both audible; only his face is
on screen while speaking and he does not turn his head; the wave builds in shot
one and breaks in shot four; he is standing and coughing when it drains, both
hands on the rope, and the boat is there behind him; the sodium light, his
description and his place at the cleat hold across every cut; real speed; no
music; no subtitles.

### Clip 03: 这杯茶

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch at the boundary: 5 beats (two inserts at half), load 3 with the recalibrated person row, S = 1.9. File: `clip-03-this-cup-of-tea.mp4`.
- Typical brief: *豪门寿宴反转名场面，女主打脸全场，短剧爆点，电影感，高级感*
- Premise on screen: Shot one is a birthday toast, seen over the old man's
  shoulder toward the door, that goes quiet when the door opens on a woman
  nobody invited; shot two is his face from the door's side, recognising her.
  Her walk up the table is shot three; the line in shot five says whose daughter
  she is.
- Internal read: Narrative lane. Turn: his toast becomes her verdict on him.
  POV: hers; he is a cup he never picks up again. Hidden want: the child's
  mother acknowledged, not money. Tactic: pour, speak, then set the cup down
  mouth-down. Visible suppressed behaviour: she pours to the last drop and does
  not sit. Non-transferable detail: the empty cup set mouth-down on the wet
  cloth, given the last shot so the frame can hold it (authored choice). Stock
  solution refused: no slap, no tears, no music.
- Screen: The first draft of this slot named a divorce agreement, a law office
  and a child and was refused; this scene names none of them. The fourth draft
  rendered with a grey face and an inverted cup; the fifth with a frozen room
  and a sulk; the sixth acted well and broke the geography: the master put the
  door behind him, his reaction looked toward the camera, and she cut from the
  door to his cup with no walk between. This draft frames the master over his
  shoulder toward the door, shoots his reaction as a reverse from the door,
  gives her walk up the table its own shot, and names the camera's side in every
  lock line.

> 镜头1：固定全景，机位在老爷子身后偏高，越过他的肩膀拍向厅堂尽头正对着主位的大门。老宅厅堂里的寿宴，红色横幅下一张大圆桌坐满了宾客，主位的老爷子背对镜头举着茶杯，宾客们跟着举杯、碰杯，有说有笑。画面尽头的大门被推开，一个女人站在门口，面对着主位。笑声停下来，宾客们一个一个转头看向门口，互相压低声音说话，没有人站起来。灯光：头顶一盏暖黄的老式吊灯，桌布和人脸都在同一种暖黄光里，门外是深蓝的夜色。老爷子：七十多岁，白发向后梳，深棕色缎面唐装，坐在主位，面对大门，背对镜头。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣，站在画面尽头的门口。机位在老爷子身后。
>
> 镜头2：反打，机位在大门方向，正面拍老爷子的近景，身边的宾客在虚焦里转头看向镜头方向的门口、小声议论。他看见她，愣住，惊慌，眼睛越过镜头一直盯着门口的她，喉结动了一下，然后把手里的茶杯慢慢放回面前的桌布上，手收回来握在桌边。灯光不变：头顶暖黄吊灯，脸在同一种暖黄光里。老爷子：七十多岁，白发向后梳，深棕色缎面唐装，坐在主位，面对大门和镜头。机位在大门方向。
>
> 镜头3：中景，机位在老爷子身旁稍后方，拍向大门：女人从门口沿着桌边朝镜头走来，脚步不快不慢，宾客们的目光跟着她转，她走到主位旁边停下，低头看着画面前景里坐着的他的侧影。灯光不变：头顶暖黄吊灯，她的脸从门外的蓝光走进桌上的暖黄光。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣，从门口走到主位旁边站定。老爷子：深棕色缎面唐装的肩膀和白发在画面前景，坐在主位。机位在老爷子身旁。
>
> 镜头4：切至桌面特写，机位在桌边：白桌布，老爷子面前那只满杯茶，他的手握成拳放在桌边。女人的右手从画面右侧伸进来，握住杯身，把杯子提到桌布上方一掌高，杯口朝他那一侧倾斜，茶水从杯沿流到白桌布上，冒着热气，一直流到杯里没有茶；整个过程杯底一直在下。他的拳头在桌布上收紧了一下。灯光不变：头顶暖黄吊灯。女人的手：袖口是旧的深灰色呢子，手背上有雨水。
>
> 镜头5：切至女人的近景，机位在桌边略低，她站在主位旁边，身后是虚焦里转头看她的宾客和红色横幅，头顶是同一盏暖黄吊灯。她低头看着画面外坐着的他，眼睛没有离开他，声音很轻，每个字都清楚，说：“这杯茶，我妈等了二十年。”说完她的眼眶红了，没有眼泪，嘴唇抿住。灯光不变：头顶暖黄吊灯，脸在暖黄光里。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣，站在主位旁边，低头面对他。机位在桌边。
>
> 镜头6：切回桌面特写，机位同镜头4。她的右手转动手腕，把空杯杯口朝下扣在湿桌布上，松开手，手退出画面。画面停在倒扣的杯子和布上漫开的茶水上，他的拳头在桌边慢慢松开。灯光不变：头顶暖黄吊灯。
>
> 声音：碰杯声和说笑声，门推开的一声之后全场安静，她的脚步声，杯子放到桌布上的一声，茶水落在布上的声音，说话时全场无声；无配乐。保持无字幕。时长：15秒。

Floor plan: An old hall with a round banquet table under one warm tungsten lamp
and a red birthday banner. The head seat faces the hall's main door at the far
end; the old man sits there. Guests fill the table. The woman appears in the
doorway, blue night behind her, and walks the length of the table to stand
beside the head seat.

| Shot | Camera | In frame | Eye-line | Action | Others | Light | Last frame |
|---|---|---|---|---|---|---|---|
| 1 | Behind the old man, high, over his shoulder toward the door; wide | Old man at the head seat, back to camera, facing the door; guests around the table; woman in the doorway at the far end, facing the table | Guests to the door | The toast alive, cups touching, laughter; the door opens; laughter stops; heads turn one by one | Guests whisper; nobody stands | Warm tungsten lamp overhead; blue night beyond the door | Her in the doorway, the room turned toward her |
| 2 | From the door, the reverse of shot 1; close | Old man facing the door and the lens; guests out of focus beside him | Past the lens to her at the door | Caught out: he freezes, alarmed, a swallow; the cup goes down on the cloth; hand to the table edge | Guests look toward the door, murmur | Same lamp | His face, the cup on the cloth |
| 3 | Beside and behind the old man, toward the door; medium | Her walking from the door along the table toward the lens; his shoulder and white hair in the foreground | Guests follow her; on arrival she looks down at him | The walk, unhurried; she stops beside the head seat | Guests' heads turn with her | Same lamp; her face passes from blue into warm | Her beside him, looking down |
| 4 | At the table edge; insert | His fist on the cloth; her right hand from frame right | None | Grip the cup by the body, lift a hand's width, tilt toward him, tea onto the cloth until empty; the base stays down | His fist tightens once | Same lamp | The empty cup tilted, steam on the wet cloth |
| 5 | Table edge, slightly low; close | Her beside the head seat, facing down at him; guests and banner out of focus behind | Down at him, off frame | The line, quiet, every word clear, eyes on him; after it her eyes redden, no tears, lips press | Guests watch | Same lamp | Her face after the line |
| 6 | Same as shot 4; insert | Her hand; his fist | None | The wrist turns, the cup is set mouth-down on the wet cloth, the hand withdraws | His fist loosens | Same lamp | The inverted cup on the wet cloth |

Review: the master looks over his shoulder toward the door; the toast is alive
until the door opens, then the room goes quiet and heads turn; his reaction is a
reverse from the door: caught out, eyes past the lens toward her, a swallow, the
cup goes down; same face colour under the same lamp in every shot; she walks the
length of the table toward the camera and stops beside him before any hand
touches the cup; the tea is poured from a tilted cup with its base down; the
line is spoken beside his seat under the warm lamp, quiet and clear, eyes on
him; the clip ends on the inverted cup; no music; no subtitles.

### Clip 04: 超时二十分钟

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch at the boundary: 5 beats, load 3, S = 1.9. File: `clip-04-twenty-minutes-late.mp4`.
- Typical brief: *外卖员被差评感人反转，正能量短剧，泪目，电影感*
- Premise on screen: Shot one is a soaked delivery rider at a door and a man in
  the doorway with his phone out; shot two is the threat of a bad review. Shot
  three shows who is under the helmet.
- Internal read: Narrative lane. Turn: a customer about to punish becomes a
  host. POV: the rider's, at the threshold. Force: the phone in his hand. Hidden
  want: to keep the job without begging. Visible suppressed behaviour: she
  offers the refund before he can ask. Non-transferable detail: the small puddle
  of rain on the wet tiles that the open door lights in the last shot (authored
  choice). Stock solution refused: no crying, no lecture, no music; he simply
  opens the door wider.
- Screen: No cue words. The reveal is a helmet coming off; no injury, no fall.
  Directed for the model: his displeasure is impatience with a frown, hers is
  tiredness and apology; the helmet, the bag and the line each get their own
  shot; every lock line says who is inside the door and who is outside; the last
  shot is framed from her position so the door and the wet tiles it lights are
  inside the frame it ends on. Draft seven names the camera's side of the
  threshold in every shot: the master from the corridor with both of them across
  the door, his close-up from her side, hers from his.

> 镜头1：固定中景，机位在走廊一侧，同时拍到门外的外卖员和门里的男人，两人隔着门槛面对面。深夜住宅楼的走廊，雨声很大。外卖员站在门外，浑身滴水，左手提着一袋外卖，右手刚按完门铃收回来，还在喘气。门被从里面打开，一个男人站在门里，右手握着手机，不耐烦，眉头皱着，上下打量她。灯光：走廊顶上一盏白色日光灯，门里透出暖黄的灯光。外卖员：黄色雨衣，黑色头盔，面罩抬起，站在门外，面对门里。男人：四十多岁，短黑发，深蓝色睡衣，站在门里，面对她。机位在走廊一侧。
>
> 镜头2：切至男人的近景，机位在门外她的位置，正面拍他。他把手机屏幕转向镜头方向的她，语气又急又冲，说：“超时二十分钟，我要给差评。”说完盯着她，等她回答。灯光不变：走廊的白色日光灯在他脸的一侧，门里的暖黄光在另一侧。男人：四十多岁，短黑发，深蓝色睡衣，右手握着手机，站在门里，面对门外。机位在门外。
>
> 镜头3：切至外卖员的近景，机位在门里他的位置，正面拍她。她没有争辩，右手解开头盔的卡扣，把头盔从头上摘下来，垂在身侧：头盔下是一头花白的短发，六十岁上下，雨水顺着脸往下流，还在喘气，又累又不好意思。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光在脸的一侧。外卖员：黄色雨衣，花白短发，六十岁上下，左手提着外卖袋，站在门外，面对门里。机位在门里。
>
> 镜头4：同一机位，外卖员的近景。她把左手的外卖袋举到胸前递向镜头方向的门里，声音低但清楚，带着歉意，说：“对不起，钱我退给您。”说完看着他，手举着等他接。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光在脸的一侧。外卖员：黄色雨衣，花白短发，六十岁上下，右手垂着头盔，站在门外，面对门里。机位在门里。
>
> 镜头5：切至固定中全景，机位在门外她的位置稍后，拍向门，她不在画面里。男人看了一眼镜头方向她湿透的鞋，然后侧身退到门边，把门拉到全开，门里的暖黄光照到门口湿的地砖上；他站在门边等她进来。画面停在敞开的门和门口地砖上的一小滩雨水上。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光照出来。男人：四十多岁，短黑发，深蓝色睡衣，右手握着手机，站在门边，面对门外。机位在门外。
>
> 声音：雨声，头盔卡扣打开的一声，塑料袋的窸窣声，门轴的声音，说话时其他声音压低；无配乐，保持无字幕。时长：15秒。

Floor plan: A residential corridor at night, a white tube light overhead; an
apartment door with warm light inside. The rider stands outside the door facing
in; the man stands inside facing out. The threshold is the axis.

| Shot | Camera | In frame | Eye-line | Action | Others | Light | Last frame |
|---|---|---|---|---|---|---|---|
| 1 | Corridor, side on to the threshold; medium | Rider outside, facing in, bag in her left hand; man inside, facing her, phone in his right hand | Each other | The door opens; he looks her up and down, impatient, brow tight | None | White tube overhead; warm light from inside | The two across the threshold |
| 2 | Outside, at her position; close | Man inside the door, facing out | Past the lens to her | Turns the phone screen toward her; the line, sharp; waits, staring | None | White on one side of his face, warm on the other | His face, waiting |
| 3 | Inside, at his position; close | Rider outside, facing in | Past the lens to him | Unclips and lifts off the helmet: grey hair, sixty or so; tired and embarrassed | None | White overhead, warm on one side | Her bare head, rain on her face |
| 4 | Same as shot 3 | Rider, helmet at her side | To him | Lifts the bag toward him; the line, low and clear, apologetic; holds it out and waits | None | Same | The bag held out |
| 5 | Outside, slightly behind her position, she out of frame; medium wide | Man in the doorway, facing out | To her shoes, then aside | Glances at her soaked shoes; steps aside; pulls the door full open; waits for her | None | Same; the warm light falls on the wet tiles | The open door and the puddle on the tiles |

Review: his line comes before the helmet comes off, impatient; her line comes
after, apologetic; each speaker alone in frame; the helmet comes off in its own
shot and the bag is offered in the next; he glances at her shoes, steps aside
and pulls the door to full open instead of taking the bag; the corridor light,
the warm light from the door and who stands on which side of it hold across
every cut; the clip ends on the open door and the puddle it lights; no music; no
subtitles.

### Clip 05: 사직서

- Language: Korean. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch: 4 beats (two at half), load 3, S = 2.1. File: `clip-05-resignation.mp4`.
- Typical brief: *사이다 사직서 장면, 직장인 드라마, 시네마틱, 4K, 감동*
- Premise on screen: Shot one is a CEO signing at night and an employee walking
  in; shot two is her envelope landing on the page he is signing. Her line says
  he stole her report and was promoted for it.
- Internal read: Narrative lane. Turn: the one who was ignored becomes the one
  who is looked at, too late. POV: hers until she leaves; then the glass gives
  us him. Tactic: put the envelope on the page. Visible suppressed behaviour:
  she does not step back. Non-transferable detail: the envelope over his
  signature in progress (authored choice). Stock solution refused: no raised
  voice, no applause, no music; his face arrives late and stays behind glass.
- Screen: No cue words; the request for legible on-screen lettering on the
  envelope was removed because rendered text garbles. Directed for the model:
  her line is calm and clear with a breath after it, his look up is flustered
  with his lips parting; every lock line says he sits behind the desk and she
  stands before it; the reflection ending was replaced by a wide from the
  corridor in which the closing door and the man behind it are both already in
  frame. Draft seven names the camera's side: the master from the door, her
  medium from behind his desk, his close-up from where she stands, the last shot
  from the corridor.

> 샷 1: 밤의 유리벽 임원실, 카메라는 문 쪽에서 책상을 향한다. 넓은 책상 뒤에서 대표가 문을 마주 보고 앉아 서류에 서명하고 있고, 문이 열려도 고개를 들지 않는다. 직원이 카메라 옆의 문을 열고 들어와 카메라에 등을 보인 채 책상 앞까지 걸어가 선다. 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠, 책상 뒤에 앉아 문을 향해 있다. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장, 목에 건 사원증, 책상 앞에 서서 그를 향해 있다. 카메라는 문 쪽.
>
> 샷 2: 책상 위 클로즈업, 카메라는 책상 옆에서 낮게. 그녀의 손이 흰 봉투 하나를 그가 서명하던 서류 바로 위에 올려놓는다. 그의 펜이 종이 위에서 멈춘다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛. 그녀의 손: 회색 정장 소매. 그의 손: 걷어 올린 흰 셔츠 소매, 검은 만년필.
>
> 샷 3: 그녀의 미디엄 숏, 카메라는 책상 뒤 그의 어깨 옆에서 낮게 올려다본다. 책상 앞에 선 그녀가 물러서지 않고 카메라 아래의 그를 내려다보며, 차분하지만 분명한 목소리로 말한다. 직원: “제 보고서, 이름만 바꾸셨더군요. 승진 축하드려요.” 말을 끝내고 잠시 그를 본다. 눈은 흔들리지 않고, 숨을 한 번 고른다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장, 목에 건 사원증, 책상 앞에 서서 그를 내려다본다. 카메라는 책상 뒤.
>
> 샷 4: 대표의 클로즈업, 카메라는 그녀가 선 자리에서 그를 향한다. 펜을 쥔 손은 종이 위에 멈춘 채, 그가 천천히 고개를 들어 카메라 너머의 그녀를 올려다본다. 당황한 얼굴, 할 말을 찾지 못해 입술이 살짝 벌어진다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠, 책상 뒤에 앉아 그녀를 올려다본다. 카메라는 책상 앞.
>
> 샷 5: 복도 쪽에서 본 와이드 숏, 유리문과 그 너머의 임원실. 그녀가 유리문을 밀고 나와 카메라 옆을 지나 화면 밖으로 걸어가고, 문이 천천히 닫힌다. 유리 너머 책상의 그는 앉은 채 봉투를 내려다보고 있다. 화면은 닫힌 유리문과 그 너머의 그에게서 멈춘다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛, 복도는 어둡다. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠, 책상 뒤에 앉아 있다. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장, 문을 나선다. 카메라는 복도.
>
> 소리: 펜이 멈추는 순간, 봉투가 종이 위에 놓이는 소리, 구두 소리, 유리문이 닫히는 소리. 대사 중에는 다른 소리를 낮춘다. 음악 없음, 자막 없음.

Floor plan: A glass-walled executive office at night; the desk faces the door;
the CEO sits behind it facing the door; one desk lamp and the city beyond the
glass. She enters from the door and stops in front of the desk. The last shot is
from the dark corridor outside the glass door.

| Shot | Camera | In frame | Eye-line | Action | Others | Light | Last frame |
|---|---|---|---|---|---|---|---|
| 1 | From the door toward the desk; wide | CEO seated behind the desk facing the door; employee enters beside the camera, back to it, and stops before the desk | His on the page; hers on him | She walks to the desk | He keeps signing | Desk lamp; city lights behind | Her standing before the desk |
| 2 | Beside the desk, low; insert | Her hand; his hand with the pen | None | The envelope is placed on the page he is signing; the pen stops | None | Lamp | The envelope over the signature |
| 3 | Behind the desk at his shoulder, low, looking up; medium | Her before the desk, facing down at him | Down to him below the lens | The line, calm and clear; then a breath, eyes steady | He is out of frame | Lamp, city lights | Her face after the breath |
| 4 | Where she stands, toward him; close | CEO behind the desk, facing up to her | Up past the lens to her | He raises his head slowly; flustered, lips part | None | Lamp | His face looking up |
| 5 | Corridor, toward the glass door; wide | She exits past the camera; he seated behind the glass | His on the envelope | She pushes out; the door closes slowly | He looks down at the envelope | Lamp and city lights behind glass; corridor dark | The closed glass door, him behind it |

Review: the envelope lands on the page he is signing and the pen stops before
she speaks; the line is Korean, calm and clear, with her alone in frame and a
breath after it; he looks up in his own shot, flustered, after the line; the
desk lamp, the two descriptions and their places (he behind the desk, she before
it) hold across every cut; the clip ends on the closed glass door with him
seated behind it looking at the envelope; no music; no subtitles.

### Clip 06: 最後の一球

- Language: Japanese. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch: 4 beats (two at half), load 3, S = 2.1. File: `clip-06-last-pitch.mp4`.
- Typical brief: *高校野球決勝ラストボール神作画、感動、エモい、有名アニメスタジオ風、4K*
- Premise on screen: Shot one is a pitcher on the mound in the rain with the
  crowd behind him; the sign, the wind-up and the swing say final pitch without
  a caption.
- Internal read: Non-narrative lane, performance. Utility intent: the last pitch
  of a final as the medium shows a decisive act: a burst on ones, one smear, one
  inverted impact frame, then a held frame in the rain. Refusal: no dialogue, no
  team pile-on, no photographic lens language, no named tournament.
- Screen: No cue words and no stated ages; the pitcher is described by mud and
  breath, not by school year. Directed for the model: one movement per shot (the
  sign, the wind-up, the swing) while the crowd, the flags and the catcher's
  mitt keep small living motion; the held frame is a position with a named
  feeling, and the medium, the light, the pitcher and his place on the mound are
  restated at the end of every shot. Draft seven names the camera's side of the
  diamond in every shot: the pitcher from home plate, the mitt from the mound,
  the swing from behind the catcher.

> 手描きの2Dセルアニメーション。セル画のキャラクターを、水彩で描かれた背景画の上に置く。作画の密度が高く、限られた色数、フィルムの粒子が乗った質感。夏の決勝戦の九回裏、雨が降り始めた球場。
>
> ショット1：ホームベース側からマウンドの投手を正面に捉えたミディアムショット。肩で大きく息をして、帽子のつばから落ちる雨を見上げる。疲れているが、目は引かない。背景の観客席は塗りの中でざわめきの色が揺れ、旗が小さくはためく。光：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子、帽子のつばから雨が落ちる、マウンドの上でホームベースを向いている。カメラはホームベース側。
>
> ショット2：カットして、マウンド側から見た捕手のミットのクローズアップ。低く構えたミットの横で、指が一度だけサインを出し、ミットが小さく二度叩かれる。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光。ミット：濡れた茶色の革、ホームベースの後ろ、マウンドを向いている。カメラはマウンド側。
>
> ショット3：カットして、ホームベース側から投手のワインドアップ。振りかぶりからリリースまでを一コマ打ちのフルアニメーションで描き、腕の軌道は一枚のスミア、雨粒が腕の動きに引かれて流れる。カメラは背景画に対して固定。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子、マウンドの上でホームベースを向いている。カメラはホームベース側。
>
> ショット4：カットして、捕手の後ろから見た打者の空振り。バットが空を切った瞬間、ボールがミットに収まる音と同時に画面全体を白黒反転のインパクトフレームにする。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光。打者：白いヘルメット、灰色のユニフォーム、バッターボックスの中でマウンドを向いている。カメラは捕手の後ろ。
>
> ショット5：カットして、ホームベース側から、止め絵に近いショット。投手がマウンドで片膝をつき、顔を空に向けている。泣きそうな、しかし笑っている顔。動くのは雨と、息で上下する肩だけ。その前後のショットは二コマ打ち。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子、帽子のつばから雨が落ちる、マウンドの上。カメラはホームベース側。
>
> 音：雨音、観客のざわめき、ミットの乾いた一音、そのあとは雨音と投手の息だけ。音楽なし、字幕なし。

Floor plan: A rain-soaked stadium in flat overcast light: the mound facing home
plate, the catcher behind the plate facing the mound, the batter in the box
facing the mound, the crowd behind. Hand-drawn cel over watercolour throughout.

| Shot | Camera | In frame | Eye-line | Action | Others | Light | Last frame |
|---|---|---|---|---|---|---|---|
| 1 | Home plate side toward the mound; medium | Pitcher on the mound facing home | Up at the rain | Breathing hard; looks up; tired but not backing down | Crowd colour moves in the paint; flags stir | Flat overcast, wet earth | His face, rain off the cap brim |
| 2 | Mound side; close | Catcher's mitt behind the plate, facing the mound | None | One sign; the mitt pats twice | None | Flat | The mitt held low |
| 3 | Home plate side; medium, locked | Pitcher on the mound | The mitt | Wind-up to release on ones, one smear, rain trailing the arm | None | Flat | Release |
| 4 | Behind the catcher; medium | Batter in the box facing the mound | The ball | Swing and miss; ball into mitt; one inverted impact frame | None | Flat, inverted for one frame | The impact frame |
| 5 | Home plate side; medium, near-held | Pitcher on one knee on the mound, face to the sky | The sky | Near-still; breathing; close to tears and smiling | Rain only | Flat, wet earth | Him kneeling in the rain |

Review: reads as drawn 2D cel over painted backgrounds in every shot, not
photoreal or 3D; the crowd and flags keep small motion rather than freezing; the
wind-up is a full-animation burst with one smear; the swing and the mitt sound
share one inverted impact frame; the clip ends on a near-held frame of the
pitcher on one knee, face to the rain, close to tears and smiling; the flat
light holds; no music.

### Clip 07: Ещё один раунд

- Language: Russian. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch: 4 beats (two at half), load 3.5, S = 2.0. File: `clip-07-one-more-round.mp4`.
- Typical brief: *тренер и боксёр перед решающим раундом, драма, кинематографично, эпично, 4k*
- Premise on screen: Shot one is a corner between rounds and a fighter who has
  stopped looking up; shot two is the trainer's line, and shot three shows who
  is watching from the stands.
- Internal read: Narrative lane. Turn: a fighter who wants permission to stop is
  given a reason to stand. POV: the corner's, at rope height. Force: the round
  to come and the woman in the stands. Visible suppressed behaviour: one nod,
  nothing else. Non-transferable detail: the towel on the top rope beside the
  empty stool (authored choice). Stock solution refused: no shouted pep talk, no
  music, no slow-motion walk-out.
- Screen: The earlier draft had a cut, bleeding brow; it is a swollen brow under
  ice. No other cue. Directed for the model: the towel hangs on the rope from
  shot one so the last frame needs no throw; the trainer's line is tired and
  loving, the nod is heavy but decided, the crowd keeps talking; every lock line
  says who sits on the stool and who stands over him. Draft seven names the
  camera's side: the corner from the hall, the trainer from below at the
  fighter's side, the stands from the corner, the fighter from the stands' side.

> Кадр 1. Статичный средний план на уровне канатов, камера со стороны зала: угол ринга между раундами, ночной боксёрский зал, зал в темноте. Боксёр сидит на табурете лицом к камере и к трибунам, тяжело дышит и смотрит в пол; плечи ходят от дыхания. Тренер стоит над ним, прижимает к его брови пакет со льдом и второй рукой держит его за затылок. Свет: одна лампа над рингом, жёсткий белый свет сверху, всё остальное в темноте. Боксёр: лет двадцать пять, короткие тёмные волосы, опухшая левая бровь, капа во рту, красные перчатки, сидит на табурете в углу лицом к трибунам. Тренер: за шестьдесят, седая щетина, серая футболка, стоит над ним, боком к камере. Белое полотенце висит на верхнем канате рядом с табуретом. Камера со стороны зала.
>
> Кадр 2. Крупный план тренера снизу, камера у плеча сидящего боксёра; тренер один в кадре, смотрит вниз, мимо камеры, на боксёра. Говорит ровно, без крика, устало и с любовью: «Хочешь бросить — бросай. Только мать смотрит.» Тот же свет: одна лампа над рингом, жёсткий белый свет сверху. Тренер: за шестьдесят, седая щетина, серая футболка, стоит в углу ринга над боксёром, лицом к нему. Камера снизу, у боксёра.
>
> Кадр 3. Кадр с трибун, камера из угла ринга смотрит в зал: среди сидящих зрителей стоит одна маленькая пожилая женщина, тёмное пальто накинуто на плечи, руки сцеплены у груди, губы беззвучно шевелятся. Зрители вокруг сидят и переговариваются. Тот же свет: лампа над рингом освещает ринг, трибуны в полутьме. Женщина: маленькая, пожилая, тёмное пальто на плечах, стоит среди сидящих зрителей лицом к рингу. Камера из угла ринга.
>
> Кадр 4. Крупный план боксёра, камера со стороны трибун; он один в кадре, сидит на табурете. Он поднимает глаза мимо камеры в сторону трибун, находит её и один раз кивает: тяжело, но решив. Тот же свет: одна лампа над рингом, жёсткий белый свет сверху. Боксёр: лет двадцать пять, короткие тёмные волосы, опухшая левая бровь, капа во рту, сидит на табурете в углу лицом к трибунам. Камера со стороны трибун.
>
> Кадр 5. Тот же средний план, что в первом кадре, камера со стороны зала. Гонг. Тренер хлопает его по плечу; боксёр встаёт и выходит из кадра вперёд, к центру ринга. Камера остаётся на пустом табурете под лампой и на полотенце, висящем на верхнем канате. Тот же свет: одна лампа над рингом, жёсткий белый свет сверху. Тренер: за шестьдесят, седая щетина, серая футболка, стоит в углу. Боксёр: красные перчатки, капа во рту, уходит из угла к центру ринга. Камера со стороны зала.
>
> Звук: тяжёлое дыхание, шум зала за кадром, звон гонга; во время реплики остальные звуки тише. Без музыки, без субтитров.

Floor plan: A dark boxing hall, one lamp over the ring. The corner: the boxer on
a stool facing the stands, the trainer standing over him side on, a white towel
on the top rope beside the stool. The stands face the ring; one small old woman
stands among seated spectators.

| Shot | Camera | In frame | Eye-line | Action | Others | Light | Last frame |
|---|---|---|---|---|---|---|---|
| 1 | Hall side, rope height; medium | Boxer on the stool facing the stands; trainer standing over him, side on | His on the floor | He breathes hard; the trainer holds the ice pack to his brow, a hand on his neck | Hall in darkness | One lamp over the ring | The corner, towel on the top rope |
| 2 | Low at the boxer's shoulder, up at the trainer; close | Trainer over him, facing down | Down past the lens to the boxer | The line, level, tired and loving | None | Same lamp | His face after the line |
| 3 | From the corner toward the stands; medium | One small old woman standing among seated spectators, facing the ring | The ring | She stands, hands clasped, lips moving without sound | Spectators sit and talk | Lamp on the ring, stands dim | Her standing |
| 4 | Stands side toward the corner; close | Boxer on the stool facing the stands | Up past the lens to her | Lifts his eyes, finds her, one nod, heavy but decided | None | Same lamp | His face after the nod |
| 5 | Same as shot 1 | Boxer and trainer in the corner | His forward to the ring | The gong; the trainer pats his shoulder; he stands and walks out of frame to the centre | None | Same lamp | The empty stool, the towel on the rope |

Review: the line is Russian, tired and level, audible with the trainer alone in
frame; the woman in the stands is standing while everyone else sits and talks;
one heavy nod follows in his own shot; the gong, the pat on the shoulder, he
leaves the frame, the clip ends on the empty stool with the towel on the rope;
the ring lamp and the corner positions hold; no music; no subtitles.

## What the first six drafts taught

The record is kept because the front page claims honesty about its own takes.

- **Draft one (2026-09-26, morning).** Seven quiet observation pieces. Not
  rendered; withdrawn as too tame for a page whose job is to stop a thumb.
- **Draft two (2026-09-26, midday).** Seven dramatic scenes. Three were
  submitted on the 即梦 surface. Clip 01 (a kitchen knife, a teenage boy with
  a split lip, a 2 a.m. door) and clip 03 (a divorce agreement in a law office,
  a child's surname) were refused before rendering. Clip 02 (the last train)
  rendered as take 1: the sprint and the door entry held; the doors were
  pushed apart with both hands rather than one forearm, and the accidental
  ending, a coat tail caught in the doors, was staged by the model as the
  character deliberately stuffing her jacket into the closing door. That take
  is the origin of two rules now in the skill: never write an involuntary
  outcome as an endpoint, and run the moderation pre-screen before delivery.
  The whole draft was replaced.
- **Draft three (2026-09-26, afternoon).** Seven screened scenes, two or
  three master shots each. Withdrawn before rendering: they passed the screen
  and had a peak, but a stranger could not tell who the people were to each
  other or why the peak mattered, because the premise lived in the internal
  read and never reached the frame. The set above replaces them: the premise
  spoken or shown by shot two, four or five shots with a reaction, a hold on
  whoever lost. The ladder now counts reactions and inserts at half a beat;
  the drafts had shown the full-beat count pushing every scene to two or
  three shots.

- **Draft four (2026-09-26, evening).** Seven scenes cut like coverage, premise
  by shot two. Clip 03 was rendered on the 即梦 surface as take 1: the banquet,
  the door, the walk to the head of the table and the line all arrived, and four
  things did not. 脸沉下来 was rendered literally as a face turning grey; of the
  four actions written into shot two (cup down, face turned away, the neighbour
  half rising, his hand reaching) the model did one; the tea was poured from a
  cup held mouth-down like a bottle; the warm lamplight of shot one had turned
  blue by shot three; and the ending written for the old man's cup never
  arrived, because the last shot was a two-shot that did not contain it. That
  take is the origin of `references/direct-for-the-model.md`: literal
  expression, one action per shot, a lock line closing every shot, prop work as
  hand mechanics, and an ending the frame can hold. All seven prompts were
  rewritten through it; the set above is draft five.

- **Draft five (2026-09-27).** The first form of direct-for-the-model: muscles
  instead of idioms, one action per shot, everyone else told to hold, a lock
  line of light and identity. Clip 03 was rendered on the 即梦 surface as take 1
  of that draft. The face kept its colour under the same lamp in every shot, the
  tea was poured from a tilted cup with its base down, and the cup was set
  mouth-down in its own close-up, all as written. Three new faults were also as
  written: the guests, told to hold, froze mid-toast with cups in the air for
  three seconds; the old man's reaction, written as 嘴角压下 and a list of muscles
  with no feeling named, read as a sulk; and the close-up for the line placed
  the woman back in the doorway with blue night light behind her, because her
  only stated position was the door. Her delivery, directed only as 嘴唇平, was a
  dead face. The reference was rewritten: a feeling plus one anchor instead of a
  bare muscle list, idle business instead of a freeze, position in every lock
  line, and a directed delivery. The set above is draft six.

- **Draft six (2026-09-27).** Feeling plus anchor, idle business, position in
  the lock line, directed delivery. Clip 03 rendered on the 即梦 surface as take 1
  of that draft, and the acting was right for the first time: the toast alive
  with laughter until the door, the old man visibly alarmed with the cup going
  down, the guests turning and whispering, her line quiet with reddened eyes,
  the pour and the set-down exact. The geography was wrong. The master framed
  the head of the table facing the camera with the door behind him, so when the
  reaction shot said he looked at her, he looked toward the camera, at nothing.
  Then the cut went from that reaction straight to her hand at his cup, with no
  walk between: a teleport. The reference gained camera side and facing in every
  lock line, reactions written as reverse angles from the side of what is
  reacted to, and the rule that every crossing of a room is on screen. The
  ladder's person row was split from these takes. The set above is draft seven.

## Optional: one true before-and-after

If credits allow one more generation, render clip 01's typical brief exactly as
printed (*rich woman disguised as poor gets humiliated at luxury store, plot
twist, satisfying, cinematic, 4k*) with the same settings. Shown side by side with the directed take, it
is the clearest single image of what the skill changes. It is optional; the
text contrast on each card already carries the point.

## Render record

| Clip | Date | Surface and model line | Duration and ratio set | Take used | Deviations from the prompt |
|---|---|---|---|---|---|
| 01 | pending | | | | |
| 02 | pending | | | | |
| 03 | 2026-09-26 | 即梦, Seedance 2.0, draft-four prompt | 15 s, 16:9 | take 1, not published | face turned grey for 脸沉下来; one of four written actions; tea poured from a cup held mouth-down; lamplight shifted warm to blue across cuts; no ending on the cup; prompt replaced by draft five, which is pending |
| 03 | 2026-09-27 | 即梦, Seedance 2.0, draft-five prompt | 15 s, 16:9 | take 1, not published | colour, pour and set-down correct; room frozen mid-toast for three seconds; reaction read as a sulk; line delivered from the doorway in blue light, position never restated; delivery flat; prompt replaced by draft six, which is pending |
| 03 | 2026-09-27 | 即梦, Seedance 2.0, draft-six prompt | 15 s, 16:9 | take 1, not published | acting as written (alive toast, alarm, quiet line with reddened eyes, exact pour and set-down); master put the door behind him and his reaction looked toward the camera; cut from the door to her hand at the cup with no walk; prompt replaced by draft seven, which is pending |
| 04 | pending | | | | |
| 05 | pending | | | | |
| 06 | pending | | | | |
| 07 | pending | | | | |
