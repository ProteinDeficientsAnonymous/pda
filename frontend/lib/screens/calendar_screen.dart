import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
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

  @override
  Widget build(BuildContext context) {
    final eventsAsync = ref.watch(eventsProvider);

    return AppScaffold(
      title: 'Community Calendar',
      child: Column(
        children: [
          _ViewSwitcher(
            selected: _view,
            onSelected: (v) => setState(() => _view = v),
          ),
          Expanded(
            child: eventsAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Failed to load events: $e')),
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
        return MonthView(events: events);
      case _CalendarView.week:
        return WeekView(events: events);
      case _CalendarView.day:
        return DayView(events: events);
    }
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
