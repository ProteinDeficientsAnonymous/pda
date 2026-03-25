import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';

const double _kHourHeight = 60.0;
const double _kTimeGutterWidth = 56.0;
const double _kMinEventHeight = 30.0;
const double _kTotalHeight = _kHourHeight * 24;
const int _kScrollToHour = 8;

class WeekView extends StatefulWidget {
  final List<Event> events;
  const WeekView({super.key, required this.events});

  @override
  State<WeekView> createState() => _WeekViewState();
}

class _WeekViewState extends State<WeekView> {
  late ScrollController _scrollController;
  late DateTime _weekStart;

  @override
  void initState() {
    super.initState();
    _weekStart = _mondayOf(DateTime.now());
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

  Widget _buildEventBlock(Event event, DateTime day, double columnWidth) {
    final theme = Theme.of(context);
    final top = _eventTopOffset(event, day);
    final height = _eventHeight(event, day);
    final startLocal = event.startDatetime.toLocal();
    final timeFmt = DateFormat('h:mm a');

    return Positioned(
      top: top,
      left: 1,
      right: 1,
      height: height,
      child: GestureDetector(
        onTap: () => debugPrint(
          'Event tapped: ${event.title} (id=${event.id})',
        ),
        child: Container(
          decoration: BoxDecoration(
            color: theme.colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(4),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
          child: _buildEventBlockContent(event, height, timeFmt, startLocal),
        ),
      ),
    );
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

  Widget _buildDayColumn(DateTime day, double columnWidth) {
    final theme = Theme.of(context);
    final isToday = _isToday(day);
    final dayEvents = _eventsForDay(day);

    final headerBackground =
        isToday ? theme.colorScheme.primary : Colors.transparent;
    final headerForeground = isToday
        ? theme.colorScheme.onPrimary
        : theme.colorScheme.onSurface;

    return SizedBox(
      width: columnWidth,
      child: Column(
        children: [
          Container(
            width: double.infinity,
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
          Expanded(
            child: Stack(
              children: [
                // Hour grid lines
                ...List.generate(24, (hour) {
                  return Positioned(
                    top: hour * _kHourHeight,
                    left: 0,
                    right: 0,
                    child: Divider(
                      height: 1,
                      thickness: 0.5,
                      color: theme.dividerColor,
                    ),
                  );
                }),
                // Event blocks
                ...dayEvents.map((e) => _buildEventBlock(e, day, columnWidth)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTimeGutter() {
    return SizedBox(
      width: _kTimeGutterWidth,
      child: Column(
        children: [
          // Spacer to match the day header height
          const SizedBox(height: 60),
          SizedBox(
            height: _kTotalHeight,
            child: Stack(
              children: List.generate(24, (hour) {
                return Positioned(
                  top: hour * _kHourHeight - 8,
                  left: 0,
                  right: 4,
                  child: Text(
                    _hourLabel(hour),
                    textAlign: TextAlign.right,
                    style: const TextStyle(fontSize: 10, color: Colors.grey),
                  ),
                );
              }),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      children: [
        // Navigation header
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
                child: Text(
                  _weekRangeLabel(),
                  textAlign: TextAlign.center,
                  style: theme.textTheme.titleMedium,
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
        // Calendar grid
        Expanded(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final availableWidth = constraints.maxWidth - _kTimeGutterWidth;
              final columnWidth = availableWidth / 7;

              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Time gutter (fixed, not scrollable horizontally)
                  SingleChildScrollView(
                    controller: _scrollController,
                    child: _buildTimeGutter(),
                  ),
                  // Day columns
                  Expanded(
                    child: SingleChildScrollView(
                      controller: _scrollController,
                      child: SizedBox(
                        height: _kTotalHeight + 60,
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: _weekDays.map((day) {
                            return SizedBox(
                              width: columnWidth,
                              height: _kTotalHeight + 60,
                              child: _buildDayColumn(day, columnWidth),
                            );
                          }).toList(),
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
