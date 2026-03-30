import 'package:intl/intl.dart';

/// Formats a [DateTime] as a lowercase time string.
/// Exact hours are simplified: 10:00 PM → "10pm", 2:30 PM → "2:30pm".
String formatTime(DateTime dt) {
  final hour = DateFormat('h').format(dt);
  final minute = dt.minute;
  final period = DateFormat('a').format(dt).toLowerCase();
  if (minute == 0) return '$hour$period';
  return '$hour:${minute.toString().padLeft(2, '0')}$period';
}
