import 'dart:async';
import 'dart:typed_data';

import 'package:crop_your_image/crop_your_image.dart' deferred as crop;
import 'package:flutter/material.dart';
import 'package:logging/logging.dart';

final _log = Logger('PhotoCropDialog');

enum PhotoCropMode { circle, rectangle }

/// Shows a crop dialog for photos.
///
/// Use [mode] to select circle (profile photos) or rectangle (event photos).
/// For rectangle mode, omit [aspectRatio] to allow free-form cropping,
/// or pass a value (e.g. `1` for square) to lock the ratio.
///
/// [maxHeightRatio] caps how tall the crop can be relative to its width
/// (e.g. `5/4` means the crop can be at most 25% taller than it is wide).
/// Only applies when [aspectRatio] is null (free-form mode).
///
/// Returns the cropped [Uint8List], or `null` if the user cancels.
Future<Uint8List?> showPhotoCropDialog({
  required BuildContext context,
  required Uint8List imageBytes,
  PhotoCropMode mode = PhotoCropMode.circle,
  double? aspectRatio,
  double? maxHeightRatio,
}) async {
  await crop.loadLibrary();
  if (!context.mounted) return null;
  return showDialog<Uint8List>(
    context: context,
    builder: (_) => _PhotoCropDialog(
      imageBytes: imageBytes,
      mode: mode,
      aspectRatio: aspectRatio,
      maxHeightRatio: maxHeightRatio,
    ),
  );
}

class _PhotoCropDialog extends StatefulWidget {
  const _PhotoCropDialog({
    required this.imageBytes,
    required this.mode,
    this.aspectRatio,
    this.maxHeightRatio,
  });

  final Uint8List imageBytes;
  final PhotoCropMode mode;
  final double? aspectRatio;

  /// When set, prevents the crop rect from exceeding this height:width ratio.
  final double? maxHeightRatio;

  @override
  State<_PhotoCropDialog> createState() => _PhotoCropDialogState();
}

class _PhotoCropDialogState extends State<_PhotoCropDialog> {
  // ignore: prefer_typing_uninitialized_variables
  late final dynamic _controller;
  bool _cropping = false;
  bool _clamping = false;

  @override
  void initState() {
    super.initState();
    _controller = crop.CropController();
  }

  void _onDone() {
    _log.info('_onDone called — _cropping=$_cropping mode=${widget.mode}');
    setState(() => _cropping = true);
    if (widget.mode == PhotoCropMode.circle) {
      _controller.cropCircle();
    } else {
      _controller.crop();
    }
    _log.info('_onDone: crop() called on controller');
  }

  void _onMoved(dynamic rect) {
    final maxRatio = widget.maxHeightRatio;
    if (maxRatio == null || widget.aspectRatio != null) return;
    if (rect.width <= 0 || _clamping) return;

    final currentRatio = rect.height / rect.width;
    _log.fine(
      '_onMoved: w=${rect.width.toStringAsFixed(1)} h=${rect.height.toStringAsFixed(1)} ratio=${currentRatio.toStringAsFixed(3)} max=$maxRatio',
    );

    if (currentRatio > maxRatio) {
      _log.info('_onMoved: clamping rect (ratio $currentRatio > $maxRatio)');
      _clamping = true;
      scheduleMicrotask(() {
        if (mounted) {
          _controller.cropRect = Rect.fromLTWH(
            rect.left,
            rect.top,
            rect.width,
            rect.width * maxRatio,
          );
        }
        _clamping = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isCircle = widget.mode == PhotoCropMode.circle;
    final title = isCircle ? 'crop profile photo' : 'crop event photo';
    final cropHeight = isCircle ? 360.0 : 400.0;

    return AlertDialog(
      title: Text(title),
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 360,
            height: cropHeight,
            child: Semantics(
              label: 'crop area — pinch to zoom, drag to reposition',
              child: crop.Crop(
                image: widget.imageBytes,
                controller: _controller,
                withCircleUi: isCircle,
                aspectRatio: widget.aspectRatio,
                onMoved: _onMoved,
                onCropped: (croppedBytes) {
                  _log.info(
                    'onCropped: ${croppedBytes.length} bytes, mounted=$mounted',
                  );
                  if (mounted) Navigator.of(context).pop(croppedBytes);
                },
                onStatusChanged: (status) {
                  _log.info(
                    'onStatusChanged: $status mounted=$mounted _cropping=$_cropping',
                  );
                  if (status != crop.CropStatus.cropping &&
                      mounted &&
                      !_cropping) {
                    setState(() {});
                  }
                },
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'pinch to zoom, drag to reposition',
            style: TextStyle(fontSize: 12, color: cs.onSurfaceVariant),
          ),
        ],
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
              : const Text('save crop'),
        ),
      ],
    );
  }
}
