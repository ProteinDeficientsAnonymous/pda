import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/launcher.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/providers/auth_provider.dart';

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
    // Always use the live event so RSVP state and edits are reflected immediately.
    final liveEvent =
        ref
            .watch(eventsProvider)
            .valueOrNull
            ?.firstWhere((e) => e.id == event.id, orElse: () => event) ??
        event;

    final dateFmt = DateFormat('EEEE, MMMM d, y');
    final timeFmt = DateFormat('h:mm a');
    final start = liveEvent.startDatetime.toLocal();
    final end = liveEvent.endDatetime.toLocal();
    final isSameDay =
        start.year == end.year &&
        start.month == end.month &&
        start.day == end.day;

    // Build host display string
    final hostNames = <String>[];
    if (liveEvent.createdByName != null) {
      hostNames.add(liveEvent.createdByName!);
    }
    hostNames.addAll(liveEvent.coHostNames);

    return ListView(
      controller: scrollController,
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                liveEvent.title,
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
        if (isSameDay) ...[
          _DetailRow(icon: Icons.calendar_today, text: dateFmt.format(start)),
          const SizedBox(height: 8),
          _DetailRow(
            icon: Icons.schedule,
            text: '${timeFmt.format(start)} – ${timeFmt.format(end)}',
          ),
        ] else ...[
          _DetailRow(
            icon: Icons.calendar_today,
            text:
                '${dateFmt.format(start)}, ${timeFmt.format(start)} – ${dateFmt.format(end)}, ${timeFmt.format(end)}',
          ),
        ],
        if (liveEvent.location.isNotEmpty) ...[
          const SizedBox(height: 8),
          _DetailRow(icon: Icons.place, text: liveEvent.location),
        ],
        if (hostNames.isNotEmpty) ...[
          const SizedBox(height: 8),
          _DetailRow(icon: Icons.person_outline, text: hostNames.join(', ')),
        ],
        if (liveEvent.whatsappLink.isNotEmpty) ...[
          const SizedBox(height: 8),
          _LinkRow(
            icon: Icons.chat,
            label: 'WhatsApp group',
            url: liveEvent.whatsappLink,
          ),
        ],
        if (liveEvent.partifulLink.isNotEmpty) ...[
          const SizedBox(height: 8),
          _LinkRow(
            icon: Icons.celebration,
            label: 'Partiful',
            url: liveEvent.partifulLink,
          ),
        ],
        if (liveEvent.otherLink.isNotEmpty) ...[
          const SizedBox(height: 8),
          _LinkRow(
            icon: Icons.link,
            label: liveEvent.otherLink,
            url: liveEvent.otherLink,
          ),
        ],
        if (liveEvent.description.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(
            liveEvent.description,
            style: const TextStyle(fontSize: 15, height: 1.6),
          ),
        ],
        if (liveEvent.rsvpEnabled) ...[
          const SizedBox(height: 24),
          const Divider(),
          const SizedBox(height: 8),
          _RSVPSection(event: liveEvent),
        ],
        const SizedBox(height: 24),
        const Divider(),
        const SizedBox(height: 8),
        _AdminActions(event: liveEvent),
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

class _RSVPSection extends ConsumerStatefulWidget {
  final Event event;
  const _RSVPSection({required this.event});

  @override
  ConsumerState<_RSVPSection> createState() => _RSVPSectionState();
}

class _RSVPSectionState extends ConsumerState<_RSVPSection> {
  bool _loading = false;

  Future<void> _setRsvp(String status) async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.post(
        '/api/community/events/${widget.event.id}/rsvp/',
        data: {'status': status},
      );
      ref.invalidate(eventsProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to update RSVP: $e')));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _removeRsvp() async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.delete('/api/community/events/${widget.event.id}/rsvp/');
      ref.invalidate(eventsProvider);
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    // Read live event from provider so RSVP changes are reflected immediately.
    final liveEvent =
        ref
            .watch(eventsProvider)
            .valueOrNull
            ?.firstWhere(
              (e) => e.id == widget.event.id,
              orElse: () => widget.event,
            ) ??
        widget.event;
    final myRsvp = liveEvent.myRsvp;
    final guests = liveEvent.guests;

    final attending = guests.where((g) => g.status == 'attending').toList();
    final maybe = guests.where((g) => g.status == 'maybe').toList();
    final cantGo = guests.where((g) => g.status == 'cant_go').toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('RSVP', style: theme.textTheme.titleSmall),
        const SizedBox(height: 10),
        if (_loading)
          const SizedBox(
            height: 36,
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          )
        else
          Row(
            children: [
              _RsvpButton(
                label: 'Attending',
                icon: Icons.check_circle_outline,
                activeColor: Colors.green,
                isActive: myRsvp == 'attending',
                onTap:
                    () =>
                        myRsvp == 'attending'
                            ? _removeRsvp()
                            : _setRsvp('attending'),
              ),
              const SizedBox(width: 8),
              _RsvpButton(
                label: 'Maybe',
                icon: Icons.help_outline,
                activeColor: Colors.orange,
                isActive: myRsvp == 'maybe',
                onTap:
                    () => myRsvp == 'maybe' ? _removeRsvp() : _setRsvp('maybe'),
              ),
              const SizedBox(width: 8),
              _RsvpButton(
                label: "Can't go",
                icon: Icons.cancel_outlined,
                activeColor: Colors.red,
                isActive: myRsvp == 'cant_go',
                onTap:
                    () =>
                        myRsvp == 'cant_go'
                            ? _removeRsvp()
                            : _setRsvp('cant_go'),
              ),
            ],
          ),
        if (guests.isNotEmpty) ...[
          const SizedBox(height: 16),
          _GuestGroup(
            label: 'Attending (${attending.length})',
            guests: attending,
            color: Colors.green,
          ),
          _GuestGroup(
            label: 'Maybe (${maybe.length})',
            guests: maybe,
            color: Colors.orange,
          ),
          _GuestGroup(
            label: "Can't go (${cantGo.length})",
            guests: cantGo,
            color: Colors.red,
          ),
        ],
      ],
    );
  }
}

class _RsvpButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color activeColor;
  final bool isActive;
  final VoidCallback onTap;

  const _RsvpButton({
    required this.label,
    required this.icon,
    required this.activeColor,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color:
              isActive
                  ? activeColor.withValues(alpha: 0.15)
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isActive ? activeColor : Colors.transparent,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 15,
              color:
                  isActive
                      ? activeColor
                      : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: 5),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color:
                    isActive
                        ? activeColor
                        : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GuestGroup extends StatelessWidget {
  final String label;
  final List<EventGuest> guests;
  final Color color;

  const _GuestGroup({
    required this.label,
    required this.guests,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    if (guests.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: guests.map((g) => _GuestChip(guest: g)).toList(),
          ),
        ],
      ),
    );
  }
}

class _GuestChip extends StatefulWidget {
  final EventGuest guest;

  const _GuestChip({required this.guest});

  @override
  State<_GuestChip> createState() => _GuestChipState();
}

class _GuestChipState extends State<_GuestChip> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final phone = widget.guest.phone;
    final isWide = MediaQuery.sizeOf(context).width >= 720;

    if (phone == null) {
      return Text(widget.guest.name, style: const TextStyle(fontSize: 13));
    }

    if (isWide) {
      return Tooltip(
        richMessage: WidgetSpan(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.phone, size: 13, color: Colors.white),
                const SizedBox(width: 5),
                Text(
                  phone,
                  style: const TextStyle(
                    fontSize: 13,
                    color: Colors.white,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
          ),
        ),
        decoration: BoxDecoration(
          color: Colors.black87,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          widget.guest.name,
          style: const TextStyle(
            fontSize: 13,
            decoration: TextDecoration.underline,
            decorationStyle: TextDecorationStyle.dotted,
          ),
        ),
      );
    }

    // Mobile: tap to reveal
    return GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            widget.guest.name,
            style: const TextStyle(
              fontSize: 13,
              decoration: TextDecoration.underline,
              decorationStyle: TextDecorationStyle.dotted,
            ),
          ),
          if (_expanded)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.phone,
                    size: 11,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 3),
                  Text(
                    phone,
                    style: TextStyle(
                      fontSize: 11,
                      fontFamily: 'monospace',
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _LinkRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String url;

  const _LinkRow({required this.icon, required this.label, required this.url});

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return InkWell(
      onTap: () => openUrl(url),
      borderRadius: BorderRadius.circular(4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 15,
                color: color,
                decoration: TextDecoration.underline,
                decorationColor: color,
              ),
            ),
          ),
        ],
      ),
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
  late final TextEditingController _otherLink;
  late DateTime _start;
  late DateTime _end;
  late bool _rsvpEnabled;
  late Set<String> _coHostIds;
  late Map<String, String> _coHostNames; // id → displayName, for chip labels
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
      _otherLink = TextEditingController(text: e.otherLink);
      _start = e.startDatetime.toLocal();
      _end = e.endDatetime.toLocal();
      _rsvpEnabled = e.rsvpEnabled;
      _coHostIds = Set<String>.from(e.coHostIds);
      _coHostNames = {
        for (var i = 0; i < e.coHostIds.length; i++)
          if (i < e.coHostNames.length) e.coHostIds[i]: e.coHostNames[i],
      };
    } else {
      _title = TextEditingController();
      _description = TextEditingController();
      _location = TextEditingController();
      _whatsappLink = TextEditingController();
      _partifulLink = TextEditingController();
      _otherLink = TextEditingController();
      final now = DateTime.now();
      _start = DateTime(now.year, now.month, now.day, now.hour + 1);
      _end = _start.add(const Duration(hours: 1));
      _rsvpEnabled = false;
      _coHostIds = {};
      _coHostNames = {};
    }
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _location.dispose();
    _whatsappLink.dispose();
    _partifulLink.dispose();
    _otherLink.dispose();
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

  String _normalizeUrl(String raw) {
    final s = raw.trim();
    if (s.isEmpty) return s;
    if (s.startsWith('http://') || s.startsWith('https://')) return s;
    return 'https://$s';
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.of(context).pop({
      'title': _title.text.trim(),
      'description': _description.text.trim(),
      'location': _location.text.trim(),
      'whatsapp_link': _normalizeUrl(_whatsappLink.text),
      'partiful_link': _normalizeUrl(_partifulLink.text),
      'other_link': _normalizeUrl(_otherLink.text),
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

    final screenWidth = MediaQuery.sizeOf(context).width;
    final dialogWidth = screenWidth < 520 ? screenWidth - 48 : 480.0;

    return AlertDialog(
      title: Text(_isEdit ? 'Edit event' : 'Add event'),
      content: SizedBox(
        width: dialogWidth,
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
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return null;
                    final normalized = _normalizeUrl(v.trim());
                    final uri = Uri.tryParse(normalized);
                    if (uri == null || !uri.hasAuthority) {
                      return 'Enter a valid URL';
                    }
                    final host = uri.host;
                    final isWhatsApp =
                        host.contains('whatsapp.com') ||
                        host == 'wa.me' ||
                        host == 'whats.app';
                    if (!isWhatsApp) {
                      return 'Must be a WhatsApp link';
                    }
                    return null;
                  },
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
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return null;
                    final normalized = _normalizeUrl(v.trim());
                    final uri = Uri.tryParse(normalized);
                    if (uri == null || !uri.hasAuthority) {
                      return 'Enter a valid URL';
                    }
                    if (!uri.host.contains('partiful.com')) {
                      return 'Must be a Partiful link (partiful.com/...)';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _otherLink,
                  decoration: const InputDecoration(
                    labelText: 'Other link (optional)',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.link),
                  ),
                  keyboardType: TextInputType.url,
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return null;
                    final uri = Uri.tryParse(_normalizeUrl(v.trim()));
                    if (uri == null || !uri.hasAuthority) {
                      return 'Enter a valid URL';
                    }
                    return null;
                  },
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
                  selectedNames: _coHostNames,
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

/// A simple value object for co-host search results.
class _CoHostResult {
  final String id;
  final String displayName;
  const _CoHostResult({required this.id, required this.displayName});
}

class _CoHostPicker extends ConsumerStatefulWidget {
  final Set<String> selectedIds;

  /// Map of id → displayName for already-selected co-hosts (populated from event).
  final Map<String, String> selectedNames;
  final ValueChanged<Set<String>> onChanged;

  const _CoHostPicker({
    required this.selectedIds,
    required this.selectedNames,
    required this.onChanged,
  });

  @override
  ConsumerState<_CoHostPicker> createState() => _CoHostPickerState();
}

class _CoHostPickerState extends ConsumerState<_CoHostPicker> {
  final _controller = TextEditingController();
  List<_CoHostResult> _results = [];
  bool _searching = false;
  // Local copy of names for selected ids (needed to display chips for selections
  // made during this session that may not yet be in widget.selectedNames).
  late Map<String, String> _knownNames;

  @override
  void initState() {
    super.initState();
    _knownNames = Map<String, String>.from(widget.selectedNames);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _search(String q) async {
    if (q.trim().isEmpty) {
      setState(() => _results = []);
      return;
    }
    setState(() => _searching = true);
    try {
      final api = ref.read(apiClientProvider);
      final resp = await api.get(
        '/api/auth/users/search/',
        queryParameters: {'q': q.trim()},
      );
      final data = (resp.data as List<dynamic>?) ?? [];
      setState(() {
        _results =
            data
                .map(
                  (item) => _CoHostResult(
                    id: item['id'] as String,
                    displayName: item['display_name'] as String,
                  ),
                )
                .toList();
      });
    } catch (_) {
      setState(() => _results = []);
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  void _toggle(String id, String name) {
    _knownNames[id] = name;
    final next = Set<String>.from(widget.selectedIds);
    if (next.contains(id)) {
      next.remove(id);
    } else {
      next.add(id);
    }
    widget.onChanged(next);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final selected = widget.selectedIds;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Selected chips
        if (selected.isNotEmpty) ...[
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children:
                selected.map((id) {
                  final name = _knownNames[id] ?? id;
                  return Chip(
                    label: Text(name, style: const TextStyle(fontSize: 13)),
                    onDeleted: () => _toggle(id, name),
                    deleteIconColor: theme.colorScheme.onSurfaceVariant,
                  );
                }).toList(),
          ),
          const SizedBox(height: 8),
        ],
        // Search field
        TextField(
          controller: _controller,
          decoration: InputDecoration(
            hintText: 'Search by name…',
            border: const OutlineInputBorder(),
            isDense: true,
            suffixIcon:
                _searching
                    ? const Padding(
                      padding: EdgeInsets.all(10),
                      child: SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                    : null,
          ),
          onChanged: _search,
        ),
        // Results
        if (_results.isNotEmpty) ...[
          const SizedBox(height: 4),
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: theme.colorScheme.outlineVariant),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children:
                  _results.map((r) {
                    final isSelected = selected.contains(r.id);
                    return ListTile(
                      dense: true,
                      title: Text(
                        r.displayName,
                        style: const TextStyle(fontSize: 13),
                      ),
                      trailing:
                          isSelected
                              ? Icon(
                                Icons.check,
                                size: 16,
                                color: theme.colorScheme.primary,
                              )
                              : null,
                      onTap: () {
                        _toggle(r.id, r.displayName);
                        if (!isSelected) {
                          _controller.clear();
                          setState(() => _results = []);
                        }
                      },
                    );
                  }).toList(),
            ),
          ),
        ],
      ],
    );
  }
}
