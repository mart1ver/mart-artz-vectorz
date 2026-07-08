# LuxCore — sources Processing (archivées)

Code d'origine du moteur LuxCore, écrit en **Processing 4**. Il reste ici comme
**référence historique** : le moteur principal du projet est désormais le
**portage Python / moderngl** (voir `../../python_port`).

## Fichiers

| Fichier | Rôle |
|---|---|
| `martz_artz_verctorz.pde` | sketch principal (boucle `draw()`) |
| `artnet_functions.pde` | réception ArtNet UDP → `dmx_data[]` |
| `draw_functions.pde` | pipeline de rendu (fond, spots, effets, blades) |
| `performance_optimization.pde` | `SpotData` + pool + rendu des formes |
| `definitions.pde` | variables globales |
| `gui_functions.pde` | GUI LazyGui |
| `sys_functions.pde` / `error_handling.pde` | utilitaires |
| `z_fixture_definition.pde` | référence DMX canal par canal (commentaires) |

## Relancer le sketch Processing

Ces `.pde` ne tournent plus depuis ce dossier : un sketch Processing a besoin de
son dossier `data/` à côté. Pour l'exécuter à nouveau :

1. Copier ces `.pde` dans un dossier de sketch nommé `martz_artz_verctorz/`.
2. Y copier le dossier `data/` du dépôt.
3. Ouvrir `martz_artz_verctorz.pde` dans Processing 4 (libs `LazyGui`,
   `ArtNet for Processing`, `PostFX for Processing`) → `Ctrl+R`.

> Note : cette version connaît **15 formes** dont l'ancienne « Plus ». Le portage
> Python a densifié à **14 formes** (Plus retiré) et ajoute la vidéo (mode 14).
