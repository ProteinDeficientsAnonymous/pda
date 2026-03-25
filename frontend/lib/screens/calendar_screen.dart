import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/day_view.dart';
import 'package:pda/screens/calendar/month_view.dart';
import 'package:pda/screens/calendar/week_view.dart';
import 'package:pda/widgets/app_scaffold.dart';

enum _CalendarView { month, week, day }

class CalendarScreen extends ConsumerStatefulWidget {
  const CalendarScreen({super.key});

  @override
  ConsumerState<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends ConsumerState<CalendarScreen> {
  _CalendarView _view = _CalendarView.month;
  late DateTime _selectedDate;

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _selectedDate = DateTime(now.year, now.month, now.day);
  }

  void _onDateChanged(DateTime date) {
    setState(() => _selectedDate = date);
  }

  void _onViewChanged(_CalendarView view) {
    setState(() => _view = view);
  }

  Future<void> _openCreateEvent() async {
    final result = await showDialog<Map<String, String>>(
      context: context,
      builder: (_) => const _CreateEventDialog(),
    );
    if (result == null) return;

    try {
      final api = ref.read(apiClientProvider);
      await api.post('/api/community/events/', data: result);
      ref.invalidate(eventsProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to create event: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final eventsAsync = ref.watch(eventsProvider);
    final user = ref.watch(authProvider).valueOrNull;

    return AppScaffold(
      title: 'Community Calendar',
      child: Stack(
        children: [
          Column(
            children: [
              _ViewSwitcher(selected: _view, onSelected: _onViewChanged),
              Expanded(
                child: eventsAsync.when(
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (e, _) => Center(child: Text('Failed to load events: $e')),
                  data: (events) => _buildView(events),
                ),
              ),
            ],
          ),
          if (user != null)
            Positioned(
              bottom: 24,
              right: 24,
              child: FloatingActionButton.extended(
                onPressed: _openCreateEvent,
                icon: const Icon(Icons.add),
                label: const Text('Add event'),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildView(events) {
    switch (_view) {
      case _CalendarView.month:
        return MonthView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
          onDayTapped: (date) {
            setState(() {
              _selectedDate = date;
              _view = _CalendarView.day;
            });
          },
        );
      case _CalendarView.week:
        return WeekView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
        );
      case _CalendarView.day:
        return DayView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
        );
    }
  }
}

class _CreateEventDialog extends StatefulWidget {
  const _CreateEventDialog();

  @override
  State<_CreateEventDialog> createState() => _CreateEventDialogState();
}

class _CreateEventDialogState extends State<_CreateEventDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _title;
  late final TextEditingController _description;
  late final TextEditingController _location;
  late final TextEditingController _start;
  late final TextEditingController _end;

  @override
  void initState() {
    super.initState();
    final iso = DateFormat("yyyy-MM-dd'T'HH:mm");
    final now = DateTime.now();
    final roundedStart = DateTime(now.year, now.month, now.day, now.hour + 1);
    final roundedEnd = roundedStart.add(const Duration(hours: 1));
    _title = TextEditingController();
    _description = TextEditingController();
    _location = TextEditingController();
    _start = TextEditingController(text: iso.format(roundedStart));
    _end = TextEditingController(text: iso.format(roundedEnd));
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _location.dispose();
    _start.dispose();
    _end.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.of(context).pop({
      'title': _title.text.trim(),
      'description': _description.text.trim(),
      'location': _location.text.trim(),
      'start_datetime': _start.text.trim(),
      'end_datetime': _end.text.trim(),
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add event'),
      content: SizedBox(
        width: 480,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _title,
                  decoration: const InputDecoration(
                    labelText: 'Title *',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) => v == null || v.trim().isEmpty ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _start,
                  decoration: const InputDecoration(
                    labelText: 'Start (YYYY-MM-DDTHH:MM)',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Required';
                    if (DateTime.tryParse(v.trim()) == null) return 'Invalid date';
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _end,
                  decoration: const InputDecoration(
                    labelText: 'End (YYYY-MM-DDTHH:MM)',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Required';
                    if (DateTime.tryParse(v.trim()) == null) return 'Invalid date';
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _description,
                  decoration: const InputDecoration(
                    labelText: 'Description',
                    border: OutlineInputBorder(),
                  ),
                  maxLines: 3,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _location,
                  decoration: const InputDecoration(
                    labelText: 'Location',
                    border: OutlineInputBorder(),
                  ),
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
        FilledButton(onPressed: _submit, child: const Text('Add')),
      ],
    );
  }
}

class _ViewSwitcher extends StatelessWidget {
  final _CalendarView selected;
  final ValueChanged<_CalendarView> onSelected;

  const _ViewSwitcher({required this.selected, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: SegmentedButton<_CalendarView>(
        segments: const [
          ButtonSegment(value: _CalendarView.month, label: Text('Month')),
          ButtonSegment(value: _CalendarView.week, label: Text('Week')),
          ButtonSegment(value: _CalendarView.day, label: Text('Day')),
        ],
        selected: {selected},
        onSelectionChanged: (s) => onSelected(s.first),
      ),
    );
  }
}
