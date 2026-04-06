import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/day_view.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/calendar/list_view.dart';
import 'package:pda/screens/calendar/month_view.dart';
import 'package:pda/screens/calendar/week_view.dart';
import 'package:pda/screens/guest_add_event_dialog.dart';
import 'package:pda/utils/create_datetime_poll.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';

enum _CalendarView { month, week, day, list }

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

    final result = await showDialog<EventFormResult>(
      context: context,
      builder: (_) => EventFormDialog(initialDate: _selectedDate),
    );
    if (result == null) return;

    try {
      final api = ref.read(apiClientProvider);
      final response = await api.post(
        '/api/community/events/',
        data: result.data,
      );
      final eventId = (response.data as Map<String, dynamic>)['id'] as String;
      if (result.photo != null) {
        await uploadEventPhoto(ref, eventId, result.photo!);
      }
      if (result.datetimePollOptions.isNotEmpty) {
        await createDatetimePoll(
          ref: ref,
          eventId: eventId,
          eventTitle: result.data['title'] as String,
          options: result.datetimePollOptions,
        );
      }
      ref.invalidate(eventsProvider);
      if (mounted) {
        showSnackBar(context, 'event created 🌱');
        context.push('/events/$eventId');
      }
    } catch (e) {
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
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreateEvent,
        icon: const Icon(Icons.add, size: 18),
        label: const Text('add event'),
      ),
      child: Column(
        children: [
          _CalendarToolbar(
            selected: _view,
            onSelected: _onViewChanged,
            onToday: _goToToday,
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
          onDayLongPressed: _createEventForDate,
        );
      case _CalendarView.week:
        return WeekView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
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
  final VoidCallback onToday;

  const _CalendarToolbar({
    required this.selected,
    required this.onSelected,
    required this.onToday,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          if (selected != _CalendarView.list)
            _TodayIconButton(onPressed: onToday),
          Expanded(
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
          ),
        ],
      ),
    );
  }
}

class _TodayIconButton extends StatelessWidget {
  final VoidCallback onPressed;

  const _TodayIconButton({required this.onPressed});

  @override
  Widget build(BuildContext context) {
    final day = DateTime.now().day;
    final color = Theme.of(context).colorScheme.primary;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Tooltip(
        message: 'go to today',
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(8),
          child: Semantics(
            button: true,
            label: 'go to today',
            excludeSemantics: true,
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Icon(Icons.calendar_today_outlined, size: 28, color: color),
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Text(
                      '$day',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: color,
                        height: 1,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
