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
without the skill), the internal read the skill used, the prompt as written,
the shape and ladder rung from `references/multishot-grammar.md`, and the review
checklist for the returned take. Every scene has stakes in frame, a force
against the character, escalation inside the clip and one visual peak (the
Stakes and Peak section of `references/directing-engine.md`), and every prompt
passed `scripts/moderation_prescreen.py` with no finding before publication.
The spectacle sits where the model renders well: weather, water, cloth, light,
drawn effects; contact stays singular; no endpoint is an accident.

### Clip 01: Footsteps

- Language: English. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (3 beats, load 0.5, S = 4.3). File: `clip-01-footsteps.mp4`.
- Typical brief: *scary parking garage scene, someone following a woman, horror, cinematic, jump scare, 4k*
- Internal read (narrative lane). Turn: alone to not alone, without anyone
  appearing. POV: hers; the audience hears what she hears and sees what she
  sees. Force: the second set of footsteps, then the open door. Visible
  suppressed behaviour: she stops dead and does not run. Non-transferable
  detail: the driver's door already open with the interior light on
  (authored choice). Stock solution refused: no figure in the shadows, no jump
  scare, no music sting; the peak is a door that should be shut.
- Screen: no named crime, no weapon, no injury; the fear is footsteps, a
  flicker, and a door.

> Shot 1. Tracking shot from behind a woman in a long coat walking fast through a near-empty underground car park at night, her heels echoing off the concrete, one fluorescent tube ahead of her flickering. A second set of footsteps echoes under hers, slightly out of step. Shot 2. Cut to a close shot of her face as she stops dead and listens: the second set of footsteps stops one beat after hers. She turns her head to look back down the aisle. Nothing there, only the tube flickering over rows of empty bays. Shot 3. Cut to her point of view as she turns back toward her car: the driver's door is already open and the interior light is on. She does not move. Cold green fluorescent light, pools of dark between the tubes. Sound: her heels, the second set of footsteps a beat behind, the tube's electrical buzz, then only the buzz. No music, no subtitles.

Review: the second footsteps stop one beat after hers, audibly; the aisle is
empty; the car door is open with the interior light on; she does not move at
the end; no music, no subtitles.

### Clip 02: Hold the line

- Language: English. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (3 beats, load 1, S = 3.75). File: `clip-02-hold-the-line.mp4`.
- Typical brief: *epic storm at sea, fisherman fights giant wave, slow motion, dramatic music, 8k*
- Internal read (narrative lane). Turn: a boat about to be lost to a boat
  still there. Force: the sea, acting first. Stakes in frame: the boat on one
  rope. Visible suppressed behaviour: he does not look at the wave; he looks
  at the rope. Non-transferable detail: boots braced against a cleat while
  water sheets around them (authored choice). Stock solution refused: no slow
  motion, no shouted defiance, no music; the peak is the rope still taut when
  the water drains.
- Screen: nothing to remove; water is the model's strongest material.

> Shot 1. Wide shot of a wooden pier at night in a storm: a small fishing boat straining at a single mooring rope, its bow lifting and slamming with each swell, rain driven sideways through one sodium lamp, and behind the boat a wave building higher than the mast. Shot 2. Cut to a medium shot at deck height: a man in a soaked oilskin has both hands on the rope, boots braced against a cleat, the rope creaking as the boat pulls; water sheets across the planks around his feet. Shot 3. Cut to a low angle: the wave breaks over the end of the pier and buries him in white water; when it drains away he is still standing, bent double, the rope still taut in his hands, the boat still there. Hold on the taut rope as the next swell lifts the bow. Orange sodium light and black water, nothing else. Sound: wind, the rope creaking, the wave's impact, water draining through the planks. No music, no subtitles.

Review: the wave builds in shot 1 and breaks in shot 3; the rope is taut
throughout; he is standing when the water drains and the boat is still there;
real speed; no music, no subtitles.

### Clip 03: 这杯茶

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (2 beats, load 3, S = 3.0). File: `clip-03-this-cup-of-tea.mp4`.
- Typical brief: *豪门家宴反转名场面，女主打脸全场，短剧爆点，电影感，高级感*
- Internal read (narrative lane). Turn: the family's toast becomes her
  verdict on the family. POV: hers; the elder is a raised cup and a frozen
  table. Hidden want: to be seen refusing, not to be heard arguing. Tactic:
  stand first, pour, speak last. Visible suppressed behaviour: she pours slowly
  to the last drop and does not sit. Non-transferable detail: the empty cup
  set upside down on the wet cloth (authored choice). Stock solution refused:
  no slap, no thrown glass, no tears, no music; the spectacle is tea spreading
  on white cloth.
- Load: one person beyond her (1), one line (1), the cup set down as contact
  (1); the cuts are free. S = 15 ÷ 5 = 3.0. The prose echo 时长：15秒 follows
  the documented tip; the duration is still set in the tool.
- Screen: the first draft of this slot named a legal document, a law office
  and a child and was refused; this version names none of them.

> 镜头1：固定中景，老宅厅堂里的家宴，一张大圆桌坐满了人，主位的老爷子举起茶杯准备说话。桌角，一位三十多岁的女人（黑色旗袍，头发盘起）先一步站起来，端起自己的茶杯，把满杯的茶慢慢倒在白色桌布上，茶水漫开、冒着热气，一直倒到杯子空了，再把空杯倒扣在湿掉的桌布上。镜头2：镜头切至全桌的广角，所有人都僵住，只有她站着。她看着主位，平静地说：“这杯茶，我妈等了二十年。”说完不坐下，画面停在满桌不动的人和那只倒扣的杯子上。灯光只有头顶一盏老式吊灯，暖黄，桌布最亮。声音：茶水落在桌布上的声音，杯底扣在桌上的一声轻响，说话时全场无声；无配乐。保持无字幕。时长：15秒。

Review: she stands before the elder speaks; the tea is poured to the last drop
and the cup set upside down; the line is Mandarin, audible, flat; the table is
frozen; the clip ends on the cup; no music, no subtitles.

### Clip 04: 竹海

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (3 beats, load 1, S = 3.75). File: `clip-04-bamboo-sea.mp4`.
- Typical brief: *红衣女侠竹林轻功，唯美国风，仙气飘飘，运镜炸裂，8K*
- Internal read (non-narrative lane, performance). Utility intent: weight and
  release made visible in bamboo, wind and rain, ending on the stalk that
  springs back empty. Refusal: no opponent, no blade, no wire-work fight, no
  music.
- Load: the landing on the near stalk is contact (1); every shot is locked.
  S = 15 ÷ 4 = 3.75.
- Screen: the first draft of this slot was a rooftop blade cut and carried
  two weapon cues; the spectacle moved into bamboo, cloth and rain.

> 镜头1：固定全景，雨中的竹海，风把整片竹梢压向一边，一个红衣女子从竹梢上掠过，每一步落下，那一竿竹子便弯一下又弹起，雨水从竹叶上被震落。镜头2：镜头切至中景，她落在离镜头最近的一竿竹子上，竹竿在她的重量下慢慢弯下来，越弯越低，把她一直送到镜头前，衣袖和发带被风拉直。镜头3：镜头切至低角度，竹竿弯到最低点的一瞬，她撑开一把油纸伞，伞面被雨打得发亮；竹竿弹回天空时她随竿而起，冲出画面上方，镜头停在空了的、还在摇晃的竹竿和雨帘上。全片青绿色的竹林和一点红衣，雨天的灰白天光。声音：风穿过竹林的声音，竹竿弯曲的吱呀声，伞面撑开时的一声脆响，雨声；无配乐，保持无字幕。时长：15秒。

Review: each landing bends a stalk that springs back; the near stalk bows to
camera; the umbrella opens at the lowest point; she leaves the frame upward as
the stalk springs back; the clip ends on the empty swaying stalk; no music.

### Clip 05: 사직서

- Language: Korean. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (2 beats, load 3, S = 3.0). File: `clip-05-resignation.mp4`.
- Typical brief: *사이다 사직서 장면, 직장인 드라마, 시네마틱, 4K, 감동*
- Internal read (narrative lane). Turn: the one who was ignored becomes the
  one who is looked at, too late. POV: hers until she turns; then the glass
  gives us him. Hidden want: to be seen once, on her terms. Tactic: put the
  envelope on the page he is signing. Subtext: the line is about a report, and
  not about the report. Visible suppressed behaviour: she does not step back.
  Non-transferable detail: the envelope placed over his signature in progress
  (authored choice). Stock solution refused: no raised voice, no applause, no
  music; his face arrives only as a reflection.
- Screen: no finding; a resignation envelope and a company office carry no
  cue.

> 샷 1: 밤의 유리벽 임원실, 책상 높이에 고정된 미디엄 숏. 넓은 책상 뒤에서 대표(오십 대 남성, 셔츠 소매를 걷음)가 서류에 서명하고 있고, 고개를 들지 않는다. 젊은 직원(이십 대 후반 여성, 회색 정장, 사원증을 목에 걸음)이 걸어 들어와 봉투 하나를 그가 서명하던 서류 바로 위에 올려놓는다. 봉투에는 ‘사직서’라고 적혀 있다. 그녀는 물러서지 않고 말한다. 직원: “제 보고서, 이름만 바꾸셨더군요.” 샷 2: 컷, 그녀가 돌아서서 문으로 걸어 나가는 뒷모습 너머로 대표가 그제야 고개를 든다. 문이 닫히고, 카메라는 유리에 비친 그의 얼굴에서 멈춘다. 조명은 책상 스탠드 하나와 창밖 도시의 불빛뿐. 소리: 펜 소리가 멈추는 순간, 봉투가 종이 위에 놓이는 소리, 구두 소리, 문이 닫히는 소리. 대사 중에는 다른 소리를 낮춘다. 음악 없음, 자막 없음.

Review: the envelope lands on the page he is signing and the pen stops; the
line is Korean and audible; he looks up only after she has turned; the clip
ends on his reflection; no music, no subtitles.

### Clip 06: 拍手

- Language: Japanese. Duration 12 s. 16:9. Shape: continuous, 2D animation. File: `clip-06-the-clap.mp4`.
- Typical brief: *神作画の巫女バトル、雨の神社、エモい、有名アニメスタジオ風、4K*
  (the studio name people usually attach is exactly what the copyright route
  removes; the prompt names technique, timing and palette instead).
- Internal read (non-narrative lane, performance). Utility intent: one
  purification clap animated the way the medium shows a decisive act: a burst
  on ones, sleeves and hair whipping, one inverted impact frame, then a held
  frame that lets the rain do the rest. Refusal: no dialogue, no
  transformation sequence, no photographic lens language, no second beast.
- Screen: the first draft armed a schoolgirl with a wooden practice blade,
  which stacked a minor with a weapon cue; the shrine maiden, no age given,
  strikes with a clap.

> 手描きの2Dセルアニメーション。セル画のキャラクターを、雨に濡れた夜の神社の石段を描いた背景画の上に置く。作画の密度が高く、限られた色数、フィルムの粒子が乗った質感。石段の中ほどで、白衣に緋袴の巫女（黒髪を一つに束ね、袖が雨で重い）が、階段の上から墨のように流れ落ちてくる黒い獣と向かい合う。獣が飛びかかる瞬間、巫女は一歩踏み込み、胸の前で両手を打ち鳴らす。踏み込みから拍手までを一コマ打ちのフルアニメーションで描き、袖と髪が遅れて大きく振れ、打った瞬間だけ画面全体を白黒反転のインパクトフレームにする。獣は黒い墨の飛沫になって砕け、雨に混じって石段を流れ落ち、消える。巫女は両手を合わせた姿勢のまま止め絵になり、肩だけが息で上下し、袖の揺れが遅れて静止する。その前後は二コマ打ち。カメラは背景画に対して固定。光は石灯籠の橙色の明かりと、雨に反射する青。音：雨音、踏み込みの足音、乾いた拍手の一音、そのあとは雨音だけ。音楽なし、字幕なし。

Review: drawn 2D cel over a painted background, not photoreal or 3D; the clap
is a burst with one inverted impact frame; the beast breaks into ink and washes
down the steps; a held frame with breathing shoulders and settling sleeves; no
music.

### Clip 07: Ещё один раунд

- Language: Russian. Duration 10 s. 16:9. Shape: continuous. File: `clip-07-one-more-round.mp4`.
- Typical brief: *тренер и боксёр перед решающим раундом, драма, кинематографично, эпично, 4k*
- Internal read (narrative lane). Turn: a fighter who has stopped looking up
  to one who stands. POV: the corner's, at rope height. Hidden want: the
  trainer wants him to finish; the fighter wants permission to stop. Tactic:
  one flat sentence and the ice held to the brow. Subtext: "then cry all you
  want" is tenderness dressed as an order. Visible suppressed behaviour: one
  nod, nothing else. Non-transferable detail: the towel left on the empty
  stool (authored choice). Stock solution refused: no shouted pep talk, no
  music, no slow-motion walk-out.
- Screen: the first draft had a cut, bleeding brow; it is now a swollen brow
  under ice, which carries the same round without the injury cue.

> Статичный средний план на уровне канатов, угол ринга между раундами. Ночной боксёрский зал, единственный свет — лампа над рингом. Боксёр (лет двадцать пять, опухшая бровь, капа во рту) сидит на табурете, тяжело дышит, смотрит в пол. Тренер (за шестьдесят, полотенце на плече, седая щетина) стоит над ним, прижимает к брови лёд, завёрнутый в полотенце, и, не повышая голоса, говорит. Тренер: «Ещё один раунд. Потом хоть плачь.» Боксёр поднимает глаза и кивает один раз. Гонг. Он встаёт и выходит из кадра, а камера остаётся на пустом табурете с брошенным полотенцем. Звук: тяжёлое дыхание, шум зала за кадром, звон гонга в конце; во время реплики остальные звуки тише. Без музыки, без субтитров.

Review: the line is Russian and audible with the ice on the brow; one nod, the
gong, he leaves the frame; the clip ends on the empty stool with the towel; no
music, no subtitles.

## What the first two drafts taught

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
  The whole draft was replaced by the set above.

## Optional: one true before-and-after

If credits allow one more generation, render clip 01's typical brief exactly as
printed (*scary parking garage scene, someone following a woman, horror,
cinematic, jump scare, 4k*) with the same settings. Shown side by side with the directed take, it
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
