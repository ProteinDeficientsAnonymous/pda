import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/calendar/week_view_wide.dart';
import 'package:pda/screens/calendar/week_view_narrow.dart';

class WeekView extends StatefulWidget {
  final List<Event> events;
  final DateTime selectedDate;
  final ValueChanged<DateTime> onDateChanged;
  final ValueChanged<DateTime>? onDayTapped;

  const WeekView({
    super.key,
    required this.events,
    required this.selectedDate,
    required this.onDateChanged,
    this.onDayTapped,
  });

  @override
  State<WeekView> createState() => _WeekViewState();
}

class _WeekViewState extends State<WeekView> {
  late DateTime _weekStart;

  @override
  void initState() {
    super.initState();
    _weekStart = _mondayOf(widget.selectedDate);
  }

  @override
  void didUpdateWidget(WeekView oldWidget) {
    super.didUpdateWidget(oldWidget);
    final newWeekStart = _mondayOf(widget.selectedDate);
    if (newWeekStart != _weekStart) {
      setState(() => _weekStart = newWeekStart);
    }
  }

  DateTime _mondayOf(DateTime date) {
    final d = DateTime(date.year, date.month, date.day);
    return d.subtract(Duration(days: d.weekday - 1));
  }

  void _goToPreviousWeek() {
    setState(() => _weekStart = _weekStart.subtract(const Duration(days: 7)));
  }

  void _goToNextWeek() {
    setState(() => _weekStart = _weekStart.add(const Duration(days: 7)));
  }

  List<DateTime> get _weekDays =>
      List.generate(7, (i) => _weekStart.add(Duration(days: i)));

  String _weekRangeLabel() {
    final weekEnd = _weekStart.add(const Duration(days: 6));
    return '${DateFormat('MMM d').format(_weekStart).toLowerCase()} \u2013 ${DateFormat('MMM d, y').format(weekEnd).toLowerCase()}';
  }

  bool _isToday(DateTime day) {
    final now = DateTime.now();
    return day.year == now.year && day.month == now.month && day.day == now.day;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final days = _weekDays;
    final isWide = MediaQuery.sizeOf(context).width >= 600;

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onHorizontalDragEnd: (details) {
        if ((details.primaryVelocity ?? 0) > 0) {
          _goToPreviousWeek();
        } else if ((details.primaryVelocity ?? 0) < 0) {
          _goToNextWeek();
        }
      },
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_left),
                  onPressed: _goToPreviousWeek,
                  tooltip: 'previous week',
                ),
                Expanded(
                  child: Text(
                    _weekRangeLabel(),
                    textAlign: TextAlign.center,
                    style: theme.textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.chevron_right),
                  onPressed: _goToNextWeek,
                  tooltip: 'next week',
                ),
              ],
            ),
          ),
          Expanded(
            child: isWide
                ? WideWeekGrid(
                    days: days,
                    events: widget.events,
                    isToday: _isToday,
                    onEventTapped: (e) => showEventDetail(context, e),
                    onDayTapped: widget.onDayTapped,
                  )
                : NarrowWeekGrid(
                    days: days,
                    events: widget.events,
                    isToday: _isToday,
                    onEventTapped: (e) => showEventDetail(context, e),
                    onDayTapped: widget.onDayTapped,
                  ),
          ),
        ],
      ),
    );
  }
}
