// ============================================================================
// LUXCORE DMX ENGINE - PERFORMANCE OPTIMIZATION UTILITIES  
// ============================================================================
// Optimisations de performance pour le rendu des spots et effets
// Author: Martin Vert
// ============================================================================

// Variables de cache pour optimisations
PMatrix3D cached_matrix;
boolean matrix_cache_valid = false;
float cached_half_width = -1;
float cached_half_height = -1;
int cached_blend_mode = -1;

// Statistiques de performance (optionnel)
long frame_render_time = 0;
int frame_count = 0;
float average_frame_time = 0;

void initialize_performance_optimization() {
  cached_matrix = new PMatrix3D();
  matrix_cache_valid = false;
  println("⚡ Performance optimization initialized");
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
  int current_blend = int(map(dmx_value & 0xFF, 0, 255, 1, 10));
  
  if (cached_blend_mode != current_blend) {
    cached_blend_mode = current_blend;
    // Cache miss - recalculate
    return current_blend;
  }
  
  // Cache hit - return cached value
  return cached_blend_mode;
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
    int pan_16bit = ((dmx[base_addr+9] & 0xFF) << 8) | (dmx[base_addr+10] & 0xFF);
    int tilt_16bit = ((dmx[base_addr+11] & 0xFF) << 8) | (dmx[base_addr+12] & 0xFF);
    int pos_pan_16bit = ((dmx[base_addr+14] & 0xFF) << 8) | (dmx[base_addr+15] & 0xFF);
    int pos_tilt_16bit = ((dmx[base_addr+16] & 0xFF) << 8) | (dmx[base_addr+17] & 0xFF);
    
    // Pre-calculate all mapped values
    size_pan = map(pan_16bit, 0, 65535, 0, 1000);
    size_tilt = map(tilt_16bit, 0, 65535, 0, 1000);
    rotation = map(dmx[base_addr+13] & 0xFF, 0, 255, 0, 360);
    position_pan = map(pos_pan_16bit, 0, 65535, -255-half_width, 255+half_width);
    position_tilt = map(pos_tilt_16bit, 0, 65535, -255-half_height, 255+half_height);
    
    mode = dmx[base_addr+18];
    is_valid = true;
  }
  
  void render_optimized() {
    if (!is_valid) return;
    
    // Skip invisible spots early
    if (alpha <= 0) return;
    
    // Set colors and alpha
    fill(fill_color, alpha);
    stroke(stroke_color, stroke_alpha);
    strokeWeight(stroke_weight);
    
    // Matrix operations
    pushMatrix();
    translate(cached_half_width + position_pan, cached_half_height + position_tilt);
    
    if (abs(rotation) > 0.1) { // Skip rotation if negligible
      rotate(radians(rotation));
    }
    
    // Render shape based on mode
    render_shape_optimized();
    
    popMatrix();
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
        
      default:
        rect(0, 0, size_pan, size_tilt);
        break;
    }
  }
  
  void render_text_optimized() {
    String message = str(char(byte(size_tilt)));
    textFont(f);
    textAlign(CENTER, CENTER);
    scale(-size_pan/80, -size_pan/80);
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

float get_average_frame_time() {
  return average_frame_time;
}

void log_performance_stats() {
  println("=== 📊 LUXCORE PERFORMANCE STATS ===");
  println("🔧 System Status:");
  println("   Spot pool initialized: " + spot_pool_initialized);
  println("   Cache valid: " + matrix_cache_valid);
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