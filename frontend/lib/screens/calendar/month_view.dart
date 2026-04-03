import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/calendar/month_row.dart';

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
    final headerLabel = DateFormat(
      'MMMM yyyy',
    ).format(_focusedMonth).toLowerCase();

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
      children: _dayHeaders
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
              child: MonthRow(
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
