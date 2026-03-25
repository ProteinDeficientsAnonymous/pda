import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/user_management_provider.dart';

/// Shows the event detail panel as a bottom sheet (narrow) or side panel (wide).
void showEventDetail(BuildContext context, Event event) {
  final width = MediaQuery.sizeOf(context).width;
  if (width >= 720) {
    _showSidePanel(context, event);
  } else {
    _showBottomSheet(context, event);
  }
}

void _showBottomSheet(BuildContext context, Event event) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
    ),
    builder:
        (_) => DraggableScrollableSheet(
          initialChildSize: 0.6,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          expand: false,
          builder:
              (ctx, controller) => _EventDetailContent(
                event: event,
                scrollController: controller,
              ),
        ),
  );
}

void _showSidePanel(BuildContext context, Event event) {
  showDialog(
    context: context,
    builder:
        (_) => Align(
          alignment: Alignment.centerRight,
          child: Material(
            elevation: 8,
            child: SizedBox(
              width: 400,
              height: double.infinity,
              child: _EventDetailContent(event: event),
            ),
          ),
        ),
  );
}

class _EventDetailContent extends ConsumerWidget {
  final Event event;
  final ScrollController? scrollController;

  const _EventDetailContent({required this.event, this.scrollController});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dateFmt = DateFormat('EEEE, MMMM d, y');
    final timeFmt = DateFormat('h:mm a');
    final start = event.startDatetime.toLocal();
    final end = event.endDatetime.toLocal();
    final isSameDay =
        start.year == end.year &&
        start.month == end.month &&
        start.day == end.day;

    // Build host display string
    final hostNames = <String>[];
    if (event.createdByName != null) hostNames.add(event.createdByName!);
    hostNames.addAll(event.coHostNames);

    return ListView(
      controller: scrollController,
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                event.title,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            IconButton(
              icon: const Icon(Icons.close),
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        ),
        const SizedBox(height: 16),
        _DetailRow(icon: Icons.calendar_today, text: dateFmt.format(start)),
        const SizedBox(height: 8),
        if (isSameDay)
          _DetailRow(
            icon: Icons.schedule,
            text: '${timeFmt.format(start)} – ${timeFmt.format(end)}',
          )
        else ...[
          _DetailRow(
            icon: Icons.schedule,
            text: '${dateFmt.format(start)} ${timeFmt.format(start)}',
          ),
          const SizedBox(height: 4),
          _DetailRow(
            icon: Icons.schedule,
            text: '${dateFmt.format(end)} ${timeFmt.format(end)}',
          ),
        ],
        if (event.location.isNotEmpty) ...[
          const SizedBox(height: 8),
          _DetailRow(icon: Icons.place, text: event.location),
        ],
        if (hostNames.isNotEmpty) ...[
          const SizedBox(height: 8),
          _DetailRow(icon: Icons.person_outline, text: hostNames.join(', ')),
        ],
        if (event.whatsappLink.isNotEmpty) ...[
          const SizedBox(height: 8),
          _DetailRow(icon: Icons.chat, text: event.whatsappLink),
        ],
        if (event.partifulLink.isNotEmpty) ...[
          const SizedBox(height: 8),
          _DetailRow(icon: Icons.celebration, text: event.partifulLink),
        ],
        if (event.description.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(
            event.description,
            style: const TextStyle(fontSize: 15, height: 1.6),
          ),
        ],
        if (event.rsvpEnabled) ...[
          const SizedBox(height: 12),
          Row(
            children: [
              Icon(
                Icons.how_to_reg,
                size: 16,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(width: 8),
              Text(
                'RSVP enabled',
                style: TextStyle(
                  fontSize: 13,
                  color: Theme.of(context).colorScheme.primary,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ],
        const SizedBox(height: 24),
        const Divider(),
        const SizedBox(height: 8),
        _AdminActions(event: event),
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _DetailRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: 18,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontSize: 15,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
    );
  }
}

class _AdminActions extends ConsumerStatefulWidget {
  final Event event;

  const _AdminActions({required this.event});

  @override
  ConsumerState<_AdminActions> createState() => _AdminActionsState();
}

class _AdminActionsState extends ConsumerState<_AdminActions> {
  bool _loading = false;

  Future<void> _delete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Delete event'),
            content: Text(
              'Delete "${widget.event.title}"? This cannot be undone.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Delete'),
              ),
            ],
          ),
    );
    if (confirmed != true) return;

    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.delete('/api/community/events/${widget.event.id}/');
      ref.invalidate(eventsProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to delete event: $e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _edit() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => EventFormDialog(event: widget.event),
    );
    if (result == null) return;

    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.patch(
        '/api/community/events/${widget.event.id}/',
        data: result,
      );
      ref.invalidate(eventsProvider);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to update event: $e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    final user = ref.watch(authProvider).valueOrNull;
    if (user == null) return const SizedBox.shrink();

    final isCreator = widget.event.createdById == user.id;
    final isManager = user.hasPermission('manage_events');
    if (!isCreator && !isManager) return const SizedBox.shrink();

    return Row(
      children: [
        OutlinedButton.icon(
          onPressed: _edit,
          icon: const Icon(Icons.edit, size: 16),
          label: const Text('Edit'),
        ),
        const SizedBox(width: 12),
        OutlinedButton.icon(
          onPressed: _delete,
          icon: Icon(
            Icons.delete,
            size: 16,
            color: Theme.of(context).colorScheme.error,
          ),
          label: Text(
            'Delete',
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
        ),
      ],
    );
  }
}

/// Shared form dialog for creating and editing events.
/// Pass [event] to pre-fill fields for editing; omit for create mode.
class EventFormDialog extends ConsumerStatefulWidget {
  final Event? event;

  const EventFormDialog({super.key, this.event});

  @override
  ConsumerState<EventFormDialog> createState() => _EventFormDialogState();
}

class _EventFormDialogState extends ConsumerState<EventFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _title;
  late final TextEditingController _description;
  late final TextEditingController _location;
  late final TextEditingController _whatsappLink;
  late final TextEditingController _partifulLink;
  late DateTime _start;
  late DateTime _end;
  late bool _rsvpEnabled;
  late Set<String> _coHostIds;
  // which field the inline calendar is editing: 'start', 'end', or null (hidden)
  String? _calendarTarget;

  bool get _isEdit => widget.event != null;

  @override
  void initState() {
    super.initState();
    final e = widget.event;
    if (e != null) {
      _title = TextEditingController(text: e.title);
      _description = TextEditingController(text: e.description);
      _location = TextEditingController(text: e.location);
      _whatsappLink = TextEditingController(text: e.whatsappLink);
      _partifulLink = TextEditingController(text: e.partifulLink);
      _start = e.startDatetime.toLocal();
      _end = e.endDatetime.toLocal();
      _rsvpEnabled = e.rsvpEnabled;
      _coHostIds = Set<String>.from(e.coHostIds);
    } else {
      _title = TextEditingController();
      _description = TextEditingController();
      _location = TextEditingController();
      _whatsappLink = TextEditingController();
      _partifulLink = TextEditingController();
      final now = DateTime.now();
      _start = DateTime(now.year, now.month, now.day, now.hour + 1);
      _end = _start.add(const Duration(hours: 1));
      _rsvpEnabled = false;
      _coHostIds = {};
    }
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _location.dispose();
    _whatsappLink.dispose();
    _partifulLink.dispose();
    super.dispose();
  }

  void _toggleCalendar(String target) {
    setState(() => _calendarTarget = _calendarTarget == target ? null : target);
  }

  void _onCalendarDaySelected(DateTime day) {
    setState(() {
      if (_calendarTarget == 'start') {
        _start = DateTime(
          day.year,
          day.month,
          day.day,
          _start.hour,
          _start.minute,
        );
        if (_end.isBefore(_start)) {
          _end = _start.add(const Duration(hours: 1));
        }
      } else {
        _end = DateTime(day.year, day.month, day.day, _end.hour, _end.minute);
        if (_end.isBefore(_start)) {
          _start = _end.subtract(const Duration(hours: 1));
        }
      }
      _calendarTarget = null;
    });
  }

  Future<void> _pickStartTime() async {
    setState(() => _calendarTarget = null);
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_start),
    );
    if (picked == null) return;
    setState(() {
      _start = DateTime(
        _start.year,
        _start.month,
        _start.day,
        picked.hour,
        picked.minute,
      );
      if (_end.isBefore(_start)) {
        _end = _start.add(const Duration(hours: 1));
      }
    });
  }

  Future<void> _pickEndTime() async {
    setState(() => _calendarTarget = null);
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_end),
    );
    if (picked == null) return;
    setState(() {
      _end = DateTime(
        _end.year,
        _end.month,
        _end.day,
        picked.hour,
        picked.minute,
      );
    });
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.of(context).pop({
      'title': _title.text.trim(),
      'description': _description.text.trim(),
      'location': _location.text.trim(),
      'whatsapp_link': _whatsappLink.text.trim(),
      'partiful_link': _partifulLink.text.trim(),
      'start_datetime': _start.toUtc().toIso8601String(),
      'end_datetime': _end.toUtc().toIso8601String(),
      'rsvp_enabled': _rsvpEnabled,
      'co_host_ids': _coHostIds.toList(),
    });
  }

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('EEE, MMM d, y');
    final timeFmt = DateFormat('h:mm a');
    final theme = Theme.of(context);

    return AlertDialog(
      title: Text(_isEdit ? 'Edit event' : 'Add event'),
      content: SizedBox(
        width: 480,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextFormField(
                  controller: _title,
                  decoration: const InputDecoration(
                    labelText: 'Title *',
                    border: OutlineInputBorder(),
                  ),
                  textCapitalization: TextCapitalization.sentences,
                  validator:
                      (v) => v == null || v.trim().isEmpty ? 'Required' : null,
                ),
                const SizedBox(height: 16),
                // Date/time rows — Google Calendar style
                _DateTimeRow(
                  label: 'Start',
                  date: dateFmt.format(_start),
                  time: timeFmt.format(_start),
                  isActive: _calendarTarget == 'start',
                  onDateTap: () => _toggleCalendar('start'),
                  onTimeTap: _pickStartTime,
                ),
                const SizedBox(height: 8),
                _DateTimeRow(
                  label: 'End',
                  date: dateFmt.format(_end),
                  time: timeFmt.format(_end),
                  isActive: _calendarTarget == 'end',
                  onDateTap: () => _toggleCalendar('end'),
                  onTimeTap: _pickEndTime,
                ),
                if (_calendarTarget != null) ...[
                  const SizedBox(height: 8),
                  CalendarDatePicker(
                    initialDate: _calendarTarget == 'start' ? _start : _end,
                    firstDate: DateTime(2000),
                    lastDate: DateTime(2100),
                    onDateChanged: _onCalendarDaySelected,
                  ),
                ],
                const SizedBox(height: 16),
                TextFormField(
                  controller: _location,
                  decoration: const InputDecoration(
                    labelText: 'Location',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.place_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _description,
                  decoration: const InputDecoration(
                    labelText: 'Description',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  maxLines: 3,
                  textCapitalization: TextCapitalization.sentences,
                ),
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                Text('Links', style: theme.textTheme.labelLarge),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _whatsappLink,
                  decoration: const InputDecoration(
                    labelText: 'WhatsApp group link (optional)',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.chat_outlined),
                  ),
                  keyboardType: TextInputType.url,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _partifulLink,
                  decoration: InputDecoration(
                    labelText: 'Partiful link (optional)',
                    border: const OutlineInputBorder(),
                    prefixIcon: const Icon(Icons.celebration_outlined),
                    helperText:
                        _rsvpEnabled
                            ? 'Consider using app RSVPs instead of Partiful'
                            : null,
                    helperStyle: TextStyle(color: theme.colorScheme.tertiary),
                  ),
                  keyboardType: TextInputType.url,
                ),
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                SwitchListTile(
                  value: _rsvpEnabled,
                  onChanged: (v) => setState(() => _rsvpEnabled = v),
                  title: const Text('Enable RSVPs'),
                  subtitle:
                      _rsvpEnabled && _partifulLink.text.trim().isNotEmpty
                          ? Text(
                            'You have a Partiful link set — consider using one or the other',
                            style: TextStyle(color: theme.colorScheme.tertiary),
                          )
                          : null,
                  contentPadding: EdgeInsets.zero,
                ),
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                Text('Co-hosts', style: theme.textTheme.labelLarge),
                const SizedBox(height: 8),
                _CoHostPicker(
                  selectedIds: _coHostIds,
                  creatorId: widget.event?.createdById,
                  onChanged: (ids) => setState(() => _coHostIds = ids),
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _submit, child: Text(_isEdit ? 'Save' : 'Add')),
      ],
    );
  }
}

class _DateTimeRow extends StatelessWidget {
  final String label;
  final String date;
  final String time;
  final bool isActive;
  final VoidCallback onDateTap;
  final VoidCallback onTimeTap;

  const _DateTimeRow({
    required this.label,
    required this.date,
    required this.time,
    required this.onDateTap,
    required this.onTimeTap,
    this.isActive = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final chipColor =
        isActive
            ? theme.colorScheme.primaryContainer
            : theme.colorScheme.surfaceContainerHighest;
    final textStyle = theme.textTheme.bodyMedium;

    return Row(
      children: [
        SizedBox(
          width: 40,
          child: Text(
            label,
            style: theme.textTheme.labelMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        const SizedBox(width: 8),
        InkWell(
          onTap: onDateTap,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: chipColor,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.calendar_today_outlined, size: 14),
                const SizedBox(width: 6),
                Text(date, style: textStyle),
              ],
            ),
          ),
        ),
        const SizedBox(width: 8),
        InkWell(
          onTap: onTimeTap,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: chipColor,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.schedule_outlined, size: 14),
                const SizedBox(width: 6),
                Text(time, style: textStyle),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _CoHostPicker extends ConsumerWidget {
  final Set<String> selectedIds;
  final String? creatorId;
  final ValueChanged<Set<String>> onChanged;

  const _CoHostPicker({
    required this.selectedIds,
    required this.onChanged,
    this.creatorId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usersAsync = ref.watch(usersProvider);

    return usersAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error:
          (e, _) => Text(
            'Could not load users: $e',
            style: const TextStyle(fontSize: 13),
          ),
      data: (users) {
        final candidates = users.where((u) => u.id != creatorId).toList();
        if (candidates.isEmpty) {
          return const Text(
            'No other members available.',
            style: TextStyle(fontSize: 13),
          );
        }
        return Wrap(
          spacing: 8,
          runSpacing: 4,
          children:
              candidates.map((u) {
                final name =
                    '${u.firstName} ${u.lastName}'.trim().isNotEmpty
                        ? '${u.firstName} ${u.lastName}'.trim()
                        : u.email;
                final selected = selectedIds.contains(u.id);
                return FilterChip(
                  label: Text(name, style: const TextStyle(fontSize: 13)),
                  selected: selected,
                  onSelected: (val) {
                    final next = Set<String>.from(selectedIds);
                    if (val) {
                      next.add(u.id);
                    } else {
                      next.remove(u.id);
                    }
                    onChanged(next);
                  },
                );
              }).toList(),
        );
      },
    );
  }
}
