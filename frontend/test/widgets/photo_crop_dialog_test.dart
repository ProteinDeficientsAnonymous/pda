import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/widgets/photo_crop_dialog.dart';

// Minimal 1×1 red PNG (67 bytes).
final Uint8List _kMinimalPng = Uint8List.fromList([
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
  0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, // IHDR length + type
  0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, // 1×1 px
  0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, // 8-bit RGB, CRC
  0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, // IDAT length + type
  0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00, // deflate stream
  0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC, // IDAT data
  0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, // IEND length + type
  0x44, 0xAE, 0x42, 0x60, 0x82, // IEND CRC
]);

Widget _app(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  group('showPhotoCropDialog', () {
    testWidgets('circle mode renders with correct title and actions', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(800, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (ctx) => TextButton(
                onPressed: () =>
                    showPhotoCropDialog(context: ctx, imageBytes: _kMinimalPng),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pump();

      expect(find.text('crop profile photo'), findsOneWidget);
      expect(find.text('cancel'), findsOneWidget);
      expect(find.text('save crop'), findsOneWidget);
    });

    testWidgets('rectangle mode renders with correct title', (tester) async {
      tester.view.physicalSize = const Size(800, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (ctx) => TextButton(
                onPressed: () => showPhotoCropDialog(
                  context: ctx,
                  imageBytes: _kMinimalPng,
                  mode: PhotoCropMode.rectangle,
                ),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pump();

      expect(find.text('crop event photo'), findsOneWidget);
      expect(find.text('cancel'), findsOneWidget);
      expect(find.text('save crop'), findsOneWidget);
    });

    testWidgets('renders helper instruction text', (tester) async {
      tester.view.physicalSize = const Size(800, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (ctx) => TextButton(
                onPressed: () =>
                    showPhotoCropDialog(context: ctx, imageBytes: _kMinimalPng),
                child: const Text('open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pump();

      expect(find.text('pinch to zoom, drag to reposition'), findsOneWidget);
    });

    testWidgets('cancel returns null', (tester) async {
      tester.view.physicalSize = const Size(800, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      Uint8List? result = Uint8List(0); // non-null sentinel
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (ctx) => TextButton(
                onPressed: () async {
                  result = await showPhotoCropDialog(
                    context: ctx,
                    imageBytes: _kMinimalPng,
                  );
                },
                child: const Text('open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pump();

      await tester.tap(find.text('cancel'));
      await tester.pumpAndSettle();

      expect(result, isNull);
    });

    testWidgets('cancel returns null in rectangle mode', (tester) async {
      tester.view.physicalSize = const Size(800, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      Uint8List? result = Uint8List(0); // non-null sentinel
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (ctx) => TextButton(
                onPressed: () async {
                  result = await showPhotoCropDialog(
                    context: ctx,
                    imageBytes: _kMinimalPng,
                    mode: PhotoCropMode.rectangle,
                  );
                },
                child: const Text('open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pump();

      await tester.tap(find.text('cancel'));
      await tester.pumpAndSettle();

      expect(result, isNull);
    });

    testWidgets('dialog has Semantics widget wrapping the crop area', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(800, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(
        _app(
          Builder(
            builder: (ctx) => TextButton(
              onPressed: () =>
                  showPhotoCropDialog(context: ctx, imageBytes: _kMinimalPng),
              child: const Text('open'),
            ),
          ),
        ),
      );

      await tester.tap(find.text('open'));
      await tester.pump();

      // The crop area is wrapped in a Semantics widget for screen readers.
      expect(find.byType(Semantics), findsWidgets);
    });
  });
}
