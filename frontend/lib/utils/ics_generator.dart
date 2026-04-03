import 'package:pda/models/event.dart';

/// Generates a valid RFC 5545 iCalendar string for a single event.
String generateEventIcs(Event event) {
  final buf = StringBuffer();
  buf.writeln('BEGIN:VCALENDAR');
  buf.writeln('VERSION:2.0');
  buf.writeln('PRODID:-//PDA//PDA Calendar//EN');
  buf.writeln('BEGIN:VEVENT');
  buf.writeln('UID:${event.id}@pda');
  buf.writeln('DTSTAMP:${_formatUtc(DateTime.now().toUtc())}');
  buf.writeln(_foldLine('SUMMARY:${_escape(event.title)}'));
  buf.writeln('DTSTART:${_formatUtc(event.startDatetime.toUtc())}');
  final end =
      event.endDatetime ?? event.startDatetime.add(const Duration(hours: 2));
  buf.writeln('DTEND:${_formatUtc(end.toUtc())}');
  final desc = _buildDescription(event);
  if (desc.isNotEmpty) {
    buf.writeln(_foldLine('DESCRIPTION:${_escape(desc)}'));
  }
  if (event.location.isNotEmpty) {
    buf.writeln(_foldLine('LOCATION:${_escape(event.location)}'));
  }
  buf.writeln('END:VEVENT');
  buf.writeln('END:VCALENDAR');
  return buf.toString();
}

/// Builds a description combining the event body with any links.
String _buildDescription(Event event) {
  final parts = <String>[];
  if (event.description.isNotEmpty) parts.add(event.description);
  if (event.whatsappLink.isNotEmpty) {
    parts.add('WhatsApp: ${event.whatsappLink}');
  }
  if (event.partifulLink.isNotEmpty) {
    parts.add('Partiful: ${event.partifulLink}');
  }
  if (event.otherLink.isNotEmpty) {
    parts.add('Link: ${event.otherLink}');
  }
  return parts.join('\n');
}

/// Builds a Google Calendar event creation URL.
String googleCalendarUrl(Event event) {
  final start = event.startDatetime.toUtc();
  final end = event.endDatetime?.toUtc() ?? start.add(const Duration(hours: 2));
  final dates = '${_formatUtc(start)}/${_formatUtc(end)}';
  final details = _buildDescription(event);
  final params = <String, String>{
    'action': 'TEMPLATE',
    'text': event.title,
    'dates': dates,
    if (details.isNotEmpty) 'details': details,
    if (event.location.isNotEmpty) 'location': event.location,
  };
  return Uri.https(
    'calendar.google.com',
    '/calendar/render',
    params,
  ).toString();
}

String _formatUtc(DateTime dt) {
  final y = dt.year.toString().padLeft(4, '0');
  final m = dt.month.toString().padLeft(2, '0');
  final d = dt.day.toString().padLeft(2, '0');
  final h = dt.hour.toString().padLeft(2, '0');
  final min = dt.minute.toString().padLeft(2, '0');
  final s = dt.second.toString().padLeft(2, '0');
  return '$y$m${d}T$h$min${s}Z';
}

String _escape(String value) {
  return value
      .replaceAll('\\', '\\\\')
      .replaceAll(',', '\\,')
      .replaceAll(';', '\\;')
      .replaceAll('\n', '\\n');
}

/// Folds lines longer than 75 octets per RFC 5545.
String _foldLine(String line) {
  if (line.length <= 75) return line;
  final buf = StringBuffer();
  var remaining = line;
  var first = true;
  while (remaining.isNotEmpty) {
    // First line: 75 chars max. Continuation lines: 74 chars (space prefix).
    final maxLen = first ? 75 : 74;
    final chunk = remaining.length <= maxLen
        ? remaining
        : remaining.substring(0, maxLen);
    if (!first) buf.write(' ');
    buf.write(chunk);
    remaining = remaining.substring(chunk.length);
    if (remaining.isNotEmpty) buf.writeln();
    first = false;
  }
  return buf.toString();
}
