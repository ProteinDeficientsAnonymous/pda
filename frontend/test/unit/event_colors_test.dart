import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/screens/calendar/event_colors.dart';

void main() {
  group('eventColors', () {
    test('returns consistent colors for same event id', () {
      final (bg1, fg1) = eventColors('event-123', Brightness.light);
      final (bg2, fg2) = eventColors('event-123', Brightness.light);
      expect(bg1, bg2);
      expect(fg1, fg2);
    });

    test('returns different colors for light vs dark brightness', () {
      final (bgLight, _) = eventColors('event-123', Brightness.light);
      final (bgDark, _) = eventColors('event-123', Brightness.dark);
      expect(bgLight, isNot(equals(bgDark)));
    });

    test('light palette has lighter backgrounds', () {
      final (bg, _) = eventColors('event-123', Brightness.light);
      // Light palette backgrounds should have high luminance (pastel)
      final hsl = HSLColor.fromColor(bg);
      expect(hsl.lightness, greaterThan(0.7));
    });

    test('dark palette has darker backgrounds', () {
      final (bg, _) = eventColors('event-123', Brightness.dark);
      // Dark palette backgrounds should have low luminance
      final hsl = HSLColor.fromColor(bg);
      expect(hsl.lightness, lessThan(0.3));
    });

    test('different event ids produce different color indices', () {
      final colors = <(Color, Color)>{};
      for (final id in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']) {
        colors.add(eventColors(id, Brightness.light));
      }
      // With 8 palette entries and 8 different single-char ids,
      // we should get at least 2 distinct colors
      expect(colors.length, greaterThanOrEqualTo(2));
    });
  });
}
