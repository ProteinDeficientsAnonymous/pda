import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';

const double _kHourHeight = 60.0;
const double _kTimeGutterWidth = 56.0;
const double _kMinEventHeight = 30.0;
const int _kScrollToHour = 8;

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
  late ScrollController _scrollController;
  late DateTime _weekStart;

  @override
  void initState() {
    super.initState();
    _weekStart = _mondayOf(widget.selectedDate);
    _scrollController = ScrollController(
      initialScrollOffset: _kScrollToHour * _kHourHeight,
    );
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
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

  String _hourLabel(int hour) {
    if (hour == 0) return '12am';
    if (hour < 12) return '${hour}am';
    if (hour == 12) return '12pm';
    return '${hour - 12}pm';
  }

  List<Event> _eventsForDay(DateTime day) {
    return widget.events.where((e) {
      final start = e.startDatetime.toLocal();
      final end = e.endDatetime.toLocal();
      final dayStart = DateTime(day.year, day.month, day.day);
      final dayEnd = dayStart.add(const Duration(days: 1));
      return start.isBefore(dayEnd) && end.isAfter(dayStart);
    }).toList();
  }

  bool get _hasAnyEventsThisWeek {
    return _weekDays.any((day) => _eventsForDay(day).isNotEmpty);
  }

  double _eventTopOffset(Event event, DateTime day) {
    final dayStart = DateTime(day.year, day.month, day.day);
    final start = event.startDatetime.toLocal();
    final effectiveStart = start.isBefore(dayStart) ? dayStart : start;
    final minutesFromMidnight =
        effectiveStart.hour * 60 + effectiveStart.minute;
    return minutesFromMidnight * 1.0;
  }

  double _eventHeight(Event event, DateTime day) {
    final dayStart = DateTime(day.year, day.month, day.day);
    final dayEnd = dayStart.add(const Duration(days: 1));
    final start = event.startDatetime.toLocal();
    final end = event.endDatetime.toLocal();
    final effectiveStart = start.isBefore(dayStart) ? dayStart : start;
    final effectiveEnd = end.isAfter(dayEnd) ? dayEnd : end;
    final durationMinutes =
        effectiveEnd.difference(effectiveStart).inMinutes.toDouble();
    return durationMinutes < _kMinEventHeight
        ? _kMinEventHeight
        : durationMinutes;
  }

  Widget _buildEventBlockContent(
    Event event,
    double height,
    DateFormat timeFmt,
    DateTime startLocal,
  ) {
    if (height < 20) {
      return Text(
        event.title,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          event.title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
        ),
        Text(
          timeFmt.format(startLocal),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 10),
        ),
      ],
    );
  }

  Widget _buildHeaderRow(List<DateTime> days, double columnWidth) {
    final theme = Theme.of(context);

    final dayHeaders =
        days.map((day) {
          final isToday = _isToday(day);
          final headerBackground =
              isToday ? theme.colorScheme.primary : Colors.transparent;
          final headerForeground =
              isToday
                  ? theme.colorScheme.onPrimary
                  : theme.colorScheme.onSurface;

          return SizedBox(
            width: columnWidth,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                color: headerBackground,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Column(
                children: [
                  Text(
                    DateFormat('EEE').format(day),
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: headerForeground,
                    ),
                  ),
                  Text(
                    '${day.day}',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: headerForeground,
                    ),
                  ),
                ],
              ),
            ),
          );
        }).toList();

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [const SizedBox(width: _kTimeGutterWidth), ...dayHeaders],
    );
  }

  Widget _buildHourRow(
    int hour,
    List<DateTime> days,
    double columnWidth,
    ThemeData theme,
  ) {
    final dayCells =
        days.map((day) {
          final dayEvents =
              _eventsForDay(day).where((e) {
                final top = _eventTopOffset(e, day);
                return top >= hour * _kHourHeight &&
                    top < (hour + 1) * _kHourHeight;
              }).toList();

          return SizedBox(
            width: columnWidth,
            height: _kHourHeight,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: Divider(
                    height: 1,
                    thickness: 0.5,
                    color: theme.dividerColor,
                  ),
                ),
                ...dayEvents.map((e) {
                  final top = _eventTopOffset(e, day) - hour * _kHourHeight;
                  final height = _eventHeight(e, day);
                  final startLocal = e.startDatetime.toLocal();
                  final timeFmt = DateFormat('h:mm a');
                  return Positioned(
                    top: top,
                    left: 1,
                    right: 1,
                    height: height,
                    child: GestureDetector(
                      onTap: () => showEventDetail(context, e),
                      child: Container(
                        decoration: BoxDecoration(
                          color: theme.colorScheme.primaryContainer,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 4,
                          vertical: 2,
                        ),
                        child: _buildEventBlockContent(
                          e,
                          height,
                          timeFmt,
                          startLocal,
                        ),
                      ),
                    ),
                  );
                }),
              ],
            ),
          );
        }).toList();

    return SizedBox(
      height: _kHourHeight,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: _kTimeGutterWidth,
            height: _kHourHeight,
            child: Align(
              alignment: Alignment.topRight,
              child: Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Transform.translate(
                  offset: const Offset(0, -8),
                  child: Text(
                    _hourLabel(hour),
                    textAlign: TextAlign.right,
                    style: const TextStyle(fontSize: 10, color: Colors.grey),
                  ),
                ),
              ),
            ),
          ),
          ...dayCells,
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

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
        const Divider(height: 1),
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final availableWidth = constraints.maxWidth - _kTimeGutterWidth;
              final columnWidth = availableWidth / 7;
              final days = _weekDays;

              return Stack(
                children: [
                  Column(
                    children: [
                      _buildHeaderRow(days, columnWidth),
                      const Divider(height: 1),
                      Expanded(
                        child: ListView.builder(
                          controller: _scrollController,
                          itemCount: 24,
                          itemBuilder:
                              (context, hour) =>
                                  _buildHourRow(hour, days, columnWidth, theme),
                        ),
                      ),
                    ],
                  ),
                  if (!_hasAnyEventsThisWeek)
                    Positioned.fill(
                      child: IgnorePointer(
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.calendar_today_outlined,
                                size: 48,
                                color: theme.colorScheme.onSurface.withValues(
                                  alpha: 0.3,
                                ),
                              ),
                              const SizedBox(height: 12),
                              Text(
                                'No events this week',
                                style: theme.textTheme.bodyLarge?.copyWith(
                                  color: theme.colorScheme.onSurface.withValues(
                                    alpha: 0.4,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }
}
