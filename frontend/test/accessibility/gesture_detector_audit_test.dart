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

      final relativePath =
          file.path.startsWith('lib/')
              ? file.path
              : file.path.split('lib/').last;
      final normalizedPath = 'lib/$relativePath'.replaceAll('//', '/');

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
