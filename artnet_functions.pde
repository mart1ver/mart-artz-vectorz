long artpoll_reply_last_ms = 0;

void initialize_artnet() {
  artnet = new ArtNetClient();
  artnet.start(iface_address);
  initialize_error_handling();
  send_artpoll_reply();
  println("🚀 ArtNet + Error handling initialized");
}

void send_artpoll_reply() {
  try {
    byte[] pkt = new byte[239];

    // ID "Art-Net\0"
    byte[] id = {'A','r','t','-','N','e','t',0};
    System.arraycopy(id, 0, pkt, 0, 8);

    // OpCode ArtPollReply = 0x2100 (little-endian)
    pkt[8] = 0x00; pkt[9] = 0x21;

    // IP Address — parse iface_address
    try {
      String[] parts = iface_address.split("\\.");
      if (parts.length == 4) {
        for (int i = 0; i < 4; i++) pkt[10+i] = (byte) Integer.parseInt(parts[i].trim());
      }
    } catch (Exception e) {}

    // Port 6454 = 0x1936 little-endian
    pkt[14] = 0x36; pkt[15] = 0x19;

    // VersInfo
    pkt[16] = 0x00; pkt[17] = 0x01;

    // NetSwitch / SubSwitch
    pkt[18] = (byte) artnet_start_universe; pkt[19] = 0x00;

    // Oem 0xFFFF (unknown), EstaMan 0x0000
    pkt[20] = (byte)0xFF; pkt[21] = (byte)0xFF;

    // ShortName (18 bytes)
    byte[] sn = "LuxCore".getBytes("UTF-8");
    System.arraycopy(sn, 0, pkt, 26, min(sn.length, 17));

    // LongName (64 bytes)
    byte[] ln = "LuxCore DMX Engine — Martin Vert".getBytes("UTF-8");
    System.arraycopy(ln, 0, pkt, 44, min(ln.length, 63));

    // NodeReport (64 bytes)
    byte[] rp = "#0001 [0000] LuxCore OK".getBytes("UTF-8");
    System.arraycopy(rp, 0, pkt, 108, min(rp.length, 63));

    // NumPorts: 1
    pkt[172] = 0x01; pkt[173] = 0x00;

    // PortTypes: DMX input
    pkt[174] = (byte)0x80;

    // GoodInput, GoodOutput
    pkt[178] = (byte)0x08;
    pkt[182] = (byte)0x80;

    // SwIn / SwOut : univers
    pkt[186] = (byte) artnet_start_universe;
    pkt[190] = (byte) artnet_start_universe;

    // Style: StNode
    pkt[200] = 0x00;

    // Status2: supporte adressage 15-bit
    pkt[212] = 0x08;

    // Envoi en broadcast
    java.net.DatagramSocket sock = new java.net.DatagramSocket();
    sock.setBroadcast(true);
    java.net.InetAddress bcast = java.net.InetAddress.getByName("255.255.255.255");
    sock.send(new java.net.DatagramPacket(pkt, pkt.length, bcast, 6454));
    sock.close();

    artpoll_reply_last_ms = millis();
    println("📡 ArtPollReply envoyé");
  } catch (Exception e) {
    println("ArtPollReply failed: " + e.getMessage());
  }
}

// Tableau pré-alloué une seule fois — zéro allocation par frame
byte[] dmx_buffer = new byte[512 * 9];

void do_artnet() {
  // Annonce ArtPollReply toutes les 2.5s (spec ArtNet)
  if (millis() - artpoll_reply_last_ms > 2500) send_artpoll_reply();

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
