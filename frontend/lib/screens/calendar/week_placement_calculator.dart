import '../../models/event.dart';
import 'placement_types.dart';

/// Calculates event placements for the week view grid.
///
/// Simpler than the month calculator — no row-boundary clamping needed.
class WeekPlacementCalculator {
  final List<DateTime> days;
  final List<Event> allEvents;

  WeekPlacementCalculator({required this.days, required this.allEvents});

  List<SpanPlacement> calculate() {
    final rowEvents = _collectRowEvents();
    rowEvents.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));

    final placements = <SpanPlacement>[];
    final occupied = List.generate(7, (_) => <int>{});

    for (final e in rowEvents) {
      final eStart = e.startDatetime.toLocal();
      final eEnd = (e.endDatetime ?? e.startDatetime).toLocal();

      final startCol = _findStartCol(eStart);
      final endCol = _findEndCol(eEnd);

      final slotRow = _findAvailableSlot(occupied, startCol, endCol);
      for (var c = startCol; c <= endCol; c++) {
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

  List<Event> _collectRowEvents() {
    final seen = <String>{};
    final rowEvents = <Event>[];
    for (final day in days) {
      for (final e in allEvents) {
        if (!seen.contains(e.id) && dayContains(day, e)) {
          seen.add(e.id);
          rowEvents.add(e);
        }
      }
    }
    return rowEvents;
  }

  int _findStartCol(DateTime eStart) {
    for (var c = 0; c < 7; c++) {
      final d = days[c];
      final ds = DateTime(d.year, d.month, d.day);
      final es = DateTime(eStart.year, eStart.month, eStart.day);
      if (ds.isAtSameMomentAs(es) || ds.isAfter(es)) {
        return c;
      }
    }
    return 0;
  }

  int _findEndCol(DateTime eEnd) {
    for (var c = 6; c >= 0; c--) {
      final d = days[c];
      final ds = DateTime(d.year, d.month, d.day);
      final lastDay = eEnd.hour == 0 && eEnd.minute == 0
          ? DateTime(eEnd.year, eEnd.month, eEnd.day - 1)
          : DateTime(eEnd.year, eEnd.month, eEnd.day);
      if (ds.isAtSameMomentAs(lastDay) || ds.isBefore(lastDay)) {
        return c;
      }
    }
    return 6;
  }

  int _findAvailableSlot(List<Set<int>> occupied, int startCol, int endCol) {
    int slotRow = 0;
    while (true) {
      final blocked = List.generate(
        endCol - startCol + 1,
        (i) => occupied[startCol + i].contains(slotRow),
      );
      if (!blocked.any((b) => b)) break;
      slotRow++;
    }
    return slotRow;
  }
}
