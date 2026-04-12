import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/screens/calendar/event_colors.dart';

void main() {
  group('eventColors', () {
    test('returns blue tones for official events in light mode', () {
      final (bg, fg) = eventColors(EventType.official, Brightness.light);
      expect(bg, const Color(0xFFD0E8FF));
      expect(fg, const Color(0xFF1A3A5C));
    });

    test('returns green tones for community events in light mode', () {
      final (bg, fg) = eventColors(EventType.community, Brightness.light);
      expect(bg, const Color(0xFFD4F0D4));
      expect(fg, const Color(0xFF1A3D1A));
    });

    test('returns blue tones for official events in dark mode', () {
      final (bg, fg) = eventColors(EventType.official, Brightness.dark);
      expect(bg, const Color(0xFF1A3050));
      expect(fg, const Color(0xFFB0D4FF));
    });

    test('returns green tones for community events in dark mode', () {
      final (bg, fg) = eventColors(EventType.community, Brightness.dark);
      expect(bg, const Color(0xFF1A3020));
      expect(fg, const Color(0xFFA8E0A8));
    });

    test('official and community have different colors', () {
      final official = eventColors(EventType.official, Brightness.light);
      final community = eventColors(EventType.community, Brightness.light);
      expect(official.$1, isNot(equals(community.$1)));
    });
  });
}
