# Front-page clips: the shooting brief

Status: seven prompts, fifth draft, written 2026-09-26; none of the current
prompts rendered yet. The fourth draft of clip 03 has one take, recorded at the
end of this file, and it is the reason the fifth draft exists. The data behind
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
Stretch rung on purpose, as the calibration the ladder's thresholds are waiting
for. Every prompt is directed for the model by
`references/direct-for-the-model.md`: one action per shot, expressions as
muscles and objects, prop work as a hand, an ending the last frame can hold, and
a lock line closing every shot. Every prompt passed
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
- Screen: No cue words. Directed for the model: the refusal is spoken from off
  frame so her shot has one action and no second face to sync; the manager's
  turn is written as the smile leaving his mouth, not as a face falling; every
  shot ends on the same daylight and the same two descriptions.

> Shot 1. Wide shot inside a hushed luxury boutique on a rainy afternoon: cream carpet, glass shelves of shoes, and two assistants in black behind the counter who stay still for the whole shot. A woman pushes the glass door open, steps inside dripping, and stops. From off frame the manager's voice, level and thin: "We're by appointment only, ma'am." She does not answer; her mouth stays closed. Light: soft grey daylight from the front window, warm spotlights on the shelves. The woman: thirties, dark hair tied back, white overalls stained with paint, tan work boots.
>
> Shot 2. Cut to a medium shot of her alone: she walks two steps to the white display chaise, sits down on it, and crosses one muddy boot over the other. Nothing else in the frame moves. Same light: soft grey daylight from the front window, warm spotlights on the shelves. The woman: thirties, dark hair tied back, white overalls stained with paint, tan work boots.
>
> Shot 3. Cut to a close shot of the manager alone, a phone already at his ear, listening. The smile leaves his mouth and his lips close; then he says, quieter: "Yes, sir. The new owner is... standing in the shop now." His eyes lift toward her, off frame. Same light: soft grey daylight from the front window, warm spotlights on the shelves. The manager: fifties, grey suit, steel-rimmed glasses.
>
> Shot 4. Cut to a two-shot from behind the chaise: she raises one arm and points at a single pair of shoes on the wall; the manager walks to the wall and lifts that pair down with both hands. Same light: soft grey daylight from the front window, warm spotlights on the shelves. The woman: thirties, dark hair tied back, white overalls stained with paint, tan work boots. The manager: fifties, grey suit, steel-rimmed glasses.
>
> Shot 5. Cut to a close insert of the cream carpet: a trail of wet bootprints from the door to the chaise, rain running down the glass door behind. Hold on the bootprints. Same light: soft grey daylight from the front window.
>
> Sound: rain on the glass door, her boots on the carpet, the murmur of the phone line, his voice dropping; no music, no subtitles.

Review: the refusal line is heard in shot one with only her on screen and her
mouth closed; the phone line in shot three with only him on screen; she never
speaks; she sits in shot two, points in shot four, and he lifts the shoes down;
the daylight and the two descriptions hold across every cut; the clip ends on
the insert of the bootprints; no music; no subtitles.

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
  he holds in every shot and the sea does the acting; the last shot is framed
  low with the bow behind him so the frame it ends on already contains him, the
  rope and the boat.

> Shot 1. Wide shot of a wooden pier at night in a storm: a small fishing boat straining at a single mooring rope, its bow lifting and slamming with each swell, rain driven sideways through one sodium lamp, and behind the boat a wave building higher than the mast. At the end of the pier a man stands with both hands on the rope and does not move. Light: one orange sodium lamp on its post at the end of the pier, black water beyond, nothing else. The man: forties, short beard streaked grey, yellow oilskin with the hood down, black rubber boots.
>
> Shot 2. Cut to a medium shot at deck height: the man has both hands on the rope, boots braced against a cleat, the rope creaking as the boat pulls; he holds and does not turn. From the dark behind the camera a voice shouts over the wind: "Let it go, Tom! It's only a boat!" Same light: one orange sodium lamp overhead, black water beyond. The man: forties, short beard streaked grey, yellow oilskin with the hood down, black rubber boots.
>
> Shot 3. Cut to a close shot of his face, rain running off his brow, eyes fixed on the rope; without turning his head he shouts back: "It's my father's!" Same light: one orange sodium lamp overhead, black water beyond. The man: forties, short beard streaked grey, yellow oilskin with the hood down.
>
> Shot 4. Cut to a low angle from the pier planks, looking up at him with the boat's bow behind him: the wave breaks over the end of the pier and buries him in white water. When the water drains through the planks he is still standing, bent double, both hands on the rope, the rope taut, the boat still there behind him. Hold on this frame as the next swell lifts the bow. Same light: one orange sodium lamp overhead, black water beyond. The man: forties, short beard streaked grey, yellow oilskin with the hood down, black rubber boots.
>
> Sound: wind, the rope creaking, the two shouts, the wave's impact, water draining through the planks. No music, no subtitles.

Review: the off-screen shout and his answer are both audible; only his face is
on screen while speaking and he does not turn his head; the wave builds in shot
one and breaks in shot four; he is standing when it drains, both hands on the
rope, and the boat is there behind him; the sodium light and his description
hold across every cut; real speed; no music; no subtitles.

### Clip 03: 这杯茶

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Stretch at the boundary: 4.5 beats (one insert at half), load 3.5, S = 1.9. File: `clip-03-this-cup-of-tea.mp4`.
- Typical brief: *豪门寿宴反转名场面，女主打脸全场，短剧爆点，电影感，高级感*
- Premise on screen: Shot one is a birthday banquet with every cup raised and a
  door opening on a woman nobody invited; shot two is the old man setting his
  cup down and the smile leaving his mouth. The line in shot four says whose
  daughter she is.
- Internal read: Narrative lane. Turn: his toast becomes her verdict on him.
  POV: hers; he is a cup he never picks up again. Hidden want: the child's
  mother acknowledged, not money. Tactic: pour, speak, then set the cup down
  mouth-down. Visible suppressed behaviour: she pours to the last drop and does
  not sit. Non-transferable detail: the empty cup set mouth-down on the wet
  cloth, given the last shot so the frame can hold it (authored choice). Stock
  solution refused: no slap, no tears, no music.
- Screen: The first draft of this slot named a divorce agreement, a law office
  and a child and was refused; this scene names none of them. The fourth draft
  rendered with a grey face, a cup held upside down while pouring, lamplight
  turning blue and no ending: this draft writes the reaction as muscles, gives
  the pour and the set-down their own close-ups with the hand written out, and
  repeats the lamp and the two descriptions at the end of every shot.

> 镜头1：固定全景，老宅厅堂里的寿宴。红色横幅下一张大圆桌坐满了宾客，主位的老爷子举着茶杯，全桌宾客也举着杯，停在半空。厅堂的门被推开，一个女人站在门口，不动；全桌宾客转头看她，然后不再动。灯光：头顶一盏暖黄的老式吊灯，桌布和人脸都在同一种暖黄光里。老爷子：七十多岁，白发向后梳，深棕色缎面唐装。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣。
>
> 镜头2：切至老爷子的近景。他把举着的茶杯放到面前的桌布上，放得很重；笑容消失，嘴角压下，下颌绷紧，眼睛看着桌布。他身边的宾客不动。灯光不变：头顶一盏暖黄吊灯，脸在暖黄光里。老爷子：七十多岁，白发向后梳，深棕色缎面唐装。
>
> 镜头3：切至桌面特写：白桌布，老爷子刚放下的那只满杯茶。女人的右手从画面右侧伸进来，握住杯身，把杯子提到桌布上方一掌高，杯口朝老爷子那一侧倾斜，茶水从杯沿流到白桌布上，冒着热气，一直流到杯里没有茶。整个过程杯子只是倾斜，杯底一直在下。老爷子放在桌边的手不动。灯光不变：头顶一盏暖黄吊灯。女人的手：袖口是旧的深灰色呢子。
>
> 镜头4：切至女人的近景，她一个人在画面里。她看着画面外的老爷子，嘴唇平，声音不高，说：“这杯茶，我妈等了二十年。”说完不动。灯光不变：头顶一盏暖黄吊灯，脸在暖黄光里。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣。
>
> 镜头5：切回桌面特写。她的右手转动手腕，把空杯杯口朝下扣在湿桌布上，松开手，手退出画面。画面停在倒扣的杯子和布上漫开的茶水上，老爷子放在桌边的手不动。灯光不变：头顶一盏暖黄吊灯。
>
> 声音：门推开的一声，杯子放到桌布上的一声，茶水落在布上的声音，说话时全场无声；无配乐。保持无字幕。时长：15秒。

Review: the door opens on her while every cup is raised, and every head turns;
he sets the cup down and the smile leaves his mouth; his face stays the same
colour in the same lamplight in every shot; the tea is poured from a tilted cup
with its base down until it is empty; the cup is set mouth-down only in the last
shot; the line is Mandarin, audible, flat, with her alone in frame; the clip
ends on the inverted cup on the wet cloth; no music; no subtitles.

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
  Directed for the model: his displeasure is a tightened brow and pressed lips,
  not a bad complexion; the helmet, the bag and the line each get their own
  shot; the last shot is framed from her position so the door and the wet tiles
  it lights are both inside the frame it ends on.

> 镜头1：固定中景，深夜住宅楼的走廊，雨声很大。外卖员站在门口，浑身滴水，左手提着一袋外卖，右手垂在身侧。门被从里面打开，一个男人站在门里，右手握着手机，眉头收紧，嘴唇抿住，看着她。两个人都不再动。灯光：走廊顶上一盏白色日光灯，门里透出暖黄的灯光。外卖员：黄色雨衣，黑色头盔，面罩抬起。男人：四十多岁，短黑发，深蓝色睡衣。
>
> 镜头2：切至男人的近景。他把手机屏幕转向她，说：“超时二十分钟，我要给差评。”说完手机还举着。灯光不变：走廊的白色日光灯在他脸的一侧，门里的暖黄光在另一侧。男人：四十多岁，短黑发，深蓝色睡衣，右手握着手机。
>
> 镜头3：切至外卖员的近景。她的右手解开头盔的卡扣，把头盔从头上摘下来，垂在身侧：头盔下是一头花白的短发，六十岁上下，雨水顺着脸往下流。她的嘴闭着。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光在脸的一侧。外卖员：黄色雨衣，花白短发，六十岁上下，左手提着外卖袋。
>
> 镜头4：同一机位，外卖员的近景。她把左手的外卖袋举到胸前，递向门里，低声说：“对不起，钱我退给您。”说完手举着不动。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光在脸的一侧。外卖员：黄色雨衣，花白短发，六十岁上下，右手垂着头盔。
>
> 镜头5：切至固定中全景，从外卖员的位置看向门，她不在画面里。男人侧身退到门边，把门拉到全开，门里的暖黄光照到门口湿的地砖上，他站在门边不动。画面停在敞开的门和门口地砖上的一小滩雨水上。灯光不变：走廊的白色日光灯在头顶，门里的暖黄光照出来。男人：四十多岁，短黑发，深蓝色睡衣，右手握着手机。
>
> 声音：雨声，头盔卡扣打开的一声，塑料袋的窸窣声，门轴的声音，说话时其他声音压低；无配乐，保持无字幕。时长：15秒。

Review: his line comes before the helmet comes off; her line comes after, each
speaker alone in frame; the helmet comes off in its own shot and the bag is
offered in the next; he steps aside and pulls the door to full open instead of
taking the bag; the corridor light and the warm light from the door hold across
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
  envelope was removed because rendered text garbles. Directed for the model: he
  looks up in his own shot rather than while she turns in his; the reflection
  ending was replaced by a wide from the corridor in which the closing door and
  the man behind it are both already in frame.

> 샷 1: 밤의 유리벽 임원실. 넓은 책상 뒤에서 대표가 서류에 서명하고 있고, 고개를 들지 않는다. 직원이 문을 열고 들어와 책상 앞까지 걸어와 선다. 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장, 목에 건 사원증.
>
> 샷 2: 책상 위 클로즈업. 그녀의 손이 흰 봉투 하나를 그가 서명하던 서류 바로 위에 올려놓는다. 그의 펜이 종이 위에서 멈춘다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛. 그녀의 손: 회색 정장 소매. 그의 손: 걷어 올린 흰 셔츠 소매, 검은 만년필.
>
> 샷 3: 그녀의 미디엄 숏, 혼자 화면에 있다. 물러서지 않고 화면 밖의 그를 내려다보며 말한다. 직원: “제 보고서, 이름만 바꾸셨더군요. 승진 축하드려요.” 말을 끝내고 움직이지 않는다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장, 목에 건 사원증.
>
> 샷 4: 대표의 클로즈업, 혼자 화면에 있다. 펜을 쥔 손은 종이 위에 멈춘 채, 그가 천천히 고개를 들어 화면 밖의 그녀를 본다. 입은 닫혀 있다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠.
>
> 샷 5: 복도 쪽에서 본 와이드 숏, 유리문과 그 너머의 임원실. 그녀가 유리문을 밀고 나와 카메라 옆을 지나 화면 밖으로 걸어가고, 문이 천천히 닫힌다. 유리 너머 책상의 그는 앉은 채 움직이지 않는다. 화면은 닫힌 유리문과 그 너머의 그에게서 멈춘다. 같은 조명: 책상 스탠드 하나의 따뜻한 빛과 창밖 도시의 불빛, 복도는 어둡다. 대표: 오십 대 남성, 백발이 섞인 짧은 머리, 소매를 걷은 흰 셔츠. 직원: 이십 대 후반 여성, 어깨까지 오는 검은 머리, 회색 정장.
>
> 소리: 펜이 멈추는 순간, 봉투가 종이 위에 놓이는 소리, 구두 소리, 유리문이 닫히는 소리. 대사 중에는 다른 소리를 낮춘다. 음악 없음, 자막 없음.

Review: the envelope lands on the page he is signing and the pen stops before
she speaks; the line is Korean and audible with her alone in frame; he looks up
in his own shot, after the line; the desk lamp and the two descriptions hold
across every cut; the clip ends on the closed glass door with him seated behind
it; no music; no subtitles.

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
  sign, the wind-up, the swing), the held frame written as a position rather
  than three gestures, and the medium, the light and the pitcher restated at the
  end of every shot so the cel look survives the cuts.

> 手描きの2Dセルアニメーション。セル画のキャラクターを、水彩で描かれた背景画の上に置く。作画の密度が高く、限られた色数、フィルムの粒子が乗った質感。夏の決勝戦の九回裏、雨が降り始めた球場。
>
> ショット1：マウンドの投手を正面から捉えたミディアムショット。肩で息をしている。それ以外は動かない。背景の観客席は塗りの中でざわめきの色だけが動く。光：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子、帽子のつばから雨が落ちる。
>
> ショット2：カットして捕手のミットのクローズアップ。低く構えたミットの横で、指が一度だけサインを出す。ミットは動かない。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光。ミット：濡れた茶色の革。
>
> ショット3：カットして投手のワインドアップ。振りかぶりからリリースまでを一コマ打ちのフルアニメーションで描き、腕の軌道は一枚のスミア、雨粒が腕の動きに引かれて流れる。カメラは背景画に対して固定。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子。
>
> ショット4：カットして打者の空振り。バットが空を切った瞬間、ボールがミットに収まる音と同時に画面全体を白黒反転のインパクトフレームにする。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光。打者：白いヘルメット、灰色のユニフォーム。
>
> ショット5：カットして止め絵に近いショット。投手がマウンドで片膝をつき、顔を空に向けている。動くのは雨と、息で上下する肩だけ。その前後のショットは二コマ打ち。作画は変わらない：手描きのセル画、水彩の背景。光は変わらない：曇天の平坦な光、濡れた土の反射。投手：泥だらけの白いユニフォーム、紺の帽子、帽子のつばから雨が落ちる。
>
> 音：雨音、観客のざわめき、ミットの乾いた一音、そのあとは雨音と投手の息だけ。音楽なし、字幕なし。

Review: reads as drawn 2D cel over painted backgrounds in every shot, not
photoreal or 3D; the wind-up is a full-animation burst with one smear; the swing
and the mitt sound share one inverted impact frame; the clip ends on a near-held
frame of the pitcher on one knee with his face to the rain; the flat light
holds; no music.

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
  shot one so the last frame needs no throw; the trainer and the fighter each
  act once in the last shot; the ring lamp and the two descriptions close every
  shot.

> Кадр 1. Статичный средний план на уровне канатов: угол ринга между раундами, ночной боксёрский зал, зал в темноте. Боксёр сидит на табурете, тяжело дышит и смотрит в пол. Тренер стоит над ним и прижимает к его брови пакет со льдом; больше никто не двигается. Свет: одна лампа над рингом, жёсткий белый свет сверху, всё остальное в темноте. Боксёр: лет двадцать пять, короткие тёмные волосы, опухшая левая бровь, капа во рту, красные перчатки. Тренер: за шестьдесят, седая щетина, серая футболка. Белое полотенце висит на верхнем канате рядом с табуретом.
>
> Кадр 2. Крупный план тренера, он один в кадре. Он говорит ровно, не повышая голоса, глядя вниз на боксёра за кадром: «Хочешь бросить — бросай. Только мать смотрит.» Тот же свет: одна лампа над рингом, жёсткий белый свет сверху. Тренер: за шестьдесят, седая щетина, серая футболка.
>
> Кадр 3. Кадр с трибун: среди сидящих зрителей стоит одна маленькая пожилая женщина, тёмное пальто накинуто на плечи, руки сцеплены у груди. Она не двигается, зрители вокруг сидят неподвижно. Тот же свет: лампа над рингом освещает ринг, трибуны в полутьме.
>
> Кадр 4. Крупный план боксёра, он один в кадре. Он поднимает глаза в сторону трибун и один раз кивает. Тот же свет: одна лампа над рингом, жёсткий белый свет сверху. Боксёр: лет двадцать пять, короткие тёмные волосы, опухшая левая бровь, капа во рту.
>
> Кадр 5. Тот же средний план, что в первом кадре. Гонг. Тренер убирает руку со льдом от брови; боксёр встаёт и выходит из кадра вперёд. Камера остаётся на пустом табурете под лампой и на полотенце, висящем на верхнем канате. Тот же свет: одна лампа над рингом, жёсткий белый свет сверху. Тренер: за шестьдесят, седая щетина, серая футболка. Боксёр: красные перчатки, капа во рту.
>
> Звук: тяжёлое дыхание, шум зала за кадром, звон гонга; во время реплики остальные звуки тише. Без музыки, без субтитров.

Review: the line is Russian and audible with the trainer alone in frame; the
woman in the stands is standing while everyone else sits; one nod follows in his
own shot; the gong, he leaves the frame, the clip ends on the empty stool with
the towel on the rope; the ring lamp holds; no music; no subtitles.

## What the first four drafts taught

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
| 04 | pending | | | | |
| 05 | pending | | | | |
| 06 | pending | | | | |
| 07 | pending | | | | |
