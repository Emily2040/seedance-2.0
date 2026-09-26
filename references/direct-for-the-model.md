# Direct for the Model — literal, alive, one action per shot, locked per shot

A video model is a crew that has never met you, cannot ask a question, and
takes every word at face value. It renders idioms as pictures, does the first
action it understands and drops the rest, forgets the light and the blocking
between cuts, and cannot move the camera unless told to. The rules below were
recorded from two rendered takes of the same banquet scene on 2026-09-26 and
2026-09-27. In the first, "his face fell" (脸沉下来) became a face turning
grey, four actions in one shot became one, a teacup was emptied like a bottle,
warm lamplight became blue two cuts later, and an ending written for a frame
the shot did not contain never arrived. The second take, written to the first
form of these rules, fixed all five and produced three new faults: a room told
to hold froze mid-toast like mannequins, a reaction written as a list of
muscles read as a sulk, and the woman delivered her line from the doorway she
had already left, because her position was never restated. Every rule below
is a repair for one of those eight. Load it with
[multishot-grammar](multishot-grammar.md) whenever a prompt has more than one
shot or more than one person.

## 1. Literal, always; and never lifeless

Write what a camera would record, never what a novelist would say. Idioms and
similes are rendered as literal pictures or ignored. But a list of muscles
without a feeling is not direction either: 嘴角压下 (mouth corners down) drew
a sulk where the scene needed a man caught out. Direct the way a director
directs an actor: name the feeling in a plain word the model knows, then give
one physical anchor. 他愣住，惊慌，眼睛盯着门口的她，喉结动了一下 (he freezes,
alarmed, eyes on her in the doorway, a swallow) is literal and alive.

| Language | Trap (renders literally or not at all) | Direction: feeling plus one anchor |
|---|---|---|
| English | his face fell; the smile goes; a look that could cut; like someone measuring the room | embarrassed, the polite smile fades and he swallows; calm, almost amused, she looks along the shelves |
| 中文 | 脸沉下来; 脸色难看; 脸色一变; 目光如刀; 心里一紧 | 他愣住，惊慌，眼睛盯着她，喉结动了一下; 不耐烦，眉头皱着，上下打量她 |
| 日本語 | 顔が曇る; 目が泳ぐ; 空気が凍る | 動揺して、笑みが消え、視線が彼女から離れない; 泣きそうな、しかし笑っている顔 |
| 한국어 | 얼굴이 어두워진다; 표정이 무너진다; 분위기가 얼어붙는다 | 당황한 얼굴, 할 말을 찾지 못해 입술이 살짝 벌어진다; 차분하지만 분명한 목소리 |
| Русский | лицо потемнело; лицо вытянулось; воздух застыл | растерян, улыбка сходит, он сглатывает; устало и с любовью, ровным голосом |

Colour is material, never mood: "warm tungsten from the ceiling lamp", not
"warm atmosphere"; "his face in the same lamplight as shot one", not "his face
darkens".

## 2. One action per shot, and the others keep living

Each shot block carries one primary action by one person. Everyone else in the
frame continues their idle business, and if one of them must act, that action
is the shot's second and last. "Hold" never means freeze. 全桌的人不动, "nothing
else in the frame moves", 動かない, 움직이지 않는다, никто не двигается render
a room of mannequins with cups in the air. Write the idle instead: the guests
keep looking at the door and whisper; the assistants exchange a glance; the
catcher pounds the mitt twice. Only objects are still. A block that says "he
puts the cup down, turns away, and the man beside him half rises" gets one of
the three. If the scene needs all three, they are three shots or two of them
are cut.

## 3. The lock line, in every shot: light, identity, position

Every shot block ends with a lock line that restates, in the same words as the
first shot: the light source and its colour; for each principal on screen
their age band, hair, wardrobe and any distinguishing object; and where each
principal is, relative to a fixed landmark. The model keeps nothing across a
cut that the prompt does not repeat, and that includes blocking: in the second
banquet take the woman's only stated position was the doorway, so her
close-up for the line put her back in the doorway with blue night light behind
her, two shots after her hand had poured the tea at the table. The lock line
is the price of a cut; write it even when it feels redundant, because
redundancy is how continuity is bought.

> 灯光不变：头顶一盏暖黄吊灯，脸在暖黄光里。老爷子：七十多岁，白发向后梳，深棕色缎面唐装，坐在主位。女人：三十多岁，黑色长发淋湿贴在脸侧，旧的深灰色呢子大衣，站在主位旁边。

> Same light: one warm tungsten lamp overhead. The manager: fifties, grey suit,
> steel-rimmed glasses, standing by the counter.

## 4. Prop mechanics, not verbs

"Pours", "flips", "hands over" are outcomes. Write the hand: which hand holds
what, by which part, the tilt, where the material goes, where the object ends.
Liquids come from vessels made to pour; a cup is tilted at the rim, a pot from
its spout. A cup set upside down is written as "turns her wrist and sets the
cup mouth-down on the cloth", not "flips the cup". Anything a human hand does
in one continuous motion of under two seconds is safe; anything with two grips
or a mid-air change of orientation is split into its own shot. The second
banquet take, with the pour and the set-down in separate close-ups, rendered
both exactly.

## 5. The frame can only hold what the shot contains

A shot ends where its framing can see. A two-shot cannot end on an insert of a
cup, and a close-up of a face cannot end on a puddle by the door. Either write
the camera move that gets there ("the camera tilts down to the wet
bootprints") or write the next shot. "The camera does not follow" is not an
ending; the frame it stays on has to be named. The same applies to people
crossing space: a cut may skip the walk from the door to the table, but the
next shot of that person must say where she now stands, or the model puts her
back where it last saw her.

## 6. Secondary people are alive, and furniture until directed

A crowd, a table of guests, a partner in a two-shot: they are described once
as a group and given one line of idle business that continues in every shot
they appear in (guests looking at the door, whispering; spectators talking).
Any individual who must act is a principal, gets a lock line, and gets one
action in one shot. This is why coverage helps: the reaction shot gives the
second person their one action without asking the model to run two
performances in one frame.

## 7. Direct the delivery, not the absence of it

"Flat", 平静地, 嘴唇平, 無表情, 담담하게 as the only direction for a line
render a dead face. Direct the voice and the eyes: quiet but every word clear;
her eyes stay on him; after the line her eyes redden but no tears come. Say
what the face does after the last word, because the model will otherwise hold
a mannequin until the cut.

## 8. The check before delivery

Read the draft and answer, per shot: what is the one action; who else is in
the frame and what idle business keeps them alive; is every reaction a plain
feeling plus one anchor, never an idiom and never a bare muscle list; does the
lock line repeat the light, each principal and where they stand; does the
ending sit inside the frame or get a move or a cut; is every prop action
written as a hand; is every line given a voice and eyes rather than "flat".
Then run the [moderation pre-screen](moderation-prescreen.md). A prompt that
fails any of these will render a different scene from the one intended, and
the retake will cost more than the sentence would have.
