# Direct for the Model — literal, one action per shot, locked per shot

A video model is a crew that has never met you, cannot ask a question, and
takes every word at face value. It renders idioms as pictures, does the first
action it understands and drops the rest, forgets the light between cuts, and
cannot move the camera unless told to. Recorded 2026-09-26 from a rendered
banquet take in which "his face fell" (脸沉下来) became a face turning grey,
four actions in one shot became one, a teacup was emptied like a bottle, warm
lamplight became blue two cuts later, and an ending written for a frame the
shot did not contain never arrived. Every rule below is a repair for one of
those. Load it with [multishot-grammar](multishot-grammar.md) whenever a prompt
has more than one shot or more than one person.

## 1. Literal, always

Write what a camera would record, never what a novelist would say. Expression
is muscles and objects: the smile leaves the mouth, the jaw sets, the eyes go to
the table, the hand puts the cup down. Idioms and similes are rendered as
literal pictures or ignored; either way the beat is lost.

| Language | Trap (renders literally or not at all) | Literal direction |
|---|---|---|
| English | his face fell; the smile goes; a look that could cut; like someone measuring the room | the smile leaves his face and his mouth closes; her eyes move from the shelves to the ceiling and back |
| 中文 | 脸沉下来; 脸色难看; 脸色一变; 目光如刀; 心里一紧 | 笑容消失，嘴角压下，下颌绷紧; 眉头收紧，嘴唇抿住; 眼睛盯住对方不动 |
| 日本語 | 顔が曇る; 目が泳ぐ; 空気が凍る | 笑みが消え、口が閉じる; 視線が左右に二度動く; 全員の動きが止まる |
| 한국어 | 얼굴이 어두워진다; 표정이 무너진다; 분위기가 얼어붙는다 | 웃음이 사라지고 입이 다물린다; 턱에 힘이 들어간다; 모두 동작을 멈춘다 |
| Русский | лицо потемнело; лицо вытянулось; воздух застыл | улыбка исчезает, губы сжимаются; глаза опускаются к столу; все замирают |

Colour is material, never mood: "warm tungsten from the ceiling lamp", not
"warm atmosphere"; "his face in the same lamplight as shot one", not "his face
darkens".

## 2. One action per shot, and the others hold

Each shot block carries one primary action by one person. Everyone else in the
frame holds their last position unless the block gives them one small action
of their own, and then that action is the shot's second and last. A block that
says "he puts the cup down, turns away, and the man beside him half rises" gets
one of the three. If the scene needs all three, they are three shots or two of
them are cut.

## 3. The lock line, in every shot

Every shot block ends with a lock line that restates, in the same words as the
first shot: the light source and its colour, and for each principal on screen
their age band, hair, wardrobe and any distinguishing object. The model keeps
nothing across a cut that the prompt does not repeat. The lock line is the
price of a cut; write it even when it feels redundant, because redundancy is
how continuity is bought.

> 灯光不变：头顶一盏暖黄吊灯。老爷子：七十多岁，白发向后梳，深棕色缎面唐装。

> Same light: one warm tungsten lamp overhead. The manager: fifties, grey suit,
> steel-rimmed glasses.

## 4. Prop mechanics, not verbs

"Pours", "flips", "hands over" are outcomes. Write the hand: which hand holds
what, by which part, the tilt, where the material goes, where the object ends.
Liquids come from vessels made to pour; a cup is tilted at the rim, a pot from
its spout. A cup set upside down is written as "turns her wrist and sets the
cup mouth-down on the cloth", not "flips the cup". Anything a human hand does
in one continuous motion of under two seconds is safe; anything with two grips
or a mid-air change of orientation is split or replaced.

## 5. The frame can only hold what the shot contains

A shot ends where its framing can see. A two-shot cannot end on an insert of a
cup, and a close-up of a face cannot end on a puddle by the door. Either write
the camera move that gets there ("the camera tilts down to the wet
bootprints") or write the next shot. "The camera does not follow" is not an
ending; the frame it stays on has to be named.

## 6. Secondary people are furniture until directed

A crowd, a table of guests, a partner in a two-shot: they are described once
as a group and told to hold. Any individual who must act is a principal, gets
a lock line, and gets one action in one shot. This is why coverage helps: the
reaction shot gives the second person their one action without asking the
model to run two performances in one frame.

## 7. The check before delivery

Read the draft and answer, per shot: what is the one action; who else is in
the frame and are they told to hold; is every expression a muscle or an object;
does the lock line repeat the light and the principals; does the ending sit
inside the frame or get a move or a cut; is every prop action written as a
hand. Then run the [moderation pre-screen](moderation-prescreen.md). A prompt
that fails any of these will render a different scene from the one intended,
and the retake will cost more than the sentence would have.
