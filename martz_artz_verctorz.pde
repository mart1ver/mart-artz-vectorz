import com.krab.lazy.*;
import ch.bildspur.artnet.*;
import ch.bildspur.postfx.builder.*;
//import ch.bildspur.postfx.pass.*;
import ch.bildspur.postfx.*;
PostFX fx;
LazyGui gui;
ArtNetClient artnet;

void settings() {
  set_fullscreen();
}

void setup() {
  initialize_gui();
  initialize_fx();
  initialize_artnet();
  initialize_font();
}

void draw() {
  do_gui();
  do_artnet();
  do_background();
  do_spots();
  do_effects();
  do_blades();
  do_blade_blur();
}

