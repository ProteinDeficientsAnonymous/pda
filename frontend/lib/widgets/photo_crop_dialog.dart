import 'dart:typed_data';

import 'package:crop_your_image/crop_your_image.dart';
import 'package:flutter/material.dart';

/// Shows a square crop dialog for profile photos.
///
/// Returns the cropped [Uint8List], or `null` if the user cancels.
Future<Uint8List?> showPhotoCropDialog({
  required BuildContext context,
  required Uint8List imageBytes,
}) {
  return showDialog<Uint8List>(
    context: context,
    builder: (_) => _PhotoCropDialog(imageBytes: imageBytes),
  );
}

class _PhotoCropDialog extends StatefulWidget {
  const _PhotoCropDialog({required this.imageBytes});

  final Uint8List imageBytes;

  @override
  State<_PhotoCropDialog> createState() => _PhotoCropDialogState();
}

class _PhotoCropDialogState extends State<_PhotoCropDialog> {
  final _controller = CropController();
  bool _cropping = false;

  void _onDone() {
    setState(() => _cropping = true);
    _controller.cropCircle();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('adjust photo'),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      content: SizedBox(
        width: 360,
        height: 360,
        child: Semantics(
          label: 'crop and adjust photo',
          child: Crop(
            image: widget.imageBytes,
            controller: _controller,
            withCircleUi: true,
            aspectRatio: 1,
            onCropped: (croppedBytes) {
              if (mounted) Navigator.of(context).pop(croppedBytes);
            },
            onStatusChanged: (status) {
              if (status != CropStatus.cropping && mounted) {
                setState(() => _cropping = false);
              }
            },
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _cropping ? null : () => Navigator.of(context).pop(),
          child: const Text('cancel'),
        ),
        FilledButton(
          onPressed: _cropping ? null : _onDone,
          child: _cropping
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('done'),
        ),
      ],
    );
  }
}
