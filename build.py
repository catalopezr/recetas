#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recetario de Cata — generador estático.

Lee data/recetas.json (fuente de verdad, transcripción fiel del material de
Ecole / Las Claves de la Pastelería) y genera:

  · recetas/<slug>.html   — una ficha por receta, siguiendo el manual de marca.
  · index.html            — inyecta las tarjetas reales entre los marcadores
                            <!-- CARDS:START --> ... <!-- CARDS:END -->.

Uso:  python3 build.py
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "recetas.json"
RECETAS_DIR = ROOT / "recetas"
INDEX = ROOT / "index.html"

LETRAS = "abcdefghijklmnopqrstuvwxyz"

# --- Iconografía de marca: mono-línea 2 px, terminaciones redondeadas ---------
ICONS = {
    "escuela": '<path d="M3 9l9-4 9 4-9 4-9-4z"/><path d="M7 11v4c0 1.2 2.4 2 5 2s5-.8 5-2v-4"/><path d="M21 9v4"/>',
    "curso":   '<path d="M5 4h10a2 2 0 0 1 2 2v14H7a2 2 0 0 0-2 2z"/><path d="M5 18a2 2 0 0 1 2-2h10"/>',
    "chef":    '<path d="M7 20h10"/><path d="M8 20v-4"/><path d="M16 20v-4"/><path d="M6.5 16a4 4 0 0 1-1-7.7A3.6 3.6 0 0 1 12 5.6a3.6 3.6 0 0 1 6.5 2.7 4 4 0 0 1-1 7.7z"/>',
    "dia":     '<rect x="4" y="5" width="16" height="16" rx="2"/><path d="M4 10h16"/><path d="M8 3v4"/><path d="M16 3v4"/>',
    "elab":    '<path d="M4 7h16"/><path d="M4 12h16"/><path d="M4 17h10"/>',
}


def esc(text):
    return html.escape(str(text), quote=True)


def icon(name, size=16, stroke="#4B2C13"):
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{stroke}" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{ICONS[name]}</svg>'
    )


# ---------------------------------------------------------------- fragmentos ---
def render_ingredientes(ingredientes):
    if not ingredientes:
        return ""
    filas = []
    for ing in ingredientes:
        cant = ing["cantidad"]
        clase = "cant sin" if cant.lower().startswith("sin cantidad") else "cant"
        filas.append(
            f'<tr><td>{esc(ing["item"])}</td>'
            f'<td class="{clase}">{esc(cant)}</td></tr>'
        )
    return (
        '<div class="ingredientes">'
        '<div class="ing-title">Ingredientes</div>'
        f'<table><tbody>{"".join(filas)}</tbody></table>'
        "</div>"
    )


def render_procedimiento(pasos, nota_proc=None):
    if not pasos:
        texto = nota_proc or "Sin procedimiento en el material original."
        return (
            '<div class="procedimiento">'
            '<div class="proc-title">Procedimiento</div>'
            f'<div class="sin-proc">{esc(texto)}</div>'
            "</div>"
        )
    items = "".join(f"<li>{esc(p)}</li>" for p in pasos)
    return (
        '<div class="procedimiento">'
        '<div class="proc-title">Procedimiento</div>'
        f"<ol>{items}</ol>"
        "</div>"
    )


def render_notas(notas):
    if not notas:
        return ""
    items = "".join(f"<li>{esc(n)}</li>" for n in notas)
    return (
        '<div class="notas">'
        '<div class="notas-label">Notas y anotaciones de clase</div>'
        f"<ul>{items}</ul>"
        "</div>"
    )


def render_componente(comp, i):
    letra = LETRAS[i] if i < len(LETRAS) else str(i + 1)
    fuente = comp.get("fuente")
    fuente_html = f'<div class="comp-fuente">{esc(fuente)}</div>' if fuente else ""
    return (
        '<section class="componente">'
        '<div class="comp-head">'
        f'<span class="comp-num">{letra}</span>'
        f"<div><h3>{esc(comp['titulo'])}</h3>{fuente_html}</div>"
        "</div>"
        '<div class="comp-grid">'
        f"{render_ingredientes(comp.get('ingredientes', []))}"
        f"{render_procedimiento(comp.get('procedimiento', []), comp.get('procedimientoNota'))}"
        "</div>"
        f"{render_notas(comp.get('notas', []))}"
        "</section>"
    )


def render_alternativa(alt):
    desc = alt.get("descripcion")
    desc_html = f'<p class="alt-desc">{esc(desc)}</p>' if desc else ""
    return (
        '<article class="alternativa">'
        '<div class="alt-head">'
        f"<h3>{esc(alt['titulo'])}</h3>"
        '<span class="alt-tag">Variante alternativa</span>'
        "</div>"
        f"{desc_html}"
        '<div class="comp-grid">'
        f"{render_ingredientes(alt.get('ingredientes', []))}"
        f"{render_procedimiento(alt.get('procedimiento', []), alt.get('procedimientoNota'))}"
        "</div>"
        f"{render_notas(alt.get('notas', []))}"
        "</article>"
    )


def render_tags(recipe, meta):
    tags = [
        ("escuela", "Escuela", meta["escuela"]),
        ("curso", "Curso", meta["curso"]),
        ("chef", "Chef instructora", meta["chef"]),
        ("dia", "Día de realización", recipe["dia"]),
    ]
    out = []
    for ic, k, v in tags:
        out.append(
            '<span class="tag">'
            f"{icon(ic)}"
            f'<span class="tg"><span class="k">{esc(k)}</span>'
            f'<span class="val">{esc(v)}</span></span>'
            "</span>"
        )
    return '<div class="tag-row">' + "".join(out) + "</div>"


# ------------------------------------------------------------------- páginas ---
def render_recipe_page(recipe, meta):
    img = recipe["imagen"]
    if img:
        foto_src = "../" + img
        foto_alt = esc(recipe["titulo"])
    else:
        foto_src = "../assets/img/recetas/placeholder.svg"
        foto_alt = "Sin fotografía en el material"

    chip = (
        '<span class="chip bonus">Bonus</span>'
        if recipe.get("bonus")
        else f'<span class="chip cat">{esc(recipe["categoria"])}</span>'
    )

    componentes = "".join(
        render_componente(c, i) for i, c in enumerate(recipe["componentes"])
    )

    alternativas = ""
    if recipe.get("alternativas"):
        alts = "".join(render_alternativa(a) for a in recipe["alternativas"])
        alternativas = (
            '<section class="alternativas">'
            '<div class="alt-divider"><span>Variantes de la receta</span></div>'
            '<p class="alt-intro">Elaboraciones alternativas anotadas a mano en el '
            "material, presentadas aparte de la receta principal.</p>"
            f"{alts}"
            "</section>"
        )

    n_elab = len(recipe["componentes"])
    elab_label = "elaboración" if n_elab == 1 else "elaboraciones"
    intro = (
        '<div class="intro-elab">'
        f"<h2>Elaboraciones</h2>"
        f"<p>Esta receta reúne {n_elab} {elab_label}, en el orden en que se montan. "
        "Las anotaciones de clase van al final de cada una, separadas del paso a paso.</p>"
        "</div>"
        if n_elab > 1
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(recipe['titulo'])} · Recetario de Cata</title>
  <meta name="description" content="{esc(recipe['resumen'])}">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='22' fill='%23BC3F29'/%3E%3Ctext x='16' y='44' font-family='Georgia,serif' font-size='34' fill='%23FBF8F1'%3ER%3C/text%3E%3Ctext x='36' y='44' font-family='Georgia,serif' font-style='italic' font-size='30' fill='%23FBF8F1'%3Ec%3C/text%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@1&family=Jost:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../assets/estilos.css">
</head>
<body>

  <header>
    <div class="wrap nav">
      <a class="brand" href="../index.html">
        <span class="monogram"><span class="r">R</span><span class="c">c</span></span>
        <span class="wordmark"><span class="recetario">Recetario</span><span class="decata">de&nbsp;Cata</span></span>
      </a>
      <nav class="links">
        <a href="../index.html#recetas">Recetas</a>
        <a href="../index.html#tecnicas">Técnicas</a>
        <a href="../index.html#valores">Oficio</a>
      </nav>
    </div>
  </header>

  <main>
    <div class="wrap" style="padding-top:26px">
      <a class="volver" href="../index.html#recetas">← Volver al recetario</a>
    </div>

    <!-- Cabecera de la ficha -->
    <div class="wrap receta-hero">
      <div class="grid">
        <div class="foto">
          <img src="{foto_src}" alt="{foto_alt}" loading="lazy" width="1200" height="1500">
        </div>
        <div class="info">
          {chip}
          <p class="kicker">{esc(meta['curso'])} · Clase de {esc(recipe['clase'])}</p>
          <h1>{esc(recipe['titulo'])}</h1>
          <p class="resumen">{esc(recipe['resumen'])}</p>
          {render_tags(recipe, meta)}
          <p class="fuente">{esc(recipe['fuente'])}</p>
        </div>
      </div>
    </div>

    <!-- Cuerpo -->
    <div class="wrap receta-body">
      {intro}
      {componentes}
      {alternativas}
    </div>
  </main>

  <footer>
    <div class="wrap foot-row">
      <a class="brand" href="../index.html" style="text-decoration:none">
        <span class="monogram"><span class="r">R</span><span class="c">c</span></span>
        <span class="wordmark"><span class="recetario">Recetario</span><span class="decata">de&nbsp;Cata</span></span>
      </a>
      <div class="foot-credits">
        <span class="line"><b>{esc(meta['curso'])}</b> · {esc(meta['escuela'])}</span>
        <span class="line">Chef instructora {esc(meta['chef'])} · {esc(recipe['dia'])}</span>
      </div>
    </div>
  </footer>

</body>
</html>
"""


def render_card(recipe):
    img = recipe["imagen"]
    src = img if img else "assets/img/recetas/placeholder.svg"
    chip = (
        '<span class="chip bonus">Bonus</span>'
        if recipe.get("bonus")
        else f'<span class="chip cat">{esc(recipe["categoria"])}</span>'
    )
    n_elab = len(recipe["componentes"])
    elab_label = "elaboración" if n_elab == 1 else "elaboraciones"
    return f"""          <a class="card" href="recetas/{recipe['slug']}.html">
            <div class="thumb">
              {chip}
              <img src="{src}" alt="{esc(recipe['titulo'])}" loading="lazy">
            </div>
            <div class="body">
              <h4>{esc(recipe['titulo'])}</h4>
              <p>{esc(recipe['resumen'])}</p>
              <div class="meta">
                <span class="item">{icon('elab', 18)}{n_elab}&nbsp;{elab_label}</span>
                <span class="item">{icon('dia', 18)}{esc(recipe['dia'])}</span>
              </div>
            </div>
          </a>"""


def inject_cards(index_html, cards_html):
    pattern = re.compile(
        r"(<!-- CARDS:START -->).*?(<!-- CARDS:END -->)", re.DOTALL
    )
    replacement = r"\1\n" + cards_html + r"\n          \2"
    if not pattern.search(index_html):
        raise SystemExit("No se encontraron los marcadores CARDS en index.html")
    return pattern.sub(replacement, index_html)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    meta = data["meta"]
    recetas = data["recetas"]

    RECETAS_DIR.mkdir(exist_ok=True)
    for recipe in recetas:
        page = render_recipe_page(recipe, meta)
        (RECETAS_DIR / f"{recipe['slug']}.html").write_text(page, encoding="utf-8")
        print(f"  ✓ recetas/{recipe['slug']}.html")

    cards = "\n".join(render_card(r) for r in recetas)
    index_html = INDEX.read_text(encoding="utf-8")
    INDEX.write_text(inject_cards(index_html, cards), encoding="utf-8")
    print(f"  ✓ index.html ({len(recetas)} tarjetas inyectadas)")


if __name__ == "__main__":
    main()
