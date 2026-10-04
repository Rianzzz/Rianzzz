"""Gera as imagens (SVG) do README do perfil.

Por que SVG e por que gerar: o README do GitHub não aceita CSS nem JavaScript, mas aceita imagens, e um SVG animado
(SMIL) funciona dentro de <img>. Os textos viram desenho vetorial (contornos das letras), então a fonte aparece igual
em qualquer máquina, sem depender de fonte instalada nem de serviço de terceiros.

Uso:
    pip install fonttools brotli
    python tools/generate_assets.py --archivo caminho/archivo-latin-wdth-normal.woff2 \
                                    --mono caminho/jetbrains-mono-latin-400-normal.woff2

As fontes (Archivo e JetBrains Mono, licença OFL) vêm dos pacotes npm @fontsource-variable/archivo e @fontsource/jetbrains-mono.
"""
import argparse
import copy
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

COBALT = "#2a35ff"
CREAM = "#f5f6ff"
SIGNAL = "#ffd60a"
INK = "#0a0c14"

OUT = Path(__file__).resolve().parent.parent / "assets"


class Face:
    """Uma fonte pronta para virar caminhos SVG."""

    def __init__(self, font: TTFont):
        self.font = font
        self.cmap = font.getBestCmap()
        self.gs = font.getGlyphSet()
        self.upm = font["head"].unitsPerEm

    def text(self, s: str, size: float, x: float = 0, y: float = 0, track: float = 0.0):
        """Devolve (d, largura). x,y é a linha de base à esquerda; `track` é o espaçamento extra, em em."""
        scale = size / self.upm
        pen = SVGPathPen(self.gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))  # 1 casa decimal: arquivo bem menor
        cx = 0.0
        for ch in s:
            name = self.cmap.get(ord(ch))
            if name is None:
                name = self.cmap.get(ord("?"))
            tp = TransformPen(pen, (scale, 0, 0, -scale, x + cx, y))
            self.gs[name].draw(tp)
            cx += self.font["hmtx"][name][0] * scale + track * size
        return pen.getCommands(), cx - track * size

    def width(self, s: str, size: float, track: float = 0.0) -> float:
        return self.text(s, size, track=track)[1]


def archivo_instance(path: Path, wght: int, wdth: int) -> Face:
    base = TTFont(str(path))
    inst = instancer.instantiateVariableFont(copy.deepcopy(base), {"wght": wght, "wdth": wdth})
    return Face(inst)


def p(d: str, fill: str, extra: str = "") -> str:
    return f'<path d="{d}" fill="{fill}" {extra}/>'


# ───────────────────────────── Banner ─────────────────────────────

# Mesmo desenho do topo do site: o HelpDeskFlow vivo. Coordenadas normalizadas.
NODES = {
    "client": (0.07, 0.5, "browser"),
    "gateway": (0.26, 0.5, "gateway"),
    "identity": (0.5, 0.12, "identity"),
    "tickets": (0.5, 0.37, "tickets"),
    "tenants": (0.5, 0.62, "tenants"),
    "notifications": (0.5, 0.87, "notifications"),
    "broker": (0.8, 0.28, "rabbitmq"),
    "db": (0.8, 0.74, "postgres"),
}
SERVICES = ["identity", "tickets", "tenants", "notifications"]
EDGES = (
    [("client", "gateway")]
    + [("gateway", s) for s in SERVICES]
    + [(s, "broker") for s in SERVICES]
    + [(s, "db") for s in SERVICES]
)
# (caminho, tipo, rótulo, início, duração). Os rótulos são nomes de eventos reais do HelpDeskFlow.
PACKETS = [
    (["client", "gateway", "tickets", "db"], "req", None, 0.0, 3.6),
    (["tickets", "broker", "notifications"], "evt", "TicketCreated", 1.4, 3.4),
    (["client", "gateway", "identity", "db"], "req", None, 0.9, 3.8),
    (["identity", "broker", "tenants"], "evt", "TenantRegistered", 2.3, 3.4),
    (["client", "gateway", "tenants", "db"], "req", None, 1.8, 3.8),
    (["tenants", "broker", "identity"], "evt", "TenantProvisioned", 3.6, 3.4),
    (["client", "gateway", "notifications", "db"], "req", None, 2.7, 4.0),
]


def banner(archivo: Face, mono: Face) -> str:
    W, H = 1200, 480
    gx0, gx1 = 70, W - 70
    gy0, gh = 40, 235

    def pt(name):
        nx, ny, _ = NODES[name]
        return gx0 + nx * (gx1 - gx0), gy0 + ny * gh

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Rian Nascimento Alves, desenvolvedor de software. Backend, integrações e IA.">']
    out.append(f'<rect width="{W}" height="{H}" fill="{COBALT}"/>')

    # arestas
    for a, b in EDGES:
        (x1, y1), (x2, y2) = pt(a), pt(b)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{CREAM}" stroke-opacity="0.22" stroke-width="1"/>')

    # nós e nomes
    for name, (nx, ny, label) in NODES.items():
        x, y = pt(name)
        out.append(f'<rect x="{x - 7:.1f}" y="{y - 7:.1f}" width="14" height="14" fill="{CREAM}"/>')
        d, w = mono.text(label, 13)
        right = nx > 0.6 or name == "client"
        lx = x + 15 if right else x - w / 2
        ly = y + 5 if right else y + 26
        d, _ = mono.text(label, 13, lx, ly)
        out.append(p(d, CREAM, 'fill-opacity="0.9"'))

    # pacotes animados (SMIL)
    for path, kind, label, begin, dur in PACKETS:
        pts = [pt(n) for n in path]
        motion = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        color = SIGNAL if kind == "evt" else CREAM
        size = 11 if kind == "evt" else 8
        out.append(f'<g opacity="0">')
        out.append(f'<rect x="{-size / 2}" y="{-size / 2}" width="{size}" height="{size}" fill="{color}"/>')
        if label:
            d, _ = mono.text(label, 13, 14, -12)
            out.append(p(d, SIGNAL))
        out.append(f'<animateMotion dur="{dur}s" begin="{begin}s" repeatCount="indefinite" path="{motion}" calcMode="linear"/>')
        # aparece no início e some no fim do trajeto
        out.append(f'<animate attributeName="opacity" dur="{dur}s" begin="{begin}s" repeatCount="indefinite" '
                   f'values="0;1;1;0" keyTimes="0;0.04;0.94;1"/>')
        out.append("</g>")

    # nome gigante, em Archivo condensado e pesado
    name_text = "RIAN NASCIMENTO ALVES"
    target = W - 2 * 60
    w100 = archivo.width(name_text, 100, track=-0.005)
    size = 100 * target / w100
    d, _ = archivo.text(name_text, size, 60, 410, track=-0.005)
    out.append(p(d, CREAM))

    # linha de apoio
    d, _ = mono.text("desenvolvedor de software  /  backend, integrações e IA", 16, 62, 450)
    out.append(p(d, CREAM, 'fill-opacity="0.9"'))
    out.append(f'<rect x="{W - 62 - 10}" y="{450 - 11}" width="10" height="10" fill="{SIGNAL}"/>')
    out.append("</svg>")
    return "\n".join(out)


# ───────────────────────────── Stack ─────────────────────────────

STACK = [
    ["C#", ".NET", "ASP.NET Core", "EF Core", "TypeScript", "Python", "FastAPI", "Flask"],
    ["PostgreSQL", "Oracle", "RabbitMQ", "Docker", "Kubernetes", "GitHub Actions", "Blip", "Agentes de IA"],
]


def stack(mono: Face) -> str:
    W, pad, gap, ph = 1200, 0, 12, 40
    rows = []
    y = 4
    for row in STACK:
        x = pad + 4
        items = []
        for item in row:
            w = mono.width(item, 15) + 36
            items.append((x, item, w))
            x += w + gap
        rows.append((y, items))
        y += ph + gap
    H = y - gap + 8
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Tecnologias: {", ".join(i for r in STACK for i in r)}">']
    for yy, items in rows:
        for x, item, w in items:
            out.append(f'<rect x="{x + 4}" y="{yy + 4}" width="{w}" height="{ph}" fill="{INK}"/>')  # sombra dura
            out.append(f'<rect x="{x}" y="{yy}" width="{w}" height="{ph}" fill="{CREAM}" stroke="{INK}" stroke-width="2"/>')
            d, _ = mono.text(item, 15, x + 18, yy + 26)
            out.append(p(d, INK))
    out.append("</svg>")
    return "\n".join(out)


# ───────────────────────────── Integration Hub ─────────────────────────────

def hub(mono: Face, archivo_bold: Face) -> str:
    W, H = 600, 250
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Várias origens de dados passam por adapters, viram um modelo único e vão para o PostgreSQL">']
    out.append(f'<rect width="{W}" height="{H}" fill="{COBALT}"/>')

    sources = ["origem A", "origem B", "origem C"]
    ys = [60, 125, 190]
    for s, y in zip(sources, ys):
        out.append(f'<rect x="30" y="{y - 18}" width="120" height="36" fill="none" stroke="{CREAM}" stroke-width="2"/>')
        d, w = mono.text(s, 13)
        d, _ = mono.text(s, 13, 30 + (120 - w) / 2, y + 5)
        out.append(p(d, CREAM))
        out.append(f'<line x1="150" y1="{y}" x2="250" y2="125" stroke="{CREAM}" stroke-opacity="0.5" stroke-width="1.5"/>')

    # adapters -> modelo único
    out.append(f'<rect x="250" y="95" width="110" height="60" fill="{CREAM}"/>')
    d, w = archivo_bold.text("ADAPTER", 20)
    d, _ = archivo_bold.text("ADAPTER", 20, 250 + (110 - w) / 2, 118)
    out.append(p(d, INK))
    d, w = mono.text("por origem", 11)
    d, _ = mono.text("por origem", 11, 250 + (110 - w) / 2, 140)
    out.append(p(d, INK, 'fill-opacity="0.8"'))
    out.append(f'<line x1="360" y1="125" x2="430" y2="125" stroke="{SIGNAL}" stroke-width="2"/>')
    out.append(f'<polygon points="430,119 442,125 430,131" fill="{SIGNAL}"/>')

    out.append(f'<rect x="442" y="85" width="128" height="80" fill="{SIGNAL}"/>')
    d, w = archivo_bold.text("PostgreSQL", 20)
    d, _ = archivo_bold.text("PostgreSQL", 20, 442 + (128 - w) / 2, 118)
    out.append(p(d, INK))
    d, w = mono.text("formato único", 11)
    d, _ = mono.text("formato único", 11, 442 + (128 - w) / 2, 142)
    out.append(p(d, INK, 'fill-opacity="0.8"'))

    # pacotes correndo: origem -> adapter
    for i, y in enumerate(ys):
        out.append(f'<rect x="-4" y="-4" width="8" height="8" fill="{SIGNAL}" opacity="0">'
                   f'<animateMotion dur="2.4s" begin="{i * 0.8}s" repeatCount="indefinite" path="M150,{y} L250,125 L442,125"/>'
                   f'<animate attributeName="opacity" dur="2.4s" begin="{i * 0.8}s" repeatCount="indefinite" values="0;1;1;0" keyTimes="0;0.05;0.92;1"/>'
                   f"</rect>")
    out.append("</svg>")
    return "\n".join(out)


# ───────────────────────────── Botões ─────────────────────────────

def button(archivo_bold: Face, label: str, fill: str, fg: str) -> str:
    size = 20
    w_text = archivo_bold.width(label.upper(), size, track=0.02)
    W, H = int(w_text + 56), 54
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W + 6}" height="{H + 6}" viewBox="0 0 {W + 6} {H + 6}" role="img" aria-label="{label}">']
    out.append(f'<rect x="6" y="6" width="{W}" height="{H}" fill="{INK}"/>')
    out.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" fill="{fill}" stroke="{INK}" stroke-width="2"/>')
    d, _ = archivo_bold.text(label.upper(), size, 28, 35, track=0.02)
    out.append(p(d, fg))
    out.append("</svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", required=True, type=Path)
    ap.add_argument("--mono", required=True, type=Path)
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    condensed = archivo_instance(a.archivo, 850, 62)
    bold = archivo_instance(a.archivo, 800, 75)
    mono = Face(TTFont(str(a.mono)))

    files = {
        "banner.svg": banner(condensed, mono),
        "stack.svg": stack(mono),
        "integration-hub.svg": hub(mono, bold),
        "btn-site.svg": button(bold, "Site", SIGNAL, INK),
        "btn-linkedin.svg": button(bold, "LinkedIn", CREAM, INK),
    }
    for name, svg in files.items():
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"{name}: {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
