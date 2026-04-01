import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/calendar/placement_types.dart';
import 'package:pda/screens/calendar/week_placement_calculator.dart';
import 'package:pda/config/constants.dart';

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
            child:
                isWide
                    ? _WideWeekGrid(
                      days: days,
                      events: widget.events,
                      isToday: _isToday,
                      onEventTapped: (e) => showEventDetail(context, e),
                      onDayTapped: widget.onDayTapped,
                    )
                    : _NarrowWeekGrid(
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

// ---------------------------------------------------------------------------
// Wide layout: horizontal grid with days as columns (original layout)
// ---------------------------------------------------------------------------

class _WideWeekGrid extends StatelessWidget {
  final List<DateTime> days;
  final List<Event> events;
  final bool Function(DateTime) isToday;
  final ValueChanged<Event> onEventTapped;
  final ValueChanged<DateTime>? onDayTapped;

  static const double _dayLabelHeight = 52.0;
  static const double _chipHeight = 22.0;
  static const double _chipSpacing = 3.0;
  static const int _maxEventRows = 4;

  const _WideWeekGrid({
    required this.days,
    required this.events,
    required this.isToday,
    required this.onEventTapped,
    this.onDayTapped,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasAnyEvents = days.any((d) {
      final ds = DateTime(d.year, d.month, d.day);
      final de = ds.add(const Duration(days: 1));
      return events.any((e) {
        final s = e.startDatetime.toLocal();
        final en = (e.endDatetime ?? e.startDatetime).toLocal();
        return s.isBefore(de) && en.isAfter(ds);
      });
    });

    final placements =
        WeekPlacementCalculator(days: days, allEvents: events).calculate();

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            border: Border.all(
              color: theme.dividerColor.withValues(alpha: 0.4),
              width: 0.5,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Stack(
            children: [
              LayoutBuilder(
                builder: (context, constraints) {
                  final colWidth = constraints.maxWidth / 7;
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Day header row
                      SizedBox(
                        height: _dayLabelHeight,
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
                                        mainAxisAlignment:
                                            MainAxisAlignment.center,
                                        children: [
                                          Text(
                                            DateFormat(
                                              'EEE',
                                            ).format(day).toLowerCase(),
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
                            // Tappable column cells with overflow indicators
                            Row(
                              children: List.generate(7, (col) {
                                final overflow =
                                    placements
                                        .where(
                                          (p) =>
                                              p.row >= _maxEventRows &&
                                              col >= p.startCol &&
                                              col <= p.endCol,
                                        )
                                        .length;
                                return Expanded(
                                  child: Semantics(
                                    button: onDayTapped != null,
                                    label: DateFormat(
                                      'EEEE, MMMM d',
                                    ).format(days[col]),
                                    child: InkWell(
                                      onTap:
                                          onDayTapped != null
                                              ? () => onDayTapped!(days[col])
                                              : null,
                                      child: Container(
                                        decoration: BoxDecoration(
                                          border: Border(
                                            right:
                                                col < 6
                                                    ? BorderSide(
                                                      color: theme.dividerColor
                                                          .withValues(
                                                            alpha: 0.4,
                                                          ),
                                                      width: 0.5,
                                                    )
                                                    : BorderSide.none,
                                          ),
                                        ),
                                        child:
                                            overflow > 0
                                                ? Align(
                                                  alignment:
                                                      Alignment.bottomCenter,
                                                  child: Padding(
                                                    padding:
                                                        const EdgeInsets.only(
                                                          bottom: 4,
                                                        ),
                                                    child: Text(
                                                      '+$overflow more',
                                                      style: TextStyle(
                                                        fontSize: 11,
                                                        fontWeight:
                                                            FontWeight.w600,
                                                        color:
                                                            theme
                                                                .colorScheme
                                                                .primary,
                                                      ),
                                                    ),
                                                  ),
                                                )
                                                : null,
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
                                        .where((p) => p.row < _maxEventRows)
                                        .map(
                                          (p) => _buildWideEventChip(
                                            p,
                                            colWidth,
                                            days,
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
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Positioned _buildWideEventChip(
    SpanPlacement p,
    double colWidth,
    List<DateTime> days,
  ) {
    final left = p.startCol * colWidth;
    final width = (p.endCol - p.startCol + 1) * colWidth;
    final top = p.row * (_chipHeight + _chipSpacing);
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
            ? '${DateFormat('MMM d').format(eStart).toLowerCase()} \u2013 ${DateFormat('MMM d').format(eEnd).toLowerCase()}'
            : formatTime(eStart);

    return Positioned(
      left: left,
      top: top,
      width: width,
      height: _chipHeight,
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
                left:
                    continuesFromPrev ? Radius.zero : const Radius.circular(6),
                right: continuesToNext ? Radius.zero : const Radius.circular(6),
              ),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 6),
            child: Text.rich(
              TextSpan(
                children: [
                  if (p.event.visibility == PageVisibility.membersOnly)
                    TextSpan(
                      text: '🔒 ',
                      style: TextStyle(fontSize: 11, color: colors.$2),
                    ),
                  if (p.event.eventType == EventType.official)
                    TextSpan(
                      text: '✦ ',
                      style: TextStyle(fontSize: 11, color: colors.$2),
                    ),
                  TextSpan(
                    text: p.event.title,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: colors.$2,
                    ),
                  ),
                  TextSpan(
                    text: '  $subLabel',
                    style: TextStyle(fontSize: 11, color: colors.$2),
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
}

// ---------------------------------------------------------------------------
// Narrow layout: days as rows on the left, events stacked horizontally
// ---------------------------------------------------------------------------

class _NarrowWeekGrid extends StatelessWidget {
  final List<DateTime> days;
  final List<Event> events;
  final bool Function(DateTime) isToday;
  final ValueChanged<Event> onEventTapped;
  final ValueChanged<DateTime>? onDayTapped;

  static int _maxVisibleForHeight(double height) {
    if (height.isInfinite) return 3;
    // 7 equal rows; each chip is 22px + 2px vertical padding = 24px.
    // Reserve ~20px for the "+N more" overflow label when present.
    final rowHeight = height / 7;
    final availableForChips = rowHeight - 20;
    return (availableForChips / 24).floor().clamp(1, 10);
  }

  const _NarrowWeekGrid({
    required this.days,
    required this.events,
    required this.isToday,
    required this.onEventTapped,
    this.onDayTapped,
  });

  List<Event> _eventsForDay(DateTime day) {
    final results = events.where((e) => dayContains(day, e)).toList();
    results.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));
    return results;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final maxVisible = _maxVisibleForHeight(constraints.maxHeight);
          return ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Container(
              decoration: BoxDecoration(
                border: Border.all(
                  color: theme.dividerColor.withValues(alpha: 0.4),
                  width: 0.5,
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: List.generate(7, (i) {
                  final day = days[i];
                  final dayEvents = _eventsForDay(day);
                  return Expanded(
                    child: _NarrowDayRow(
                      day: day,
                      events: dayEvents,
                      isToday: isToday(day),
                      isLast: i == 6,
                      maxVisible: maxVisible,
                      onDayTapped: onDayTapped,
                      onEventTapped: onEventTapped,
                    ),
                  );
                }),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _NarrowDayRow extends StatelessWidget {
  final DateTime day;
  final List<Event> events;
  final bool isToday;
  final bool isLast;
  final int maxVisible;
  final ValueChanged<DateTime>? onDayTapped;
  final ValueChanged<Event> onEventTapped;

  const _NarrowDayRow({
    required this.day,
    required this.events,
    required this.isToday,
    required this.isLast,
    required this.maxVisible,
    required this.onDayTapped,
    required this.onEventTapped,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final visible = events.take(maxVisible).toList();
    final overflow = events.length - maxVisible;

    return Semantics(
      button: onDayTapped != null,
      label: DateFormat('EEEE, MMMM d').format(day),
      child: InkWell(
        onTap: onDayTapped != null ? () => onDayTapped!(day) : null,
        child: Container(
          decoration: BoxDecoration(
            border: Border(
              bottom:
                  isLast
                      ? BorderSide.none
                      : BorderSide(
                        color: theme.dividerColor.withValues(alpha: 0.4),
                        width: 0.5,
                      ),
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Day label
              SizedBox(
                width: 56,
                child: Center(
                  child: _NarrowDayLabel(day: day, isToday: isToday),
                ),
              ),
              // Divider
              Container(
                width: 0.5,
                color: theme.dividerColor.withValues(alpha: 0.4),
              ),
              // Events
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 4,
                    vertical: 2,
                  ),
                  child:
                      events.isEmpty
                          ? const SizedBox.shrink()
                          : Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              ...visible.map(
                                (e) => _NarrowEventChip(
                                  event: e,
                                  onTap: () => onEventTapped(e),
                                ),
                              ),
                              if (overflow > 0)
                                Semantics(
                                  button: true,
                                  label: '$overflow more events',
                                  child: InkWell(
                                    onTap:
                                        onDayTapped != null
                                            ? () => onDayTapped!(day)
                                            : null,
                                    borderRadius: BorderRadius.circular(4),
                                    child: Padding(
                                      padding: const EdgeInsets.only(
                                        left: 4,
                                        top: 1,
                                      ),
                                      child: Text(
                                        '+$overflow more',
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w600,
                                          color: theme.colorScheme.primary,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NarrowDayLabel extends StatelessWidget {
  final DateTime day;
  final bool isToday;

  const _NarrowDayLabel({required this.day, required this.isToday});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dayName = DateFormat('EEE').format(day).toLowerCase();
    final dayNum = '${day.day}';

    if (isToday) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: theme.colorScheme.primary,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              dayName,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onPrimary,
              ),
            ),
            Text(
              dayNum,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: theme.colorScheme.onPrimary,
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          dayName,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          dayNum,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: theme.colorScheme.onSurface,
          ),
        ),
      ],
    );
  }
}

class _NarrowEventChip extends StatelessWidget {
  final Event event;
  final VoidCallback onTap;

  const _NarrowEventChip({required this.event, required this.onTap});

  String _buildLabel() {
    final lockPrefix =
        event.visibility == PageVisibility.membersOnly ? '🔒 ' : '';
    final prefix =
        '$lockPrefix${event.eventType == EventType.official ? '✦ ' : ''}';
    final dateFmt = DateFormat('MMM d');
    final start = event.startDatetime.toLocal();
    final end = event.endDatetime?.toLocal();

    if (end == null) {
      return '$prefix${event.title} \u00b7 ${formatTime(start)}';
    }

    final sameDay =
        start.year == end.year &&
        start.month == end.month &&
        start.day == end.day;

    if (sameDay) {
      return '$prefix${event.title} \u00b7 ${formatTime(start)} \u2013 ${formatTime(end)}';
    }

    return '$prefix${event.title} \u00b7 ${dateFmt.format(start).toLowerCase()} \u2013 ${dateFmt.format(end).toLowerCase()}';
  }

  @override
  Widget build(BuildContext context) {
    final colors = eventColors(event.id);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Semantics(
        button: true,
        label: event.title,
        excludeSemantics: true,
        child: InkWell(
          onTap: onTap,
          splashColor: Colors.transparent,
          highlightColor: Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          child: Container(
            height: 22,
            decoration: BoxDecoration(
              color: colors.$1,
              borderRadius: BorderRadius.circular(4),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 6),
            alignment: Alignment.centerLeft,
            child: Text(
              _buildLabel(),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: colors.$2,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
