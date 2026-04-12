import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logging/logging.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/day_view.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/calendar/list_view.dart';
import 'package:pda/screens/calendar/month_view.dart';
import 'package:pda/screens/calendar/week_view.dart';
import 'package:pda/screens/guest_add_event_dialog.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/submit_event.dart';
import 'package:pda/widgets/app_scaffold.dart';

final _log = Logger('CalendarScreen');

enum _CalendarView { month, week, day, list }

class CalendarScreen extends ConsumerStatefulWidget {
  const CalendarScreen({super.key});

  @override
  ConsumerState<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends ConsumerState<CalendarScreen> {
  _CalendarView _view = _CalendarView.month;
  String? _typeFilter;
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

  void _goToToday() {
    final now = DateTime.now();
    setState(() => _selectedDate = DateTime(now.year, now.month, now.day));
  }

  Future<void> _createEventForDate(DateTime date) async {
    setState(() => _selectedDate = date);
    await _openCreateEvent();
  }

  Future<void> _openCreateEvent() async {
    final user = ref.read(authProvider).value;

    if (user == null) {
      if (!mounted) return;
      final loggedIn = await showDialog<bool>(
        context: context,
        builder: (_) => const GuestAddEventDialog(),
      );
      if (loggedIn != true || !mounted) return;
    }

    final result = await showEventForm(context, initialDate: _selectedDate);
    if (result == null) return;

    try {
      final eventId = await submitNewEvent(ref, result);
      _log.info('created event $eventId');
      if (mounted) {
        showSnackBar(context, 'event created 🌱');
        context.push('/events/$eventId');
      }
    } catch (e, st) {
      _log.warning('failed to create event', e, st);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('something went wrong creating that event'),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final eventsAsync = ref.watch(eventsProvider);
    // Rebuild when auth changes (FAB tap checks auth) and re-fetch events
    // so authenticated users see member-only fields (location, links, RSVP).
    ref.listen(authProvider, (_, __) => ref.invalidate(eventsProvider));

    return AppScaffold(
      child: Column(
        children: [
          _CalendarToolbar(selected: _view, onSelected: _onViewChanged),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: SegmentedButton<String?>(
              segments: const [
                ButtonSegment(value: null, label: Text('all')),
                ButtonSegment(
                  value: EventType.official,
                  label: Text('official'),
                ),
                ButtonSegment(
                  value: EventType.community,
                  label: Text('community'),
                ),
              ],
              selected: {_typeFilter},
              onSelectionChanged: (s) => setState(() => _typeFilter = s.first),
              showSelectedIcon: false,
              style: const ButtonStyle(visualDensity: VisualDensity.compact),
            ),
          ),
          Expanded(
            child: eventsAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => const Center(
                child: Text('couldn\'t load events — try refreshing'),
              ),
              data: (events) => _buildView(events),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildView(List<Event> allEvents) {
    final events = _typeFilter == null
        ? allEvents
        : allEvents.where((e) => e.eventType == _typeFilter).toList();
    final user = ref.watch(authProvider).value;
    final startOnMonday = user?.weekStart == 'monday';
    switch (_view) {
      case _CalendarView.month:
        return MonthView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
          onToday: _goToToday,
          startOnMonday: startOnMonday,
          onDayTapped: (date) {
            setState(() {
              _selectedDate = date;
              _view = _CalendarView.day;
            });
          },
          onDayLongPressed: _createEventForDate,
        );
      case _CalendarView.week:
        return WeekView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
          onToday: _goToToday,
          startOnMonday: startOnMonday,
          onDayTapped: (date) {
            setState(() {
              _selectedDate = date;
              _view = _CalendarView.day;
            });
          },
          onDayLongPressed: _createEventForDate,
        );
      case _CalendarView.day:
        return DayView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
          onToday: _goToToday,
          onLongPress: () => _createEventForDate(_selectedDate),
        );
      case _CalendarView.list:
        return EventListView(events: events);
    }
  }
}

class _CalendarToolbar extends StatelessWidget {
  final _CalendarView selected;
  final ValueChanged<_CalendarView> onSelected;

  const _CalendarToolbar({required this.selected, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: SegmentedButton<_CalendarView>(
        segments: const [
          ButtonSegment(value: _CalendarView.month, label: Text('month')),
          ButtonSegment(value: _CalendarView.week, label: Text('week')),
          ButtonSegment(value: _CalendarView.day, label: Text('day')),
          ButtonSegment(value: _CalendarView.list, label: Text('list')),
        ],
        selected: {selected},
        onSelectionChanged: (s) => onSelected(s.first),
        showSelectedIcon: false,
      ),
    );
  }
}
