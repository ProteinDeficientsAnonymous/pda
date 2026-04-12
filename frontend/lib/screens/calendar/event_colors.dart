import 'package:flutter/material.dart';
import 'package:pda/config/constants.dart';

const _kOfficialLight = (Color(0xFFD0E8FF), Color(0xFF1A3A5C));
const _kCommunityLight = (Color(0xFFD4F0D4), Color(0xFF1A3D1A));
const _kOfficialDark = (Color(0xFF1A3050), Color(0xFFB0D4FF));
const _kCommunityDark = (Color(0xFF1A3020), Color(0xFFA8E0A8));

/// Returns (backgroundColor, foregroundColor) for an event based on its type.
(Color, Color) eventColors(String eventType, Brightness brightness) {
  final isOfficial = eventType == EventType.official;
  if (brightness == Brightness.dark) {
    return isOfficial ? _kOfficialDark : _kCommunityDark;
  }
  return isOfficial ? _kOfficialLight : _kCommunityLight;
}
