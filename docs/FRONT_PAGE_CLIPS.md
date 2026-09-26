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
  or append a style name.
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
checklist for the returned take. Every scene has a turn, a threat or a strike:
these are the clips people stop for, and each one still keeps the rules that
make a take reviewable (one move per shot, a visible endpoint, no seconds in
the prompt, no studio names, one speaker).

### Clip 01: Get in.

- Language: English. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (3 beats, load 2, S = 3.0). File: `clip-01-get-in.mp4`.
- Typical brief: *scary moment, woman hears someone breaking in at night, thriller, cinematic, suspense music, 4k*
- Internal read (narrative lane). Turn: intruder to shelter. POV: the mother's;
  the camera stands where she stands. Power: the door holds it, then she does.
  Hidden want: to keep the home closed. Tactic: the chain and the knife.
  Subtext: she says "Get in", not "what happened". Visible suppressed
  behaviour: the knife lowers but the shoulder stays tense. Non-transferable
  detail: the school lanyard with his key still in his hand (authored choice).
  Stock solution refused: no scream, no music sting, no jump scare.
- Load: one person beyond the first (1), one spoken line (1); every shot is
  locked, so the cuts are free. S = 15 ÷ 5 = 3.0.

> Shot 1. Locked shot down a dark apartment hallway at two in the morning: the front door with its chain on, one bar of streetlight across the floor, and in the foreground a woman in a T-shirt standing very still with a kitchen knife held low along her thigh. A key scrapes in the lock, misses, tries again. Shot 2. Cut to the door from her side as it opens to the length of the chain: in the gap, a teenage boy soaked with rain, a split lip, a school lanyard with the key still in his hand, his eyes on the knife. Shot 3. Cut to a close shot of her face: she takes one breath, the knife hand drops out of frame but the shoulder stays tense, and she says quietly: "Get in." Then she reaches past the camera to slide the chain. Light only from the streetlamp through the window and the stairwell bulb behind him. Sound: the key in the lock, rain on the landing, the chain sliding at the very end. No music, no subtitles.

Review: three framings in this order; the knife lowers but the shoulder stays
tense; the line is quiet and audible; no scream, no sting, no subtitles; the
chain slides only at the end.

### Clip 02: Last train

- Language: English. Duration 12 s. 16:9. Shape: continuous. File: `clip-02-last-train.mp4`.
- Typical brief: *girl running to catch the last train, action scene, dynamic camera, slow motion, epic*
- Internal read (non-narrative lane, physical action). Utility intent: one
  sprint with a mechanical obstacle that answers back, ending on a small
  humiliation instead of a triumph. Refusal: no slow motion, no hero
  landing, no second character, no score.

> Handheld tracking shot running alongside a woman in a wet raincoat as she sprints down an empty subway platform toward the last train, her bag slamming against her hip, the door-closing chime already sounding. The doors begin to slide shut; she throws her forearm into the gap; the rubber edges bite, bounce back open, and she gets through as they close behind her, catching the tail of her coat outside the glass. The camera stops at the closed door with her coat tail pinned in it as the train starts to move. Cold fluorescent platform light, warm light inside the carriage. Sound: her footsteps and breath, the chime, the rubber slap of the doors, the train pulling away. No music, no subtitles.

Review: one tracking move that stops at the closed door; the forearm goes in,
the doors reopen, the coat tail is pinned as the train moves; real speed, no
music, no subtitles.

### Clip 03: 签字

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (2 beats, load 3, S = 3.0). File: `clip-03-the-signature.mp4`.
- Typical brief: *霸总短剧，离婚签字名场面，女主逆袭，电影感，高级感，8K*
- Internal read (narrative lane). Turn: the party who was owed becomes the
  party who dictates. POV: hers; his hands are all we get of him. Hidden want:
  the child's name, not the money. Tactic: sign first, speak second. Subtext:
  the ring on the signature says what the line does not. Visible suppressed
  behaviour: the pen pauses before the last stroke. Non-transferable detail:
  the ring placed on the signature (authored choice). Stock solution refused:
  no tears, no slap, no music swell; the camera stays on his hands.
- Load: one person beyond the first (1), one line (1), the ring set on the
  paper as contact that must land (1). S = 15 ÷ 5 = 3.0.

> 镜头1：固定特写，深夜律师事务所的会议桌，一份离婚协议摊在桌上，一支钢笔在“女方”一栏签下名字，笔尖停顿一下再收；签完，一枚婚戒被摘下来，轻轻放在签名上面。镜头2：镜头切至女方的中近景，她（三十五岁上下，黑色西装，头发全部束起，眼睛不红）看向对面，平静地说：“房子我不要。孩子的姓，改回来。”说完起身离开画面，镜头不跟，停在对面男人放在桌上一动不动的双手上，直到画面结束。灯光只有桌面上方一盏冷白色的吊灯，窗外是城市夜景。声音：钢笔划纸声，戒指落在纸上的轻响，椅子推开的声音，说话时其他声音压低；无配乐。保持无字幕。

Review: the pen pauses and the ring lands on the signature before the cut; the
line is Mandarin, audible, flat, dry-eyed; the camera stays on his hands; no
music, no subtitles.

### Clip 04: 雪夜斩灯

- Language: Chinese. Duration 15 s. 16:9. Shape: storyboard. Rung: Safe (3 beats, load 1.5, S = 3.3). File: `clip-04-lantern-cut.mp4`.
- Typical brief: *武侠女侠雪夜拔刀，超燃打戏，运镜炸裂，大片感，特效*
- Internal read (non-narrative lane, performance). Utility intent: one draw,
  one cut, and the discipline of the sheathing, with the falling lantern as
  the only opponent. Refusal: no enemy crowd, no wire-work flight, no score.
- Load: the blade through the lantern is contact that must land (1); the third
  shot's push-in is the only move (0.5). S = 15 ÷ 4.5 = 3.3. The prose echo
  时长：15秒 follows the documented tip; the duration is still set in the tool.

> 镜头1：固定全景，雪夜的古城屋脊，一名女剑客（二十多岁，黑色劲装，斗笠压低）背对镜头站在瓦片上，右手按在刀柄上，雪落在肩头不化。远处一盏红灯笼从高处坠落。镜头2：镜头切至侧面中景，灯笼落到她身前的一瞬，她拔刀，只出一刀，刀光横过画面，灯笼被整齐劈成两半，烛火在半空中晃了一下熄灭，两半灯笼各自落向屋檐两侧。镜头3：镜头切至低角度，缓慢推近她收刀入鞘的手，刀身上沾的雪粒随着入鞘被刮落，最后停在刀镡合上的那一刻，画面保持。全片冷蓝月光，只有灯笼熄灭前的一点暖光。声音：风雪声，拔刀的金属声，灯笼纸被劈开的脆响，入鞘的一声轻响；无配乐，保持无字幕。时长：15秒。

Review: one draw, one cut, two halves, flame out; the only move is the push-in
in shot 3, ending as the guard closes; no music, no subtitles.

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
- Load: one person beyond the first (1), one line (1), the envelope placed on
  the page as contact (1). S = 15 ÷ 5 = 3.0.

> 샷 1: 밤의 유리벽 임원실, 책상 높이에 고정된 미디엄 숏. 넓은 책상 뒤에서 대표(오십 대 남성, 셔츠 소매를 걷음)가 서류에 서명하고 있고, 고개를 들지 않는다. 젊은 직원(이십 대 후반 여성, 회색 정장, 사원증을 목에 걸음)이 걸어 들어와 봉투 하나를 그가 서명하던 서류 바로 위에 올려놓는다. 봉투에는 ‘사직서’라고 적혀 있다. 그녀는 물러서지 않고 말한다. 직원: “제 보고서, 이름만 바꾸셨더군요.” 샷 2: 컷, 그녀가 돌아서서 문으로 걸어 나가는 뒷모습 너머로 대표가 그제야 고개를 든다. 문이 닫히고, 카메라는 유리에 비친 그의 얼굴에서 멈춘다. 조명은 책상 스탠드 하나와 창밖 도시의 불빛뿐. 소리: 펜 소리가 멈추는 순간, 봉투가 종이 위에 놓이는 소리, 구두 소리, 문이 닫히는 소리. 대사 중에는 다른 소리를 낮춘다. 음악 없음, 자막 없음.

Review: the envelope lands on the page he is signing and the pen stops; the
line is Korean and audible; he looks up only after she has turned; the clip
ends on his reflection; no music, no subtitles.

### Clip 06: 雨の石段

- Language: Japanese. Duration 12 s. 16:9. Shape: continuous, 2D animation. File: `clip-06-rain-steps.mp4`.
- Typical brief: *神作画の少女バトル、雨の神社、エモい、有名アニメスタジオ風、4K*
  (the studio name people usually attach is exactly what the copyright route
  removes; the prompt names technique, timing and palette instead).
- Internal read (non-narrative lane, performance). Utility intent: one strike
  animated the way the medium shows a decisive strike, a smear, an inverted
  impact frame, a burst on ones, and then a held frame that lets the rain do
  the rest. Refusal: no dialogue, no transformation sequence, no photographic
  lens language, no second beast.

> 手描きの2Dセルアニメーション。セル画のキャラクターを、雨に濡れた夜の神社の石段を描いた背景画の上に置く。作画の密度が高く、限られた色数、フィルムの粒子が乗った質感。石段の中ほどで、少女（十七歳、黒い学生服の上に透明な雨合羽、木刀を両手で構える）が、階段の上から流れ落ちてくる墨のような黒い獣と向かい合う。獣が飛びかかる瞬間、少女は一歩踏み込んで木刀を横に振り抜く。振りの軌道は一枚のスミアで描き、当たった瞬間だけ画面全体を白黒反転のインパクトフレームにする。獣は黒い墨の飛沫になって砕け、雨に混じって石段を流れ落ち、消える。少女は振り抜いた姿勢のまま止め絵になり、肩だけが息で上下し、髪と合羽の裾が遅れて揺れて静止する。動きは踏み込みから振り抜きまでを一コマ打ちのフルアニメーションで、その前後は二コマ打ち、止め絵で終わる。カメラは背景画に対して固定。光は石灯籠の橙色の明かりと、雨に反射する青。音：雨音、踏み込みの足音、風を切る一振り、当たった瞬間の鋭い一音、そのあとは雨音だけ。音楽なし、字幕なし。

Review: drawn 2D cel over a painted background, not photoreal or 3D; the
strike is one smear and one inverted impact frame; the beast breaks into ink
and washes down the steps; a held frame with breathing shoulders and settling
cloth; no music.

### Clip 07: Ещё один раунд

- Language: Russian. Duration 10 s. 16:9. Shape: continuous. File: `clip-07-one-more-round.mp4`.
- Typical brief: *тренер и боксёр перед решающим раундом, драма, кинематографично, эпично, 4k*
- Internal read (narrative lane). Turn: a fighter who has stopped looking up
  to one who stands. POV: the corner's, at rope height. Hidden want: the
  trainer wants him to finish; the fighter wants permission to stop. Tactic:
  one flat sentence and the enswell held to the brow. Subtext: "then cry all
  you want" is tenderness dressed as an order. Visible suppressed behaviour:
  one nod, nothing else. Non-transferable detail: the mouthguard taken out,
  checked and put back (authored choice). Stock solution refused: no shouted
  pep talk, no music, no slow-motion walk-out; the camera stays on the empty
  stool.

> Статичный средний план на уровне канатов, угол ринга между раундами. Ночной боксёрский зал, единственный свет — лампа над рингом. Боксёр (лет двадцать пять, рассечённая бровь, капа во рту) сидит на табурете, тяжело дышит, смотрит в пол. Тренер (за шестьдесят, полотенце на плече, седая щетина) стоит над ним, прижимает к брови холодный металлический утюжок и, не повышая голоса, говорит. Тренер: «Ещё один раунд. Потом хоть плачь.» Боксёр поднимает глаза, кивает один раз; тренер вынимает капу, проверяет и вставляет обратно. Гонг. Боксёр встаёт и выходит из кадра, а камера остаётся на пустом табурете с полотенцем. Звук: тяжёлое дыхание, шум зала за кадром, звон гонга в конце; во время реплики остальные звуки тише. Без музыки, без субтитров.

Review: the line is Russian and audible with the enswell on the brow; one
nod, the mouthguard checked and replaced, the gong, he leaves the frame; the
clip ends on the empty stool; no music, no subtitles.

## Optional: one true before-and-after

If credits allow one more generation, render clip 01's typical brief exactly as
printed (*scary moment, woman hears someone breaking in at night, thriller,
cinematic, suspense music, 4k*) with the same settings. Shown side by side with the directed take, it
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
