import 'package:flutter/material.dart';

// Light mode: pleasant pastel background + dark foreground pairs
const List<(Color, Color)> _kEventPaletteLight = [
  (Color(0xFFD0E8FF), Color(0xFF1A3A5C)), // blue
  (Color(0xFFD4F0D4), Color(0xFF1A3D1A)), // green
  (Color(0xFFFFE5CC), Color(0xFF5C3000)), // orange
  (Color(0xFFF5D0F5), Color(0xFF4A0A4A)), // purple
  (Color(0xFFFFD6D6), Color(0xFF5C1A1A)), // red
  (Color(0xFFD6F5F0), Color(0xFF0A3D35)), // teal
  (Color(0xFFFFF3CC), Color(0xFF5C4500)), // yellow
  (Color(0xFFE8D6FF), Color(0xFF2D0A5C)), // violet
];

// Dark mode: deep muted background + light foreground pairs
const List<(Color, Color)> _kEventPaletteDark = [
  (Color(0xFF1A3050), Color(0xFFB0D4FF)), // blue
  (Color(0xFF1A3020), Color(0xFFA8E0A8)), // green
  (Color(0xFF3D2210), Color(0xFFFFD6A8)), // orange
  (Color(0xFF301030), Color(0xFFE8B0E8)), // purple
  (Color(0xFF3D1818), Color(0xFFFFB0B0)), // red
  (Color(0xFF103028), Color(0xFFA8E8D8)), // teal
  (Color(0xFF3D3010), Color(0xFFFFE8A0)), // yellow
  (Color(0xFF201040), Color(0xFFD0B8FF)), // violet
];

/// Returns (backgroundColor, foregroundColor) for an event based on its id.
(Color, Color) eventColors(String eventId, Brightness brightness) {
  final palette = brightness == Brightness.dark
      ? _kEventPaletteDark
      : _kEventPaletteLight;
  final index = eventId.codeUnits.fold(0, (sum, c) => sum + c) % palette.length;
  return palette[index];
}
