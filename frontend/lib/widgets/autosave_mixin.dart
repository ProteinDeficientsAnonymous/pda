import 'dart:async';

import 'package:flutter/material.dart';
import 'package:logging/logging.dart';

final _log = Logger('Autosave');

enum AutosaveStatus { idle, saving, saved, error }

/// Mixin that adds debounced autosave to any [State].
///
/// Usage:
/// 1. `with AutosaveMixin<MyWidget> on State<MyWidget>`
/// 2. Call [initAutosave] in [initState], passing the controller and save fn.
/// 3. Call [disposeAutosave] in [dispose].
/// 4. Use [autosaveStatus] in [build] to show a status indicator.
mixin AutosaveMixin<T extends StatefulWidget> on State<T> {
  Timer? _debounce;
  AutosaveStatus _autosaveStatus = AutosaveStatus.idle;
  AutosaveStatus get autosaveStatus => _autosaveStatus;

  late Future<void> Function(String) _saveFn;
  late TextEditingController _autosaveController;
  bool _ownsController = false;

  void initAutosave({
    required TextEditingController controller,
    required Future<void> Function(String) onSave,
    Duration delay = const Duration(seconds: 2),
  }) {
    _autosaveController = controller;
    _saveFn = onSave;
    _autosaveController.addListener(() => _scheduleAutosave(delay));
  }

  /// Variant for editors that don't use [TextEditingController] (e.g. Quill).
  /// Call [triggerAutosave] with the latest content string from your [onChanged]
  /// callback to debounce and save.
  void initAutosaveCallback({
    required Future<void> Function(String) onSave,
    Duration delay = const Duration(seconds: 2),
  }) {
    _saveFn = onSave;
    // Internal controller to hold the latest content string.
    _autosaveController = TextEditingController();
    _ownsController = true;
  }

  /// Call this from your editor's onChanged callback with the latest content.
  void triggerAutosave(
    String content, {
    Duration delay = const Duration(seconds: 2),
  }) {
    _autosaveController.text = content;
    _scheduleAutosave(delay);
  }

  void _scheduleAutosave(Duration delay) {
    _debounce?.cancel();
    _debounce = Timer(delay, _autosave);
  }

  Future<void> _autosave() async {
    if (!mounted) return;
    setState(() => _autosaveStatus = AutosaveStatus.saving);
    try {
      await _saveFn(_autosaveController.text);
      if (!mounted) return;
      setState(() => _autosaveStatus = AutosaveStatus.saved);
      // Reset to idle after 2s so the indicator fades away
      Future.delayed(const Duration(seconds: 2), () {
        if (mounted) setState(() => _autosaveStatus = AutosaveStatus.idle);
      });
    } catch (e, st) {
      _log.warning('autosave failed', e, st);
      if (!mounted) return;
      setState(() => _autosaveStatus = AutosaveStatus.error);
    }
  }

  void disposeAutosave() {
    _debounce?.cancel();
    if (_ownsController) _autosaveController.dispose();
  }
}

/// Small status chip shown near the editor toolbar.
class AutosaveIndicator extends StatelessWidget {
  const AutosaveIndicator({super.key, required this.status});

  final AutosaveStatus status;

  @override
  Widget build(BuildContext context) {
    if (status == AutosaveStatus.idle) return const SizedBox.shrink();

    final (icon, label, color) = switch (status) {
      AutosaveStatus.saving => (
        Icons.sync,
        'Saving…',
        Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      AutosaveStatus.saved => (
        Icons.check_circle_outline,
        'Saved',
        Theme.of(context).colorScheme.primary,
      ),
      AutosaveStatus.error => (
        Icons.error_outline,
        'Save failed',
        Theme.of(context).colorScheme.error,
      ),
      AutosaveStatus.idle => (Icons.sync, '', Colors.transparent),
    };

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 12, color: color)),
      ],
    );
  }
}
