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
  initialize_performance_optimization();
  initialize_spot_pool(number_of_spots);
}

void draw() {
  start_frame_timing();
  do_gui();
  do_artnet();
  update_screen_cache();
  do_background();
  do_spots_optimized();
  do_effects();
  do_blades();
  do_blade_blur();
  end_frame_timing();
}

