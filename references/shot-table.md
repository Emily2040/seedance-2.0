# Shot Table — the plan that exists before the prompt

Four takes of one fifteen-second banquet scene cost real money, and every
fault in them was a blank cell: a camera side the prompt never stated, a walk
it never scheduled, a crowd it never gave anything to do. The model fills
every blank with a default, and the default is never dramatic. A director does
not begin with prose. A director begins with a floor plan and a shot list, and
the prose is written from it. This reference makes that order mandatory for
the skill: for any prompt with more than one shot or more than one person, the
shot table exists first, the prompt is rendered from it, and the table travels
with the prompt so the person paying for the take can check the geometry on
paper before they spend anything. A single-subject continuous clip skips it.

## 1. The header: the floor plan in words

Before the table, three or four sentences that a stranger could draw from:
the landmarks (door, table, counter, window, ring), who is where at the start
and facing what, and the light source with its colour. Name the axis: "the
head of the table faces the door", "the counter is to the right of the door".
If the header cannot be drawn, the table cannot be filled.

## 2. The table

One row per shot, and every column filled in every row.

| Column | What goes in it | The default the model uses if it is blank |
|---|---|---|
| Shot | Number, in event order | — |
| Camera | Which side of the room, relative to a named landmark, and the size (wide, medium, close, insert) | Whatever composition is most common for the setting; the head of the table facing the lens |
| In frame | Each principal present, where they stand or sit, which way they face; background groups named once | People placed where the model last saw them |
| Eye-line | Who looks at what; for a reaction, the camera stands on the side of the thing reacted to, so the eyes go past the lens | Eyes to the lens, at nothing |
| Action | The one action of the shot; a reaction is a plain feeling plus one physical anchor; a prop is a hand and a tilt; a line is words plus voice plus eyes | The first verb understood; the rest dropped |
| Others | One line of idle business for everyone else in frame | A freeze, or invention |
| Light | The source and colour in the same words as the first row | Drift, warm to blue |
| Last frame | What the frame holds when the shot ends; it must be visible from the Camera cell | An ending the shot cannot see |

Rules for filling it:

- A cell that is empty, or says "default", "wherever", "as before" without the
  words repeated, means the prompt is not ready to be written.
- A principal who moves between landmarks gets a row for the crossing, with the
  camera placed so they move toward or past it. A cut from the door to a hand
  at the table is a teleport.
- A reaction row's Camera cell is on the side of what is reacted to. If the
  master was shot over his shoulder toward the door, his reaction is the
  reverse, from the door.
- The Last frame cell is checked against the Camera cell: a close-up cannot
  end on a puddle by the door; write the move or the next row.
- Positions are relative to landmarks, never to the previous shot.

## 3. The paper render

Read the finished table as a crew that has never met you, one row at a time,
and answer aloud: Where is the camera? What does each person face? Can the
person who reacts physically see the thing? Where was each person in the
previous row, and if elsewhere, which row walked them there? What is everyone
else doing? What feeling is named, and what does the body do? What does the
last frame hold? Any answer of "unstated" or "presumably" is a fault found on
paper, for free. A paper render costs nothing; a take on Seedance 2.0 costs
money and a retake costs it again. The table is the first debugging tool and
the retake is the last.

## 4. Render the prose from the rows

Each row becomes one shot block in the official order: the cut or camera
first, then the action and expression, then any change of position, then the
audio for that shot, then the lock line: light, each principal's identity,
position and facing, and the camera's side, in the same words as row one.
Nothing appears in the prose that is not in the table, and nothing in the
table is missing from the prose. The block rules and the lock line are in
[direct-for-the-model](direct-for-the-model.md); the block order and the ladder
are in [multishot-grammar](multishot-grammar.md).

## 5. Deliver the table with the prompt

The prompt is delivered with its table beneath it, collapsed where the surface
allows, so the person about to pay for the take can check the geometry on
paper first. The short route builds the table and may deliver the prompt
alone, but a cell it cannot fill is a question it must ask before delivering.

## 6. Both walls

Every rule in this repository was learned from a rendered fault, and every
fault has an opposite. A rule applied as an absolute swings the scene into the
other wall. Write to the middle column.

| Principle | One wall (observed) | The other wall (observed) | The middle |
|---|---|---|---|
| Expression | An idiom: the face turned grey | A bare list of muscles: a sulk | A plain feeling plus one physical anchor |
| Everyone else | Unwritten: invented business | "Nobody moves": a room of mannequins | One line of idle business that continues |
| Actions per shot | Four stacked: one survives | One per shot with the walk cut: a teleport | One action per shot, and the crossing is a shot |
| Position | Identity only: back in the doorway | Position without a camera side: looking at nothing | Position, facing and camera side in every lock line |
| Delivery | Only adjectives: overplayed | "Flat": a dead face | Voice, eyes, and what the face does after the last word |
| Shot count | Too many: lines and cuts garble (official) | Trimmed to fit a number: the story's shot is cut | The ladder ranks risk and never edits the table; when it says Ambitious, split into two generations |

## 7. The lint

`scripts/shot_table_check.py` reads every shot block of a storyboard prompt
and fails on a block without a camera side, a block without a light
statement, or a trap phrase from `data/direction-traps.json`. Run it on a
prompt of your own with `--text path`. It checks presence, not judgement: a
passing prompt can still be wrong, and a paper render is still owed.
