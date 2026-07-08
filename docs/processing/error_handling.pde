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
  if (data == null) {
    log_error("DMX data is null");
    return false;
  }
  
  if (data.length < number_of_base_parameters) {
    log_error("DMX data too short: " + data.length + " bytes (need " + number_of_base_parameters + ")");
    return false;
  }
  
  // Validation sémantique : mode de chaque spot doit être dans [0, 14]
  int expected_total = number_of_base_parameters + (number_of_spots * number_of_parameters_by_spots);
  if (data.length >= expected_total) {
    for (int spot = 0; spot < number_of_spots; spot++) {
      int base_addr = number_of_base_parameters + (spot * number_of_parameters_by_spots);
      int mode = data[base_addr + 19] & 0xFF;
      if (mode > 14) {
        log_error("Invalid spot mode at spot " + spot + ": " + mode + " (max 14)");
        return false;
      }
    }
  }
  
  return true;
}

byte[] get_safe_dmx_data(byte[] incoming_data) {
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
  if (valid_data != null && valid_data.length >= number_of_base_parameters) {
    // Copier les données valides
    int copy_length = min(valid_data.length, last_valid_dmx_data.length);
    System.arraycopy(valid_data, 0, last_valid_dmx_data, 0, copy_length);
    
    backup_data_available = true;
    last_valid_data_time = millis();
  }
}

byte[] create_emergency_data() {
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
  if (error_count > 0) {
    error_count = 0;
    artnet_connection_ok = true;
    dmx_data_valid = true;
    println("✅ System recovered - error state reset");
  }
}

boolean is_system_healthy() {
  long time_since_valid = millis() - last_valid_data_time;
  
  return artnet_connection_ok && 
         dmx_data_valid && 
         error_count < max_error_threshold &&
         time_since_valid < error_recovery_timeout;
}

void log_error(String message) {
  println("🚨 [" + millis() + "] ERROR: " + message);
}

void display_system_status() {
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