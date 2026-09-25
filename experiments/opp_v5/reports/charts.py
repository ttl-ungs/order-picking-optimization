"""MetaPost chart helpers shared by the ConTeXt exploration reports.

Charts are emitted as \\startMPcode blocks following docs/guides/context_style_guide.md
(palette colours, 1pt axes, 1.5pt lines, 4pt dots). Numbers are formatted the Spanish
way because the reports are written in Spanish, like the rest of the thesis documents.
"""
import csv
import math
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
STUDIES = os.path.join(ROOT, "experiments", "opp_v5", "studies")


def rows(rel):
    with open(os.path.join(STUDIES, rel), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def es(v, dec=1):
    """Spanish number format: decimal comma, thousands dot."""
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


class Chart:
    def __init__(self, xmin, xmax, ymin, ymax, w=11.0, h=6.0, logy=False, xcat=None):
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax
        self.w, self.h, self.logy = w, h, logy
        self.out = [f"numeric w, h; w := {w}cm; h := {h}cm;"]

    def X(self, x):
        return (x - self.xmin) / (self.xmax - self.xmin) * self.w

    def Y(self, y):
        if self.logy:
            lo, hi = math.log10(self.ymin), math.log10(self.ymax)
            return (math.log10(y) - lo) / (hi - lo) * self.h
        return (y - self.ymin) / (self.ymax - self.ymin) * self.h

    @staticmethod
    def p(x, y):
        return f"({x:.3f}cm,{y:.3f}cm)"

    def axes(self, xticks, yticks, xlabel, ylabel):
        o = self.out
        o.append("drawarrow (0,0)--(w+0.4cm,0) withpen pencircle scaled 1pt;")
        o.append("drawarrow (0,0)--(0,h+0.4cm) withpen pencircle scaled 1pt;")
        for v, lab in xticks:
            x = self.X(v)
            o.append(f"draw {self.p(x, 0)}--{self.p(x, -0.12)} withpen pencircle scaled .5pt;")
            o.append(f'label.bot(textext("\\tfx {lab}"), {self.p(x, -0.12)});')
        for v, lab in yticks:
            y = self.Y(v)
            o.append(f"draw {self.p(0, y)}--{self.p(-0.12, y)} withpen pencircle scaled .5pt;")
            o.append(f'label.lft(textext("\\tfx {lab}"), {self.p(-0.12, y)});')
        o.append(f'label.bot(textext("{xlabel}"), (w/2,-0.85cm));')
        o.append(f'label.lft(textext("{ylabel}") rotated 90, (-1.25cm,h/2));')

    def cat_axes(self, cats, yticks, ylabel):
        """Categorical x axis: cats is a list of (center_x_value, label)."""
        o = self.out
        o.append("drawarrow (0,0)--(w+0.4cm,0) withpen pencircle scaled 1pt;")
        o.append("drawarrow (0,0)--(0,h+0.4cm) withpen pencircle scaled 1pt;")
        for v, lab in cats:
            o.append(f'label.bot(textext("\\tfx {lab}"), {self.p(self.X(v), -0.1)});')
        for v, lab in yticks:
            y = self.Y(v)
            o.append(f"draw {self.p(0, y)}--{self.p(-0.12, y)} withpen pencircle scaled .5pt;")
            o.append(f'label.lft(textext("\\tfx {lab}"), {self.p(-0.12, y)});')
        o.append(f'label.lft(textext("{ylabel}") rotated 90, (-1.25cm,h/2));')

    def line(self, pts, color, dashed=False, smooth=False, markers=True):
        path = ("..." if smooth else "--").join(self.p(self.X(x), self.Y(y)) for x, y in pts)
        dash = " dashed evenly" if dashed else ""
        self.out.append(f"draw {path} withpen pencircle scaled 1.5pt withcolor \\MPcolor{{{color}}}{dash};")
        if markers:
            for x, y in pts:
                self.dot(x, y, color)

    def dot(self, x, y, color):
        self.out.append(f"fill fullcircle scaled 4pt shifted {self.p(self.X(x), self.Y(y))} withcolor \\MPcolor{{{color}}};")

    def open_dot(self, x, y, color):
        self.out.append(
            f"draw fullcircle scaled 6pt shifted {self.p(self.X(x), self.Y(y))} "
            f"withpen pencircle scaled 1pt withcolor \\MPcolor{{{color}}};")

    def note(self, x, y, text, pos="top", dx=0.0, dy=0.0):
        self.out.append(f'label.{pos}(textext("\\tfxx {text}"), {self.p(self.X(x) + dx, self.Y(y) + dy)});')

    def hline(self, y, text, at="left"):
        yy = self.Y(y)
        self.out.append(f"draw {self.p(0, yy)}--{self.p(self.w, yy)} withpen pencircle scaled .5pt dashed evenly;")
        if at == "left":
            self.out.append(f'label.rt(textext("\\tfxx {text}"), {self.p(0.1, yy + 0.2)});')
        else:
            self.out.append(f'label.lft(textext("\\tfxx {text}"), {self.p(self.w - 0.1, yy - 0.2)});')

    def bar(self, x0, width, y0, y1, color, outline=False):
        a, b = self.X(x0), self.X(x0 + width)
        c, d = (self.Y(y0) if y0 > 0 or not self.logy else 0.0), self.Y(y1)
        box = f"{self.p(a, c)}--{self.p(b, c)}--{self.p(b, d)}--{self.p(a, d)}--cycle"
        if outline:
            self.out.append(f"draw {box} withpen pencircle scaled 1pt withcolor \\MPcolor{{{color}}};")
        else:
            self.out.append(f"fill {box} withcolor \\MPcolor{{{color}}};")

    def legend(self, entries, x=0.35, top=None):
        top = self.h - 0.15 if top is None else top
        for i, (color, text, kind) in enumerate(entries):
            y = top - 0.42 * i
            if kind == "line":
                self.out.append(f"draw {self.p(x, y)}--{self.p(x + 0.6, y)} withpen pencircle scaled 1.5pt withcolor \\MPcolor{{{color}}};")
            elif kind == "dashed":
                self.out.append(f"draw {self.p(x, y)}--{self.p(x + 0.6, y)} withpen pencircle scaled 1.5pt withcolor \\MPcolor{{{color}}} dashed evenly;")
            elif kind == "dot":
                self.out.append(f"fill fullcircle scaled 4pt shifted {self.p(x + 0.3, y)} withcolor \\MPcolor{{{color}}};")
            elif kind == "open":
                self.out.append(f"draw fullcircle scaled 6pt shifted {self.p(x + 0.3, y)} withpen pencircle scaled 1pt withcolor \\MPcolor{{{color}}};")
            elif kind == "box":
                self.out.append(f"fill {self.p(x + 0.1, y - 0.12)}--{self.p(x + 0.5, y - 0.12)}--{self.p(x + 0.5, y + 0.12)}--{self.p(x + 0.1, y + 0.12)}--cycle withcolor \\MPcolor{{{color}}};")
            elif kind == "outline":
                self.out.append(f"draw {self.p(x + 0.1, y - 0.12)}--{self.p(x + 0.5, y - 0.12)}--{self.p(x + 0.5, y + 0.12)}--{self.p(x + 0.1, y + 0.12)}--cycle withpen pencircle scaled 1pt withcolor \\MPcolor{{{color}}};")
            self.out.append(f'label.rt(textext("\\tfx {text}"), {self.p(x + 0.7, y)});')

    def code(self):
        return "\\startMPcode\n" + "\n".join(self.out) + "\n\\stopMPcode"


def log_ticks(lo_exp, hi_exp, seconds=True):
    ticks = []
    for e in range(lo_exp, hi_exp + 1):
        v = 10 ** e
        ticks.append((v, es(v, 0) if seconds and e <= 4 else f"$10^{{{e}}}$"))
    return ticks


def f(r, k):
    return float(r[k])
