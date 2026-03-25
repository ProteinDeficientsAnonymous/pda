import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';

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

  static const int _maxChipsVisible = 3;
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

  /// Returns a list of DateTime values representing the grid cells,
  /// including leading days from the previous month and trailing days
  /// from the next month to fill complete weeks.
  List<DateTime> _buildGridDays() {
    final firstOfMonth = DateTime(_focusedMonth.year, _focusedMonth.month, 1);
    final lastOfMonth = DateTime(
      _focusedMonth.year,
      _focusedMonth.month + 1,
      0,
    );

    // Sunday = 0, weekday property: Mon=1 … Sun=7, so convert
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

  bool _isSameDay(DateTime a, DateTime b) {
    return a.year == b.year && a.month == b.month && a.day == b.day;
  }

  bool _isToday(DateTime day) {
    return _isSameDay(day, DateTime.now());
  }

  bool _isCurrentMonth(DateTime day) {
    return day.year == _focusedMonth.year && day.month == _focusedMonth.month;
  }

  List<Event> _eventsForDay(DateTime day) {
    return widget.events
        .where((e) => _isSameDay(e.startDatetime.toLocal(), day))
        .toList();
  }

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
        return IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children:
                rowDays
                    .map((day) => Expanded(child: _buildCell(context, day)))
                    .toList(),
          ),
        );
      },
    );
  }

  Widget _buildCell(BuildContext context, DateTime day) {
    final events = _eventsForDay(day);
    final isToday = _isToday(day);
    final isCurrentMonth = _isCurrentMonth(day);

    return GestureDetector(
      onTap: () => widget.onDayTapped(day),
      child: Container(
        constraints: const BoxConstraints(minHeight: _minCellHeight),
        decoration: BoxDecoration(
          border: Border.all(color: Theme.of(context).dividerColor, width: 0.5),
        ),
        padding: const EdgeInsets.all(4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildDayLabel(context, day, isToday, isCurrentMonth),
            const SizedBox(height: 2),
            ..._buildEventChips(context, events),
          ],
        ),
      ),
    );
  }

  Widget _buildDayLabel(
    BuildContext context,
    DateTime day,
    bool isToday,
    bool isCurrentMonth,
  ) {
    final colorScheme = Theme.of(context).colorScheme;

    if (isToday) {
      return CircleAvatar(
        radius: 13,
        backgroundColor: colorScheme.primary,
        child: Text(
          '${day.day}',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: colorScheme.onPrimary,
          ),
        ),
      );
    }

    final textColor =
        isCurrentMonth
            ? colorScheme.onSurface
            : colorScheme.onSurface.withValues(alpha: 0.35);

    return Text('${day.day}', style: TextStyle(fontSize: 12, color: textColor));
  }

  List<Widget> _buildEventChips(BuildContext context, List<Event> events) {
    if (events.isEmpty) {
      return [];
    }

    final colorScheme = Theme.of(context).colorScheme;
    final visibleEvents = events.take(_maxChipsVisible).toList();
    final overflow = events.length - _maxChipsVisible;

    final chips =
        visibleEvents
            .map(
              (e) => _EventChip(
                title: e.title,
                color: colorScheme.primaryContainer,
                textColor: colorScheme.onPrimaryContainer,
              ),
            )
            .toList();

    final result = <Widget>[...chips];

    if (overflow > 0) {
      result.add(
        Padding(
          padding: const EdgeInsets.only(top: 2),
          child: Text(
            '+$overflow more',
            style: TextStyle(fontSize: 10, color: colorScheme.onSurfaceVariant),
          ),
        ),
      );
    }

    return result;
  }
}

class _EventChip extends StatelessWidget {
  final String title;
  final Color color;
  final Color textColor;

  const _EventChip({
    required this.title,
    required this.color,
    required this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 2),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        title,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(fontSize: 10, color: textColor),
      ),
    );
  }
}
