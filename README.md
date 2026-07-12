# Recetario de Cata

Repositorio de recetas, tips y anotaciones de repostería. Sitio estático que sigue
el [manual de marca](Manual_de_marca/Recetario-de-Cata_Brand-Guardrails.md):
*precisión técnica con calidez de taller.*

## Curso incorporado

**Las Claves de la Pastelería — Ecole** · Chef instructora **Fernanda Pérez**

- **Clase 1 · Cookies** (6 de julio de 2026): galletas de limón, galletas mangueadas,
  cookies de maní con caramelo y la delicia bonus de frambuesa y sésamo.
- **Clase 2 · Cakes** (7 de julio de 2026): brownie de avellana, magdalenas francesas,
  cake cuatro cuartos y muffins de arándanos.

Cada ficha es una transcripción fiel del material impreso y de las anotaciones
manuscritas: el paso a paso va separado de las **notas y anotaciones de clase**, y las
recetas manuscritas al margen (como la *masa sablée para tartas*) se presentan como
**variantes** en una jerarquía aparte, al final de la receta.

## Estructura

```
index.html              Portada: hero + tarjetas de las 8 recetas + tips + oficio
recetas/                Una ficha HTML por receta (generadas)
data/recetas.json       Fuente de verdad: transcripción estructurada de las 8 recetas
assets/estilos.css      Hoja de estilos de marca (paleta + tipografías + fichas)
assets/img/recetas/     Fotografías optimizadas + placeholder de marca (recetas sin foto)
build.py                Genera las fichas e inyecta las tarjetas en index.html
Manual_de_marca/        Guardrails de marca para agentes
Curso Las Claves de la Pastelería/   Material original (Word + imágenes)
```

## Regenerar el sitio

Todo el contenido vive en `data/recetas.json`. Tras editarlo:

```bash
python3 build.py
```

Esto reescribe las 8 fichas de `recetas/` y actualiza las tarjetas de `index.html`
entre los marcadores `<!-- CARDS:START -->` y `<!-- CARDS:END -->`.

## Tags de cada receta

Escuela · Curso · Chef instructora · Día de realización — presentes en cada ficha y en
los créditos del pie de página.
