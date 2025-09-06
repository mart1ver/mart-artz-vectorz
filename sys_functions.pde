void set_fullscreen() {
  JSONObject json_obj = loadJSONObject("data/gui/martz_artz_verctorz/saves/auto.json");
  JSONArray  json_arr = json_obj.getJSONArray("children");
  JSONObject extract0 = json_arr.getJSONObject(2);
  JSONArray  extract1 = extract0.getJSONArray("children");
  JSONObject extract2 = extract1.getJSONObject(0);
  used_screen = int(extract2.getInt("valueFloat"));
  switch(used_screen) {
  case 0:
    size (800, 600, P2D);
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
  default:
    blend_mode_string = "BLEND";
    break;
  case 1:
    blend_mode_string = "BLEND";
    break;
  case 2:
    blend_mode_string = "ADD";
    break;
  case 3:
    blend_mode_string = "SUBTRACT";
    break;
  case 4:
    blend_mode_string = "DARKEST";
    break;
  case 5:
    blend_mode_string = "LIGHTEST";
    break;
  case 6:
    blend_mode_string = "DIFFERENCE";
    break;
  case 7:
    blend_mode_string = "EXCLUSION";
    break;
  case 8:
    blend_mode_string = "MULTIPLY";
    break;
  case 9:
    blend_mode_string = "SCREEN";
    break;
  case 10:
    blend_mode_string = "REPLACE";
    break;
  }
  return blend_mode_string;
}
