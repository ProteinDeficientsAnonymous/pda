import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/widgets/photo_crop_dialog.dart';

// Minimal 1×1 red PNG (67 bytes).
final Uint8List _kMinimalPng = Uint8List.fromList([
  0x89,
  0x50,
  0x4E,
  0x47,
  0x0D,
  0x0A,
  0x1A,
  0x0A,
  0x00,
  0x00,
  0x00,
  0x0D,
  0x49,
  0x48,
  0x44,
  0x52,
  0x00,
  0x00,
  0x00,
  0x01,
  0x00,
  0x00,
  0x00,
  0x01,
  0x08,
  0x02,
  0x00,
  0x00,
  0x00,
  0x90,
  0x77,
  0x53,
  0xDE,
  0x00,
  0x00,
  0x00,
  0x0C,
  0x49,
  0x44,
  0x41,
  0x54,
  0x08,
  0xD7,
  0x63,
  0xF8,
  0xCF,
  0xC0,
  0x00,
  0x00,
  0x00,
  0x02,
  0x00,
  0x01,
  0xE2,
  0x21,
  0xBC,
  0x33,
  0x00,
  0x00,
  0x00,
  0x00,
  0x49,
  0x45,
  0x4E,
  0x44,
  0xAE,
  0x42,
  0x60,
  0x82,
]);

void main() {
  group('photo crop dialog accessibility', () {
    testWidgets('meets labeled tap target guideline', (tester) async {
      tester.view.physicalSize = const Size(800, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder:
                  (ctx) => TextButton(
                    onPressed:
                        () => showPhotoCropDialog(
                          context: ctx,
                          imageBytes: _kMinimalPng,
                        ),
                    child: const Text('open'),
                  ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pump();

      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      handle.dispose();
    });

    testWidgets('meets android tap target guideline', (tester) async {
      tester.view.physicalSize = const Size(800, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      final handle = tester.ensureSemantics();
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder:
                  (ctx) => TextButton(
                    onPressed:
                        () => showPhotoCropDialog(
                          context: ctx,
                          imageBytes: _kMinimalPng,
                        ),
                    child: const Text('open'),
                  ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pump();

      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      handle.dispose();
    });
  });
}
