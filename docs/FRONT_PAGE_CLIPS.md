# Front-page clips: the shooting brief

Status: seven prompts written 2026-09-26, none rendered yet. The data behind
this page and the README slates is `data/front-page-clips.json`; the slates are
built by `scripts/build_clip_posters.py`, and `--check` keeps them in step.

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
Stretch rung on purpose, as the calibration the ladder's thresholds are
waiting for. Every prompt passed `scripts/moderation_prescreen.py` with no
finding before publication.

### Clip 01: By appointment only

- Language: English. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch: 4 beats, load 3, S = 2.1. File: `clip-01-by-appointment-only.mp4`.
- Typical brief: *rich woman disguised as poor gets humiliated at luxury store, plot twist, satisfying, cinematic, 4k*
- Premise on screen: By the end of shot one the audience knows she is being
  refused because of how she is dressed; shot three tells them she owns the
  place.
- Internal read: Narrative lane. Turn: the person being kept out is the person
  who owns the door. POV: hers, so she never has to speak. Force: the manager
  and the room's contempt. Visible suppressed behaviour: she sits on the display
  chaise instead of arguing. Non-transferable detail: wet bootprints across
  cream carpet (authored choice). Stock solution refused: no speech, no reveal
  card, no music.
- Screen: No cue words; the humiliation is in a line, the reversal is in a phone
  call.

> Shot 1. Wide shot inside a hushed luxury boutique on a rainy afternoon: cream carpet, glass shelves of shoes, two assistants in black. A woman in paint-stained overalls and work boots pushes the door open, dripping, and the manager steps into her path before she has taken three steps, hands folded, a thin smile: "We're by appointment only, ma'am." Shot 2. Cut to a medium shot of her: she does not answer; she sits down on the white display chaise, crosses her muddy boots, and looks around the room like someone measuring it. Shot 3. Cut to a close shot of the manager as his phone buzzes; he answers, listens, and the smile goes: "Yes, sir. The new owner is... standing in the shop now." His eyes lift to her. Shot 4. Cut to a two-shot from behind her: she points at one pair of shoes on the wall without a word, and the manager hurries to fetch them. Hold on the wet bootprints across the cream carpet. Soft grey window light, warm spots on the shelves. Sound: rain on the glass door, her boots on the carpet, the phone's buzz, his voice dropping; no music, no subtitles.

Review: the refusal line lands in shot one and the phone line in shot three,
each audible with the speaker alone in frame; she never speaks; she sits, then
points; the clip ends on the bootprints; no music; no subtitles.

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
  voice stays off screen so only one face has to sync.

> Shot 1. Wide shot of a wooden pier at night in a storm: a small fishing boat straining at a single mooring rope, its bow lifting and slamming with each swell, rain driven sideways through one sodium lamp, and behind the boat a wave building higher than the mast. Shot 2. Cut to a medium shot at deck height: a man in a soaked oilskin has both hands on the rope, boots braced against a cleat, the rope creaking as the boat pulls. From the dark behind the camera a voice shouts over the wind: "Let it go, Tom! It's only a boat!" Shot 3. Cut to a close shot of his face, rain running off his brow, eyes on the rope, and he shouts back without turning: "It's my father's!" Shot 4. Cut to a low angle: the wave breaks over the end of the pier and buries him in white water; when it drains away he is still standing, bent double, the rope still taut in his hands, the boat still there. Hold on the taut rope as the next swell lifts the bow. Orange sodium light and black water, nothing else. Sound: wind, the rope creaking, the two shouts, the wave's impact, water draining through the planks. No music, no subtitles.

Review: the off-screen shout and his answer are both audible; only his face is
on screen while speaking; the wave builds in shot one and breaks in shot four;
he is standing when it drains and the boat is still there; real speed; no
music; no subtitles.

### Clip 03: 这杯茶

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch: 4 beats, load 3, S = 2.1. File: `clip-03-this-cup-of-tea.mp4`.
- Typical brief: *豪门寿宴反转名场面，女主打脸全场，短剧爆点，电影感，高级感*
- Premise on screen: Shot one is a birthday banquet and a door opening on a
  woman nobody invited; shot two is the old man putting his cup down and turning
  away. The line in shot four says whose daughter she is.
- Internal read: Narrative lane. Turn: his toast becomes her verdict on him.
  POV: hers; he is a cup he never picks up again. Hidden want: the child's
  mother acknowledged, not money. Tactic: pour, then speak. Visible suppressed
  behaviour: she pours to the last drop and does not sit. Non-transferable
  detail: the empty cup set upside down on the wet cloth (authored choice).
  Stock solution refused: no slap, no tears, no music.
- Screen: The first draft of this slot named a divorce agreement, a law office
  and a child and was refused; this scene names none of them and says more.

> 镜头1：固定全景，老宅厅堂里的寿宴，红色横幅下一张大圆桌坐满了人，主位的老爷子举起茶杯，全桌跟着举杯。厅堂的门被推开，一个穿旧呢子大衣、头发淋湿的女人站在门口，全桌的人回头看她。镜头2：镜头切至老爷子的近景，他举着的杯子停在半空，然后重重放下，把脸转开；他身边的中年男人半站起来，伸手要拦。镜头3：镜头切至女人的中景，她从最近的座位上端起一只满杯的茶，一步一步走到主位前，桌边的人纷纷把椅子往后挪；她把整杯茶慢慢倒在老爷子面前的白桌布上，茶水漫开、冒着热气，一直倒到杯子空了，再把空杯倒扣在湿桌布上。镜头4：镜头切至两人的中景，她看着他，平静地说：“这杯茶，我妈等了二十年。”说完转身走向门口，镜头不跟，留在老爷子那只放下了、再也没有端起来的杯子上。灯光只有头顶一盏暖黄的老式吊灯。声音：全桌举杯的碰响，门推开的一声，杯子重重放下的声音，椅子挪动，茶水落在布上，说话时全场无声；无配乐。保持无字幕。时长：15秒。

Review: the door opens on her during the toast and every head turns; he puts
the cup down and turns away before she moves; the tea is poured to the last
drop and the cup set upside down; the line is Mandarin, audible, flat; the
clip ends on his cup; no music; no subtitles.

### Clip 04: 超时二十分钟

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch at the boundary: 4 beats, load 4, S = 1.9. File: `clip-04-twenty-minutes-late.mp4`.
- Typical brief: *外卖员被差评感人反转，正能量短剧，泪目，电影感*
- Premise on screen: Shot one is a soaked delivery rider at a door and a man
  with his phone out; shot two is the threat of a bad review. Shot three shows
  who is under the helmet.
- Internal read: Narrative lane. Turn: a customer about to punish becomes a
  host. POV: the rider's, at the threshold. Force: the phone in his hand. Hidden
  want: to keep the job without begging. Visible suppressed behaviour: she
  offers the refund before he can ask. Non-transferable detail: the small puddle
  of rain on his doormat that the last shot holds on (authored choice). Stock
  solution refused: no crying, no lecture, no music; he simply opens the door
  wider.
- Screen: No cue words. The reveal is a helmet coming off; no injury, no fall.

> 镜头1：固定中景，深夜住宅楼的走廊，雨声很大。一个穿黄色雨衣、戴着头盔的外卖员浑身滴水地站在门口，双手捧着一袋外卖。门开了，一个穿睡衣、握着手机的中年男人堵在门里，脸色难看。镜头2：镜头切至男人的近景，他把手机屏幕转向对方，说：“超时二十分钟，我要给差评。”镜头3：镜头切至外卖员的近景，她摘下头盔：花白的短发，六十岁上下，雨水顺着脸往下流。她把外卖递过去，低声说：“对不起，钱我退给您。”镜头4：镜头切至男人的近景，他按向屏幕的手指停住了，目光落到她湿透的鞋上；他没有接外卖，而是侧身让开门口，把门拉得更开。画面停在敞开的门和门口那一小滩雨水上。灯光只有走廊的白炽灯和门里透出的暖光。声音：雨声，头盔卡扣打开的声音，塑料袋的窸窣声，说话时其他声音压低；无配乐，保持无字幕。时长：15秒。

Review: his line comes before the helmet comes off; her line comes after, each
speaker alone in frame; the finger stops over the screen and he steps aside
instead of taking the bag; the clip ends on the open door and the puddle; no
music; no subtitles.

### Clip 05: 사직서

- Language: Korean. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch: 3.5 beats (two inserts at half), load 4, S = 2.0. File: `clip-05-resignation.mp4`.
- Typical brief: *사이다 사직서 장면, 직장인 드라마, 시네마틱, 4K, 감동*
- Premise on screen: Shot one is a CEO signing at night and an employee walking
  in; shot two is her envelope landing on the page he is signing. Her line says
  he stole her report and was promoted for it.
- Internal read: Narrative lane. Turn: the one who was ignored becomes the one
  who is looked at, too late. POV: hers until she turns; then the glass gives us
  him. Tactic: put the envelope on the page. Visible suppressed behaviour: she
  does not step back. Non-transferable detail: the envelope over his signature
  in progress (authored choice). Stock solution refused: no raised voice, no
  applause, no music; his face arrives only as a reflection.
- Screen: No cue words; the request for legible on-screen lettering on the
  envelope was removed because rendered text garbles.

> 샷 1: 밤의 유리벽 임원실, 넓은 책상 뒤에서 대표(오십 대 남성, 셔츠 소매를 걷음)가 서류에 서명하고 있고, 고개를 들지 않는다. 젊은 직원(이십 대 후반 여성, 회색 정장, 사원증을 목에 걸음)이 문을 열고 들어와 책상 앞까지 걸어온다. 샷 2: 책상 위 클로즈업, 그녀의 손이 흰 봉투 하나를 그가 서명하던 서류 바로 위에 올려놓는다. 펜이 멈춘다. 샷 3: 그녀의 미디엄 숏, 물러서지 않고 그를 내려다보며 말한다. 직원: “제 보고서, 이름만 바꾸셨더군요. 승진 축하드려요.” 샷 4: 대표의 클로즈업, 펜을 쥔 손이 굳고, 그제야 천천히 고개를 든다. 이미 그녀는 등을 돌려 문으로 걸어가고 있다. 샷 5: 유리문이 닫히고, 카메라는 유리에 비친 그의 얼굴에서 멈춘다. 조명은 책상 스탠드 하나와 창밖 도시의 불빛뿐. 소리: 펜 소리가 멈추는 순간, 봉투가 종이 위에 놓이는 소리, 구두 소리, 문이 닫히는 소리. 대사 중에는 다른 소리를 낮춘다. 음악 없음, 자막 없음.

Review: the envelope lands on the page he is signing and the pen stops before
she speaks; the line is Korean and audible; he looks up only after she has
turned; the clip ends on his reflection in the glass door; no music; no
subtitles.

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
  breath, not by school year.

> 手描きの2Dセルアニメーション。セル画のキャラクターを、水彩で描かれた背景画の上に置く。作画の密度が高く、限られた色数、フィルムの粒子が乗った質感。夏の決勝戦の九回裏、雨が降り始めた球場。ショット1：マウンドの投手（泥だらけのユニフォーム、帽子のつばから雨が落ちる）を正面から捉えたミディアムショット。肩で息をしている。背景の観客席は塗りの中でざわめきの色だけが動く。ショット2：カットして捕手のミットのクローズアップ。指がサインを出し、ミットが低く構えられる。ショット3：カットして投手のワインドアップ。振りかぶりからリリースまでを一コマ打ちのフルアニメーションで描き、腕の軌道は一枚のスミア、雨粒が腕の動きに引かれて流れる。ショット4：カットして打者の空振り。バットが空を切った瞬間、ボールがミットに収まる音と同時に画面全体を白黒反転のインパクトフレームにする。ショット5：カットして止め絵。投手がマウンドで膝をつき、帽子を取って空を見上げる。雨だけが動いている。その前後は二コマ打ち。カメラは背景画に対して固定。光は曇天の平坦な光と、濡れた土の反射。音：雨音、観客のざわめき、ミットの乾いた一音、そのあとは雨音と投手の息だけ。音楽なし、字幕なし。

Review: reads as drawn 2D cel over painted backgrounds, not photoreal or 3D;
the wind-up is a full-animation burst with one smear; the swing and the mitt
sound share one inverted impact frame; the clip ends on a held frame of the
pitcher kneeling in the rain; no music.

### Clip 07: Ещё один раунд

- Language: Russian. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch at the boundary: 4 beats (two at half), load 4, S = 1.9. File: `clip-07-one-more-round.mp4`.
- Typical brief: *тренер и боксёр перед решающим раундом, драма, кинематографично, эпично, 4k*
- Premise on screen: Shot one is a corner between rounds and a fighter who has
  stopped looking up; shot two is the trainer's line, and shot three shows who
  is watching from the stands.
- Internal read: Narrative lane. Turn: a fighter who wants permission to stop is
  given a reason to stand. POV: the corner's, at rope height. Force: the round
  to come and the woman in the stands. Visible suppressed behaviour: one nod,
  nothing else. Non-transferable detail: the towel left on the empty stool
  (authored choice). Stock solution refused: no shouted pep talk, no music, no
  slow-motion walk-out.
- Screen: The earlier draft had a cut, bleeding brow; it is a swollen brow under
  ice. No other cue.

> Кадр 1. Статичный средний план на уровне канатов: угол ринга между раундами, ночной боксёрский зал, единственный свет — лампа над рингом. Боксёр (лет двадцать пять, опухшая бровь, капа во рту) сидит на табурете, тяжело дышит и смотрит в пол. Тренер (за шестьдесят, полотенце на плече, седая щетина) прижимает к его брови лёд, завёрнутый в полотенце. Кадр 2. Крупный план тренера, он говорит ровно, не повышая голоса: «Хочешь бросить — бросай. Только мать смотрит.» Кадр 3. Кадр с трибун: среди сидящих зрителей стоит одна маленькая пожилая женщина в пальто, накинутом на плечи, руки сцеплены у груди. Кадр 4. Крупный план боксёра: он поднимает глаза в сторону трибун и один раз кивает. Кадр 5. Гонг. Он встаёт и выходит из кадра, а камера остаётся на пустом табурете с брошенным полотенцем. Звук: тяжёлое дыхание, шум зала за кадром, звон гонга в конце; во время реплики остальные звуки тише. Без музыки, без субтитров.

Review: the line is Russian and audible with the trainer alone in frame; the
woman in the stands is standing while everyone else sits; one nod follows; the
gong, he leaves the frame, the clip ends on the empty stool with the towel; no
music; no subtitles.

## What the first three drafts taught

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
| 03 | pending | | | | |
| 04 | pending | | | | |
| 05 | pending | | | | |
| 06 | pending | | | | |
| 07 | pending | | | | |
