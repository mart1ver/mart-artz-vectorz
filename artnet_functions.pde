void initialize_artnet() {
  artnet = new ArtNetClient();
  artnet.start(iface_address);
  
  // Initialize error handling system  
  initialize_error_handling();
  println("🚀 ArtNet + Error handling initialized");
}

void do_artnet() {
  // Version sécurisée avec gestion d'erreurs
  try {
    // Lecture sécurisée du premier univers
    byte[] primary_data = safe_artnet_read(0, artnet_start_universe);
    
    if (primary_data != null) {
      dmx_data = primary_data;
      
      // Concaténation sécurisée des univers additionnels
      for (int i = 1; i < 9; i++) {
        try {
          byte[] additional_data = artnet.readDmxData(i, artnet_start_universe);
          if (additional_data != null && validate_dmx_data(additional_data)) {
            dmx_data = concat(dmx_data, additional_data);
          } else {
            // Utiliser des données vides sûres pour cet univers
            byte[] safe_additional = new byte[512];
            dmx_data = concat(dmx_data, safe_additional);
          }
        } catch (Exception e) {
          log_error("Additional universe " + i + " read failed: " + e.getMessage());
          // Continuer avec données vides pour cet univers
          byte[] safe_additional = new byte[512];
          dmx_data = concat(dmx_data, safe_additional);
        }
      }
    } else {
      // Fallback complet en cas d'échec
      dmx_data = create_emergency_data();
    }
    
  } catch (Exception e) {
    log_error("Critical ArtNet failure: " + e.getMessage());
    dmx_data = create_emergency_data();
  }
  
  // Afficher le statut si problème détecté (mode debug)
  if (!is_system_healthy()) {
    display_system_status();
  }
}

void do_artnet_restart() {
  artnet.stop();
  artnet = new ArtNetClient();
  artnet.start(iface_address);
}
