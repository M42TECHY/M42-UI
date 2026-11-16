# Third-party notices

## Bundled with M42 UI (`m42/bundled/`)

| What | Version | Licence | Where from |
|---|---|---|---|
| Bootstrap (CSS + JS bundle) | 5.3.3 | MIT | getbootstrap.com |
| Bootstrap Icons (CSS + fonts) | 1.x | MIT | icons.getbootstrap.com |
| jQuery | 3.7.1 | MIT | jquery.com |
| SweetAlert2 | 11.14.5 | MIT | sweetalert2.github.io |
| Toastr | 2.x | MIT | github.com/CodeSeven/toastr |
| anime.js | 3.2.2 | MIT | animejs.com |
| Lucide icons (font `fonts/lucide.woff2`, `lucide.css`, `lucide-tags.json`) | 1.59.0 | ISC (`licenses/lucide-LICENSE.txt`) | lucide.dev |
| Poppins, Inter, Playfair Display, Lato, Space Grotesk, Nunito (`fonts/*.woff2`, latin) | @fontsource 5.3.0 | SIL OFL 1.1 (`licenses/OFL-fonts.txt`) | fonts.google.com via fontsource |
| Anton (`fonts/anton-400.woff2`, latin) | @fontsource 5.2.7 | SIL OFL 1.1 (`licenses/OFL-fonts.txt`) | fonts.google.com via fontsource |
| ui-ux-pro-max-skill design data (`bundled/uiux/*.csv`, `LICENSE` beside them) | main, 2026-11 | MIT, © 2024 Next Level Builder | github.com/nextlevelbuilder/ui-ux-pro-max-skill |

The UI files of the app window (`m42/ui/vendor/`) keep the licence headers of their libraries.

## Downloaded by the user (not in this repository)

| What | Licence | Where from |
|---|---|---|
| llama.cpp (llama-server) | MIT | github.com/ggml-org/llama.cpp |
| Qwen3.5-4B (GGUF) and its vision projector | Apache-2.0 (see the model card) | huggingface.co/Qwen |
| UI-DETR-1 (optional) | MIT | huggingface.co/racineai/UI-DETR-1 |
| UIGEN-T2 dataset (optional, `knowledge/uigen-t2/`) | Apache-2.0 | huggingface.co/datasets/Tesslate/UIGEN-T2 |

## Design references

Pictures you attach and the GitHub template demos M42 UI captures are used only for their layout, look and colours
while building your page; they are kept in `m42/cache/` on your PC and are not part of this repository. A captured
template's repository and licence are shown in the chat.

## Open Doodles
Drawings by Pablo Stanley, https://www.opendoodles.com - CC0 1.0 (public domain dedication). Files: m42/bundled/doodles/ (recoloured to each page's colours when used).

## Humaaans
Illustrations of people by Pablo Stanley, https://www.humaaans.com - offered there under CC0 (public domain); an
older copy (github.com/Calinou/humaaans, 2019) is marked CC BY 4.0, so the credit is kept anyway: here, and as an
HTML comment ("Illustration: Humaaans by Pablo Stanley, humaaans.com") next to each one on a built page.
Files: m42/bundled/humaaans/ (the 32 whole figures, sitting-1..8 and standing-1..24; their blue clothes recoloured
to each page's accent when used).

## three.js r128 (MIT)
Copyright 2010-2021 three.js authors, https://threejs.org - MIT License.
Files: m42/bundled/three.min.js, m42/bundled/GLTFLoader.js, m42/bundled/STLLoader.js (copied into a page's lib/ only
when its request asked for 3D). m42/bundled/m42-3d.js (M42's own 3D objects and scenes) is part of M42 UI.
3D models found online for a page come from Poly Haven (https://polyhaven.com, CC0); each one is named with its link
in that page's models/CREDITS.txt.
