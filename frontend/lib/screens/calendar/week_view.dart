import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/calendar/placement_types.dart';
import 'package:pda/screens/calendar/week_placement_calculator.dart';

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

  static const double _dayLabelHeight = 52.0;
  static const double _chipHeight = 22.0;
  static const double _chipSpacing = 3.0;
  static const int _maxEventRows = 4;

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
    return '${DateFormat('MMM d').format(_weekStart)} \u2013 ${DateFormat('MMM d, y').format(weekEnd)}';
  }

  bool _isToday(DateTime day) {
    final now = DateTime.now();
    return day.year == now.year && day.month == now.month && day.day == now.day;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final days = _weekDays;
    final hasAnyEvents = days.any((d) {
      final ds = DateTime(d.year, d.month, d.day);
      final de = ds.add(const Duration(days: 1));
      return widget.events.any((e) {
        final s = e.startDatetime.toLocal();
        final en = (e.endDatetime ?? e.startDatetime).toLocal();
        return s.isBefore(de) && en.isAfter(ds);
      });
    });

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
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Container(
                decoration: BoxDecoration(
                  border: Border.all(
                    color: Theme.of(
                      context,
                    ).dividerColor.withValues(alpha: 0.4),
                    width: 0.5,
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Stack(
                  children: [
                    _WeekGrid(
                      days: days,
                      allEvents: widget.events,
                      isToday: _isToday,
                      dayLabelHeight: _dayLabelHeight,
                      chipHeight: _chipHeight,
                      chipSpacing: _chipSpacing,
                      maxEventRows: _maxEventRows,
                      onEventTapped: (e) => showEventDetail(context, e),
                      onDayTapped: widget.onDayTapped,
                    ),
                    if (!hasAnyEvents)
                      Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.event_note_outlined,
                              size: 40,
                              color: theme.colorScheme.onSurface.withValues(
                                alpha: 0.2,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'all quiet this week 🌿',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                color: theme.colorScheme.onSurface.withValues(
                                  alpha: 0.3,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
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

class _WeekGrid extends StatelessWidget {
  final List<DateTime> days;
  final List<Event> allEvents;
  final bool Function(DateTime) isToday;
  final double dayLabelHeight;
  final double chipHeight;
  final double chipSpacing;
  final int maxEventRows;
  final ValueChanged<Event> onEventTapped;
  final ValueChanged<DateTime>? onDayTapped;

  const _WeekGrid({
    required this.days,
    required this.allEvents,
    required this.isToday,
    required this.dayLabelHeight,
    required this.chipHeight,
    required this.chipSpacing,
    required this.maxEventRows,
    required this.onEventTapped,
    this.onDayTapped,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final placements =
        WeekPlacementCalculator(days: days, allEvents: allEvents).calculate();

    return LayoutBuilder(
      builder: (context, constraints) {
        final totalWidth = constraints.maxWidth;
        final colWidth = totalWidth / 7;

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Day header row
            SizedBox(
              height: dayLabelHeight,
              child: Row(
                children:
                    days.map((day) {
                      final today = isToday(day);
                      final bgColor =
                          today
                              ? theme.colorScheme.primary
                              : Colors.transparent;
                      final fgColor =
                          today
                              ? theme.colorScheme.onPrimary
                              : theme.colorScheme.onSurface;
                      return Expanded(
                        child: InkWell(
                          onTap:
                              onDayTapped != null
                                  ? () => onDayTapped!(day)
                                  : null,
                          borderRadius: BorderRadius.circular(8),
                          child: Container(
                            decoration: BoxDecoration(
                              color: bgColor,
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
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
                                    fontWeight: FontWeight.w600,
                                    color: fgColor,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    }).toList(),
              ),
            ),
            Divider(
              height: 1,
              color: theme.dividerColor.withValues(alpha: 0.4),
            ),
            // Event area
            Expanded(
              child: Stack(
                children: [
                  // Column dividers
                  Row(
                    children: List.generate(7, (col) {
                      return Expanded(
                        child: Container(
                          decoration: BoxDecoration(
                            border: Border(
                              right:
                                  col < 6
                                      ? BorderSide(
                                        color: theme.dividerColor.withValues(
                                          alpha: 0.4,
                                        ),
                                        width: 0.5,
                                      )
                                      : BorderSide.none,
                            ),
                          ),
                        ),
                      );
                    }),
                  ),
                  // Event spans
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Stack(
                      children:
                          placements
                              .where((p) => p.row < maxEventRows)
                              .map(
                                (p) => _buildEventChip(
                                  p,
                                  colWidth,
                                  days,
                                  chipHeight,
                                  chipSpacing,
                                  onEventTapped,
                                ),
                              )
                              .toList(),
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}

Widget _buildEventChip(
  SpanPlacement p,
  double colWidth,
  List<DateTime> days,
  double chipHeight,
  double chipSpacing,
  ValueChanged<Event> onEventTapped,
) {
  final left = p.startCol * colWidth;
  final width = (p.endCol - p.startCol + 1) * colWidth;
  final top = p.row * (chipHeight + chipSpacing);
  final colors = eventColors(p.event.id);

  final continuesFromPrev =
      p.startCol == 0 &&
      p.event.startDatetime.toLocal().isBefore(
        DateTime(days[0].year, days[0].month, days[0].day),
      );
  final eEnd = (p.event.endDatetime ?? p.event.startDatetime).toLocal();
  final continuesToNext =
      p.endCol == 6 &&
      eEnd.isAfter(DateTime(days[6].year, days[6].month, days[6].day + 1));

  final isMultiDay =
      p.startCol != p.endCol || continuesFromPrev || continuesToNext;

  final eStart = p.event.startDatetime.toLocal();
  final subLabel =
      isMultiDay
          ? '${DateFormat('MMM d').format(eStart)} \u2013 ${DateFormat('MMM d').format(eEnd)}'
          : DateFormat('h:mm a').format(eStart);

  return Positioned(
    left: left,
    top: top,
    width: width,
    height: chipHeight,
    child: Semantics(
      button: true,
      label: p.event.title,
      excludeSemantics: true,
      child: InkWell(
        onTap: () => onEventTapped(p.event),
        splashColor: Colors.transparent,
        highlightColor: Colors.transparent,
        child: Container(
          margin: EdgeInsets.only(
            left: continuesFromPrev ? 0 : 2,
            right: continuesToNext ? 0 : 2,
          ),
          decoration: BoxDecoration(
            color: colors.$1,
            borderRadius: BorderRadius.horizontal(
              left: continuesFromPrev ? Radius.zero : const Radius.circular(6),
              right: continuesToNext ? Radius.zero : const Radius.circular(6),
            ),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: p.event.title,
                  style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: FontWeight.w500,
                    color: colors.$2,
                  ),
                ),
                TextSpan(
                  text: '  $subLabel',
                  style: TextStyle(
                    fontSize: 10,
                    color: colors.$2.withValues(alpha: 0.8),
                  ),
                ),
              ],
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ),
    ),
  );
}
