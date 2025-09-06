// ============================================================================
// LUXCORE DMX ENGINE - ERROR HANDLING UTILITIES
// ============================================================================
// Gestion d'erreurs robuste pour communication ArtNet et validation DMX
// Author: Martin Vert
// ============================================================================

// Variables globales pour gestion d'erreurs
boolean artnet_connection_ok = true;
boolean dmx_data_valid = true;
int error_count = 0;
int max_error_threshold = 5;
long last_valid_data_time = 0;
long error_recovery_timeout = 5000; // 5 secondes

// Backup des dernières données valides
byte[] last_valid_dmx_data;
boolean backup_data_available = false;

void initialize_error_handling() {
  """Initialize error handling system"""
  last_valid_dmx_data = new byte[512];
  // Initialiser avec des valeurs par défaut sûres
  for (int i = 0; i < 512; i++) {
    last_valid_dmx_data[i] = 0;
  }
  last_valid_data_time = millis();
  backup_data_available = false;
  println("🛡️  Error handling system initialized");
}

boolean validate_dmx_data(byte[] data) {
  """Validate incoming DMX data for corruption or errors"""
  
  if (data == null) {
    log_error("DMX data is null");
    return false;
  }
  
  if (data.length < number_of_base_parameters) {
    log_error("DMX data too short: " + data.length + " bytes (need " + number_of_base_parameters + ")");
    return false;
  }
  
  // Validation basique des plages de valeurs critiques
  // Vérifier les canaux RGB de base (0-2)
  for (int i = 0; i < 3; i++) {
    int value = data[i] & 0xFF;
    if (value < 0 || value > 255) {
      log_error("Invalid RGB value at channel " + i + ": " + value);
      return false;
    }
  }
  
  // Vérifier le mode de mélange (canal 19)
  if (data.length > 19) {
    int blend_val = data[19] & 0xFF;
    if (blend_val < 0 || blend_val > 255) {
      log_error("Invalid blend mode value: " + blend_val);
      return false;
    }
  }
  
  // Validation des canaux de spots si assez de données
  int expected_total = number_of_base_parameters + (number_of_spots * number_of_parameters_by_spots);
  if (data.length >= expected_total) {
    for (int spot = 0; spot < number_of_spots; spot++) {
      int base_addr = number_of_base_parameters + (spot * number_of_parameters_by_spots);
      
      // Vérifier alpha spot (ne doit pas être négatif)
      if (base_addr + 3 < data.length) {
        int alpha = data[base_addr + 3] & 0xFF;
        if (alpha < 0 || alpha > 255) {
          log_error("Invalid spot alpha at spot " + spot + ": " + alpha);
          return false;
        }
      }
    }
  }
  
  return true;
}

byte[] get_safe_dmx_data(byte[] incoming_data) {
  """Get safe DMX data with fallback and error recovery"""
  
  // Tentative de validation des données entrantes
  if (validate_dmx_data(incoming_data)) {
    // Données valides - sauvegarder comme backup
    backup_valid_data(incoming_data);
    reset_error_state();
    return incoming_data;
  }
  
  // Données invalides - incrémenter compteur d'erreurs
  error_count++;
  artnet_connection_ok = false;
  dmx_data_valid = false;
  
  println("⚠️  DMX validation failed (error #" + error_count + ")");
  
  // Si trop d'erreurs, utiliser les données de backup
  if (error_count >= max_error_threshold) {
    println("🚨 Error threshold reached - using backup data");
    if (backup_data_available) {
      return last_valid_dmx_data;
    } else {
      // Créer données d'urgence sûres
      return create_emergency_data();
    }
  }
  
  // Sinon, utiliser les dernières données valides
  if (backup_data_available) {
    return last_valid_dmx_data;
  } else {
    return create_emergency_data();
  }
}

void backup_valid_data(byte[] valid_data) {
  """Backup valid DMX data for emergency recovery"""
  if (valid_data != null && valid_data.length >= number_of_base_parameters) {
    // Copier les données valides
    int copy_length = min(valid_data.length, last_valid_dmx_data.length);
    System.arraycopy(valid_data, 0, last_valid_dmx_data, 0, copy_length);
    
    backup_data_available = true;
    last_valid_data_time = millis();
  }
}

byte[] create_emergency_data() {
  """Create safe emergency DMX data"""
  byte[] emergency_data = new byte[512];
  
  // Valeurs d'urgence sûres
  emergency_data[0] = 50;   // Rouge base faible
  emergency_data[1] = 50;   // Vert base faible  
  emergency_data[2] = 100;  // Bleu base modéré (signe visuel de mode urgence)
  
  // Blades complètement ouvertes (0 = ouvert)
  for (int i = 3; i < 19; i++) {
    emergency_data[i] = 0;
  }
  
  // Mode de mélange normal
  emergency_data[19] = 0;
  
  // Spots éteints par sécurité
  for (int spot = 0; spot < number_of_spots; spot++) {
    int base_addr = number_of_base_parameters + (spot * number_of_parameters_by_spots);
    if (base_addr + 3 < emergency_data.length) {
      emergency_data[base_addr + 3] = 0; // Alpha = 0 (éteint)
    }
  }
  
  println("🆘 Emergency data activated - safe minimal state");
  return emergency_data;
}

void reset_error_state() {
  """Reset error state when system recovers"""
  if (error_count > 0) {
    error_count = 0;
    artnet_connection_ok = true;
    dmx_data_valid = true;
    println("✅ System recovered - error state reset");
  }
}

boolean is_system_healthy() {
  """Check if system is in healthy state"""
  long time_since_valid = millis() - last_valid_data_time;
  
  return artnet_connection_ok && 
         dmx_data_valid && 
         error_count < max_error_threshold &&
         time_since_valid < error_recovery_timeout;
}

void log_error(String message) {
  """Log error with timestamp"""
  println("🚨 [" + millis() + "] ERROR: " + message);
}

void display_system_status() {
  """Display system health status (for debugging)"""
  String status = is_system_healthy() ? "HEALTHY" : "DEGRADED";
  String color_indicator = is_system_healthy() ? "🟢" : "🟡";
  
  if (error_count > 0) {
    println(color_indicator + " System: " + status + 
            " | Errors: " + error_count + 
            " | Backup: " + (backup_data_available ? "Available" : "None"));
  }
}

// Wrapper sécurisé pour la fonction artnet existante
byte[] safe_artnet_read(int universe, int start_universe) {
  """Safe wrapper for ArtNet reading with error handling"""
  try {
    byte[] raw_data = artnet.readDmxData(universe, start_universe);
    return get_safe_dmx_data(raw_data);
  } catch (Exception e) {
    log_error("ArtNet read exception: " + e.getMessage());
    error_count++;
    artnet_connection_ok = false;
    
    if (backup_data_available) {
      return last_valid_dmx_data;
    } else {
      return create_emergency_data();
    }
  }
}