import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/event_poll.dart';
import 'package:pda/providers/event_poll_provider.dart';
import 'package:pda/widgets/date_time_picker_dialog.dart';
import 'package:pda/widgets/poll_widgets.dart';

/// Inline editor for an active poll's options — shown inside EventFormDialog
/// when editing an event that already has a poll.
class LivePollEditor extends ConsumerStatefulWidget {
  final String eventId;
  final VoidCallback onRemovePoll;
  final bool removingPoll;

  const LivePollEditor({
    super.key,
    required this.eventId,
    required this.onRemovePoll,
    required this.removingPoll,
  });

  @override
  ConsumerState<LivePollEditor> createState() => _LivePollEditorState();
}

class _LivePollEditorState extends ConsumerState<LivePollEditor> {
  bool _adding = false;

  Future<void> _addOption() async {
    final now = DateTime.now();
    final dt = await showDateTimePicker(
      context: context,
      initialDateTime: now,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 2),
    );
    if (dt == null || !mounted) return;
    setState(() => _adding = true);
    try {
      await addPollOption(ref: ref, eventId: widget.eventId, datetime: dt);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('couldn\'t add option — try again')),
        );
      }
    } finally {
      if (mounted) setState(() => _adding = false);
    }
  }

  Future<void> _removeOption(EventPollOption option) async {
    try {
      await deletePollOption(
        ref: ref,
        eventId: widget.eventId,
        optionId: option.id,
      );
    } catch (e) {
      if (mounted) {
        final msg = e.toString().contains('at least 2')
            ? 'a poll needs at least 2 options'
            : 'couldn\'t remove option — try again';
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(msg)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final pollAsync = ref.watch(eventPollProvider(widget.eventId));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text('time options', style: theme.textTheme.titleSmall),
            ),
            TextButton(
              onPressed: widget.removingPoll ? null : widget.onRemovePoll,
              style: TextButton.styleFrom(
                foregroundColor: theme.colorScheme.error,
                padding: EdgeInsets.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: Text(widget.removingPoll ? 'removing...' : 'remove poll'),
            ),
          ],
        ),
        Text(
          'members are voting on these',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 8),
        pollAsync.when(
          loading: () => const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (_, __) => const Text('couldn\'t load options'),
          data: (poll) {
            if (poll == null) return const SizedBox.shrink();
            final options = poll.options;
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final option in options)
                  Row(
                    children: [
                      const Icon(Icons.access_time_outlined, size: 16),
                      const SizedBox(width: 8),
                      Expanded(child: Text(formatPollOption(option.datetime))),
                      Text(
                        '${option.totalCount}',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                      IconButton(
                        tooltip: 'remove option',
                        icon: const Icon(Icons.close, size: 18),
                        onPressed: options.length > 2
                            ? () => _removeOption(option)
                            : null,
                      ),
                    ],
                  ),
              ],
            );
          },
        ),
        TextButton.icon(
          onPressed: _adding ? null : _addOption,
          icon: const Icon(Icons.add),
          label: Text(_adding ? 'adding...' : 'add another time'),
        ),
      ],
    );
  }
}
