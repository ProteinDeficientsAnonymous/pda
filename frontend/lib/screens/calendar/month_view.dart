import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';

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
    'Sun',
    'Mon',
    'Tue',
    'Wed',
    'Thu',
    'Fri',
    'Sat',
  ];

  static const int _maxEventRows = 3;
  static const double _dayLabelHeight = 28.0;
  static const double _chipHeight = 18.0;
  static const double _chipSpacing = 2.0;
  static const double _minCellHeight = 80.0;

  @override
  void initState() {
    super.initState();
    _focusedMonth = DateTime(
      widget.selectedDate.year,
      widget.selectedDate.month,
    );
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
    final headerLabel = DateFormat('MMMM yyyy').format(_focusedMonth);

    return Column(
      children: [
        _buildMonthHeader(context, headerLabel),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: _buildDayOfWeekHeaders(context),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: _buildGrid(context, gridDays),
          ),
        ),
      ],
    );
  }

  Future<void> _openDatePicker(BuildContext context) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _focusedMonth,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      initialEntryMode: DatePickerEntryMode.calendarOnly,
    );
    if (picked == null) return;
    setState(() {
      _focusedMonth = DateTime(picked.year, picked.month);
    });
    widget.onDateChanged(picked);
  }

  Widget _buildMonthHeader(BuildContext context, String label) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: _goToPreviousMonth,
            tooltip: 'Previous month',
          ),
          GestureDetector(
            onTap: () => _openDatePicker(context),
            child: Text(label, style: Theme.of(context).textTheme.titleMedium),
          ),
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
                      padding: const EdgeInsets.symmetric(vertical: 6),
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
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: rowCount,
      itemBuilder: (context, rowIndex) {
        final rowDays = days.sublist(rowIndex * 7, (rowIndex + 1) * 7);
        return _MonthRow(
          days: rowDays,
          allEvents: widget.events,
          isToday: _isToday,
          isCurrentMonth: _isCurrentMonth,
          onDayTapped: widget.onDayTapped,
          onEventTapped: (e) => showEventDetail(context, e),
          minCellHeight: _minCellHeight,
          dayLabelHeight: _dayLabelHeight,
          chipHeight: _chipHeight,
          chipSpacing: _chipSpacing,
          maxEventRows: _maxEventRows,
        );
      },
    );
  }
}

/// Represents a positioned event span within a week row.
class _SpanPlacement {
  final Event event;
  final int startCol; // 0–6
  final int endCol; // 0–6 inclusive
  final int row; // slot row index

  const _SpanPlacement({
    required this.event,
    required this.startCol,
    required this.endCol,
    required this.row,
  });
}

class _MonthRow extends StatelessWidget {
  final List<DateTime> days; // exactly 7
  final List<Event> allEvents;
  final bool Function(DateTime) isToday;
  final bool Function(DateTime) isCurrentMonth;
  final ValueChanged<DateTime> onDayTapped;
  final ValueChanged<Event> onEventTapped;
  final double minCellHeight;
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
    required this.minCellHeight,
    required this.dayLabelHeight,
    required this.chipHeight,
    required this.chipSpacing,
    required this.maxEventRows,
  });

  bool _dayContains(DateTime day, Event e) {
    final dayStart = DateTime(day.year, day.month, day.day);
    final dayEnd = dayStart.add(const Duration(days: 1));
    final start = e.startDatetime.toLocal();
    final end = e.endDatetime.toLocal();
    return start.isBefore(dayEnd) && end.isAfter(dayStart);
  }

  /// Assign each event that appears in this row to a slot row (0, 1, 2…).
  /// Multi-day events get clamped to the week boundaries and placed
  /// consistently across the row.
  List<_SpanPlacement> _computePlacements() {
    final rowStart = days.first;
    final rowEnd = days.last;

    // Collect events that touch this row at all, deduplicated by id.
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
    // Sort by start time so earlier events get lower slot rows.
    rowEvents.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));

    final placements = <_SpanPlacement>[];
    // occupied[col] = set of row indices already taken in that column
    final occupied = List.generate(7, (_) => <int>{});

    for (final e in rowEvents) {
      final eStart = e.startDatetime.toLocal();
      final eEnd = e.endDatetime.toLocal();

      // Clamp to row boundaries
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
        // end is exclusive midnight so last day is eEnd - 1 day (if midnight)
        final lastDay =
            eEnd.hour == 0 && eEnd.minute == 0
                ? DateTime(eEnd.year, eEnd.month, eEnd.day - 1)
                : DateTime(eEnd.year, eEnd.month, eEnd.day);
        if (ds.isAtSameMomentAs(lastDay) || ds.isBefore(lastDay)) {
          endCol = c;
          break;
        }
      }

      // Clamp to rowStart/rowEnd
      final rs = DateTime(rowStart.year, rowStart.month, rowStart.day);
      final re = DateTime(rowEnd.year, rowEnd.month, rowEnd.day);
      final es = DateTime(eStart.year, eStart.month, eStart.day);
      final ee = DateTime(eEnd.year, eEnd.month, eEnd.day);
      if (es.isAfter(re) || ee.isBefore(rs)) continue;

      // Find the lowest row not taken by any column in this span
      int slotRow = 0;
      while (true) {
        final blocked = List.generate(
          endCol - startCol + 1,
          (i) => occupied[startCol + i].contains(slotRow),
        );
        if (!blocked.any((b) => b)) break;
        slotRow++;
      }

      for (var c = startCol; c <= endCol; c++) {
        occupied[c].add(slotRow);
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
    final placements = _computePlacements();
    // visibleRows: highest slot row that fits within maxEventRows, clamped.
    final visibleMaxRow =
        placements.isEmpty
            ? 0
            : placements
                .where((p) => p.row < maxEventRows)
                .fold(-1, (m, p) => p.row > m ? p.row : m);
    final visibleRows = visibleMaxRow.clamp(0, maxEventRows - 1);
    // overflowByCol: per-column count of events that are hidden (row >= maxEventRows).
    // Only count an event for columns it actually covers.
    final overflowByCol = <int, int>{};
    for (final p in placements) {
      if (p.row >= maxEventRows) {
        for (var c = p.startCol; c <= p.endCol; c++) {
          overflowByCol[c] = (overflowByCol[c] ?? 0) + 1;
        }
      }
    }

    final eventsAreaHeight =
        visibleRows * (chipHeight + chipSpacing) + chipHeight + chipSpacing;
    final rowHeight = (dayLabelHeight + eventsAreaHeight + 4).clamp(
      minCellHeight,
      double.infinity,
    );

    return SizedBox(
      height: rowHeight,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final totalWidth = constraints.maxWidth;
          final colWidth = totalWidth / 7;

          return Stack(
            children: [
              // Day cell backgrounds + date labels + overflow indicators
              Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: List.generate(7, (col) {
                  final day = days[col];
                  final today = isToday(day);
                  final currentMonth = isCurrentMonth(day);
                  final overflow = overflowByCol[col] ?? 0;
                  return Expanded(
                    child: GestureDetector(
                      onTap: () => onDayTapped(day),
                      child: Container(
                        decoration: BoxDecoration(
                          border: Border.all(
                            color: Theme.of(context).dividerColor,
                            width: 0.5,
                          ),
                        ),
                        padding: const EdgeInsets.all(4),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _DayLabel(
                              day: day,
                              isToday: today,
                              isCurrentMonth: currentMonth,
                              height: dayLabelHeight,
                            ),
                            if (overflow > 0) ...[
                              SizedBox(
                                height:
                                    visibleRows * (chipHeight + chipSpacing),
                              ),
                              Text(
                                '+$overflow more',
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ),
                  );
                }),
              ),

              // Event span bars
              ...placements.where((p) => p.row < maxEventRows).map((p) {
                final left = p.startCol * colWidth;
                final width = (p.endCol - p.startCol + 1) * colWidth;
                final top =
                    dayLabelHeight + 4 + p.row * (chipHeight + chipSpacing);
                final colors = eventColors(p.event.id);
                // continues from previous row if startCol==0 and event started before this row
                final continuesFromPrev =
                    p.startCol == 0 &&
                    p.event.startDatetime.toLocal().isBefore(
                      DateTime(days[0].year, days[0].month, days[0].day),
                    );
                final continuesToNext =
                    p.endCol == 6 &&
                    p.event.endDatetime.toLocal().isAfter(
                      DateTime(days[6].year, days[6].month, days[6].day + 1),
                    );

                final borderRadius = BorderRadius.horizontal(
                  left:
                      continuesFromPrev
                          ? Radius.zero
                          : const Radius.circular(3),
                  right:
                      continuesToNext ? Radius.zero : const Radius.circular(3),
                );

                return Positioned(
                  left: left,
                  top: top,
                  width: width,
                  height: chipHeight,
                  child: GestureDetector(
                    onTap: () => onEventTapped(p.event),
                    child: Container(
                      margin: EdgeInsets.only(
                        left: continuesFromPrev ? 0 : 1,
                        right: continuesToNext ? 0 : 1,
                      ),
                      decoration: BoxDecoration(
                        color: colors.$1,
                        borderRadius: borderRadius,
                      ),
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      alignment: Alignment.centerLeft,
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
                  ),
                );
              }),
            ],
          );
        },
      ),
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
          width: 22,
          height: 22,
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
                fontSize: 12,
                fontWeight: isToday ? FontWeight.bold : FontWeight.normal,
                color:
                    isToday
                        ? colorScheme.onPrimary
                        : isCurrentMonth
                        ? colorScheme.onSurface
                        : colorScheme.onSurface.withValues(alpha: 0.35),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
