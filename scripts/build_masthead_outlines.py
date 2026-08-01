"""Produce assets/masthead-outlines.json: display type as vector outlines."""
import json
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

ROM, ITA = "BodoniModa-var.ttf", "BodoniModa-Italic-var.ttf"

def outline(src, text, size, opsz, wght, precision):
    font = instantiateVariableFont(TTFont(src), {"opsz": opsz, "wght": wght}, inplace=False)
    font.save("/tmp/_i.ttf")
    data = open("/tmp/_i.ttf","rb").read()
    face = hb.Face(data); hbf = hb.Font(face); upem = face.upem; hbf.scale = (upem, upem)
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    hb.shape(hbf, buf, {"kern": True, "liga": True})
    gs, order = font.getGlyphSet(), font.getGlyphOrder()
    scale = size/upem; x = 0.0; parts = []
    fmt = (lambda v: f"{v:.{precision}f}")
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = SVGPathPen(gs, ntos=fmt)
        t = Transform(scale, 0, 0, -scale, x + pos.x_offset*scale, -pos.y_offset*scale)
        gs[order[info.codepoint]].draw(TransformPen(pen, t))
        d = pen.getCommands()
        if d: parts.append(d)
        x += pos.x_advance*scale + tracking_of(text)
    return " ".join(parts), round(x, 2)

def tracking_of(_t): return 0.0

# Optical size tracks the rendered size, clamped to the axis range (6-96).
# That is what the axis is for: a didone drawn for 96px has hairlines that
# vanish at 26px, and one drawn for 26px looks clumsy blown up to 128.
def opsz_for(size): return max(6, min(96, size))

SPECS = {
    "wordmark":  dict(src=ROM, text="Seedance 2.0",                  size=128, wght=400, precision=1),
    "skill_os":  dict(src=ROM, text="Skill OS",                      size=66,  wght=400, precision=1),
    "tagline_1": dict(src=ITA, text="Direct the model.",             size=26,  wght=400, precision=1),
    "tagline_2": dict(src=ITA, text="Don’t micro-manage the frame.", size=26, wght=400, precision=1),
}

glyphs = {}
for key, s in SPECS.items():
    d, adv = outline(s["src"], s["text"], s["size"], opsz_for(s["size"]), s["wght"], s["precision"])
    glyphs[key] = {"text": s["text"], "size": s["size"], "advance": adv, "d": d}
    print(f"{key:10} advance={adv:8.2f} chars={len(d)}")

doc = {
    "_comment": (
        "Display type for the masthead, stored as vector outlines rather than live text. "
        "Regenerate with scripts/build_masthead_outlines.py only when the wordmark or "
        "tagline copy changes."
    ),
    "provenance": {
        "font_family": "Bodoni Moda",
        "font_version": "Version 2.005",
        "designer": "Owen Earl",
        "license": "SIL Open Font License 1.1",
        "license_url": "https://scripts.sil.org/OFL",
        "source": "https://github.com/google/fonts/tree/main/ofl/bodonimoda",
        "instances": "opsz tracks rendered size clamped to 6-96; wght=400 throughout",
        "shaping": "HarfBuzz with kern and liga features enabled",
        "note": (
            "Outlines are glyph geometry, not the font software; the OFL permits this and "
            "no font file is redistributed here. Attribution is retained above."
        ),
    },
    "glyphs": glyphs,
}
json.dump(doc, open("masthead-outlines.json","w"), indent=2, ensure_ascii=False)
print("total bytes:", len(json.dumps(doc)))
