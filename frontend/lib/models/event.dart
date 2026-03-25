import 'package:freezed_annotation/freezed_annotation.dart';

part 'event.freezed.dart';
part 'event.g.dart';

@freezed
abstract class Event with _$Event {
  const factory Event({
    required String id,
    required String title,
    required String description,
    required DateTime startDatetime,
    required DateTime endDatetime,
    required String location,
  }) = _Event;

  factory Event.fromJson(Map<String, dynamic> json) => _$EventFromJson(json);
}
