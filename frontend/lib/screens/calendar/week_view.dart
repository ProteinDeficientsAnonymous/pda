import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';

class WeekView extends StatefulWidget {
  final List<Event> events;
  final DateTime selectedDate;
  final ValueChanged<DateTime> onDateChanged;

  const WeekView({
    super.key,
    required this.events,
    required this.selectedDate,
    required this.onDateChanged,
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

  DateTime _mondayOf(DateTime date) {
    final d = DateTime(date.year, date.month, date.day);
    return d.subtract(Duration(days: d.weekday - 1));
  }

  void _goToPreviousWeek() {
    setState(() {
      _weekStart = _weekStart.subtract(const Duration(days: 7));
    });
  }

  void _goToNextWeek() {
    setState(() {
      _weekStart = _weekStart.add(const Duration(days: 7));
    });
  }

  Future<void> _openDatePicker() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _weekStart,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked == null) return;
    setState(() => _weekStart = _mondayOf(picked));
    widget.onDateChanged(picked);
  }

  List<DateTime> get _weekDays {
    return List.generate(7, (i) => _weekStart.add(Duration(days: i)));
  }

  String _weekRangeLabel() {
    final weekEnd = _weekStart.add(const Duration(days: 6));
    final startFmt = DateFormat('MMM d');
    final endFmt = DateFormat('MMM d, y');
    return '${startFmt.format(_weekStart)} \u2013 ${endFmt.format(weekEnd)}';
  }

  bool _isToday(DateTime day) {
    final now = DateTime.now();
    return day.year == now.year && day.month == now.month && day.day == now.day;
  }

  List<Event> _eventsForDay(DateTime day) {
    final dayStart = DateTime(day.year, day.month, day.day);
    final dayEnd = dayStart.add(const Duration(days: 1));
    final results =
        widget.events.where((e) {
          final start = e.startDatetime.toLocal();
          final end = e.endDatetime.toLocal();
          return start.isBefore(dayEnd) && end.isAfter(dayStart);
        }).toList();
    results.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));
    return results;
  }

  Widget _buildBody(BuildContext context, List<DateTime> days) {
    final allEvents = days.expand((d) => _eventsForDay(d));
    final hasAnyEvents = allEvents.isNotEmpty;
    final columns = Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children:
          days.map((day) {
            return Expanded(
              child: _DayEventsColumn(day: day, events: _eventsForDay(day)),
            );
          }).toList(),
    );

    if (hasAnyEvents) return columns;

    return Stack(
      children: [
        columns,
        Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.calendar_today_outlined,
                size: 40,
                color: Theme.of(
                  context,
                ).colorScheme.onSurface.withValues(alpha: 0.2),
              ),
              const SizedBox(height: 8),
              Text(
                'No events this week',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(
                    context,
                  ).colorScheme.onSurface.withValues(alpha: 0.3),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final days = _weekDays;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              IconButton(
                icon: const Icon(Icons.chevron_left),
                onPressed: _goToPreviousWeek,
                tooltip: 'Previous week',
              ),
              Expanded(
                child: GestureDetector(
                  onTap: _openDatePicker,
                  child: Text(
                    _weekRangeLabel(),
                    textAlign: TextAlign.center,
                    style: theme.textTheme.titleMedium,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.chevron_right),
                onPressed: _goToNextWeek,
                tooltip: 'Next week',
              ),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: Container(
                decoration: BoxDecoration(
                  border: Border.all(
                    color: Theme.of(context).dividerColor,
                    width: 0.5,
                  ),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  children: [
                    _DayHeaderRow(days: days, isToday: _isToday),
                    Divider(height: 1, color: Theme.of(context).dividerColor),
                    Expanded(child: _buildBody(context, days)),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _DayHeaderRow extends StatelessWidget {
  final List<DateTime> days;
  final bool Function(DateTime) isToday;

  const _DayHeaderRow({required this.days, required this.isToday});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children:
          days.map((day) {
            final today = isToday(day);
            final bgColor =
                today ? theme.colorScheme.primary : Colors.transparent;
            final fgColor =
                today
                    ? theme.colorScheme.onPrimary
                    : theme.colorScheme.onSurface;
            return Expanded(
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Column(
                  children: [
                    Text(
                      DateFormat('EEE').format(day),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: fgColor,
                      ),
                    ),
                    Text(
                      '${day.day}',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: fgColor,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
    );
  }
}

class _DayEventsColumn extends StatelessWidget {
  final DateTime day;
  final List<Event> events;

  const _DayEventsColumn({required this.day, required this.events});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (events.isEmpty) {
      return Container(
        decoration: BoxDecoration(
          border: Border(
            right: BorderSide(color: theme.dividerColor, width: 0.5),
          ),
        ),
        padding: const EdgeInsets.symmetric(vertical: 8),
        alignment: Alignment.topCenter,
        child: Text(
          '\u2014',
          style: TextStyle(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.3),
            fontSize: 14,
          ),
        ),
      );
    }

    return Container(
      decoration: BoxDecoration(
        border: Border(
          right: BorderSide(color: theme.dividerColor, width: 0.5),
        ),
      ),
      padding: const EdgeInsets.all(3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: events.map((e) => _WeekEventChip(event: e)).toList(),
      ),
    );
  }
}

class _WeekEventChip extends StatelessWidget {
  final Event event;

  const _WeekEventChip({required this.event});

  @override
  Widget build(BuildContext context) {
    final colors = eventColors(event.id);
    final bgColor = colors.$1;
    final fgColor = colors.$2;
    final startLocal = event.startDatetime.toLocal();
    final timeLabel = DateFormat('h:mm a').format(startLocal);

    return GestureDetector(
      onTap: () => showEventDetail(context, event),
      child: Container(
        margin: const EdgeInsets.only(bottom: 3),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(4),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              event.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: fgColor,
              ),
            ),
            Text(
              timeLabel,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 10,
                color: fgColor.withValues(alpha: 0.8),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
