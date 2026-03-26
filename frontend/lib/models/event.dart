import 'package:freezed_annotation/freezed_annotation.dart';

part 'event.freezed.dart';
part 'event.g.dart';

@freezed
abstract class EventGuest with _$EventGuest {
  const factory EventGuest({
    required String userId,
    required String name,
    required String status,
    String? phone,
  }) = _EventGuest;

  factory EventGuest.fromJson(Map<String, dynamic> json) =>
      _$EventGuestFromJson(json);
}

@freezed
abstract class Event with _$Event {
  const factory Event({
    required String id,
    required String title,
    required String description,
    required DateTime startDatetime,
    required DateTime endDatetime,
    required String location,
    @Default('') String whatsappLink,
    @Default('') String partifulLink,
    @Default('') String otherLink,
    @Default(false) bool rsvpEnabled,
    String? createdById,
    String? createdByName,
    @Default([]) List<String> coHostIds,
    @Default([]) List<String> coHostNames,
    @Default([]) List<EventGuest> guests,
    String? myRsvp,
  }) = _Event;

  factory Event.fromJson(Map<String, dynamic> json) => _$EventFromJson(json);
}
