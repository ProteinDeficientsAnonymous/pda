import 'package:intl/intl.dart';

final pollDateFmt = DateFormat('EEE, MMM d · h:mm a');

class EventPhotonResult {
  final String name;
  final String? city;
  final String fullAddress;
  final double lat;
  final double lon;

  const EventPhotonResult({
    required this.name,
    this.city,
    required this.fullAddress,
    required this.lat,
    required this.lon,
  });
}

class CoHostResult {
  final String id;
  final String displayName;
  final String phone;

  const CoHostResult({
    required this.id,
    required this.displayName,
    required this.phone,
  });
}
