import 'package:flutter/material.dart';

// A fixed palette of pleasant pastel background + foreground pairs
const List<(Color, Color)> _kEventPalette = [
  (Color(0xFFD0E8FF), Color(0xFF1A3A5C)), // blue
  (Color(0xFFD4F0D4), Color(0xFF1A3D1A)), // green
  (Color(0xFFFFE5CC), Color(0xFF5C3000)), // orange
  (Color(0xFFF5D0F5), Color(0xFF4A0A4A)), // purple
  (Color(0xFFFFD6D6), Color(0xFF5C1A1A)), // red
  (Color(0xFFD6F5F0), Color(0xFF0A3D35)), // teal
  (Color(0xFFFFF3CC), Color(0xFF5C4500)), // yellow
  (Color(0xFFE8D6FF), Color(0xFF2D0A5C)), // violet
];

/// Returns (backgroundColor, foregroundColor) for an event based on its id.
(Color, Color) eventColors(String eventId) {
  final index =
      eventId.codeUnits.fold(0, (sum, c) => sum + c) % _kEventPalette.length;
  return _kEventPalette[index];
}
