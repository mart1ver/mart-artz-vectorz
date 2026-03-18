void initialize_gui() {
  noCursor();
  gui = new LazyGui(this, new LazyGuiSettings()
    .setStartGuiHidden(true)
    .setHideBuiltInFolders(true)
    .setSketchNameOverride("LuxCore DMX Engine")
    );
  do_gui();
}

void do_gui() {
  gui.pushFolder("config");
  screen_number = gui.sliderInt("Screen number", screen_number, 0, 4);
  if (screen_number == 0) {
    String raw_w = gui.text("Window width",  str(win_width)).trim();
    String raw_h = gui.text("Window height", str(win_height)).trim();
    int new_w = max(int(raw_w), 600);
    int new_h = max(int(raw_h), 600);
    if (new_w != win_width || new_h != win_height) {
      win_width  = new_w;
      win_height = new_h;
      saveStrings(dataPath("window_size.txt"), new String[]{ win_width + " " + win_height });
      println("Taille sauvegardée : " + win_width + " x " + win_height + " (Ctrl+R pour appliquer)");
    }
  }
  iface_address = gui.text("Iface ip. address").trim();
  number_of_spots = gui.sliderInt("Nb. of spots", 7, 0, 256);
  artnet_start_universe = gui.sliderInt("Start universe", 0, 0, 10000);
  end_universe = artnet_start_universe;
  end_address = number_of_base_parameters+((number_of_parameters_by_spots*number_of_spots)+artnet_start_address);
  n_used_universes_minus_one = round(end_address/512);
  for (int i = 0; i < n_used_universes_minus_one; i++) {
    if (end_address > 512) {
      end_address = end_address - 512;
      end_universe = end_universe +1;
    }
  }
  if (gui.button("Restart artnet")) {
    do_artnet_restart();
  }
  gui.popFolder();
  
  
  gui.pushFolder("status");
  gui.textSet("Artnet usage: ", "from "+artnet_start_universe+"."+artnet_start_address+" to "+ end_universe+"."+end_address);
  gui.textSet("Actual blend mode: ", return_blend_mode());
  gui.popFolder();
}
