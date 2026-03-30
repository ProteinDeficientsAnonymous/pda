import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/utils/validators.dart' as v;

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
  final _scrollController = ScrollController();
  late final TextEditingController _title;
  late final TextEditingController _description;
  late final TextEditingController _location;
  late final TextEditingController _whatsappLink;
  late final TextEditingController _partifulLink;
  late final TextEditingController _otherLink;
  late DateTime _start;
  late DateTime? _end;
  late bool _rsvpEnabled;
  late Set<String> _coHostIds;
  late Map<String, String> _coHostNames;
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
      _end = e.endDatetime?.toLocal();
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
      _end = null;
      _rsvpEnabled = false;
      _coHostIds = {};
      _coHostNames = {};
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
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
        if (_end != null && _end!.isBefore(_start)) {
          _end = _start.add(const Duration(hours: 1));
        }
      } else {
        final base = _end ?? _start;
        _end = DateTime(day.year, day.month, day.day, base.hour, base.minute);
        if (_end!.isBefore(_start)) {
          _start = _end!.subtract(const Duration(hours: 1));
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
      if (_end != null && _end!.isBefore(_start)) {
        _end = _start.add(const Duration(hours: 1));
      }
    });
  }

  Future<void> _pickEndTime() async {
    setState(() => _calendarTarget = null);
    final base = _end ?? _start;
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(base),
    );
    if (picked == null) return;
    final dateBase = _end ?? _start;
    setState(() {
      _end = DateTime(
        dateBase.year,
        dateBase.month,
        dateBase.day,
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
      'end_datetime': _end?.toUtc().toIso8601String(),
      'rsvp_enabled': _rsvpEnabled,
      'co_host_ids': _coHostIds.toList(),
    });
  }

  Widget _buildNoFeesNote(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.info_outline,
            size: 16,
            color: theme.colorScheme.onSecondaryContainer,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'keep it accessible \u{2728} events should be free or at-cost only '
              '(e.g. splitting the grocery bill). no fees or markups please!',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSecondaryContainer,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTitleField() {
    return TextFormField(
      controller: _title,
      decoration: const InputDecoration(
        labelText: 'what\'s the event? *',
        border: OutlineInputBorder(),
      ),
      textCapitalization: TextCapitalization.sentences,
      validator: v.all([v.required(), v.maxLength(300)]),
    );
  }

  void _addEndTime() {
    setState(() {
      _end = _start.add(const Duration(hours: 1));
      _calendarTarget = null;
    });
  }

  void _clearEndTime() {
    setState(() {
      _end = null;
      _calendarTarget = null;
    });
  }

  List<Widget> _buildEndTimeSection(String Function(DateTime) dateFmt) {
    if (_end == null) {
      return [
        Semantics(
          button: true,
          label: 'add end time',
          child: InkWell(
            onTap: _addEndTime,
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
            child: _DateTimeRow(
              label: 'end',
              date: dateFmt(_end!),
              time: formatTime(_end!),
              isActive: _calendarTarget == 'end',
              onDateTap: () => _toggleCalendar('end'),
              onTimeTap: _pickEndTime,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 16),
            tooltip: 'Remove end time',
            onPressed: _clearEndTime,
          ),
        ],
      ),
    ];
  }

  List<Widget> _buildDateTimeSection(String Function(DateTime) dateFmt) {
    return [
      _DateTimeRow(
        label: 'start',
        date: dateFmt(_start),
        time: formatTime(_start),
        isActive: _calendarTarget == 'start',
        onDateTap: () => _toggleCalendar('start'),
        onTimeTap: _pickStartTime,
      ),
      const SizedBox(height: 8),
      ..._buildEndTimeSection(dateFmt),
      if (_calendarTarget != null) ...[
        const SizedBox(height: 8),
        CalendarDatePicker(
          initialDate: _calendarTarget == 'start' ? _start : (_end ?? _start),
          firstDate: DateTime(2000),
          lastDate: DateTime(2100),
          onDateChanged: _onCalendarDaySelected,
        ),
      ],
    ];
  }

  Widget _buildLocationField() {
    return TextFormField(
      controller: _location,
      decoration: const InputDecoration(
        labelText: 'where?',
        border: OutlineInputBorder(),
        prefixIcon: Icon(Icons.place_outlined),
      ),
      validator: v.maxLength(300),
    );
  }

  Widget _buildDescriptionField() {
    return TextFormField(
      controller: _description,
      decoration: const InputDecoration(
        labelText: 'tell us more',
        border: OutlineInputBorder(),
        alignLabelWithHint: true,
      ),
      maxLines: 3,
      textCapitalization: TextCapitalization.sentences,
      validator: v.maxLength(2000),
    );
  }

  List<Widget> _buildLinksSection(ThemeData theme) {
    return [
      const Divider(),
      const SizedBox(height: 8),
      Text('links', style: theme.textTheme.labelLarge),
      const SizedBox(height: 12),
      TextFormField(
        controller: _whatsappLink,
        decoration: const InputDecoration(
          labelText: 'whatsapp group link (optional)',
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
          labelText: 'partiful link (optional)',
          border: const OutlineInputBorder(),
          prefixIcon: const Icon(Icons.celebration_outlined),
          helperText:
              _rsvpEnabled
                  ? 'consider using app RSVPs instead of partiful'
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
          labelText: 'other link (optional)',
          border: OutlineInputBorder(),
          prefixIcon: Icon(Icons.link),
        ),
        keyboardType: TextInputType.url,
        validator: v.optionalUrl(httpsOnly: true),
      ),
    ];
  }

  Widget _buildRsvpToggle(ThemeData theme) {
    return SwitchListTile(
      value: _rsvpEnabled,
      onChanged: (v) => setState(() => _rsvpEnabled = v),
      title: const Text('enable RSVPs'),
      subtitle:
          _rsvpEnabled && _partifulLink.text.trim().isNotEmpty
              ? Text(
                'you have a partiful link set — consider using one or the other',
                style: TextStyle(color: theme.colorScheme.tertiary),
              )
              : null,
      contentPadding: EdgeInsets.zero,
    );
  }

  List<Widget> _buildCoHostPicker(ThemeData theme) {
    return [
      const Divider(),
      const SizedBox(height: 8),
      Text('co-hosts', style: theme.textTheme.labelLarge),
      const SizedBox(height: 8),
      _CoHostPicker(
        selectedIds: _coHostIds,
        selectedNames: _coHostNames,
        onChanged: (ids) => setState(() => _coHostIds = ids),
        scrollController: _scrollController,
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    String dateFmt(DateTime d) =>
        DateFormat('EEE, MMM d, y').format(d).toLowerCase();
    final theme = Theme.of(context);

    final screenWidth = MediaQuery.sizeOf(context).width;
    final dialogWidth = screenWidth < 520 ? screenWidth - 48 : 480.0;

    return AlertDialog(
      title: Text(_isEdit ? 'edit event' : 'new event \u{1F331}'),
      contentPadding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
      clipBehavior: Clip.none,
      content: SizedBox(
        width: dialogWidth,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            controller: _scrollController,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildTitleField(),
                const SizedBox(height: 12),
                _buildNoFeesNote(theme),
                const SizedBox(height: 16),
                ..._buildDateTimeSection(dateFmt),
                const SizedBox(height: 16),
                _buildLocationField(),
                const SizedBox(height: 12),
                _buildDescriptionField(),
                const SizedBox(height: 16),
                ..._buildLinksSection(theme),
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                _buildRsvpToggle(theme),
                const SizedBox(height: 16),
                ..._buildCoHostPicker(theme),
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
        FilledButton(onPressed: _submit, child: Text(_isEdit ? 'save' : 'add')),
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

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.labelMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            Flexible(
              child: InkWell(
                onTap: onDateTap,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: chipColor,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.calendar_today_outlined, size: 14),
                      const SizedBox(width: 6),
                      Flexible(
                        child: Text(
                          date,
                          style: textStyle,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(width: 8),
            InkWell(
              onTap: onTimeTap,
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
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
        ),
      ],
    );
  }
}

class _CoHostResult {
  final String id;
  final String displayName;
  final String phone;
  const _CoHostResult({
    required this.id,
    required this.displayName,
    required this.phone,
  });
}

class _CoHostPicker extends ConsumerStatefulWidget {
  final Set<String> selectedIds;
  final Map<String, String> selectedNames;
  final ValueChanged<Set<String>> onChanged;
  final ScrollController? scrollController;

  const _CoHostPicker({
    required this.selectedIds,
    required this.selectedNames,
    required this.onChanged,
    this.scrollController,
  });

  @override
  ConsumerState<_CoHostPicker> createState() => _CoHostPickerState();
}

class _CoHostPickerState extends ConsumerState<_CoHostPicker> {
  final _controller = TextEditingController();
  List<_CoHostResult> _results = [];
  bool _searching = false;
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
                    phone: item['phone_number'] as String,
                  ),
                )
                .toList();
      });
      if (_results.isNotEmpty) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          final sc = widget.scrollController;
          if (sc != null && sc.hasClients) {
            sc.animateTo(
              sc.position.maxScrollExtent,
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
            );
          }
        });
      }
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
        TextField(
          controller: _controller,
          decoration: InputDecoration(
            hintText: 'search by name or phone…',
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
                      subtitle: Text(
                        r.phone,
                        style: TextStyle(
                          fontSize: 12,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
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
