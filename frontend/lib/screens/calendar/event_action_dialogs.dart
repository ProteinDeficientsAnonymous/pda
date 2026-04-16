import 'package:flutter/material.dart';
import 'package:pda/models/event.dart';

/// Result returned by [showCancelEventDialog].
class CancelDialogResult {
  final bool confirmed;
  final bool notifyAttendees;
  const CancelDialogResult({
    required this.confirmed,
    required this.notifyAttendees,
  });
}

/// Shows a confirmation dialog for cancelling an event.
/// Returns [CancelDialogResult] — never null.
Future<CancelDialogResult> showCancelEventDialog(
  BuildContext context,
  Event event,
) async {
  var notifyAttendees = true;

  final confirmed = await showDialog<bool>(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setState) => AlertDialog(
        title: const Text('cancel event'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'cancel "${event.title}"? attendees will see it\'s been cancelled.',
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Checkbox(
                  value: notifyAttendees,
                  onChanged: (v) => setState(() => notifyAttendees = v ?? true),
                ),
                const SizedBox(width: 4),
                const Text('notify attendees'),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('nevermind'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(ctx).colorScheme.error,
            ),
            child: const Text('cancel event'),
          ),
        ],
      ),
    ),
  );

  return CancelDialogResult(
    confirmed: confirmed == true,
    notifyAttendees: notifyAttendees,
  );
}

/// Shows a confirmation dialog for deleting an event.
/// Returns true if the user confirmed.
Future<bool> showDeleteEventDialog(BuildContext context, Event event) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (ctx) => AlertDialog(
      title: const Text('delete event'),
      content: Text('delete "${event.title}"? this can\'t be undone.'),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(ctx).pop(false),
          child: const Text('nevermind'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(ctx).pop(true),
          style: FilledButton.styleFrom(
            backgroundColor: Theme.of(ctx).colorScheme.error,
          ),
          child: const Text('delete'),
        ),
      ],
    ),
  );
  return confirmed == true;
}
