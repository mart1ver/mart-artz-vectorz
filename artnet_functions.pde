void initialize_artnet() {
  artnet = new ArtNetClient();
  artnet.start(iface_address);
}

void do_artnet() {
  dmx_data = artnet.readDmxData(0, artnet_start_universe);
  for (int i = 1; i < 9; i++) {
    dmx_data = concat(dmx_data, artnet.readDmxData(i, artnet_start_universe));
  }
}

void do_artnet_restart() {
  artnet.stop();
  artnet = new ArtNetClient();
  artnet.start(iface_address);
}
