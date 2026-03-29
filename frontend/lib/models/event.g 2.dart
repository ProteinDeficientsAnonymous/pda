// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'event.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_EventGuest _$EventGuestFromJson(Map<String, dynamic> json) => _EventGuest(
  userId: json['user_id'] as String,
  name: json['name'] as String,
  status: json['status'] as String,
  phone: json['phone'] as String?,
);

Map<String, dynamic> _$EventGuestToJson(_EventGuest instance) =>
    <String, dynamic>{
      'user_id': instance.userId,
      'name': instance.name,
      'status': instance.status,
      'phone': instance.phone,
    };

_Event _$EventFromJson(Map<String, dynamic> json) => _Event(
  id: json['id'] as String,
  title: json['title'] as String,
  description: json['description'] as String,
  startDatetime: DateTime.parse(json['start_datetime'] as String),
  endDatetime: DateTime.parse(json['end_datetime'] as String),
  location: json['location'] as String,
  whatsappLink: json['whatsapp_link'] as String? ?? '',
  partifulLink: json['partiful_link'] as String? ?? '',
  otherLink: json['other_link'] as String? ?? '',
  rsvpEnabled: json['rsvp_enabled'] as bool? ?? false,
  createdById: json['created_by_id'] as String?,
  createdByName: json['created_by_name'] as String?,
  coHostIds:
      (json['co_host_ids'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ??
      const [],
  coHostNames:
      (json['co_host_names'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ??
      const [],
  guests:
      (json['guests'] as List<dynamic>?)
          ?.map((e) => EventGuest.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  myRsvp: json['my_rsvp'] as String?,
);

Map<String, dynamic> _$EventToJson(_Event instance) => <String, dynamic>{
  'id': instance.id,
  'title': instance.title,
  'description': instance.description,
  'start_datetime': instance.startDatetime.toIso8601String(),
  'end_datetime': instance.endDatetime.toIso8601String(),
  'location': instance.location,
  'whatsapp_link': instance.whatsappLink,
  'partiful_link': instance.partifulLink,
  'other_link': instance.otherLink,
  'rsvp_enabled': instance.rsvpEnabled,
  'created_by_id': instance.createdById,
  'created_by_name': instance.createdByName,
  'co_host_ids': instance.coHostIds,
  'co_host_names': instance.coHostNames,
  'guests': instance.guests.map((e) => e.toJson()).toList(),
  'my_rsvp': instance.myRsvp,
};
