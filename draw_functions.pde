void do_background() {
  bg_color = color(dmx_data[0] & 0xFF, dmx_data[1] & 0xFF, dmx_data[2] & 0xFF);
  // set background
  background(bg_color);
}

void do_spots_optimized() {
  // Version optimisée utilisant le spot pool et les calculs cachés
  update_screen_cache();
  
  // Redimensionner le pool si l'utilisateur a changé le nombre de spots
  resize_spot_pool_if_needed(number_of_spots);
  
  for (int i = 0; i < number_of_spots; i++) {
    int base_addr = number_of_base_parameters + (i * number_of_parameters_by_spots);
    
    // Utiliser le spot pool pré-alloué
    SpotData spot = spot_pool[i];
    spot.update_from_dmx(dmx_data, base_addr, cached_half_width, cached_half_height);
    spot.render_optimized();
  }
}

void do_blend_mode() {
  // Gestion centralisée du blend mode depuis le canal DMX 20 (index 19)
  blend_mode = get_optimized_blend_mode(dmx_data[19]);
  blendMode(blend_mode);
}

void reset_blend_mode() {
  // Retour au mode de mélange normal
  blendMode(BLEND);
}

void do_blades() {
  pushMatrix();
  noStroke();  // Les blades ne doivent pas avoir de contour
  // read the from byte 3 to byte 18 to set the blades (16-bit precision)

  // Convert 16-bit values for each blade side
  int b = BLADE_BASE_OFFSET;
  int bladeA1 = ((dmx_data[b+ 0]&0xFF) << 8) | (dmx_data[b+ 1]&0xFF);
  int bladeA2 = ((dmx_data[b+ 2]&0xFF) << 8) | (dmx_data[b+ 3]&0xFF);
  int bladeB1 = ((dmx_data[b+ 4]&0xFF) << 8) | (dmx_data[b+ 5]&0xFF);
  int bladeB2 = ((dmx_data[b+ 6]&0xFF) << 8) | (dmx_data[b+ 7]&0xFF);
  int bladeC1 = ((dmx_data[b+ 8]&0xFF) << 8) | (dmx_data[b+ 9]&0xFF);
  int bladeC2 = ((dmx_data[b+10]&0xFF) << 8) | (dmx_data[b+11]&0xFF);
  int bladeD1 = ((dmx_data[b+12]&0xFF) << 8) | (dmx_data[b+13]&0xFF);
  int bladeD2 = ((dmx_data[b+14]&0xFF) << 8) | (dmx_data[b+15]&0xFF);

  fill(0);

  //blade A (top), inclinable
  beginShape();
  vertex(0, 0);
  vertex(width, 0);
  vertex(width, map(bladeA2, 0, 65535, 0, height));
  vertex(0, map(bladeA1, 0, 65535, 0, height));
  endShape(CLOSE);

  //blade B (right), inclinable
  beginShape();
  vertex(width, 0);
  vertex(width, height);
  vertex(map(bladeB2, 0, 65535, width, 0), height);
  vertex(map(bladeB1, 0, 65535, width, 0), 0);
  endShape(CLOSE);

  //blade C (down), inclinable
  beginShape();
  vertex(0, height);
  vertex(0, map(bladeC1, 0, 65535, height, 0));
  vertex(width, map(bladeC2, 0, 65535, height, 0));
  vertex(width, height);
  endShape(CLOSE);

  //blade D (left), inclinable
  beginShape();
  vertex(0, height);
  vertex(map(bladeD2, 0, 65535, 0, width), height);
  vertex(map(bladeD1, 0, 65535, 0, width), 0);
  vertex(0, 0);
  endShape(CLOSE);

  popMatrix();
}
void initialize_font() {
  // Scanner data/fonts/ pour lister les TTF disponibles
  java.io.File fonts_dir = new java.io.File(sketchPath("data/fonts"));
  if (fonts_dir.exists()) {
    java.io.File[] files = fonts_dir.listFiles(new java.io.FilenameFilter() {
      public boolean accept(java.io.File d, String n) {
        return n.toLowerCase().endsWith(".ttf");
      }
    });
    if (files != null && files.length > 0) {
      available_fonts = new String[files.length];
      for (int i = 0; i < files.length; i++) available_fonts[i] = files[i].getName();
      java.util.Arrays.sort(available_fonts);
    }
  }
  if (available_fonts.length == 0) available_fonts = new String[]{"police.ttf"};
  // Pré-charger toutes les polices dans le cache
  font_cache = new PFont[available_fonts.length];
  for (int i = 0; i < available_fonts.length; i++) {
    font_cache[i] = createFont(sketchPath("data/fonts/") + available_fonts[i], 200);
  }
  f = font_cache[0];
  println("Polices chargées : " + available_fonts.length);
}

void do_blade_blur() {
  int blurA = (dmx_data[20] & 0xFF);  // Channel 21 - efx blur A
  float blurB = dmx_data[21] & 0xFF;  // Channel 22 - efx blur B
  if (blurA > .1 || blurB > .1) {
    fx.render()
      .blur(blurA, blurB)
      .compose();
  }
}


void do_effects() {
  // add filters (experimental) ///sobel()ok  rgbSplit(20)ok pixelate()ok chromaticAberration() ok  saturationVibrance(flot,flot)ok bloom() denoise rgbSplit vignette grayScale  brightnessContrast bloom ..
  if ((dmx_data[22]& 0xFF)>1) {
    fx.render()
      .pixelate(map(dmx_data[22] & 0xFF, 0, 255, 255, 20))
      .compose();
  }

  if ((dmx_data[23]& 0xFF)>128) {
    fx.render()
      .sobel()
      .compose();
  }
  if ((dmx_data[24]& 0xFF)>1) {
    fx.render()
      .rgbSplit(dmx_data[24]& 0xFF)
      .compose();
  }
  float saturationVibranceA = (dmx_data[25] & 0xFF);
  float saturationVibranceB = (dmx_data[26] & 0xFF);
  if (saturationVibranceA > .001 || saturationVibranceB > .001 ) {
    fx.render()
      .saturationVibrance(saturationVibranceA, saturationVibranceB)
      .compose();
  }
  if ((dmx_data[27]& 0xFF)>128) {
    fx.render()
      .chromaticAberration()
      .compose();
  }
}

void initialize_fx() {
  fx = new PostFX(this);
}

