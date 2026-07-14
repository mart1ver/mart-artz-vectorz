#!/usr/bin/env python3
"""
Génère les fichiers GDTF pour LuxCore DMX Engine.
GDTF = Generic Device Type Format (ANSI E1.75)
Un fichier .gdtf est un ZIP contenant description.xml

Fixtures produites :
  LuxCore_Spot_23ch.gdtf  — à patcher N fois (un par spot)
  LuxCore_Base_32ch.gdtf  — à patcher une fois (fond + blades + effets + PostFX)

Patch (adresses 1-based) :
  Base  : adresse 1
  Spot0 : adresse 33  (= 32 + 0×23 + 1)
  Spot1 : adresse 56  (= 32 + 1×23 + 1)
  SpotN : adresse 32 + N×23 + 1

Le bloc de base fait 32 canaux (28 d'origine + 4 PostFX : feedback, bloom seuil,
bloom intensité, kaléidoscope). Le canal Mode du spot code des VALEURS LITTÉRALES
(le moteur lit l'octet brut) : 0..14 = formes, 100..113 = forme remplie par la vidéo.
"""

import zipfile
import uuid
import os


def spot_xml():
    """LuxCore Spot — 23 canaux DMX"""
    fid = str(uuid.uuid4())
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<GDTF DataVersion="1.2">
  <FixtureType
    Name="LuxCore Spot"
    ShortName="LCSpot"
    LongName="LuxCore DMX Engine - Spot"
    Manufacturer="Martin Vert"
    Description="Spot vectoriel 23ch : RGB fill, alpha, stroke, taille Pan/Tilt 16-bit, rotation 16-bit, position Pan/Tilt 16-bit, mode (14 formes 0..14 dont 13=Rafale, 14=Video ; bande 100..113 = forme remplie par la video), enable, blend mode individuel, police/selecteur video. Adresse spot N = 32 + N*23 + 1. Multi-univers : 20 spots/univers, 43 sur 2, 65 sur 3."
    FixtureTypeID="{fid}"
    RefFT=""
    Thumbnail="">

    <AttributeDefinitions>
      <Attributes>
        <Attribute Name="ColorAdd_R"   Pretty="R"        Activation="ColorMix" Feature="Color.Color"       PhysicalUnit="None"  Color="0.64 0.33 0.21"/>
        <Attribute Name="ColorAdd_G"   Pretty="G"        Activation="ColorMix" Feature="Color.Color"       PhysicalUnit="None"  Color="0.3 0.6 0.15"/>
        <Attribute Name="ColorAdd_B"   Pretty="B"        Activation="ColorMix" Feature="Color.Color"       PhysicalUnit="None"  Color="0.15 0.06 0.79"/>
        <Attribute Name="Dimmer"       Pretty="Alpha"    Activation="Dimmer"   Feature="Dimmer.Dimmer"     PhysicalUnit="None"  Color="0.32 0.32 0.32"/>
        <Attribute Name="StrokeW"      Pretty="Stroke W" Activation="None"     Feature="Beam.Beam"         PhysicalUnit="None"  Color="0.32 0.32 0.32"/>
        <Attribute Name="StrokeA"      Pretty="Stroke A" Activation="None"     Feature="Beam.Beam"         PhysicalUnit="None"  Color="0.32 0.32 0.32"/>
        <Attribute Name="StrokeR"      Pretty="Stroke R" Activation="None"     Feature="Color.Color"       PhysicalUnit="None"  Color="0.64 0.33 0.21"/>
        <Attribute Name="StrokeG"      Pretty="Stroke G" Activation="None"     Feature="Color.Color"       PhysicalUnit="None"  Color="0.3 0.6 0.15"/>
        <Attribute Name="StrokeB"      Pretty="Stroke B" Activation="None"     Feature="Color.Color"       PhysicalUnit="None"  Color="0.15 0.06 0.79"/>
        <Attribute Name="Zoom"         Pretty="Size Pan" Activation="Zoom"     Feature="Beam.Beam"         PhysicalUnit="Angle" Color="0.32 0.32 0.32"/>
        <Attribute Name="SizeTilt"     Pretty="Size Tilt" Activation="None"    Feature="Beam.Beam"         PhysicalUnit="None"  Color="0.32 0.32 0.32"/>
        <Attribute Name="Rotation"     Pretty="Rot"      Activation="Rotation" Feature="Position.PanTilt"  PhysicalUnit="Angle" Color="0.32 0.32 0.32"/>
        <Attribute Name="Pan"          Pretty="Pan"      Activation="Pan"      Feature="Position.PanTilt"  PhysicalUnit="Angle" Color="0.32 0.32 0.32"/>
        <Attribute Name="Tilt"         Pretty="Tilt"     Activation="Tilt"     Feature="Position.PanTilt"  PhysicalUnit="Angle" Color="0.32 0.32 0.32"/>
        <Attribute Name="Gobo1"        Pretty="Mode"     Activation="None"     Feature="Beam.Beam"         PhysicalUnit="None"  Color="0.32 0.32 0.32"/>
        <Attribute Name="Enable"       Pretty="Enable"   Activation="None"     Feature="Beam.Beam"         PhysicalUnit="None"  Color="0.32 0.32 0.32"/>
        <Attribute Name="BlendSpot"    Pretty="Blend/Sp" Activation="None"     Feature="Beam.Beam"         PhysicalUnit="None"  Color="0.32 0.32 0.32"/>
        <Attribute Name="FontIndex"    Pretty="Font/Vid" Activation="None"     Feature="Beam.Beam"         PhysicalUnit="None"  Color="0.32 0.32 0.32"/>
      </Attributes>
      <ActivationGroups>
        <ActivationGroup Name="ColorMix"/>
        <ActivationGroup Name="Dimmer"/>
        <ActivationGroup Name="Zoom"/>
        <ActivationGroup Name="Pan"/>
        <ActivationGroup Name="Tilt"/>
        <ActivationGroup Name="Rotation"/>
      </ActivationGroups>
      <Features>
        <FeatureGroup Name="Dimmer"   Pretty="Dimmer">  <Feature Name="Dimmer"/>   </FeatureGroup>
        <FeatureGroup Name="Color"    Pretty="Color">   <Feature Name="Color"/>    </FeatureGroup>
        <FeatureGroup Name="Position" Pretty="Position"><Feature Name="PanTilt"/>  </FeatureGroup>
        <FeatureGroup Name="Beam"     Pretty="Beam">    <Feature Name="Beam"/>     </FeatureGroup>
      </Features>
    </AttributeDefinitions>

    <Wheels/>
    <PhysicalDescriptions/>
    <Models/>
    <Geometries>
      <Geometry Name="Body" Model="" Position="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
    </Geometries>

    <DMXModes>
      <DMXMode Name="23ch" Geometry="Body">
        <DMXChannels>

          <!-- +0  Canal 1 : Rouge fill -->
          <DMXChannel DMXBreak="1" Offset="1" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="ColorAdd_R" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="ColorAdd_R" Name="Red" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +1  Canal 2 : Vert fill -->
          <DMXChannel DMXBreak="1" Offset="2" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="ColorAdd_G" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="ColorAdd_G" Name="Green" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +2  Canal 3 : Bleu fill -->
          <DMXChannel DMXBreak="1" Offset="3" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="ColorAdd_B" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="ColorAdd_B" Name="Blue" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +3  Canal 4 : Alpha / Dimmer -->
          <DMXChannel DMXBreak="1" Offset="4" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="Dimmer" Snap="No" Master="Grand" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Dimmer" Name="Alpha" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +4  Canal 5 : Stroke weight -->
          <DMXChannel DMXBreak="1" Offset="5" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="StrokeW" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="StrokeW" Name="Stroke Weight" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +5  Canal 6 : Stroke alpha -->
          <DMXChannel DMXBreak="1" Offset="6" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="StrokeA" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="StrokeA" Name="Stroke Alpha" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +6  Canal 7 : Stroke rouge -->
          <DMXChannel DMXBreak="1" Offset="7" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="StrokeR" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="StrokeR" Name="Stroke Red" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +7  Canal 8 : Stroke vert -->
          <DMXChannel DMXBreak="1" Offset="8" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="StrokeG" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="StrokeG" Name="Stroke Green" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +8  Canal 9 : Stroke bleu -->
          <DMXChannel DMXBreak="1" Offset="9" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="StrokeB" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="StrokeB" Name="Stroke Blue" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +9+10  Canaux 10-11 : Taille Pan 16-bit -->
          <DMXChannel DMXBreak="1" Offset="10 11" Highlight="32767" Geometry="Body">
            <LogicalChannel Attribute="Zoom" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Zoom" Name="Size Pan" OriginalAttribute="" DMXFrom="0/1" Default="32767/1" PhysicalFrom="0" PhysicalTo="360" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +11+12  Canaux 12-13 : Taille Tilt 16-bit -->
          <DMXChannel DMXBreak="1" Offset="12 13" Highlight="32767" Geometry="Body">
            <LogicalChannel Attribute="SizeTilt" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="SizeTilt" Name="Size Tilt" OriginalAttribute="" DMXFrom="0/1" Default="32767/1" PhysicalFrom="0" PhysicalTo="360" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +13+14  Canaux 14-15 : Rotation 16-bit (0-360°) -->
          <DMXChannel DMXBreak="1" Offset="14 15" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="Rotation" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Rotation" Name="Rotation" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="360" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +15+16  Canaux 16-17 : Position Pan 16-bit -->
          <DMXChannel DMXBreak="1" Offset="16 17" Highlight="32767" Geometry="Body">
            <LogicalChannel Attribute="Pan" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Pan" Name="Pan" OriginalAttribute="" DMXFrom="0/1" Default="32767/1" PhysicalFrom="-100" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +17+18  Canaux 18-19 : Position Tilt 16-bit -->
          <DMXChannel DMXBreak="1" Offset="18 19" Highlight="32767" Geometry="Body">
            <LogicalChannel Attribute="Tilt" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Tilt" Name="Tilt" OriginalAttribute="" DMXFrom="0/1" Default="32767/1" PhysicalFrom="-100" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- +19  Canal 20 : Mode / Forme — VALEURS LITTÉRALES (octet brut) -->
          <!-- 0..14 = formes ; 100..113 = même forme remplie par la vidéo (+22 = source) -->
          <DMXChannel DMXBreak="1" Offset="20" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="Gobo1" Snap="Yes" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Gobo1" Name="Mode" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="113" RealFade="0" RealAcceleration="0">
                <ChannelSet Name="0 Ellipse"        DMXFrom="0/1"  />
                <ChannelSet Name="1 Rectangle"      DMXFrom="1/1"  />
                <ChannelSet Name="2 Texte"          DMXFrom="2/1"  />
                <ChannelSet Name="3 Triangle"       DMXFrom="3/1"  />
                <ChannelSet Name="4 Pentagone"      DMXFrom="4/1"  />
                <ChannelSet Name="5 Hexagone"       DMXFrom="5/1"  />
                <ChannelSet Name="6 Losange"        DMXFrom="6/1"  />
                <ChannelSet Name="7 Octogone"       DMXFrom="7/1"  />
                <ChannelSet Name="8 Etoile"         DMXFrom="8/1"  />
                <ChannelSet Name="9 Croix"          DMXFrom="9/1"  />
                <ChannelSet Name="10 Fleche"        DMXFrom="10/1" />
                <ChannelSet Name="11 Coeur"         DMXFrom="11/1" />
                <ChannelSet Name="12 Segment"       DMXFrom="12/1" />
                <ChannelSet Name="13 Rafale"        DMXFrom="13/1" />
                <ChannelSet Name="14 VIDEO"         DMXFrom="14/1" />
                <ChannelSet Name="(15-99 = Rect.)"  DMXFrom="15/1" />
                <ChannelSet Name="100 Ellipse+vid"  DMXFrom="100/1"/>
                <ChannelSet Name="101 Rect+vid"     DMXFrom="101/1"/>
                <ChannelSet Name="102 Texte+vid"    DMXFrom="102/1"/>
                <ChannelSet Name="103 Triangle+vid" DMXFrom="103/1"/>
                <ChannelSet Name="104 Penta+vid"    DMXFrom="104/1"/>
                <ChannelSet Name="105 Hexa+vid"     DMXFrom="105/1"/>
                <ChannelSet Name="106 Losange+vid"  DMXFrom="106/1"/>
                <ChannelSet Name="107 Octo+vid"     DMXFrom="107/1"/>
                <ChannelSet Name="108 Etoile+vid"   DMXFrom="108/1"/>
                <ChannelSet Name="109 Croix+vid"    DMXFrom="109/1"/>
                <ChannelSet Name="110 Fleche+vid"   DMXFrom="110/1"/>
                <ChannelSet Name="111 Coeur+vid"    DMXFrom="111/1"/>
                <ChannelSet Name="112 Segment+vid"  DMXFrom="112/1"/>
                <ChannelSet Name="113 Rafale+vid"   DMXFrom="113/1"/>
              </ChannelFunction>
            </LogicalChannel>
          </DMXChannel>

          <!-- +20  Canal 21 : Enable (0=off, 1-255=on) -->
          <DMXChannel DMXBreak="1" Offset="21" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="Enable" Snap="Yes" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Enable" Name="Enable" OriginalAttribute="" DMXFrom="0/1" Default="255/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0">
                <ChannelSet Name="Off" DMXFrom="0/1"/>
                <ChannelSet Name="On"  DMXFrom="1/1"/>
              </ChannelFunction>
            </LogicalChannel>
          </DMXChannel>

          <!-- +21  Canal 22 : Blend mode individuel (0=global, sinon LUT) -->
          <DMXChannel DMXBreak="1" Offset="22" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BlendSpot" Snap="Yes" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BlendSpot" Name="Blend Spot" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="10" RealFade="0" RealAcceleration="0">
                <ChannelSet Name="0 Global"     DMXFrom="0/1"  />
                <ChannelSet Name="1 BLEND"      DMXFrom="1/1"  />
                <ChannelSet Name="2 ADD"        DMXFrom="29/1" />
                <ChannelSet Name="3 SUBTRACT"   DMXFrom="57/1" />
                <ChannelSet Name="4 DARKEST"    DMXFrom="85/1" />
                <ChannelSet Name="5 LIGHTEST"   DMXFrom="114/1"/>
                <ChannelSet Name="6 DIFFERENCE" DMXFrom="142/1"/>
                <ChannelSet Name="7 EXCLUSION"  DMXFrom="170/1"/>
                <ChannelSet Name="8 MULTIPLY"   DMXFrom="199/1"/>
                <ChannelSet Name="9 SCREEN"     DMXFrom="227/1"/>
                <ChannelSet Name="10 REPLACE"   DMXFrom="255/1"/>
              </ChannelFunction>
            </LogicalChannel>
          </DMXChannel>

          <!-- +22  Canal 23 : Police (mode Texte) OU sélecteur de vidéo (mode VIDEO / forme+vidéo) -->
          <DMXChannel DMXBreak="1" Offset="23" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="FontIndex" Snap="Yes" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="FontIndex" Name="Font / Video select" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

        </DMXChannels>
        <Relations/>
        <FTMacros/>
      </DMXMode>
    </DMXModes>

    <Protocols/>
    <FTPresets/>
  </FixtureType>
</GDTF>'''


def base_xml():
    """LuxCore Base — 32 canaux DMX (fond + blades + effets + PostFX)"""
    fid = str(uuid.uuid4())
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<GDTF DataVersion="1.2">
  <FixtureType
    Name="LuxCore Base"
    ShortName="LCBase"
    LongName="LuxCore DMX Engine - Base"
    Manufacturer="Martin Vert"
    Description="Canaux de base LuxCore (32) : fond RGB (1-3), 8 blades 16-bit (4-19), blend mode (20), blur (21-22), pixelate (23), sobel (24), rgb split (25), saturation (26-27), chromatic aberration (28), feedback (29), bloom seuil (30), bloom intensite (31), kaleidoscope (32)."
    FixtureTypeID="{fid}"
    RefFT=""
    Thumbnail="">

    <AttributeDefinitions>
      <Attributes>
        <Attribute Name="ColorAdd_R" Pretty="BG R"      Activation="ColorMix" Feature="Color.Color" PhysicalUnit="None" Color="0.64 0.33 0.21"/>
        <Attribute Name="ColorAdd_G" Pretty="BG G"      Activation="ColorMix" Feature="Color.Color" PhysicalUnit="None" Color="0.3 0.6 0.15"/>
        <Attribute Name="ColorAdd_B" Pretty="BG B"      Activation="ColorMix" Feature="Color.Color" PhysicalUnit="None" Color="0.15 0.06 0.79"/>
        <Attribute Name="BladeA1"    Pretty="A1 top-L"  Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BladeA2"    Pretty="A2 top-R"  Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BladeB1"    Pretty="B1 right-T" Activation="None"    Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BladeB2"    Pretty="B2 right-B" Activation="None"    Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BladeC1"    Pretty="C1 bot-L"  Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BladeC2"    Pretty="C2 bot-R"  Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BladeD1"    Pretty="D1 left-T" Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BladeD2"    Pretty="D2 left-B" Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BlendMode"  Pretty="Blend"     Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BlurSize"   Pretty="Blur Size" Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BlurSigma"  Pretty="Blur Sigma" Activation="None"    Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="Pixelate"   Pretty="Pixelate"  Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="Sobel"      Pretty="Sobel"     Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="RGBSplit"   Pretty="RGB Split" Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="SatA"       Pretty="Sat A"     Activation="None"     Feature="Color.Color" PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="SatB"       Pretty="Vib B"     Activation="None"     Feature="Color.Color" PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="Chromatic"  Pretty="Chromatic" Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="Feedback"   Pretty="Feedback"  Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BloomThr"   Pretty="Bloom Thr" Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="BloomAmt"   Pretty="Bloom Amt" Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
        <Attribute Name="Kaleido"    Pretty="Kaleido"   Activation="None"     Feature="Beam.Beam"   PhysicalUnit="None" Color="0.32 0.32 0.32"/>
      </Attributes>
      <ActivationGroups>
        <ActivationGroup Name="ColorMix"/>
      </ActivationGroups>
      <Features>
        <FeatureGroup Name="Color" Pretty="Color"><Feature Name="Color"/></FeatureGroup>
        <FeatureGroup Name="Beam"  Pretty="Beam"> <Feature Name="Beam"/> </FeatureGroup>
      </Features>
    </AttributeDefinitions>

    <Wheels/>
    <PhysicalDescriptions/>
    <Models/>
    <Geometries>
      <Geometry Name="Body" Model="" Position="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
    </Geometries>

    <DMXModes>
      <DMXMode Name="32ch" Geometry="Body">
        <DMXChannels>

          <!-- Canaux 1-3 : RGB fond -->
          <DMXChannel DMXBreak="1" Offset="1" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="ColorAdd_R" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="ColorAdd_R" Name="BG Red" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>
          <DMXChannel DMXBreak="1" Offset="2" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="ColorAdd_G" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="ColorAdd_G" Name="BG Green" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>
          <DMXChannel DMXBreak="1" Offset="3" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="ColorAdd_B" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="ColorAdd_B" Name="BG Blue" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canaux 4-5 : Blade A1 16-bit (haut gauche) -->
          <DMXChannel DMXBreak="1" Offset="4 5" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BladeA1" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BladeA1" Name="Blade A1 top-left" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canaux 6-7 : Blade A2 16-bit (haut droite) -->
          <DMXChannel DMXBreak="1" Offset="6 7" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BladeA2" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BladeA2" Name="Blade A2 top-right" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canaux 8-9 : Blade B1 16-bit (droite haut) -->
          <DMXChannel DMXBreak="1" Offset="8 9" Highlight="65535" Geometry="Body">
            <LogicalChannel Attribute="BladeB1" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BladeB1" Name="Blade B1 right-top" OriginalAttribute="" DMXFrom="0/1" Default="65535/1" PhysicalFrom="0" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canaux 10-11 : Blade B2 16-bit (droite bas) -->
          <DMXChannel DMXBreak="1" Offset="10 11" Highlight="65535" Geometry="Body">
            <LogicalChannel Attribute="BladeB2" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BladeB2" Name="Blade B2 right-bottom" OriginalAttribute="" DMXFrom="0/1" Default="65535/1" PhysicalFrom="0" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canaux 12-13 : Blade C1 16-bit (bas gauche) -->
          <DMXChannel DMXBreak="1" Offset="12 13" Highlight="65535" Geometry="Body">
            <LogicalChannel Attribute="BladeC1" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BladeC1" Name="Blade C1 bottom-left" OriginalAttribute="" DMXFrom="0/1" Default="65535/1" PhysicalFrom="0" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canaux 14-15 : Blade C2 16-bit (bas droite) -->
          <DMXChannel DMXBreak="1" Offset="14 15" Highlight="65535" Geometry="Body">
            <LogicalChannel Attribute="BladeC2" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BladeC2" Name="Blade C2 bottom-right" OriginalAttribute="" DMXFrom="0/1" Default="65535/1" PhysicalFrom="0" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canaux 16-17 : Blade D1 16-bit (gauche haut) -->
          <DMXChannel DMXBreak="1" Offset="16 17" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BladeD1" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BladeD1" Name="Blade D1 left-top" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canaux 18-19 : Blade D2 16-bit (gauche bas) -->
          <DMXChannel DMXBreak="1" Offset="18 19" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BladeD2" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BladeD2" Name="Blade D2 left-bottom" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="100" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 20 : Blend mode -->
          <DMXChannel DMXBreak="1" Offset="20" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BlendMode" Snap="Yes" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BlendMode" Name="Blend Mode" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0">
                <ChannelSet Name="BLEND"      DMXFrom="0/1"  />
                <ChannelSet Name="ADD"        DMXFrom="29/1" />
                <ChannelSet Name="SUBTRACT"   DMXFrom="57/1" />
                <ChannelSet Name="DARKEST"    DMXFrom="85/1" />
                <ChannelSet Name="LIGHTEST"   DMXFrom="114/1"/>
                <ChannelSet Name="DIFFERENCE" DMXFrom="142/1"/>
                <ChannelSet Name="EXCLUSION"  DMXFrom="170/1"/>
                <ChannelSet Name="MULTIPLY"   DMXFrom="199/1"/>
                <ChannelSet Name="SCREEN"     DMXFrom="227/1"/>
                <ChannelSet Name="REPLACE"    DMXFrom="255/1"/>
              </ChannelFunction>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 21 : Blur size -->
          <DMXChannel DMXBreak="1" Offset="21" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BlurSize" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BlurSize" Name="Blur Size" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 22 : Blur sigma -->
          <DMXChannel DMXBreak="1" Offset="22" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BlurSigma" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BlurSigma" Name="Blur Sigma" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 23 : Pixelate (255=fin, 20=gros) -->
          <DMXChannel DMXBreak="1" Offset="23" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="Pixelate" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Pixelate" Name="Pixelate" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="255" PhysicalTo="20" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 24 : Sobel (bistable >128) -->
          <DMXChannel DMXBreak="1" Offset="24" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="Sobel" Snap="Yes" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Sobel" Name="Sobel" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0">
                <ChannelSet Name="Off" DMXFrom="0/1"  />
                <ChannelSet Name="On"  DMXFrom="128/1"/>
              </ChannelFunction>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 25 : RGB Split -->
          <DMXChannel DMXBreak="1" Offset="25" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="RGBSplit" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="RGBSplit" Name="RGB Split" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 26 : Saturation A -->
          <DMXChannel DMXBreak="1" Offset="26" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="SatA" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="SatA" Name="Saturation A" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 27 : Vibrance B -->
          <DMXChannel DMXBreak="1" Offset="27" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="SatB" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="SatB" Name="Vibrance B" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 28 : Chromatic aberration (bistable >128) -->
          <DMXChannel DMXBreak="1" Offset="28" Highlight="255" Geometry="Body">
            <LogicalChannel Attribute="Chromatic" Snap="Yes" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Chromatic" Name="Chromatic Aberration" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="1" RealFade="0" RealAcceleration="0">
                <ChannelSet Name="Off" DMXFrom="0/1"  />
                <ChannelSet Name="On"  DMXFrom="128/1"/>
              </ChannelFunction>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 29 : Feedback / trails (0=off, sinon persistance) -->
          <DMXChannel DMXBreak="1" Offset="29" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="Feedback" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Feedback" Name="Feedback" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 30 : Bloom seuil (luminance du glow) -->
          <DMXChannel DMXBreak="1" Offset="30" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BloomThr" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BloomThr" Name="Bloom Threshold" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 31 : Bloom intensité (0=off, sinon force du halo) -->
          <DMXChannel DMXBreak="1" Offset="31" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="BloomAmt" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="BloomAmt" Name="Bloom Amount" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0"/>
            </LogicalChannel>
          </DMXChannel>

          <!-- Canal 32 : Kaléidoscope (0/1=off, 2-255 = nb de branches) -->
          <DMXChannel DMXBreak="1" Offset="32" Highlight="0" Geometry="Body">
            <LogicalChannel Attribute="Kaleido" Snap="No" Master="None" MibFade="0" DMXChangeTimeLimit="0">
              <ChannelFunction Attribute="Kaleido" Name="Kaleidoscope" OriginalAttribute="" DMXFrom="0/1" Default="0/1" PhysicalFrom="0" PhysicalTo="255" RealFade="0" RealAcceleration="0">
                <ChannelSet Name="Off"       DMXFrom="0/1"/>
                <ChannelSet Name="Branches"  DMXFrom="2/1"/>
              </ChannelFunction>
            </LogicalChannel>
          </DMXChannel>

        </DMXChannels>
        <Relations/>
        <FTMacros/>
      </DMXMode>
    </DMXModes>

    <Protocols/>
    <FTPresets/>
  </FixtureType>
</GDTF>'''


def write_gdtf(xml, path):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('description.xml', xml)
    print(f"OK  {path}")


if __name__ == '__main__':
    out = os.path.dirname(os.path.abspath(__file__))

    write_gdtf(spot_xml(), os.path.join(out, 'LuxCore_Spot_23ch.gdtf'))
    write_gdtf(base_xml(), os.path.join(out, 'LuxCore_Base_32ch.gdtf'))

    print()
    print("Patch (adresses 1-based) :")
    print("  LuxCore Base  → adresse 1")
    print("  LuxCore Spot0 → adresse 33  (= 32 + 0×23 + 1)")
    print("  LuxCore Spot1 → adresse 56  (= 32 + 1×23 + 1)")
    print("  LuxCore SpotN → adresse 32 + N×23 + 1")
    print()
    print("Blend mode — valeurs DMX exactes :")
    print("  BLEND=0  ADD=29  SUBTRACT=57  DARKEST=85  LIGHTEST=114")
    print("  DIFFERENCE=142  EXCLUSION=170  MULTIPLY=199  SCREEN=227  REPLACE=255")
