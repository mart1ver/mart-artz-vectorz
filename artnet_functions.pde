void initialize_artnet() {
  artnet = new ArtNetClient();
  artnet.start(iface_address);
  
  // Initialize error handling system  
  initialize_error_handling();
  println("🚀 ArtNet + Error handling initialized");
}

// Tableau pré-alloué une seule fois — zéro allocation par frame
byte[] dmx_buffer = new byte[512 * 9];

void do_artnet() {
  try {
    byte[] primary_data = safe_artnet_read(0, artnet_start_universe);

    if (primary_data != null) {
      // Copie du premier univers dans le buffer fixe
      System.arraycopy(primary_data, 0, dmx_buffer, 0, min(primary_data.length, 512));

      // Copie des univers additionnels dans le buffer fixe
      for (int i = 1; i < 9; i++) {
        try {
          byte[] additional_data = artnet.readDmxData(i, artnet_start_universe);
          if (additional_data != null && validate_dmx_data(additional_data)) {
            System.arraycopy(additional_data, 0, dmx_buffer, i * 512, min(additional_data.length, 512));
          } else {
            java.util.Arrays.fill(dmx_buffer, i * 512, (i + 1) * 512, (byte) 0);
          }
        } catch (Exception e) {
          log_error("Additional universe " + i + " read failed: " + e.getMessage());
          java.util.Arrays.fill(dmx_buffer, i * 512, (i + 1) * 512, (byte) 0);
        }
      }
      dmx_data = dmx_buffer;
    } else {
      dmx_data = create_emergency_data();
    }

  } catch (Exception e) {
    log_error("Critical ArtNet failure: " + e.getMessage());
    dmx_data = create_emergency_data();
  }

  if (!is_system_healthy()) {
    display_system_status();
  }
}

void do_artnet_restart() {
  artnet.stop();
  artnet = new ArtNetClient();
  artnet.start(iface_address);
}
