// ============================================================================
// LUXCORE DMX ENGINE - PERFORMANCE OPTIMIZATION UTILITIES  
// ============================================================================
// Optimisations de performance pour le rendu des spots et effets
// Author: Martin Vert
// ============================================================================

// Variables de cache pour optimisations
float cached_half_width = -1;
float cached_half_height = -1;

// LUT blend mode : DMX 0-255 → constantes Processing exactes
int[] blend_mode_lut = new int[256];

// Statistiques de performance (optionnel)
long frame_render_time = 0;
int frame_count = 0;
float average_frame_time = 0;

void initialize_performance_optimization() {
  build_blend_mode_lut();
  println("⚡ Performance optimization initialized");
}

void build_blend_mode_lut() {
  // Valeurs DMX exactes (CLAUDE.md) → constantes Processing
  int[] dmx_vals  = {  0,  29,  57,  85, 114, 142, 170, 199, 227, 255};
  int[] proc_vals = {BLEND, ADD, SUBTRACT, DARKEST, LIGHTEST,
                     DIFFERENCE, EXCLUSION, MULTIPLY, SCREEN, REPLACE};
  for (int d = 0; d < 256; d++) {
    int best = BLEND, best_dist = 256;
    for (int i = 0; i < dmx_vals.length; i++) {
      int dist = abs(d - dmx_vals[i]);
      if (dist < best_dist) { best_dist = dist; best = proc_vals[i]; }
    }
    blend_mode_lut[d] = best;
  }
}

void update_screen_cache() {
  float current_half_width = width * 0.5;
  float current_half_height = height * 0.5;
  
  if (cached_half_width != current_half_width || cached_half_height != current_half_height) {
    cached_half_width = current_half_width;
    cached_half_height = current_half_height;
    println("📺 Screen dimensions cached: " + width + "x" + height);
  }
}

int get_optimized_blend_mode(byte dmx_value) {
  return blend_mode_lut[dmx_value & 0xFF];
}

class SpotData {
  // Pré-calculé pour éviter recalculs constants
  color fill_color;
  color stroke_color;
  int alpha;
  int stroke_alpha;
  float size_pan, size_tilt;
  float position_pan, position_tilt;
  float rotation;
  int stroke_weight;
  int mode;
  boolean enabled;
  int spot_blend_mode;
  int font_index;

  boolean is_valid = false;
  
  void update_from_dmx(byte[] dmx, int base_addr, float half_width, float half_height) {
    
    // Extract colors with single pass
    fill_color = color(dmx[base_addr] & 0xFF, dmx[base_addr+1] & 0xFF, dmx[base_addr+2] & 0xFF);
    stroke_color = color(dmx[base_addr+6] & 0xFF, dmx[base_addr+7] & 0xFF, dmx[base_addr+8] & 0xFF);
    
    // Extract alphas
    alpha = dmx[base_addr+3] & 0xFF;
    stroke_alpha = dmx[base_addr+5] & 0xFF;
    stroke_weight = dmx[base_addr+4] & 0xFF;
    
    // Pre-calculate 16-bit values - optimized bit operations
    int pan_16bit      = ((dmx[base_addr+9]  & 0xFF) << 8) | (dmx[base_addr+10] & 0xFF);
    int tilt_16bit     = ((dmx[base_addr+11] & 0xFF) << 8) | (dmx[base_addr+12] & 0xFF);
    int rot_16bit      = ((dmx[base_addr+13] & 0xFF) << 8) | (dmx[base_addr+14] & 0xFF);
    int pos_pan_16bit  = ((dmx[base_addr+15] & 0xFF) << 8) | (dmx[base_addr+16] & 0xFF);
    int pos_tilt_16bit = ((dmx[base_addr+17] & 0xFF) << 8) | (dmx[base_addr+18] & 0xFF);

    // Pre-calculate all mapped values
    size_pan      = map(pan_16bit,      0, 65535, 0, 1000);
    size_tilt     = map(tilt_16bit,     0, 65535, 0, 1000);
    rotation      = map(rot_16bit,      0, 65535, 0, 360);
    position_pan  = map(pos_pan_16bit,  0, 65535, -255-half_width,  255+half_width);
    position_tilt = map(pos_tilt_16bit, 0, 65535, -255-half_height, 255+half_height);

    mode = dmx[base_addr+19];

    // Canaux +20/+21/+22 : enable, blend mode individuel, font index
    enabled = (dmx[base_addr+20] & 0xFF) > 0;
    int blend_raw = dmx[base_addr+21] & 0xFF;
    spot_blend_mode = (blend_raw == 0) ? blend_mode : blend_mode_lut[blend_raw];
    font_index = constrain(
      (dmx[base_addr+22] & 0xFF) * max(1, available_fonts.length) / 256,
      0, max(0, available_fonts.length - 1)
    );

    is_valid = true;
  }
  
  void render_optimized() {
    if (!is_valid) return;
    if (!enabled || alpha <= 0) return;

    boolean blend_override = (spot_blend_mode != blend_mode);
    if (blend_override) blendMode(spot_blend_mode);

    fill(fill_color, alpha);
    stroke(stroke_color, stroke_alpha);
    strokeWeight(stroke_weight);

    pushMatrix();
    translate(cached_half_width + position_pan, cached_half_height + position_tilt);

    if (abs(rotation) > 0.1) {
      rotate(radians(rotation));
    }

    render_shape_optimized();

    popMatrix();

    if (blend_override) blendMode(blend_mode);
  }
  
  void render_shape_optimized() {
    switch(mode) {
      case 0: // Ellipse
        ellipse(0, 0, size_pan, size_tilt);
        break;
        
      case 1: // Rectangle  
        rect(0, 0, size_pan, size_tilt);
        break;
        
      case 2: // Texte
        render_text_optimized();
        break;
        
      case 3: // Triangle
        render_triangle_optimized();
        break;
        
      case 4: // Pentagone  
        render_pentagon_optimized();
        break;
        
      case 5: // Hexagone  
        render_hexagon_optimized();
        break;
        
      case 6: // Losange
        render_diamond_optimized();
        break;
        
      case 7: // Octogone
        render_octagon_optimized();
        break;
        
      case 8: // Étoile 5 branches
        render_star_optimized();
        break;
        
      case 9: // Croix
        render_cross_optimized();
        break;
        
      case 10: // Flèche
        render_arrow_optimized();
        break;
        
      case 11: // Plus
        render_plus_optimized();
        break;
        
      case 12: // Cœur simple
        render_heart_simple_optimized();
        break;
        
      case 13: // Segment
        render_segment_optimized();
        break;
        
      case 14: // Fleur 6 pétales
        render_flower_optimized();
        break;
        
      default:
        rect(0, 0, size_pan, size_tilt);
        break;
    }
  }
  
  void render_text_optimized() {
    String message = str(char(byte(size_tilt)));
    if (font_cache != null && font_index >= 0 && font_index < font_cache.length) {
      textFont(font_cache[font_index]);
    } else {
      textFont(f);
    }
    textAlign(CENTER, CENTER);
    scale(size_pan/80, size_pan/80);
    text(message, 0, 0);
  }
  
  void render_triangle_optimized() {
    strokeWeight(stroke_weight/5);
    beginShape();
    vertex(0, -size_tilt/2);
    vertex(-size_pan/2, size_tilt/2);  
    vertex(size_pan/2, size_tilt/2);
    endShape(CLOSE);
    strokeWeight(stroke_weight);
  }
  
  void render_pentagon_optimized() {
    strokeWeight(stroke_weight/5);
    beginShape();
    float radius = size_pan/2;
    for (int p = 0; p < 5; p++) {
      float angle = TWO_PI * p / 5 - PI/2;
      vertex(radius * cos(angle), radius * sin(angle));
    }
    endShape(CLOSE);
    strokeWeight(stroke_weight);
  }
  
  void render_hexagon_optimized() {
    strokeWeight(stroke_weight/5);
    beginShape();
    float radius = size_pan/2;
    for (int h = 0; h < 6; h++) {
      float angle = TWO_PI * h / 6;
      vertex(radius * cos(angle), radius * sin(angle));
    }
    endShape(CLOSE);
    strokeWeight(stroke_weight);
  }
  
  void render_diamond_optimized() {
    strokeWeight(stroke_weight/5);
    beginShape();
    vertex(0, -size_tilt/2);                 // Haut
    vertex(size_pan/2, 0);                   // Droite
    vertex(0, size_tilt/2);                  // Bas
    vertex(-size_pan/2, 0);                  // Gauche
    endShape(CLOSE);
    strokeWeight(stroke_weight);
  }
  
  void render_octagon_optimized() {
    strokeWeight(stroke_weight/5);
    beginShape();
    float radius = size_pan/2;
    for (int o = 0; o < 8; o++) {
      float angle = TWO_PI * o / 8;
      vertex(radius * cos(angle), radius * sin(angle));
    }
    endShape(CLOSE);
    strokeWeight(stroke_weight);
  }
  
  void render_star_optimized() {
    // Étoile 5 branches (remplace l'ancienne étoile 8 branches)
    strokeWeight(stroke_weight/5);
    beginShape();
    float outer_radius = size_pan / 2;
    float inner_radius = outer_radius * 0.4;  // ratio doré ~0.382
    for (int s = 0; s < 10; s++) {
      float angle = TWO_PI * s / 10 - HALF_PI;  // pointe vers le haut
      if (s % 2 == 0) {
        vertex(outer_radius * cos(angle), outer_radius * sin(angle));
      } else {
        vertex(inner_radius * cos(angle), inner_radius * sin(angle));
      }
    }
    endShape(CLOSE);
    strokeWeight(stroke_weight);
  }
  
  void render_cross_optimized() {
    // Croix en un seul polygone 12 vertices (contour propre, pas 2 rectangles)
    strokeWeight(stroke_weight/5);
    float t = size_pan * 0.25;   // épaisseur des bras
    float a = size_pan * 0.50;   // demi-longueur des bras

    beginShape();
    vertex(-t/2, -a);    // P1  haut-gauche bras haut
    vertex( t/2, -a);    // P2  haut-droite  bras haut
    vertex( t/2, -t/2);  // P3  coin intérieur haut-droit
    vertex( a,   -t/2);  // P4  droite-haut  bras droit
    vertex( a,    t/2);  // P5  droite-bas   bras droit
    vertex( t/2,  t/2);  // P6  coin intérieur bas-droit
    vertex( t/2,  a);    // P7  bas-droite   bras bas
    vertex(-t/2,  a);    // P8  bas-gauche   bras bas
    vertex(-t/2,  t/2);  // P9  coin intérieur bas-gauche
    vertex(-a,    t/2);  // P10 gauche-bas   bras gauche
    vertex(-a,   -t/2);  // P11 gauche-haut  bras gauche
    vertex(-t/2, -t/2);  // P12 coin intérieur haut-gauche
    endShape(CLOSE);

    strokeWeight(stroke_weight);
  }
  
  void render_arrow_optimized() {
    strokeWeight(stroke_weight/5);
    beginShape();
    float head_width = size_pan * 0.6;
    float head_height = size_tilt * 0.3;
    float shaft_width = size_pan * 0.25;
    
    // Pointe de la flèche (vers le haut)
    vertex(0, -size_tilt/2);                                    // Pointe
    vertex(head_width/2, -size_tilt/2 + head_height);          // Droite pointe
    vertex(shaft_width/2, -size_tilt/2 + head_height);         // Début shaft droite
    vertex(shaft_width/2, size_tilt/2);                        // Bas shaft droite
    vertex(-shaft_width/2, size_tilt/2);                       // Bas shaft gauche
    vertex(-shaft_width/2, -size_tilt/2 + head_height);        // Début shaft gauche
    vertex(-head_width/2, -size_tilt/2 + head_height);         // Gauche pointe
    
    endShape(CLOSE);
    strokeWeight(stroke_weight);
  }
  
  void render_plus_optimized() {
    // Plus ✚ en un seul polygone 12 vertices (bras fins)
    strokeWeight(stroke_weight/5);
    float t = size_pan * 0.15;   // épaisseur fine
    float a = size_pan * 0.50;   // demi-longueur des bras

    beginShape();
    vertex(-t/2, -a);
    vertex( t/2, -a);
    vertex( t/2, -t/2);
    vertex( a,   -t/2);
    vertex( a,    t/2);
    vertex( t/2,  t/2);
    vertex( t/2,  a);
    vertex(-t/2,  a);
    vertex(-t/2,  t/2);
    vertex(-a,    t/2);
    vertex(-a,   -t/2);
    vertex(-t/2, -t/2);
    endShape(CLOSE);

    strokeWeight(stroke_weight);
  }
  
  void render_heart_simple_optimized() {
    strokeWeight(stroke_weight/5);
    float w = size_pan * 0.4;
    float h = size_tilt * 0.4;
    int steps = 72;  // 3x plus de facettes pour un cœur ultra-lisse

    beginShape();
    for (int i = 0; i < steps; i++) {
      float t = TWO_PI * i / steps;
      // Formule paramétrique mathématique du cœur
      float hx = 16 * pow(sin(t), 3);
      float hy = -(13 * cos(t) - 5 * cos(2*t) - 2 * cos(3*t) - cos(4*t));
      vertex(hx * w / 16.0, hy * h / 17.0);
    }
    endShape(CLOSE);

    strokeWeight(stroke_weight);
  }
  
  void render_segment_optimized() {
    // Segment — size_pan = longueur, size_tilt = épaisseur (1–130px)
    float thickness = max(1, size_tilt / 500.0);
    strokeWeight(thickness);
    line(-size_pan / 2, 0, size_pan / 2, 0);
    strokeWeight(stroke_weight);
  }
  
  void render_flower_optimized() {
    // Fleur 6 pétales - formule polaire r = R * (0.3 + 0.7 * |cos(3t)|)
    strokeWeight(stroke_weight/5);
    float outer_radius = size_pan * 0.45;
    int steps = 180;  // 3x plus de facettes pour une fleur ultra-lisse
    beginShape();
    for (int i = 0; i < steps; i++) {
      float t = TWO_PI * i / steps;
      float r = outer_radius * (0.28 + 0.72 * abs(cos(3 * t)));
      vertex(r * cos(t), r * sin(t));
    }
    endShape(CLOSE);
    strokeWeight(stroke_weight);
  }
}

// Pool de spots pour éviter allocations répétées
SpotData[] spot_pool;
boolean spot_pool_initialized = false;

void initialize_spot_pool(int max_spots) {
  if (!spot_pool_initialized) {
    spot_pool = new SpotData[max_spots];
    for (int i = 0; i < max_spots; i++) {
      spot_pool[i] = new SpotData();
    }
    spot_pool_initialized = true;
    println("🏊 Spot pool initialized: " + max_spots + " spots");
  }
}

void resize_spot_pool_if_needed(int new_size) {
  if (!spot_pool_initialized || spot_pool.length < new_size) {
    // Redimensionner le pool si nécessaire
    SpotData[] new_pool = new SpotData[new_size];
    
    // Copier les spots existants
    if (spot_pool_initialized) {
      int copy_count = min(spot_pool.length, new_size);
      for (int i = 0; i < copy_count; i++) {
        new_pool[i] = spot_pool[i];
      }
    }
    
    // Créer les nouveaux spots
    int start_index = spot_pool_initialized ? spot_pool.length : 0;
    for (int i = start_index; i < new_size; i++) {
      new_pool[i] = new SpotData();
    }
    
    spot_pool = new_pool;
    spot_pool_initialized = true;
    println("🔄 Spot pool resized to: " + new_size + " spots");
  }
}

void start_frame_timing() {
  frame_render_time = System.nanoTime();
}

void end_frame_timing() {
  if (frame_render_time > 0) {
    long frame_duration = System.nanoTime() - frame_render_time;
    frame_count++;
    
    // Update rolling average
    float current_frame_ms = frame_duration / 1000000.0;
    average_frame_time = (average_frame_time * (frame_count - 1) + current_frame_ms) / frame_count;
    
    // Log performance issues  
    if (current_frame_ms > 33.0) { // > 30 FPS
      println("⚠️  Slow frame detected: " + current_frame_ms + "ms");
    }
    
    frame_render_time = 0;
  }
}

void log_performance_stats() {
  println("=== 📊 LUXCORE PERFORMANCE STATS ===");
  println("🔧 System Status:");
  println("   Spot pool initialized: " + spot_pool_initialized);
  println("   Screen: " + width + "x" + height);
  println("⏱️  Performance Metrics:");
  println("   Average frame time: " + average_frame_time + "ms");  
  println("   Estimated FPS: " + (1000.0 / max(average_frame_time, 1.0)));
  println("   Total frames rendered: " + frame_count);
  println("   Current framerate: " + frameRate);
  println("🎯 DMX Status:");
  println("   DMX data length: " + (dmx_data != null ? dmx_data.length : "null"));
  println("   Base parameters: " + number_of_base_parameters);
  println("   Number of spots: " + number_of_spots);
  println("=====================================");
}