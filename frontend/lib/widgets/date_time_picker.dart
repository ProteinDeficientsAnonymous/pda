import 'package:flutter/material.dart';

/// Inline combined date + time picker.
///
/// Top half: Flutter's [CalendarDatePicker] (no pencil icon — that only
/// appears in the dialog variant).
/// Bottom half: three [ListWheelScrollView] scroll wheels for hour, minute
/// (5-minute intervals by default), and AM/PM.
///
/// Fires [onDateTimeChanged] on every calendar tap or wheel scroll settle.
/// No confirm/cancel — the parent controls that (see [showDateTimePicker]).
class DateTimePicker extends StatefulWidget {
  const DateTimePicker({
    super.key,
    required this.initialDateTime,
    required this.onDateTimeChanged,
    this.firstDate,
    this.lastDate,
    this.minuteInterval = 5,
  });

  final DateTime initialDateTime;
  final ValueChanged<DateTime> onDateTimeChanged;
  final DateTime? firstDate;
  final DateTime? lastDate;

  /// Interval between minute options (must divide 60 evenly). Defaults to 5.
  final int minuteInterval;

  @override
  State<DateTimePicker> createState() => _DateTimePickerState();
}

class _DateTimePickerState extends State<DateTimePicker> {
  late DateTime _current;

  late final FixedExtentScrollController _hourController;
  late final FixedExtentScrollController _minuteController;
  late final FixedExtentScrollController _periodController;

  List<int> get _minutes {
    final count = 60 ~/ widget.minuteInterval;
    return List.generate(count, (i) => i * widget.minuteInterval);
  }

  int get _hourIndex => (_current.hour % 12 == 0 ? 12 : _current.hour % 12) - 1;
  int get _minuteIndex {
    final snapped =
        (_current.minute ~/ widget.minuteInterval) * widget.minuteInterval;
    return _minutes.indexOf(snapped).clamp(0, _minutes.length - 1);
  }

  int get _periodIndex => _current.hour < 12 ? 0 : 1;

  @override
  void initState() {
    super.initState();
    _current = widget.initialDateTime;
    _hourController = FixedExtentScrollController(initialItem: _hourIndex);
    _minuteController = FixedExtentScrollController(initialItem: _minuteIndex);
    _periodController = FixedExtentScrollController(initialItem: _periodIndex);
  }

  @override
  void didUpdateWidget(DateTimePicker oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialDateTime != oldWidget.initialDateTime) {
      _current = widget.initialDateTime;
      _hourController.jumpToItem(_hourIndex);
      _minuteController.jumpToItem(_minuteIndex);
      _periodController.jumpToItem(_periodIndex);
    }
  }

  @override
  void dispose() {
    _hourController.dispose();
    _minuteController.dispose();
    _periodController.dispose();
    super.dispose();
  }

  void _onDateSelected(DateTime date) {
    setState(() {
      _current = DateTime(
        date.year,
        date.month,
        date.day,
        _current.hour,
        _current.minute,
      );
    });
    widget.onDateTimeChanged(_current);
  }

  void _updateTime() {
    final hourVal = _hourController.selectedItem % 12 + 1; // 1-12
    final minuteVal =
        _minutes[_minuteController.selectedItem % _minutes.length];
    final isPm = _periodController.selectedItem % 2 == 1;
    final hour24 =
        isPm
            ? (hourVal == 12 ? 12 : hourVal + 12)
            : (hourVal == 12 ? 0 : hourVal);
    setState(() {
      _current = DateTime(
        _current.year,
        _current.month,
        _current.day,
        hour24,
        minuteVal,
      );
    });
    widget.onDateTimeChanged(_current);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final first = widget.firstDate ?? DateTime(2000);
    final last = widget.lastDate ?? DateTime(2100);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        CalendarDatePicker(
          initialDate: _current,
          firstDate: first,
          lastDate: last,
          onDateChanged: _onDateSelected,
        ),
        const Divider(height: 1),
        const SizedBox(height: 8),
        _TimeWheelSelector(
          hourController: _hourController,
          minuteController: _minuteController,
          periodController: _periodController,
          minutes: _minutes,
          onScrollEnd: _updateTime,
          selectedColor: theme.colorScheme.primaryContainer,
          onSelectedColor: theme.colorScheme.onPrimaryContainer,
          textStyle: theme.textTheme.titleMedium!,
        ),
        const SizedBox(height: 8),
      ],
    );
  }
}

class _TimeWheelSelector extends StatelessWidget {
  const _TimeWheelSelector({
    required this.hourController,
    required this.minuteController,
    required this.periodController,
    required this.minutes,
    required this.onScrollEnd,
    required this.selectedColor,
    required this.onSelectedColor,
    required this.textStyle,
  });

  final FixedExtentScrollController hourController;
  final FixedExtentScrollController minuteController;
  final FixedExtentScrollController periodController;
  final List<int> minutes;
  final VoidCallback onScrollEnd;
  final Color selectedColor;
  final Color onSelectedColor;
  final TextStyle textStyle;

  static const double _itemExtent = 44.0;
  static const double _wheelHeight = 132.0; // 3 visible items

  Widget _buildWheel({
    required FixedExtentScrollController controller,
    required List<String> items,
    required String semanticLabel,
  }) {
    return Semantics(
      label: semanticLabel,
      child: SizedBox(
        height: _wheelHeight,
        width: 72,
        child: ListWheelScrollView.useDelegate(
          controller: controller,
          itemExtent: _itemExtent,
          physics: const FixedExtentScrollPhysics(),
          onSelectedItemChanged: (_) => onScrollEnd(),
          childDelegate: ListWheelChildBuilderDelegate(
            childCount: items.length,
            builder: (context, index) {
              final selected =
                  controller.hasClients &&
                  controller.selectedItem % items.length == index;
              return Container(
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: selected ? selectedColor : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  items[index],
                  style: textStyle.copyWith(
                    color: selected ? onSelectedColor : null,
                    fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final hourItems = List.generate(12, (i) => '${i + 1}');
    final minuteItems =
        minutes.map((m) => m.toString().padLeft(2, '0')).toList();
    const periodItems = ['AM', 'PM'];

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _buildWheel(
          controller: hourController,
          items: hourItems,
          semanticLabel: 'hour',
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Text(':', style: textStyle),
        ),
        _buildWheel(
          controller: minuteController,
          items: minuteItems,
          semanticLabel: 'minute',
        ),
        const SizedBox(width: 8),
        _buildWheel(
          controller: periodController,
          items: periodItems,
          semanticLabel: 'AM or PM',
        ),
      ],
    );
  }
}
