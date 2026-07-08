void set_fullscreen() {
  try {
    JSONObject json_obj = loadJSONObject("data/gui/martz_artz_verctorz/saves/auto.json");
    JSONArray  json_arr = json_obj.getJSONArray("children");
    JSONObject extract0 = json_arr.getJSONObject(2);
    JSONArray  extract1 = extract0.getJSONArray("children");
    JSONObject extract2 = extract1.getJSONObject(0);
    used_screen = int(extract2.getInt("valueFloat"));
  } catch (Exception e) {
    println("set_fullscreen: auto.json absent ou invalide, fallback mode fenêtré 800x600");
    used_screen = 0;
  }
  switch(used_screen) {
  case 0:
    int sw = 800, sh = 600;
    try {
      java.io.File wf = new java.io.File(sketchPath("data/window_size.txt"));
      if (wf.exists()) {
        java.util.Scanner sc = new java.util.Scanner(wf);
        sw = max(600, sc.nextInt());
        sh = max(600, sc.nextInt());
        sc.close();
      }
    } catch (Exception e) {}
    size(sw, sh, P2D);
    break;
  case 1:
    fullScreen(P2D, 1);
    break;
  case 2:
    fullScreen(P2D, 2);
    break;
  case 3:
    fullScreen(P2D, 3);
    break;
  case 4:
    fullScreen(P2D, 4);
    break;
  }
}
void keyPressed() {
  if (key == 'h' ) {
    toggle_cursor();
  }
  if (key == 'p' || key == 'P') {
    println("🔍 Touche P pressée - Affichage des stats...");
    log_performance_stats();
  }
}

void toggle_cursor() {
  if (is_cursor_visible) {
    noCursor();
    is_cursor_visible = false;
  } else {
    cursor();
    is_cursor_visible = true;
  }
}
String return_blend_mode() {
  switch(blend_mode) {
  case BLEND:      blend_mode_string = "BLEND";      break;
  case ADD:        blend_mode_string = "ADD";         break;
  case SUBTRACT:   blend_mode_string = "SUBTRACT";    break;
  case DARKEST:    blend_mode_string = "DARKEST";     break;
  case LIGHTEST:   blend_mode_string = "LIGHTEST";    break;
  case DIFFERENCE: blend_mode_string = "DIFFERENCE";  break;
  case EXCLUSION:  blend_mode_string = "EXCLUSION";   break;
  case MULTIPLY:   blend_mode_string = "MULTIPLY";    break;
  case SCREEN:     blend_mode_string = "SCREEN";      break;
  case REPLACE:    blend_mode_string = "REPLACE";     break;
  default:         blend_mode_string = "BLEND";       break;
  }
  return blend_mode_string;
}
