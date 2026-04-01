import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/calendar/placement_types.dart';
import 'package:pda/config/constants.dart';

class MonthView extends StatefulWidget {
  final List<Event> events;
  final DateTime selectedDate;
  final ValueChanged<DateTime> onDateChanged;
  final ValueChanged<DateTime> onDayTapped;

  const MonthView({
    super.key,
    required this.events,
    required this.selectedDate,
    required this.onDateChanged,
    required this.onDayTapped,
  });

  @override
  State<MonthView> createState() => _MonthViewState();
}

class _MonthViewState extends State<MonthView> {
  late DateTime _focusedMonth;

  static const List<String> _dayHeaders = [
    'sun',
    'mon',
    'tue',
    'wed',
    'thu',
    'fri',
    'sat',
  ];

  static const int _maxEventRows = 10;
  static const double _dayLabelHeight = 20.0;
  static const double _chipHeight = 20.0;
  static const double _chipSpacing = 3.0;
  @override
  void initState() {
    super.initState();
    _focusedMonth = DateTime(
      widget.selectedDate.year,
      widget.selectedDate.month,
    );
  }

  @override
  void didUpdateWidget(MonthView oldWidget) {
    super.didUpdateWidget(oldWidget);
    final d = widget.selectedDate;
    final newMonth = DateTime(d.year, d.month);
    if (newMonth != _focusedMonth) {
      setState(() => _focusedMonth = newMonth);
    }
  }

  void _goToPreviousMonth() {
    setState(() {
      _focusedMonth = DateTime(_focusedMonth.year, _focusedMonth.month - 1);
    });
  }

  void _goToNextMonth() {
    setState(() {
      _focusedMonth = DateTime(_focusedMonth.year, _focusedMonth.month + 1);
    });
  }

  List<DateTime> _buildGridDays() {
    final firstOfMonth = DateTime(_focusedMonth.year, _focusedMonth.month, 1);
    final lastOfMonth = DateTime(
      _focusedMonth.year,
      _focusedMonth.month + 1,
      0,
    );

    final leadingDays = firstOfMonth.weekday % 7;
    final trailingDays = 6 - (lastOfMonth.weekday % 7);

    final days = <DateTime>[];
    for (var i = leadingDays; i > 0; i--) {
      days.add(firstOfMonth.subtract(Duration(days: i)));
    }
    for (var d = 1; d <= lastOfMonth.day; d++) {
      days.add(DateTime(_focusedMonth.year, _focusedMonth.month, d));
    }
    for (var i = 1; i <= trailingDays; i++) {
      days.add(lastOfMonth.add(Duration(days: i)));
    }
    return days;
  }

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  bool _isToday(DateTime day) => _isSameDay(day, DateTime.now());

  bool _isCurrentMonth(DateTime day) =>
      day.year == _focusedMonth.year && day.month == _focusedMonth.month;

  @override
  Widget build(BuildContext context) {
    final gridDays = _buildGridDays();
    final headerLabel =
        DateFormat('MMMM yyyy').format(_focusedMonth).toLowerCase();

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onHorizontalDragEnd: (details) {
        if ((details.primaryVelocity ?? 0) > 0) {
          _goToPreviousMonth();
        } else if ((details.primaryVelocity ?? 0) < 0) {
          _goToNextMonth();
        }
      },
      child: Column(
        children: [
          _buildMonthHeader(context, headerLabel),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: _buildDayOfWeekHeaders(context),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 4),
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
                  child: _buildGrid(context, gridDays),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMonthHeader(BuildContext context, String label) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: _goToPreviousMonth,
            tooltip: 'Previous month',
          ),
          Text(label, style: Theme.of(context).textTheme.titleMedium),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            onPressed: _goToNextMonth,
            tooltip: 'Next month',
          ),
        ],
      ),
    );
  }

  Widget _buildDayOfWeekHeaders(BuildContext context) {
    final textStyle = Theme.of(context).textTheme.bodySmall?.copyWith(
      fontWeight: FontWeight.w600,
      color: Theme.of(context).colorScheme.onSurfaceVariant,
    );
    return Row(
      children:
          _dayHeaders
              .map(
                (h) => Expanded(
                  child: Center(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 2),
                      child: Text(h, style: textStyle),
                    ),
                  ),
                ),
              )
              .toList(),
    );
  }

  Widget _buildGrid(BuildContext context, List<DateTime> days) {
    final rowCount = (days.length / 7).ceil();
    return LayoutBuilder(
      builder: (context, constraints) {
        final rowHeight = constraints.maxHeight / rowCount;
        // Available space for chips = row height - day label - padding - "+N more" text
        final availableForChips = rowHeight - _dayLabelHeight - 4 - 16;
        final fittableRows = (availableForChips / (_chipHeight + _chipSpacing))
            .floor()
            .clamp(1, _maxEventRows);
        return Column(
          children: List.generate(rowCount, (rowIndex) {
            final rowDays = days.sublist(rowIndex * 7, (rowIndex + 1) * 7);
            return Expanded(
              child: _MonthRow(
                days: rowDays,
                allEvents: widget.events,
                isToday: _isToday,
                isCurrentMonth: _isCurrentMonth,
                onDayTapped: widget.onDayTapped,
                onEventTapped: (e) => showEventDetail(context, e),
                dayLabelHeight: _dayLabelHeight,
                chipHeight: _chipHeight,
                chipSpacing: _chipSpacing,
                maxEventRows: fittableRows,
              ),
            );
          }),
        );
      },
    );
  }
}

class _MonthRow extends StatelessWidget {
  final List<DateTime> days; // exactly 7
  final List<Event> allEvents;
  final bool Function(DateTime) isToday;
  final bool Function(DateTime) isCurrentMonth;
  final ValueChanged<DateTime> onDayTapped;
  final ValueChanged<Event> onEventTapped;
  final double dayLabelHeight;
  final double chipHeight;
  final double chipSpacing;
  final int maxEventRows;

  const _MonthRow({
    required this.days,
    required this.allEvents,
    required this.isToday,
    required this.isCurrentMonth,
    required this.onDayTapped,
    required this.onEventTapped,
    required this.dayLabelHeight,
    required this.chipHeight,
    required this.chipSpacing,
    required this.maxEventRows,
  });

  bool _dayContains(DateTime day, Event e) {
    final dayStart = DateTime(day.year, day.month, day.day);
    final dayEnd = dayStart.add(const Duration(days: 1));
    final start = e.startDatetime.toLocal();
    final end =
        e.endDatetime?.toLocal() ?? start.add(const Duration(minutes: 1));
    return start.isBefore(dayEnd) && end.isAfter(dayStart);
  }

  /// Collect events touching any day in this row, deduplicated and sorted:
  /// longer spans first (so multi-day events claim low rows), then by start.
  List<Event> _rowEventsSorted() {
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
    rowEvents.sort((a, b) {
      final aSpan = a.endDatetime?.difference(a.startDatetime) ?? Duration.zero;
      final bSpan = b.endDatetime?.difference(b.startDatetime) ?? Duration.zero;
      final cmp = bSpan.compareTo(aSpan);
      if (cmp != 0) return cmp;
      return a.startDatetime.compareTo(b.startDatetime);
    });
    return rowEvents;
  }

  /// Find the column index where the event visually starts (clamped to 0).
  int _startColFor(DateTime eStart) {
    for (var c = 0; c < 7; c++) {
      final ds = DateTime(days[c].year, days[c].month, days[c].day);
      final es = DateTime(eStart.year, eStart.month, eStart.day);
      if (ds.isAtSameMomentAs(es) || ds.isAfter(es)) return c;
    }
    return 0;
  }

  /// Find the column index where the event visually ends (clamped to 6).
  int _endColFor(DateTime eEnd) {
    final lastDay =
        eEnd.hour == 0 && eEnd.minute == 0
            ? DateTime(eEnd.year, eEnd.month, eEnd.day - 1)
            : DateTime(eEnd.year, eEnd.month, eEnd.day);
    for (var c = 6; c >= 0; c--) {
      final ds = DateTime(days[c].year, days[c].month, days[c].day);
      if (ds.isAtSameMomentAs(lastDay) || ds.isBefore(lastDay)) return c;
    }
    return 6;
  }

  /// Assign each event that appears in this row to a slot row (0, 1, 2…).
  /// Uses _dayContains as the single source of truth for which days an event
  /// covers, so multi-day events that end mid-week don't block slots on days
  /// after they finish.
  List<SpanPlacement> _computePlacements() {
    final rowEvents = _rowEventsSorted();
    final placements = <SpanPlacement>[];
    // occupied[col] = set of row indices already taken in that column.
    final occupied = List.generate(7, (_) => <int>{});

    for (final e in rowEvents) {
      final startCol = _startColFor(e.startDatetime.toLocal());
      final endCol = _endColFor((e.endDatetime ?? e.startDatetime).toLocal());

      // Only block slots for columns where the event actually appears on that day.
      final activeCols = [
        for (var c = startCol; c <= endCol; c++)
          if (_dayContains(days[c], e)) c,
      ];
      if (activeCols.isEmpty) continue;

      // Find the lowest slot row free across all active columns.
      var slotRow = 0;
      while (activeCols.any((c) => occupied[c].contains(slotRow))) {
        slotRow++;
      }

      for (final c in activeCols) {
        occupied[c].add(slotRow);
      }

      placements.add(
        SpanPlacement(
          event: e,
          startCol: startCol,
          endCol: endCol,
          row: slotRow,
        ),
      );
    }

    return placements;
  }

  /// Per-column highest visible slot row (row < maxEventRows).
  Map<int, int> _visibleRowsByCol(List<SpanPlacement> placements) {
    final result = <int, int>{};
    for (final p in placements) {
      if (p.row >= maxEventRows) continue;
      for (var c = p.startCol; c <= p.endCol; c++) {
        if (!_dayContains(days[c], p.event)) continue;
        final current = result[c] ?? -1;
        if (p.row > current) result[c] = p.row;
      }
    }
    return result;
  }

  /// Per-column count of hidden events (row >= maxEventRows).
  Map<int, int> _overflowByCol(List<SpanPlacement> placements) {
    final result = <int, int>{};
    for (final p in placements) {
      if (p.row < maxEventRows) continue;
      for (var c = p.startCol; c <= p.endCol; c++) {
        if (_dayContains(days[c], p.event)) {
          result[c] = (result[c] ?? 0) + 1;
        }
      }
    }
    return result;
  }

  Widget _buildDayCell(
    BuildContext context,
    int col,
    Map<int, int> visibleRowsByCol,
    Map<int, int> overflowByCol,
  ) {
    final day = days[col];
    final overflow = overflowByCol[col] ?? 0;
    return Expanded(
      child: Semantics(
        button: true,
        label: DateFormat('MMMM d').format(day),
        child: InkWell(
          onTap: () => onDayTapped(day),
          splashColor: Colors.transparent,
          highlightColor: Colors.transparent,
          child: Container(
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(
                  color: Theme.of(context).dividerColor.withValues(alpha: 0.4),
                  width: 0.5,
                ),
                right:
                    col < 6
                        ? BorderSide(
                          color: Theme.of(
                            context,
                          ).dividerColor.withValues(alpha: 0.4),
                          width: 0.5,
                        )
                        : BorderSide.none,
              ),
            ),
            padding: const EdgeInsets.fromLTRB(6, 4, 6, 4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _DayLabel(
                  day: day,
                  isToday: isToday(day),
                  isCurrentMonth: isCurrentMonth(day),
                  height: dayLabelHeight,
                ),
                if (overflow > 0) ...[
                  SizedBox(
                    height:
                        ((visibleRowsByCol[col] ?? -1) + 1) *
                        (chipHeight + chipSpacing),
                  ),
                  Text(
                    '+$overflow more',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Positioned _buildEventChip(SpanPlacement p, double colWidth) {
    final left = p.startCol * colWidth;
    final width = (p.endCol - p.startCol + 1) * colWidth;
    final top = dayLabelHeight + 4 + p.row * (chipHeight + chipSpacing);
    final colors = eventColors(p.event.id);
    final continuesFromPrev =
        p.startCol == 0 &&
        p.event.startDatetime.toLocal().isBefore(
          DateTime(days[0].year, days[0].month, days[0].day),
        );
    final continuesToNext =
        p.endCol == 6 &&
        (p.event.endDatetime ?? p.event.startDatetime).toLocal().isAfter(
          DateTime(days[6].year, days[6].month, days[6].day + 1),
        );
    final borderRadius = BorderRadius.horizontal(
      left: continuesFromPrev ? Radius.zero : const Radius.circular(6),
      right: continuesToNext ? Radius.zero : const Radius.circular(6),
    );

    return Positioned(
      left: left,
      top: top,
      width: width,
      height: chipHeight,
      child: Semantics(
        button: true,
        label: p.event.title,
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
              borderRadius: borderRadius,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 6),
            alignment: Alignment.centerLeft,
            child: Text(
              '${p.event.title}${p.event.visibility == PageVisibility.membersOnly ? ' 🔒' : ''}${p.event.eventType == EventType.official ? ' ✦' : ''}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: colors.$2,
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final placements = _computePlacements();
    final visibleRowsByCol = _visibleRowsByCol(placements);
    final overflowByCol = _overflowByCol(placements);

    return LayoutBuilder(
      builder: (context, constraints) {
        final colWidth = constraints.maxWidth / 7;
        return Stack(
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: List.generate(
                7,
                (col) => _buildDayCell(
                  context,
                  col,
                  visibleRowsByCol,
                  overflowByCol,
                ),
              ),
            ),
            ...placements
                .where((p) => p.row < maxEventRows)
                .map((p) => _buildEventChip(p, colWidth)),
          ],
        );
      },
    );
  }
}

class _DayLabel extends StatelessWidget {
  final DateTime day;
  final bool isToday;
  final bool isCurrentMonth;
  final double height;

  const _DayLabel({
    required this.day,
    required this.isToday,
    required this.isCurrentMonth,
    required this.height,
  });

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return SizedBox(
      height: height,
      width: height,
      child: Center(
        child: Container(
          width: 20,
          height: 20,
          decoration:
              isToday
                  ? BoxDecoration(
                    color: colorScheme.primary,
                    shape: BoxShape.circle,
                  )
                  : null,
          child: Center(
            child: Text(
              '${day.day}',
              style: TextStyle(
                fontSize: 11,
                fontWeight: isToday ? FontWeight.w600 : FontWeight.normal,
                color:
                    isToday
                        ? colorScheme.onPrimary
                        : isCurrentMonth
                        ? colorScheme.onSurface
                        : colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
