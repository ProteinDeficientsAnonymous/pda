import 'dart:async';

import 'package:flutter/material.dart';

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

  void initAutosave({
    required TextEditingController controller,
    required Future<void> Function(String) onSave,
    Duration delay = const Duration(seconds: 2),
  }) {
    _autosaveController = controller;
    _saveFn = onSave;
    _autosaveController.addListener(() => _onChanged(delay));
  }

  void _onChanged(Duration delay) {
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
    } catch (_) {
      if (!mounted) return;
      setState(() => _autosaveStatus = AutosaveStatus.error);
    }
  }

  void disposeAutosave() {
    _debounce?.cancel();
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
        Colors.green,
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
