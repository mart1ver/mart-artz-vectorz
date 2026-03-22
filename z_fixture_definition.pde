/*
 Convention : tous les index sont en BASE 0 (= index du tableau dmx_data[] dans Processing)

###base  (28 octets, index 0 à 27)
  0 red background
  1 green background
  2 blue background
  3 blade A1 MSB   (top, côté gauche)
  4 blade A1 LSB
  5 blade A2 MSB   (top, côté droit)
  6 blade A2 LSB
  7 blade B1 MSB   (right, haut)
  8 blade B1 LSB
  9 blade B2 MSB   (right, bas)
 10 blade B2 LSB
 11 blade C1 MSB   (bottom, côté gauche)
 12 blade C1 LSB
 13 blade C2 MSB   (bottom, côté droit)
 14 blade C2 LSB
 15 blade D1 MSB   (left, haut)
 16 blade D1 LSB
 17 blade D2 MSB   (left, bas)
 18 blade D2 LSB
 19 blend mode global (BLEND=0, ADD=29, SUBTRACT=57, DARKEST=85, LIGHTEST=114,
                       DIFFERENCE=142, EXCLUSION=170, MULTIPLY=199, SCREEN=227, REPLACE=255)
 20 efx blur A — size (appliqué aussi sur les blades)
 21 efx blur B — sigma (appliqué aussi sur les blades)
 22 efx pixelate amount
 23 efx sobel — bistable (>128 = ON)
 24 efx rgb split
 25 efx saturation / vibrance A
 26 efx saturation / vibrance B
 27 efx chromatic aberration — bistable (>128 = ON)

 ###spot  (23 octets par spot, offset = 28 + spot_id × 23)
  +0 red fill
  +1 green fill
  +2 blue fill
  +3 alpha
  +4 stroke weight
  +5 stroke alpha
  +6 stroke red
  +7 stroke green
  +8 stroke blue
  +9 size pan MSB    (largeur, 16-bit)
 +10 size pan LSB
 +11 size tilt MSB   (hauteur, 16-bit ; en mode Texte : encode le caractère ASCII)
 +12 size tilt LSB
 +13 rotation MSB    (16-bit, 0=0° → 65535=360°)
 +14 rotation LSB
 +15 pan MSB         (position X, 16-bit, 32767=centre)
 +16 pan LSB
 +17 tilt MSB        (position Y, 16-bit, 32767=centre)
 +18 tilt LSB
 +19 mode       (0-14, voir table des formes ci-dessous)
 +20 enable     (0=désactivé, 1-255=actif)
 +21 blend mode (0=utilise le blend mode global ; sinon même LUT que canal 19 base :
                 BLEND=0 ADD=29 SUBTRACT=57 DARKEST=85 LIGHTEST=114
                 DIFFERENCE=142 EXCLUSION=170 MULTIPLY=199 SCREEN=227 REPLACE=255)
 +22 font index (0-255 → clampé sur nb polices disponibles dans data/fonts/)

 ###modes (canal 20 du spot)
  0  Ellipse
  1  Rectangle
  2  Texte       ← size_tilt encode le caractère ASCII affiché
  3  Triangle
  4  Pentagone
  5  Hexagone
  6  Losange
  7  Octogone
  8  Étoile (5 branches)
  9  Croix
 10  Flèche
 11  Plus
 12  Cœur
 13  Segment     ← size_pan = longueur, size_tilt = épaisseur (1–130px), rotation = angle
 14  Fleur

 ###mode texte (mode 2)
 size_tilt encode le caractère ASCII via byte(size_tilt) dans Processing.
 Formule Python : math.ceil(ord(c) * 65535 / 1000)
 Attention : utiliser ceil() et non int() — int() tronque et affiche
             le caractère précédent (ex. 'b' → 'a' avec int()).
 Exemples :
   'A' (65)  → ceil(65  * 65535 / 1000) = 4261
   'a' (97)  → ceil(97  * 65535 / 1000) = 6357
   'M' (77)  → ceil(77  * 65535 / 1000) = 5042
   '0' (48)  → ceil(48  * 65535 / 1000) = 3146
 size_pan contrôle l'échelle du texte (Processing: scale(-size_pan/80)).
 Valeur raisonnable : size_pan ∈ [10000, 50000]
 */
