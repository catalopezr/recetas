#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera un Artifact autocontenido (una sola página) del Recetario de Cata.

El CSP de los Artifacts bloquea recursos externos, así que:
  · las fuentes de marca (Jost + DM Serif Display) se embeben en base64,
  · las fotos se incrustan como data URIs,
  · todas las fichas viven en la misma página y se navegan con JavaScript.

Reutiliza los renderizadores de build.py para no duplicar la transcripción.
Salida: scratchpad/recetario-artifact.html
"""

import base64
import json
import re
import subprocess
import urllib.request
from pathlib import Path

import build  # reutiliza esc, icon, render_componente, render_alternativa, render_tags...

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "recetas.json"
SCRATCH = Path(
    "/private/tmp/claude-501/-Users-catal-recetas/"
    "8ce71c10-227d-4508-8ccb-59aac0fca0a0/scratchpad"
)
FONT_CACHE = SCRATCH / "fonts_cache.json"
OUT = SCRATCH / "recetario-artifact.html"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

FONT_URLS = {
    "jost": "https://fonts.googleapis.com/css2?family=Jost:wght@400;500;600&display=swap",
    "dmserif": "https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@1&display=swap",
}


def _fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30).read()


def build_font_faces():
    """Descarga (o lee de caché) los woff2 latinos y devuelve reglas @font-face."""
    if FONT_CACHE.exists():
        faces = json.loads(FONT_CACHE.read_text())
    else:
        faces = []
        for css_url in FONT_URLS.values():
            css = _fetch(css_url).decode("utf-8")
            for m in re.finditer(r"/\*\s*latin\s*\*/\s*@font-face\s*\{(.*?)\}", css, re.S):
                block = m.group(1)
                fam = re.search(r"font-family:\s*'([^']+)'", block).group(1)
                weight = re.search(r"font-weight:\s*(\d+)", block).group(1)
                style = re.search(r"font-style:\s*(\w+)", block).group(1)
                url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
                b64 = base64.b64encode(_fetch(url)).decode("ascii")
                faces.append({"fam": fam, "weight": weight, "style": style, "b64": b64})
        FONT_CACHE.write_text(json.dumps(faces))
        print(f"  ✓ {len(faces)} fuentes descargadas y cacheadas")

    rules = []
    for f in faces:
        rules.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%s;"
            "font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');}"
            % (f["fam"], f["style"], f["weight"], f["b64"])
        )
    return "\n".join(rules)


def img_data_uri(path, max_px=1000, q=78):
    tmp = SCRATCH / ("emb_" + Path(path).stem + ".jpg")
    subprocess.run(
        ["sips", "-Z", str(max_px), "-s", "format", "jpeg",
         "-s", "formatOptions", str(q), str(path), "--out", str(tmp)],
        check=True, capture_output=True,
    )
    b64 = base64.b64encode(tmp.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def placeholder_data_uri():
    svg = (ROOT / "assets/img/recetas/placeholder.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")


# --------------------------------------------------------------- render views ---
def render_card(recipe, uri):
    chip = ('<span class="chip bonus">Bonus</span>' if recipe.get("bonus")
            else f'<span class="chip cat">{build.esc(recipe["categoria"])}</span>')
    n = len(recipe["componentes"])
    lbl = "elaboración" if n == 1 else "elaboraciones"
    return f"""<a class="card" href="#receta-{recipe['slug']}" data-nav="receta-{recipe['slug']}">
  <div class="thumb">{chip}<img src="{uri}" alt="{build.esc(recipe['titulo'])}"></div>
  <div class="body">
    <h4>{build.esc(recipe['titulo'])}</h4>
    <p>{build.esc(recipe['resumen'])}</p>
    <div class="meta">
      <span class="item">{build.icon('elab', 18)}{n}&nbsp;{lbl}</span>
      <span class="item">{build.icon('dia', 18)}{build.esc(recipe['dia'])}</span>
    </div>
  </div>
</a>"""


def render_receta_view(recipe, meta, uri):
    chip = ('<span class="chip bonus">Bonus</span>' if recipe.get("bonus")
            else f'<span class="chip cat">{build.esc(recipe["categoria"])}</span>')
    alt = ""
    foto_alt = build.esc(recipe["titulo"]) if recipe["imagen"] else "Sin fotografía en el material"
    componentes = "".join(build.render_componente(c, i) for i, c in enumerate(recipe["componentes"]))
    if recipe.get("alternativas"):
        alts = "".join(build.render_alternativa(a) for a in recipe["alternativas"])
        alt = ('<section class="alternativas"><div class="alt-divider">'
               '<span>Variantes de la receta</span></div><p class="alt-intro">'
               'Elaboraciones alternativas anotadas a mano en el material, presentadas '
               f'aparte de la receta principal.</p>{alts}</section>')
    n = len(recipe["componentes"])
    intro = ""
    if n > 1:
        intro = ('<div class="intro-elab"><h2>Elaboraciones</h2><p>Esta receta reúne '
                 f'{n} elaboraciones, en el orden en que se montan. Las anotaciones de '
                 'clase van al final de cada una, separadas del paso a paso.</p></div>')
    return f"""<section class="view" id="receta-{recipe['slug']}">
  <div class="wrap" style="padding-top:26px"><a class="volver" href="#inicio" data-nav="inicio">← Volver al recetario</a></div>
  <div class="wrap receta-hero"><div class="grid">
    <div class="foto"><img src="{uri}" alt="{foto_alt}" width="1200" height="1500"></div>
    <div class="info">
      {chip}
      <p class="kicker">{build.esc(meta['curso'])} · Clase de {build.esc(recipe['clase'])}</p>
      <h1>{build.esc(recipe['titulo'])}</h1>
      <p class="resumen">{build.esc(recipe['resumen'])}</p>
      {build.render_tags(recipe, meta)}
      <p class="fuente">{build.esc(recipe['fuente'])}</p>
    </div>
  </div></div>
  <div class="wrap receta-body">{intro}{componentes}{alt}</div>
</section>"""


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    meta, recetas = data["meta"], data["recetas"]

    print("  · Preparando fuentes de marca...")
    fontface = build_font_faces()
    print("  · Incrustando imágenes...")
    ph = placeholder_data_uri()
    uris = {r["slug"]: (img_data_uri(ROOT / r["imagen"]) if r["imagen"] else ph) for r in recetas}

    css = (ROOT / "assets/estilos.css").read_text(encoding="utf-8")
    cards = "\n".join(render_card(r, uris[r["slug"]]) for r in recetas)
    recetas_views = "\n".join(render_receta_view(r, meta, uris[r["slug"]]) for r in recetas)

    featured = next(r for r in recetas if r["slug"] == "cake-cuatro-cuartos")

    html = f"""<title>Recetario de Cata</title>
<style>
{fontface}
{css}
/* --- Navegación de vistas (single-page artifact) --- */
.view {{ display: none; }}
.view.active {{ display: block; }}
.card {{ cursor: pointer; }}
.cover-card {{ cursor: pointer; }}
</style>

<header>
  <div class="wrap nav">
    <a class="brand" href="#inicio" data-nav="inicio">
      <span class="monogram"><span class="r">R</span><span class="c">c</span></span>
      <span class="wordmark"><span class="recetario">Recetario</span><span class="decata">de&nbsp;Cata</span></span>
    </a>
    <nav class="links">
      <a href="#recetas" data-nav="inicio" data-scroll="recetas">Recetas</a>
      <a href="#tecnicas" data-nav="inicio" data-scroll="tecnicas">Técnicas</a>
      <a href="#valores" data-nav="inicio" data-scroll="valores">Oficio</a>
    </nav>
  </div>
</header>

<main>
  <section class="view active" id="inicio">
    <div class="wrap hero"><div class="hero-grid">
      <div>
        <p class="kicker">Ecole · Las Claves de la Pastelería · Chef Fernanda Pérez</p>
        <h1>Precisión técnica con <em>calidez de taller</em>.</h1>
        <p class="lead">Transcripción fiel de las clases de cookies y cakes: cantidades al gramo, tiempos y temperaturas exactas, y las anotaciones de clase separadas del paso a paso. Ocho recetas listas para reproducir y estandarizar.</p>
        <div class="cta-row">
          <a class="btn btn-primary" href="#recetas" data-nav="inicio" data-scroll="recetas">Ver las 8 recetas</a>
          <a class="btn btn-ghost" href="#tecnicas" data-nav="inicio" data-scroll="tecnicas">Técnicas y tips</a>
        </div>
      </div>
      <a class="cover-card" href="#receta-{featured['slug']}" data-nav="receta-{featured['slug']}" style="text-decoration:none">
        <span class="eyebrow">Ficha destacada</span>
        <h3>Cake cuatro cuartos</h3>
        <p style="opacity:.9">Cake clásico de partes iguales con glucosa y pasta de vainilla, terminado con un baño dulce de chocolate y nueces. Reposa en frío antes de hornear.</p>
        <div class="stat-row">
          <div class="stat"><span class="n">150&nbsp;°C</span><span class="l">Horneado</span></div>
          <div class="stat"><span class="n">40&nbsp;min</span><span class="l">En horno</span></div>
          <div class="stat"><span class="n">500&nbsp;g</span><span class="l">Por molde</span></div>
        </div>
      </a>
    </div></div>

    <section class="block" id="recetas"><div class="wrap">
      <div class="sec-head">
        <h2>Recetas del curso</h2>
        <p>Clase 1 — Cookies (6 de julio) y Clase 2 — Cakes (7 de julio). Cada ficha va al grano: ingredientes al gramo, tiempos y temperaturas, y las anotaciones de clase como tips separados.</p>
      </div>
      <div class="cards">
{cards}
      </div>
    </div></section>

    <section class="block" id="tecnicas" style="padding-top:0"><div class="wrap">
      <div class="sec-head">
        <h2>Técnicas y anotaciones</h2>
        <p>El consejo se toma su espacio. Aquí van las notas de oficio que hacen que una receta salga igual de bien la décima vez que la primera.</p>
      </div>
      <div class="tip">
        <span class="label">Tip:</span>
        <p>Para saber si un cake está cocido, apunta a <strong>85&nbsp;°C en el centro</strong> con termómetro de aguja; en carrot cake o cakes rellenos con fruta, sube a 92&nbsp;°C. Y en el caramelo seco: fuego medio, echando el azúcar de a poco, y cocina hasta 106&nbsp;°C.</p>
      </div>
    </div></section>

    <section class="values" id="valores"><div class="wrap block"><div class="grid3">
      <div class="v"><span class="num">01</span><h3>Preciso, no rígido</h3><p>Cantidades y tiempos exactos, en lenguaje humano. El dato en gramos, minutos y grados; nunca «un poco» ni «al gusto».</p></div>
      <div class="v"><span class="num">02</span><h3>Fiel al material</h3><p>Se conserva el texto impreso como base y las correcciones de clase se marcan de forma explícita. Lo dudoso queda señalado, no inventado.</p></div>
      <div class="v"><span class="num">03</span><h3>Listo para escalar</h3><p>Recetas, ingredientes y cantidades estandarizados, pensados para crecer hacia producciones mayores sin perder el punto.</p></div>
    </div></div></section>
  </section>

{recetas_views}
</main>

<footer>
  <div class="wrap foot-row">
    <a class="brand" href="#inicio" data-nav="inicio" style="text-decoration:none">
      <span class="monogram"><span class="r">R</span><span class="c">c</span></span>
      <span class="wordmark"><span class="recetario">Recetario</span><span class="decata">de&nbsp;Cata</span></span>
    </a>
    <div class="foot-credits">
      <span class="line"><b>Las Claves de la Pastelería</b> · Ecole</span>
      <span class="line">Chef instructora Fernanda Pérez · Cookies 6 jul · Cakes 7 jul de 2026</span>
    </div>
  </div>
</footer>

<script>
(function () {{
  var views = document.querySelectorAll('.view');
  function show(id, scrollId) {{
    for (var i = 0; i < views.length; i++) views[i].classList.toggle('active', views[i].id === id);
    if (scrollId) {{
      var el = document.getElementById(scrollId);
      if (el) el.scrollIntoView();
    }} else {{
      window.scrollTo(0, 0);
    }}
  }}
  var links = document.querySelectorAll('[data-nav]');
  for (var i = 0; i < links.length; i++) {{
    links[i].addEventListener('click', function (e) {{
      e.preventDefault();
      show(this.getAttribute('data-nav'), this.getAttribute('data-scroll'));
    }});
  }}
}})();
</script>
"""
    OUT.write_text(html, encoding="utf-8")
    kb = len(html.encode("utf-8")) / 1024
    print(f"  ✓ {OUT.name} generado ({kb:.0f} KB)")


if __name__ == "__main__":
    main()
