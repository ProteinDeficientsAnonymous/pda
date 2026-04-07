import 'package:flutter/material.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/screens/calendar/event_form_field_sections.dart';
import 'package:pda/screens/calendar/poll_options_dialog.dart';
import 'package:pda/widgets/date_time_picker.dart';

class EventFormWhenSection extends StatefulWidget {
  final bool isEdit;
  final Event? event;
  final DateTime start;
  final DateTime? end;
  final bool datetimeTbd;
  final List<DateTime> datetimePollOptions;
  final bool removingPoll;
  final ValueChanged<DateTime> onStartChanged;
  final ValueChanged<DateTime> onEndChanged;
  final VoidCallback onAddEndTime;
  final VoidCallback onClearEndTime;
  final void Function(List<DateTime> options) onPollOptionsChanged;
  final VoidCallback onRemovePoll;
  final double pickerWidth;
  final String Function(DateTime) dateFmt;

  const EventFormWhenSection({
    super.key,
    required this.isEdit,
    required this.event,
    required this.start,
    required this.end,
    required this.datetimeTbd,
    required this.datetimePollOptions,
    required this.removingPoll,
    required this.onStartChanged,
    required this.onEndChanged,
    required this.onAddEndTime,
    required this.onClearEndTime,
    required this.onPollOptionsChanged,
    required this.onRemovePoll,
    required this.pickerWidth,
    required this.dateFmt,
  });

  @override
  State<EventFormWhenSection> createState() => _EventFormWhenSectionState();
}

class _EventFormWhenSectionState extends State<EventFormWhenSection> {
  DateTimePickerMode? _startPickerMode;
  DateTimePickerMode? _endPickerMode;
  late bool _dateSetByPoll;

  @override
  void initState() {
    super.initState();
    _dateSetByPoll =
        widget.isEdit &&
        (widget.event?.hasPoll ?? false) &&
        !(widget.event?.datetimeTbd ?? true);
  }

  void _toggleStartMode(DateTimePickerMode mode) {
    setState(() {
      _startPickerMode = _startPickerMode == mode ? null : mode;
    });
  }

  void _toggleEndMode(DateTimePickerMode mode) {
    setState(() {
      _endPickerMode = _endPickerMode == mode ? null : mode;
    });
  }

  Future<void> _openPollDialog() async {
    final hasActivePoll =
        widget.isEdit &&
        (widget.event?.hasPoll ?? false) &&
        (widget.event?.datetimeTbd ?? true);

    final result = await showDialog<List<DateTime>>(
      context: context,
      builder: (_) => PollOptionsDialog(
        initialOptions: widget.datetimePollOptions,
        eventId: hasActivePoll ? widget.event!.id : null,
      ),
    );

    // In live-edit mode the dialog returns null (mutations are live).
    // In create mode, result is the updated options list.
    if (result != null) {
      widget.onPollOptionsChanged(result);
    }
  }

  List<Widget> _buildDateTimeRows() {
    return [
      EventFormDateTimeRow(
        label: 'start',
        date: widget.dateFmt(widget.start),
        time: formatTime(widget.start),
        isDateExpanded: _startPickerMode == DateTimePickerMode.dateOnly,
        isTimeExpanded: _startPickerMode == DateTimePickerMode.timeOnly,
        onDateTap: () => _toggleStartMode(DateTimePickerMode.dateOnly),
        onTimeTap: () => _toggleStartMode(DateTimePickerMode.timeOnly),
      ),
      if (_startPickerMode != null) ...[
        const SizedBox(height: 8),
        TapRegion(
          onTapOutside: (_) => setState(() {
            _startPickerMode = null;
            _endPickerMode = null;
          }),
          child: SizedBox(
            width: widget.pickerWidth,
            child: DateTimePicker(
              initialDateTime: widget.start,
              onDateTimeChanged: (dt) {
                setState(() => _dateSetByPoll = false);
                widget.onStartChanged(dt);
              },
              firstDate: DateTime(2000),
              lastDate: DateTime(2100),
              mode: _startPickerMode!,
            ),
          ),
        ),
      ],
      const SizedBox(height: 8),
      ..._buildEndTimeRows(),
    ];
  }

  List<Widget> _buildEndTimeRows() {
    if (widget.end == null) {
      return [
        Semantics(
          button: true,
          label: 'add end time',
          child: InkWell(
            onTap: widget.onAddEndTime,
            borderRadius: BorderRadius.circular(8),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.add,
                    size: 16,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'add end time',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ];
    }
    return [
      Row(
        children: [
          Expanded(
            child: EventFormDateTimeRow(
              label: 'end',
              date: widget.dateFmt(widget.end!),
              time: formatTime(widget.end!),
              isDateExpanded: _endPickerMode == DateTimePickerMode.dateOnly,
              isTimeExpanded: _endPickerMode == DateTimePickerMode.timeOnly,
              onDateTap: () => _toggleEndMode(DateTimePickerMode.dateOnly),
              onTimeTap: () => _toggleEndMode(DateTimePickerMode.timeOnly),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 16),
            tooltip: 'Remove end time',
            onPressed: widget.onClearEndTime,
          ),
        ],
      ),
      if (_endPickerMode != null) ...[
        const SizedBox(height: 8),
        TapRegion(
          onTapOutside: (_) => setState(() {
            _startPickerMode = null;
            _endPickerMode = null;
          }),
          child: SizedBox(
            width: widget.pickerWidth,
            child: DateTimePicker(
              initialDateTime: widget.end!,
              onDateTimeChanged: (dt) {
                setState(() => _dateSetByPoll = false);
                widget.onEndChanged(dt);
              },
              firstDate: DateTime(2000),
              lastDate: DateTime(2100),
              mode: _endPickerMode!,
            ),
          ),
        ),
      ],
    ];
  }

  Widget _buildPollButton(ThemeData theme, String label) {
    return InkWell(
      onTap: _openPollDialog,
      borderRadius: BorderRadius.circular(24),
      child: Semantics(
        button: true,
        label: label,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: theme.colorScheme.outlineVariant),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.poll_outlined,
                size: 16,
                color: theme.colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 6),
              Text(
                label,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    // Editing an event with an active (non-finalized) poll — show edit button.
    final hasActivePoll =
        widget.isEdit &&
        (widget.event?.hasPoll ?? false) &&
        (widget.event?.datetimeTbd ?? true);

    if (hasActivePoll) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('date & time tbd', style: theme.textTheme.bodyMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 12,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              _buildPollButton(theme, 'edit poll'),
              TextButton(
                onPressed: widget.removingPoll ? null : widget.onRemovePoll,
                style: TextButton.styleFrom(
                  foregroundColor: theme.colorScheme.error,
                  padding: EdgeInsets.zero,
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: Text(
                  widget.removingPoll ? 'removing...' : 'remove poll',
                ),
              ),
            ],
          ),
        ],
      );
    }

    // Editing with finalized poll — date pickers + "set by poll" badge.
    if (_dateSetByPoll) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ..._buildDateTimeRows(),
          const SizedBox(height: 4),
          Row(
            children: [
              Icon(
                Icons.check_circle_outline,
                size: 14,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: 5),
              Text(
                'set by poll',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _buildPollButton(theme, 're-poll members for a time'),
        ],
      );
    }

    // Creating with poll options already chosen — show summary + edit button.
    if (widget.datetimePollOptions.isNotEmpty) {
      final count = widget.datetimePollOptions.length;
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              _buildPollButton(
                theme,
                'edit poll ($count option${count == 1 ? '' : 's'})',
              ),
              TextButton(
                onPressed: () => widget.onPollOptionsChanged([]),
                child: const Text('cancel poll'),
              ),
            ],
          ),
        ],
      );
    }

    // Default: date/time pickers + offer to start a poll.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        ..._buildDateTimeRows(),
        const SizedBox(height: 10),
        Center(child: _buildPollButton(theme, 'or poll members for a time')),
      ],
    );
  }
}
