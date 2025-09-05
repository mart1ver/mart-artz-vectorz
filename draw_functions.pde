void do_background() {
  bg_color = color(dmx_data[0] & 0xFF, dmx_data[1] & 0xFF, dmx_data[2] & 0xFF);
  // set background
  background(bg_color);
}
void do_spots() {
  for (int i = 0; i < number_of_spots; i++) {
    //first we fill the variables
    blend_mode         = int(map(dmx_data[11] & 0xFF, 0, 255, 1, 10));//blend mode is for the base but it is applied individualy on each spots thats why it is there
    current_spot_address = i*number_of_parameters_by_spots;
    spot_color         = color(dmx_data[number_of_base_parameters+(current_spot_address)] & 0xFF, dmx_data[number_of_base_parameters+1+(current_spot_address)] & 0xFF, dmx_data[number_of_base_parameters+2] & 0xFF);
    spot_alpha         = dmx_data[number_of_base_parameters+3+(current_spot_address)] & 0xFF;
    spot_stroke        = dmx_data[number_of_base_parameters+4+(current_spot_address)] & 0xFF;
    spot_stroke_alpha  = dmx_data[number_of_base_parameters+5+(current_spot_address)] & 0xFF;
    spot_stroke_color  = color(dmx_data[number_of_base_parameters+6+(current_spot_address)] & 0xFF, dmx_data[number_of_base_parameters+7+(current_spot_address)] & 0xFF, dmx_data[number_of_base_parameters+8+(current_spot_address)] & 0xFF);
    spot_size_pan      = map(((dmx_data[number_of_base_parameters+9+(current_spot_address)] & 0xFF)*256)+(dmx_data[number_of_base_parameters+10+(current_spot_address)] & 0xFF), 0, 65536, 0, 1000)    ;
    spot_size_tilt     = map(((dmx_data[number_of_base_parameters+11+(current_spot_address)] & 0xFF)*256)+(dmx_data[number_of_base_parameters+12+(current_spot_address)] & 0xFF), 0, 65536, 0, 1000)    ;
    spot_rotation      = map(dmx_data[number_of_base_parameters+13+(current_spot_address)] & 0xFF, 0, 255, 0, 360);
    spot_position_pan  = map(((dmx_data[number_of_base_parameters+14+(current_spot_address)] & 0xFF)*256)+(dmx_data[number_of_base_parameters+15+(current_spot_address)] & 0xFF), 0, 65536, -255-(width/2), 255+(width/2));
    spot_position_tilt = map(((dmx_data[number_of_base_parameters+16+(current_spot_address)] & 0xFF)*256)+(dmx_data[number_of_base_parameters+17+(current_spot_address)] & 0xFF), 0, 65536, -255-(height/2), 255+(height/2));
    spot_mode          = dmx_data[number_of_base_parameters+18+(current_spot_address)];
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
    translate(width/2, height/2);
    translate(spot_position_pan, spot_position_tilt);
    rotate(radians(spot_rotation));
    //next modifications are there!
    switch(spot_mode) {
    case 0:
      //rectangle
      rect(0, 0, spot_size_pan, spot_size_tilt);
      break;
    case 1:
      //ellipse
      ellipse(0, 0, spot_size_pan, spot_size_tilt);
      break;
    case 2:
      // star
      strokeWeight(spot_stroke/5);
      beginShape();
      vertex(0, -50);
      vertex(14, -20);
      vertex(47, -15);
      vertex(23, 7);
      vertex(29, 40);
      vertex(0, 25);
      vertex(-29, 40);
      vertex(-23, 7);
      vertex(-47, -15);
      vertex(-14, -20);
      scale(spot_size_pan/40);
      endShape(CLOSE);
      strokeWeight(spot_stroke);
      break;
    case 3:
      //letter
      message = (str(char(byte(spot_size_tilt))));
      textFont(f);
      textAlign(CENTER);
      pushMatrix();
      scale(-spot_size_pan/80, -spot_size_pan/80);
      text(message, 0, 0);
      popMatrix();
      break;
    case 4:
      // star
      strokeWeight(spot_stroke/5);
      beginShape();
      vertex(0, -50);
      vertex(14, -20);
      vertex(47, -15);
      vertex(23, 7);
      vertex(29, 40);
      vertex(0, 25);
      vertex(-29, 40);
      vertex(-23, 7);
      vertex(-47, -15);
      vertex(-14, -20);
      scale(spot_size_pan/40);
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
  // read the from byte 3 to byte 10 to set the blades
  //blade1, up
  fill(0);
  beginShape();
  vertex(0, 0);
  vertex(width, 0);
  vertex( width, map(dmx_data[4]&0xFF, 0, 255, 0, height));
  vertex(0, map(dmx_data[3]&0xFF, 0, 255, 0, height));
  endShape(CLOSE);
  //blade2, right
  beginShape();
  vertex(width, 0);
  vertex( width, height);
  vertex(map(dmx_data[6]&0xFF, 0, 255, width, 0), height);
  vertex(map(dmx_data[5]&0xFF, 0, 255, width, 0), 0);
  endShape(CLOSE);
  //blade3, down
  beginShape();
  vertex(0, height);
  vertex(0, map(dmx_data[8]&0xFF, 0, 255, height, 0));
  vertex( width, map(dmx_data[7]&0xFF, 0, 255, height, 0));
  vertex( width, height);
  endShape(CLOSE);
  //blade4, left
  beginShape();
  vertex(0, height);
  vertex(map(dmx_data[9]&0xFF, 0, 255, 0, width), height);
  vertex(map(dmx_data[10]&0xFF, 0, 255, 0, width), 0);
  vertex(0, 0);
  endShape(CLOSE);
  popMatrix();
}
void initialize_font() {
  f = createFont("arial", 200);
}

void do_blade_blur() {
  int blurA = (dmx_data[12] & 0xFF);
  float blurB = dmx_data[13] & 0xFF;
  if (blurA > .1 || blurB > .1) {
    fx.render()
      .blur(blurA, blurB)
      .compose();
  }
}


void do_effects() {
  // add filters (experimental) ///sobel()ok  rgbSplit(20)ok pixelate()ok chromaticAberration() ok  saturationVibrance(flot,flot)ok bloom() denoise rgbSplit vignette grayScale  brightnessContrast bloom ..
  if ((dmx_data[14]& 0xFF)>1) {
    fx.render()
      .pixelate(map(dmx_data[14] & 0xFF, 0, 255, 255, 20))
      .compose();
  }

  if ((dmx_data[15]& 0xFF)>128) {
    fx.render()
      .sobel()
      .compose();
  }
  if ((dmx_data[16]& 0xFF)>1) {
    fx.render()
      .rgbSplit(dmx_data[16]& 0xFF)
      .compose();
  }
  float saturationVibranceA = (dmx_data[17] & 0xFF);
  float saturationVibranceB = (dmx_data[18] & 0xFF);
  if (saturationVibranceA > .001 || saturationVibranceB > .001 ) {
    fx.render()
      .saturationVibrance(saturationVibranceA, saturationVibranceB)
      .compose();
  }
  if ((dmx_data[19]& 0xFF)>128) {
    fx.render()
      .chromaticAberration()
      .compose();
  }
}

void initialize_fx() {
  fx = new PostFX(this);
}
