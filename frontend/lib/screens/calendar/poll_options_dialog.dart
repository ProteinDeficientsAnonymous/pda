import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/event_poll.dart';
import 'package:pda/providers/event_poll_provider.dart';
import 'package:pda/screens/calendar/event_form_models.dart';
import 'package:pda/widgets/date_time_picker_dialog.dart';
import 'package:pda/widgets/poll_widgets.dart';

/// Dialog for adding/removing datetime poll options.
///
/// **Create mode** (no [eventId]): manages a local list and returns it on done.
/// **Edit mode** ([eventId] provided): calls live API endpoints for each change.
class PollOptionsDialog extends ConsumerStatefulWidget {
  final List<DateTime> initialOptions;
  final String? eventId;

  const PollOptionsDialog({
    super.key,
    this.initialOptions = const [],
    this.eventId,
  });

  @override
  ConsumerState<PollOptionsDialog> createState() => _PollOptionsDialogState();
}

class _PollOptionsDialogState extends ConsumerState<PollOptionsDialog> {
  late List<DateTime> _localOptions;
  bool _adding = false;
  bool _updating = false;

  bool get _isLive => widget.eventId != null;
  bool get _busy => _adding || _updating;

  @override
  void initState() {
    super.initState();
    _localOptions = [...widget.initialOptions];
  }

  Future<void> _addOption() async {
    final now = DateTime.now();
    final dt = await showDateTimePicker(
      context: context,
      initialDateTime: now,
      firstDate: now,
      lastDate: DateTime(now.year + 2),
    );
    if (dt == null || !mounted) return;

    if (_isLive) {
      setState(() => _adding = true);
      try {
        await addPollOption(ref: ref, eventId: widget.eventId!, datetime: dt);
      } catch (_) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('couldn\'t add option — try again')),
          );
        }
      } finally {
        if (mounted) setState(() => _adding = false);
      }
    } else {
      setState(() => _localOptions.add(dt));
    }
  }

  Future<void> _removeOption({int? localIndex, EventPollOption? option}) async {
    if (_isLive && option != null) {
      try {
        await deletePollOption(
          ref: ref,
          eventId: widget.eventId!,
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
    } else if (localIndex != null) {
      setState(() => _localOptions.removeAt(localIndex));
    }
  }

  Future<void> _editLocalOption(int index) async {
    final now = DateTime.now();
    final dt = await showDateTimePicker(
      context: context,
      initialDateTime: _localOptions[index],
      firstDate: now,
      lastDate: DateTime(now.year + 2),
    );
    if (dt == null || !mounted) return;
    setState(() => _localOptions[index] = dt);
  }

  Future<void> _updateOption(EventPollOption option) async {
    final now = DateTime.now();
    final dt = await showDateTimePicker(
      context: context,
      initialDateTime: option.datetime.toLocal(),
      firstDate: now,
      lastDate: DateTime(now.year + 2),
    );
    if (dt == null || !mounted) return;

    setState(() => _updating = true);
    try {
      await updatePollOption(
        ref: ref,
        eventId: widget.eventId!,
        optionId: option.id,
        datetime: dt,
      );
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('couldn\'t update option — try again')),
        );
      }
    } finally {
      if (mounted) setState(() => _updating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return AlertDialog(
      title: const Text('time options'),
      contentPadding: const EdgeInsets.fromLTRB(24, 12, 24, 0),
      content: SizedBox(
        width: 340,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _isLive
                  ? 'members are voting on these'
                  : 'members will vote on these — date is set when you pick a winner',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            if (_isLive) _buildLiveOptions() else _buildLocalOptions(),
            const SizedBox(height: 4),
            TextButton.icon(
              onPressed: _adding ? null : _addOption,
              icon: const Icon(Icons.add),
              label: Text(_adding ? 'adding...' : 'add another time'),
            ),
          ],
        ),
      ),
      actions: [
        if (!_isLive)
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('cancel'),
          ),
        FilledButton(
          onPressed: () {
            if (_isLive) {
              Navigator.of(context).pop();
            } else {
              Navigator.of(context).pop(_localOptions);
            }
          },
          child: const Text('done'),
        ),
      ],
    );
  }

  Widget _buildLocalOptions() {
    if (_localOptions.isEmpty) {
      return Text(
        'no options yet — add at least 2',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      );
    }
    return Column(
      children: [
        for (var i = 0; i < _localOptions.length; i++)
          _optionTile(
            label: pollDateFmt.format(_localOptions[i]).toLowerCase(),
            onEdit: () => _editLocalOption(i),
            onRemove: () => _removeOption(localIndex: i),
          ),
      ],
    );
  }

  Widget _buildLiveOptions() {
    final pollAsync = ref.watch(eventPollProvider(widget.eventId!));
    return pollAsync.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => const Text('couldn\'t load options'),
      data: (poll) {
        if (poll == null) return const SizedBox.shrink();
        final options = poll.options;
        return Column(
          children: [
            for (final option in options)
              _optionTile(
                label: formatPollOption(option.datetime),
                trailing: '${option.totalCount}',
                onEdit: _busy ? null : () => _updateOption(option),
                onRemove: options.length > 2 && !_busy
                    ? () => _removeOption(option: option)
                    : null,
              ),
          ],
        );
      },
    );
  }

  Widget _optionTile({
    required String label,
    String? trailing,
    VoidCallback? onEdit,
    VoidCallback? onRemove,
  }) {
    final theme = Theme.of(context);
    return Row(
      children: [
        const Icon(Icons.access_time_outlined, size: 16),
        const SizedBox(width: 8),
        Expanded(child: Text(label)),
        if (trailing != null)
          Padding(
            padding: const EdgeInsets.only(right: 4),
            child: Text(
              trailing,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        if (onEdit != null)
          IconButton(
            tooltip: 'edit time',
            icon: const Icon(Icons.edit_outlined, size: 18),
            onPressed: onEdit,
          ),
        if (onRemove != null)
          IconButton(
            tooltip: 'remove option',
            icon: const Icon(Icons.close, size: 18),
            onPressed: onRemove,
          )
        else if (onEdit == null)
          const SizedBox(width: 48),
      ],
    );
  }
}
