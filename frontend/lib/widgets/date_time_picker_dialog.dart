import 'package:flutter/material.dart';

import 'date_time_picker.dart';

/// Shows a combined date+time picker in an [AlertDialog].
///
/// Returns the selected [DateTime], or `null` if the user cancels.
Future<DateTime?> showDateTimePicker({
  required BuildContext context,
  required DateTime initialDateTime,
  DateTime? firstDate,
  DateTime? lastDate,
  int minuteInterval = 5,
}) {
  return showDialog<DateTime>(
    context: context,
    builder: (_) => _DateTimePickerDialog(
      initialDateTime: initialDateTime,
      firstDate: firstDate,
      lastDate: lastDate,
      minuteInterval: minuteInterval,
    ),
  );
}

class _DateTimePickerDialog extends StatefulWidget {
  const _DateTimePickerDialog({
    required this.initialDateTime,
    this.firstDate,
    this.lastDate,
    this.minuteInterval = 5,
  });

  final DateTime initialDateTime;
  final DateTime? firstDate;
  final DateTime? lastDate;
  final int minuteInterval;

  @override
  State<_DateTimePickerDialog> createState() => _DateTimePickerDialogState();
}

class _DateTimePickerDialogState extends State<_DateTimePickerDialog> {
  late DateTime _selected;

  @override
  void initState() {
    super.initState();
    _selected = widget.initialDateTime;
  }

  @override
  Widget build(BuildContext context) {
    // Fixed width is required because CalendarDatePicker embeds a Viewport
    // (GridView) internally, and AlertDialog tries to compute intrinsic width
    // of its content. Viewports do not support intrinsic dimensions, so we
    // give a concrete width constraint instead.
    const double dialogWidth = 360;

    return AlertDialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      content: SizedBox(
        width: dialogWidth,
        child: DateTimePicker(
          initialDateTime: _selected,
          onDateTimeChanged: (dt) => setState(() => _selected = dt),
          firstDate: widget.firstDate,
          lastDate: widget.lastDate,
          minuteInterval: widget.minuteInterval,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(_selected),
          child: const Text('done'),
        ),
      ],
    );
  }
}
