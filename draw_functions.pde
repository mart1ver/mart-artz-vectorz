void do_background() {
  bg_color = color(dmx_data[0] & 0xFF, dmx_data[1] & 0xFF, dmx_data[2] & 0xFF);
  // set background
  background(bg_color);
}
void do_spots() {
  // Cache expensive calculations outside the loop
  blend_mode = int(map(dmx_data[11] & 0xFF, 0, 255, 1, 10));
  float half_width = width * 0.5;
  float half_height = height * 0.5;

  for (int i = 0; i < number_of_spots; i++) {
    // Pre-calculate base address for efficient DMX access
    int base_addr = number_of_base_parameters + (i * number_of_parameters_by_spots);

    // Extract DMX values efficiently with fixed blue channel bug
    spot_color         = color(dmx_data[base_addr] & 0xFF, dmx_data[base_addr+1] & 0xFF, dmx_data[base_addr+2] & 0xFF);
    spot_alpha         = dmx_data[base_addr+3] & 0xFF;
    spot_stroke        = dmx_data[base_addr+4] & 0xFF;
    spot_stroke_alpha  = dmx_data[base_addr+5] & 0xFF;
    spot_stroke_color  = color(dmx_data[base_addr+6] & 0xFF, dmx_data[base_addr+7] & 0xFF, dmx_data[base_addr+8] & 0xFF);

    // Pre-calculate 16-bit values for better performance
    int pan_16bit = ((dmx_data[base_addr+9] & 0xFF) << 8) + (dmx_data[base_addr+10] & 0xFF);
    int tilt_16bit = ((dmx_data[base_addr+11] & 0xFF) << 8) + (dmx_data[base_addr+12] & 0xFF);
    int pos_pan_16bit = ((dmx_data[base_addr+14] & 0xFF) << 8) + (dmx_data[base_addr+15] & 0xFF);
    int pos_tilt_16bit = ((dmx_data[base_addr+16] & 0xFF) << 8) + (dmx_data[base_addr+17] & 0xFF);

    spot_size_pan      = map(pan_16bit, 0, 65535, 0, 1000);
    spot_size_tilt     = map(tilt_16bit, 0, 65535, 0, 1000);
    spot_rotation      = map(dmx_data[base_addr+13] & 0xFF, 0, 255, 0, 360);
    spot_position_pan  = map(pos_pan_16bit, 0, 65535, -255-half_width, 255+half_width);
    spot_position_tilt = map(pos_tilt_16bit, 0, 65535, -255-half_height, 255+half_height);
    spot_mode          = dmx_data[base_addr+18];
    // set blendmode
    blendMode(blend_mode);
    //then we draw the spot
    strokeWeight(spot_stroke);
    stroke(spot_stroke_color, spot_stroke_alpha );
    fill(spot_color, spot_alpha);
    shapeMode(CENTER);
    rectMode(CENTER);
    ellipseMode(CENTER);
    pushMatrix();
    translate(half_width + spot_position_pan, half_height + spot_position_tilt);
    rotate(radians(spot_rotation));
    //next modifications are there!
    switch(spot_mode) {
    case 0:
      //ellipse
      ellipse(0, 0, spot_size_pan, spot_size_tilt);
      break;
    case 1:
      //rectangle
      rect(0, 0, spot_size_pan, spot_size_tilt);
      break;
    case 2:
      //letter
      message = (str(char(byte(spot_size_tilt))));
      textFont(f);
      textAlign(CENTER, CENTER);
      // Utilise directement la rotation déjà appliquée par la matrice parent
      scale(-spot_size_pan/80, -spot_size_pan/80);
      text(message, 0, 0);
      break;
    case 3:
      // triangle
      strokeWeight(spot_stroke/5);
      beginShape();
      vertex(0, -spot_size_tilt/2);                    // Point du haut
      vertex(-spot_size_pan/2, spot_size_tilt/2);      // Point gauche
      vertex(spot_size_pan/2, spot_size_tilt/2);       // Point droit
      endShape(CLOSE);
      strokeWeight(spot_stroke);
      break;
    case 4:
      // pentagone
      strokeWeight(spot_stroke/5);
      beginShape();
      float radius = spot_size_pan/2;
      for (int p = 0; p < 5; p++) {
        float angle = TWO_PI * p / 5 - PI/2;  // Commence par le haut
        vertex(radius * cos(angle), radius * sin(angle));
      }
      endShape(CLOSE);
      strokeWeight(spot_stroke);
      break;
    default:
      rect(0, 0, spot_size_pan, spot_size_tilt);
      break;
    }
    popMatrix();
    noStroke();
  }
  blendMode(BLEND);//back to normal blend
}
void do_blades() {
  pushMatrix();
  // read the from byte 3 to byte 18 to set the blades (16-bit precision)

  // Convert 16-bit values for each blade side
  int bladeA1 = ((dmx_data[3]&0xFF) << 8) | (dmx_data[4]&0xFF);  // MSB + LSB
  int bladeA2 = ((dmx_data[5]&0xFF) << 8) | (dmx_data[6]&0xFF);
  int bladeB1 = ((dmx_data[7]&0xFF) << 8) | (dmx_data[8]&0xFF);
  int bladeB2 = ((dmx_data[9]&0xFF) << 8) | (dmx_data[10]&0xFF);
  int bladeC1 = ((dmx_data[11]&0xFF) << 8) | (dmx_data[12]&0xFF);
  int bladeC2 = ((dmx_data[13]&0xFF) << 8) | (dmx_data[14]&0xFF);
  int bladeD1 = ((dmx_data[15]&0xFF) << 8) | (dmx_data[16]&0xFF);
  int bladeD2 = ((dmx_data[17]&0xFF) << 8) | (dmx_data[18]&0xFF);

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
  // Use a system font that's more likely to be available
  String[] fontList = PFont.list();
  if (fontList.length > 0) {
    f = createFont(fontList[0], 200);  // Use first available font
  } else {
    f = createFont("SansSerif", 200);  // Fallback generic font
  }
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
