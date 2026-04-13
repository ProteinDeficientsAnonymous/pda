import 'package:flutter/material.dart';
import 'package:pda/config/constants.dart';

// Official (blue)
const _kOfficialLight = (Color(0xFFD0E8FF), Color(0xFF1A3A5C));
const _kOfficialDark = (Color(0xFF1A3050), Color(0xFFB0D4FF));

// Public community (green)
const _kPublicLight = (Color(0xFFD4F0D4), Color(0xFF1A3D1A));
const _kPublicDark = (Color(0xFF1A3020), Color(0xFFA8E0A8));

// Members only (orange)
const _kMembersOnlyLight = (Color(0xFFFFE5CC), Color(0xFF5C3000));
const _kMembersOnlyDark = (Color(0xFF3D2210), Color(0xFFFFD6A8));

// Invite only (purple)
const _kInviteOnlyLight = (Color(0xFFF5D0F5), Color(0xFF4A0A4A));
const _kInviteOnlyDark = (Color(0xFF301030), Color(0xFFE8B0E8));

/// Returns (backgroundColor, foregroundColor) for an event based on its
/// type and visibility.
///
/// The four visibility choices map to distinct colors:
/// - Official PDA event (type=official) → blue
/// - Public community event → green
/// - Members only → orange
/// - Invite only → purple
(Color, Color) eventColors(
  String eventType,
  String visibility,
  Brightness brightness,
) {
  if (eventType == EventType.official) {
    return brightness == Brightness.dark ? _kOfficialDark : _kOfficialLight;
  }
  if (visibility == PageVisibility.inviteOnly) {
    return brightness == Brightness.dark ? _kInviteOnlyDark : _kInviteOnlyLight;
  }
  if (visibility == PageVisibility.membersOnly) {
    return brightness == Brightness.dark
        ? _kMembersOnlyDark
        : _kMembersOnlyLight;
  }
  return brightness == Brightness.dark ? _kPublicDark : _kPublicLight;
}
