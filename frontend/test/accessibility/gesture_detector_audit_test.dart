import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// Scans lib/ for bare GestureDetector usage. Any GestureDetector in
/// user-facing code must be explicitly approved in the allowlist below
/// with a reason (e.g., "backdrop dismiss overlay, not user-facing").
///
/// If this test fails, replace GestureDetector with InkWell + Semantics.
void main() {
  test('no unapproved GestureDetector usage in lib/', () {
    // Allowlist: file:line patterns where GestureDetector is intentional.
    // Each entry must have a comment explaining why it's acceptable.
    final allowlist = <String>{
      // Backdrop dismiss overlay — not a user-facing interactive element
      'lib/screens/calendar/event_detail_panel.dart',
      // Phone tooltip overlay dismiss — not a user-facing interactive element
      'lib/screens/calendar/rsvp_section.dart',
      // Feedback overlay backdrop dismiss — not a user-facing interactive element
      'lib/widgets/feedback_button.dart',
      // Horizontal swipe navigation — gesture-only, not a tappable element
      'lib/screens/calendar/month_view.dart',
      'lib/screens/calendar/day_view.dart',
      'lib/screens/calendar/week_view.dart',
    };

    final libDir = Directory('lib');
    final violations = <String>[];

    for (final file in libDir.listSync(recursive: true)) {
      if (file is! File || !file.path.endsWith('.dart')) continue;

      // Skip generated files
      if (file.path.endsWith('.g.dart') ||
          file.path.endsWith('.freezed.dart')) {
        continue;
      }

      // Normalize to a path starting with 'lib/' regardless of working dir.
      final libIndex = file.path.indexOf('lib/');
      final normalizedPath =
          libIndex >= 0 ? file.path.substring(libIndex) : file.path;

      if (allowlist.any((allowed) => normalizedPath.contains(allowed))) {
        continue;
      }

      final content = file.readAsStringSync();
      if (content.contains('GestureDetector')) {
        violations.add(normalizedPath);
      }
    }

    expect(
      violations,
      isEmpty,
      reason:
          'Found GestureDetector usage in: ${violations.join(', ')}. '
          'GestureDetector does not create semantic nodes — screen readers '
          'skip it. Use InkWell + Semantics instead, or add to the allowlist '
          'with justification if not user-facing.',
    );
  });
}
