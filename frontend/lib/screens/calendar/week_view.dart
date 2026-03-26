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

  static const double _dayLabelHeight = 52.0;
  static const double _chipHeight = 22.0;
  static const double _chipSpacing = 3.0;
  static const int _maxEventRows = 4;

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
    setState(() => _weekStart = _weekStart.subtract(const Duration(days: 7)));
  }

  void _goToNextWeek() {
    setState(() => _weekStart = _weekStart.add(const Duration(days: 7)));
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
        final en = e.endDatetime.toLocal();
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
                    ),
                    if (!hasAnyEvents)
                      Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.calendar_today_outlined,
                              size: 40,
                              color: theme.colorScheme.onSurface.withValues(
                                alpha: 0.2,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'No events this week',
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

class _SpanPlacement {
  final Event event;
  final int startCol;
  final int endCol;
  final int row;

  const _SpanPlacement({
    required this.event,
    required this.startCol,
    required this.endCol,
    required this.row,
  });
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

  const _WeekGrid({
    required this.days,
    required this.allEvents,
    required this.isToday,
    required this.dayLabelHeight,
    required this.chipHeight,
    required this.chipSpacing,
    required this.maxEventRows,
    required this.onEventTapped,
  });

  bool _dayContains(DateTime day, Event e) {
    final dayStart = DateTime(day.year, day.month, day.day);
    final dayEnd = dayStart.add(const Duration(days: 1));
    final start = e.startDatetime.toLocal();
    final end = e.endDatetime.toLocal();
    return start.isBefore(dayEnd) && end.isAfter(dayStart);
  }

  List<_SpanPlacement> _computePlacements() {
    final seen = <String>{};
    final rowEvents = <Event>[];
    for (final day in days) {
      for (final e in allEvents) {
        if (!seen.contains(e.id) && _dayContains(day, e)) {
          seen.add(e.id);
          rowEvents.add(e);
        }
      }
    }
    rowEvents.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));

    final placements = <_SpanPlacement>[];
    final occupied = List.filled(7, -1);

    for (final e in rowEvents) {
      final eStart = e.startDatetime.toLocal();
      final eEnd = e.endDatetime.toLocal();

      int startCol = 0;
      for (var c = 0; c < 7; c++) {
        final d = days[c];
        final ds = DateTime(d.year, d.month, d.day);
        final es = DateTime(eStart.year, eStart.month, eStart.day);
        if (ds.isAtSameMomentAs(es) || ds.isAfter(es)) {
          startCol = c;
          break;
        }
      }

      int endCol = 6;
      for (var c = 6; c >= 0; c--) {
        final d = days[c];
        final ds = DateTime(d.year, d.month, d.day);
        final lastDay =
            eEnd.hour == 0 && eEnd.minute == 0
                ? DateTime(eEnd.year, eEnd.month, eEnd.day - 1)
                : DateTime(eEnd.year, eEnd.month, eEnd.day);
        if (ds.isAtSameMomentAs(lastDay) || ds.isBefore(lastDay)) {
          endCol = c;
          break;
        }
      }

      int slotRow = 0;
      while (true) {
        bool fits = true;
        for (var c = startCol; c <= endCol; c++) {
          if (occupied[c] >= slotRow) {
            fits = false;
            break;
          }
        }
        if (fits) break;
        slotRow++;
      }
      for (var c = startCol; c <= endCol; c++) {
        occupied[c] = slotRow;
      }

      placements.add(
        _SpanPlacement(
          event: e,
          startCol: startCol,
          endCol: endCol,
          row: slotRow,
        ),
      );
    }

    return placements;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final placements = _computePlacements();

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
                        child: Container(
                          decoration: BoxDecoration(
                            color: bgColor,
                            borderRadius: BorderRadius.circular(6),
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
                                  fontWeight: FontWeight.bold,
                                  color: fgColor,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
              ),
            ),
            Divider(height: 1, color: theme.dividerColor),
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
                                        color: theme.dividerColor,
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
                          placements.where((p) => p.row < maxEventRows).map((
                            p,
                          ) {
                            final left = p.startCol * colWidth;
                            final width =
                                (p.endCol - p.startCol + 1) * colWidth;
                            final top = p.row * (chipHeight + chipSpacing);
                            final colors = eventColors(p.event.id);

                            final continuesFromPrev =
                                p.startCol == 0 &&
                                p.event.startDatetime.toLocal().isBefore(
                                  DateTime(
                                    days[0].year,
                                    days[0].month,
                                    days[0].day,
                                  ),
                                );
                            final continuesToNext =
                                p.endCol == 6 &&
                                p.event.endDatetime.toLocal().isAfter(
                                  DateTime(
                                    days[6].year,
                                    days[6].month,
                                    days[6].day + 1,
                                  ),
                                );

                            final isMultiDay =
                                p.startCol != p.endCol ||
                                continuesFromPrev ||
                                continuesToNext;

                            final eStart = p.event.startDatetime.toLocal();
                            final eEnd = p.event.endDatetime.toLocal();
                            final subLabel =
                                isMultiDay
                                    ? '${DateFormat('MMM d').format(eStart)} – ${DateFormat('MMM d').format(eEnd)}'
                                    : DateFormat('h:mm a').format(eStart);

                            return Positioned(
                              left: left,
                              top: top,
                              width: width,
                              height: chipHeight,
                              child: GestureDetector(
                                onTap: () => onEventTapped(p.event),
                                child: Container(
                                  margin: EdgeInsets.only(
                                    left: continuesFromPrev ? 0 : 2,
                                    right: continuesToNext ? 0 : 2,
                                  ),
                                  decoration: BoxDecoration(
                                    color: colors.$1,
                                    borderRadius: BorderRadius.horizontal(
                                      left:
                                          continuesFromPrev
                                              ? Radius.zero
                                              : const Radius.circular(4),
                                      right:
                                          continuesToNext
                                              ? Radius.zero
                                              : const Radius.circular(4),
                                    ),
                                  ),
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 5,
                                  ),
                                  child: Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          p.event.title,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                            color: colors.$2,
                                          ),
                                        ),
                                      ),
                                      if (isMultiDay) const SizedBox(width: 4),
                                      Text(
                                        subLabel,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          fontSize: 10,
                                          color: colors.$2.withValues(
                                            alpha: 0.8,
                                          ),
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
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
