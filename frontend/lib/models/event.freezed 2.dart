// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'event.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$EventGuest {

 String get userId; String get name; String get status; String? get phone;
/// Create a copy of EventGuest
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$EventGuestCopyWith<EventGuest> get copyWith => _$EventGuestCopyWithImpl<EventGuest>(this as EventGuest, _$identity);

  /// Serializes this EventGuest to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is EventGuest&&(identical(other.userId, userId) || other.userId == userId)&&(identical(other.name, name) || other.name == name)&&(identical(other.status, status) || other.status == status)&&(identical(other.phone, phone) || other.phone == phone));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,userId,name,status,phone);

@override
String toString() {
  return 'EventGuest(userId: $userId, name: $name, status: $status, phone: $phone)';
}


}

/// @nodoc
abstract mixin class $EventGuestCopyWith<$Res>  {
  factory $EventGuestCopyWith(EventGuest value, $Res Function(EventGuest) _then) = _$EventGuestCopyWithImpl;
@useResult
$Res call({
 String userId, String name, String status, String? phone
});




}
/// @nodoc
class _$EventGuestCopyWithImpl<$Res>
    implements $EventGuestCopyWith<$Res> {
  _$EventGuestCopyWithImpl(this._self, this._then);

  final EventGuest _self;
  final $Res Function(EventGuest) _then;

/// Create a copy of EventGuest
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? userId = null,Object? name = null,Object? status = null,Object? phone = freezed,}) {
  return _then(_self.copyWith(
userId: null == userId ? _self.userId : userId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,phone: freezed == phone ? _self.phone : phone // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [EventGuest].
extension EventGuestPatterns on EventGuest {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _EventGuest value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _EventGuest() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _EventGuest value)  $default,){
final _that = this;
switch (_that) {
case _EventGuest():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _EventGuest value)?  $default,){
final _that = this;
switch (_that) {
case _EventGuest() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String userId,  String name,  String status,  String? phone)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _EventGuest() when $default != null:
return $default(_that.userId,_that.name,_that.status,_that.phone);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String userId,  String name,  String status,  String? phone)  $default,) {final _that = this;
switch (_that) {
case _EventGuest():
return $default(_that.userId,_that.name,_that.status,_that.phone);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String userId,  String name,  String status,  String? phone)?  $default,) {final _that = this;
switch (_that) {
case _EventGuest() when $default != null:
return $default(_that.userId,_that.name,_that.status,_that.phone);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _EventGuest implements EventGuest {
  const _EventGuest({required this.userId, required this.name, required this.status, this.phone});
  factory _EventGuest.fromJson(Map<String, dynamic> json) => _$EventGuestFromJson(json);

@override final  String userId;
@override final  String name;
@override final  String status;
@override final  String? phone;

/// Create a copy of EventGuest
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$EventGuestCopyWith<_EventGuest> get copyWith => __$EventGuestCopyWithImpl<_EventGuest>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$EventGuestToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _EventGuest&&(identical(other.userId, userId) || other.userId == userId)&&(identical(other.name, name) || other.name == name)&&(identical(other.status, status) || other.status == status)&&(identical(other.phone, phone) || other.phone == phone));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,userId,name,status,phone);

@override
String toString() {
  return 'EventGuest(userId: $userId, name: $name, status: $status, phone: $phone)';
}


}

/// @nodoc
abstract mixin class _$EventGuestCopyWith<$Res> implements $EventGuestCopyWith<$Res> {
  factory _$EventGuestCopyWith(_EventGuest value, $Res Function(_EventGuest) _then) = __$EventGuestCopyWithImpl;
@override @useResult
$Res call({
 String userId, String name, String status, String? phone
});




}
/// @nodoc
class __$EventGuestCopyWithImpl<$Res>
    implements _$EventGuestCopyWith<$Res> {
  __$EventGuestCopyWithImpl(this._self, this._then);

  final _EventGuest _self;
  final $Res Function(_EventGuest) _then;

/// Create a copy of EventGuest
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? userId = null,Object? name = null,Object? status = null,Object? phone = freezed,}) {
  return _then(_EventGuest(
userId: null == userId ? _self.userId : userId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,phone: freezed == phone ? _self.phone : phone // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$Event {

 String get id; String get title; String get description; DateTime get startDatetime; DateTime get endDatetime; String get location; String get whatsappLink; String get partifulLink; String get otherLink; bool get rsvpEnabled; String? get createdById; String? get createdByName; List<String> get coHostIds; List<String> get coHostNames; List<EventGuest> get guests; String? get myRsvp;
/// Create a copy of Event
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$EventCopyWith<Event> get copyWith => _$EventCopyWithImpl<Event>(this as Event, _$identity);

  /// Serializes this Event to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Event&&(identical(other.id, id) || other.id == id)&&(identical(other.title, title) || other.title == title)&&(identical(other.description, description) || other.description == description)&&(identical(other.startDatetime, startDatetime) || other.startDatetime == startDatetime)&&(identical(other.endDatetime, endDatetime) || other.endDatetime == endDatetime)&&(identical(other.location, location) || other.location == location)&&(identical(other.whatsappLink, whatsappLink) || other.whatsappLink == whatsappLink)&&(identical(other.partifulLink, partifulLink) || other.partifulLink == partifulLink)&&(identical(other.otherLink, otherLink) || other.otherLink == otherLink)&&(identical(other.rsvpEnabled, rsvpEnabled) || other.rsvpEnabled == rsvpEnabled)&&(identical(other.createdById, createdById) || other.createdById == createdById)&&(identical(other.createdByName, createdByName) || other.createdByName == createdByName)&&const DeepCollectionEquality().equals(other.coHostIds, coHostIds)&&const DeepCollectionEquality().equals(other.coHostNames, coHostNames)&&const DeepCollectionEquality().equals(other.guests, guests)&&(identical(other.myRsvp, myRsvp) || other.myRsvp == myRsvp));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,title,description,startDatetime,endDatetime,location,whatsappLink,partifulLink,otherLink,rsvpEnabled,createdById,createdByName,const DeepCollectionEquality().hash(coHostIds),const DeepCollectionEquality().hash(coHostNames),const DeepCollectionEquality().hash(guests),myRsvp);

@override
String toString() {
  return 'Event(id: $id, title: $title, description: $description, startDatetime: $startDatetime, endDatetime: $endDatetime, location: $location, whatsappLink: $whatsappLink, partifulLink: $partifulLink, otherLink: $otherLink, rsvpEnabled: $rsvpEnabled, createdById: $createdById, createdByName: $createdByName, coHostIds: $coHostIds, coHostNames: $coHostNames, guests: $guests, myRsvp: $myRsvp)';
}


}

/// @nodoc
abstract mixin class $EventCopyWith<$Res>  {
  factory $EventCopyWith(Event value, $Res Function(Event) _then) = _$EventCopyWithImpl;
@useResult
$Res call({
 String id, String title, String description, DateTime startDatetime, DateTime endDatetime, String location, String whatsappLink, String partifulLink, String otherLink, bool rsvpEnabled, String? createdById, String? createdByName, List<String> coHostIds, List<String> coHostNames, List<EventGuest> guests, String? myRsvp
});




}
/// @nodoc
class _$EventCopyWithImpl<$Res>
    implements $EventCopyWith<$Res> {
  _$EventCopyWithImpl(this._self, this._then);

  final Event _self;
  final $Res Function(Event) _then;

/// Create a copy of Event
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? title = null,Object? description = null,Object? startDatetime = null,Object? endDatetime = null,Object? location = null,Object? whatsappLink = null,Object? partifulLink = null,Object? otherLink = null,Object? rsvpEnabled = null,Object? createdById = freezed,Object? createdByName = freezed,Object? coHostIds = null,Object? coHostNames = null,Object? guests = null,Object? myRsvp = freezed,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,description: null == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String,startDatetime: null == startDatetime ? _self.startDatetime : startDatetime // ignore: cast_nullable_to_non_nullable
as DateTime,endDatetime: null == endDatetime ? _self.endDatetime : endDatetime // ignore: cast_nullable_to_non_nullable
as DateTime,location: null == location ? _self.location : location // ignore: cast_nullable_to_non_nullable
as String,whatsappLink: null == whatsappLink ? _self.whatsappLink : whatsappLink // ignore: cast_nullable_to_non_nullable
as String,partifulLink: null == partifulLink ? _self.partifulLink : partifulLink // ignore: cast_nullable_to_non_nullable
as String,otherLink: null == otherLink ? _self.otherLink : otherLink // ignore: cast_nullable_to_non_nullable
as String,rsvpEnabled: null == rsvpEnabled ? _self.rsvpEnabled : rsvpEnabled // ignore: cast_nullable_to_non_nullable
as bool,createdById: freezed == createdById ? _self.createdById : createdById // ignore: cast_nullable_to_non_nullable
as String?,createdByName: freezed == createdByName ? _self.createdByName : createdByName // ignore: cast_nullable_to_non_nullable
as String?,coHostIds: null == coHostIds ? _self.coHostIds : coHostIds // ignore: cast_nullable_to_non_nullable
as List<String>,coHostNames: null == coHostNames ? _self.coHostNames : coHostNames // ignore: cast_nullable_to_non_nullable
as List<String>,guests: null == guests ? _self.guests : guests // ignore: cast_nullable_to_non_nullable
as List<EventGuest>,myRsvp: freezed == myRsvp ? _self.myRsvp : myRsvp // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [Event].
extension EventPatterns on Event {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Event value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Event() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Event value)  $default,){
final _that = this;
switch (_that) {
case _Event():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Event value)?  $default,){
final _that = this;
switch (_that) {
case _Event() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String title,  String description,  DateTime startDatetime,  DateTime endDatetime,  String location,  String whatsappLink,  String partifulLink,  String otherLink,  bool rsvpEnabled,  String? createdById,  String? createdByName,  List<String> coHostIds,  List<String> coHostNames,  List<EventGuest> guests,  String? myRsvp)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Event() when $default != null:
return $default(_that.id,_that.title,_that.description,_that.startDatetime,_that.endDatetime,_that.location,_that.whatsappLink,_that.partifulLink,_that.otherLink,_that.rsvpEnabled,_that.createdById,_that.createdByName,_that.coHostIds,_that.coHostNames,_that.guests,_that.myRsvp);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String title,  String description,  DateTime startDatetime,  DateTime endDatetime,  String location,  String whatsappLink,  String partifulLink,  String otherLink,  bool rsvpEnabled,  String? createdById,  String? createdByName,  List<String> coHostIds,  List<String> coHostNames,  List<EventGuest> guests,  String? myRsvp)  $default,) {final _that = this;
switch (_that) {
case _Event():
return $default(_that.id,_that.title,_that.description,_that.startDatetime,_that.endDatetime,_that.location,_that.whatsappLink,_that.partifulLink,_that.otherLink,_that.rsvpEnabled,_that.createdById,_that.createdByName,_that.coHostIds,_that.coHostNames,_that.guests,_that.myRsvp);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String title,  String description,  DateTime startDatetime,  DateTime endDatetime,  String location,  String whatsappLink,  String partifulLink,  String otherLink,  bool rsvpEnabled,  String? createdById,  String? createdByName,  List<String> coHostIds,  List<String> coHostNames,  List<EventGuest> guests,  String? myRsvp)?  $default,) {final _that = this;
switch (_that) {
case _Event() when $default != null:
return $default(_that.id,_that.title,_that.description,_that.startDatetime,_that.endDatetime,_that.location,_that.whatsappLink,_that.partifulLink,_that.otherLink,_that.rsvpEnabled,_that.createdById,_that.createdByName,_that.coHostIds,_that.coHostNames,_that.guests,_that.myRsvp);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Event implements Event {
  const _Event({required this.id, required this.title, required this.description, required this.startDatetime, required this.endDatetime, required this.location, this.whatsappLink = '', this.partifulLink = '', this.otherLink = '', this.rsvpEnabled = false, this.createdById, this.createdByName, final  List<String> coHostIds = const [], final  List<String> coHostNames = const [], final  List<EventGuest> guests = const [], this.myRsvp}): _coHostIds = coHostIds,_coHostNames = coHostNames,_guests = guests;
  factory _Event.fromJson(Map<String, dynamic> json) => _$EventFromJson(json);

@override final  String id;
@override final  String title;
@override final  String description;
@override final  DateTime startDatetime;
@override final  DateTime endDatetime;
@override final  String location;
@override@JsonKey() final  String whatsappLink;
@override@JsonKey() final  String partifulLink;
@override@JsonKey() final  String otherLink;
@override@JsonKey() final  bool rsvpEnabled;
@override final  String? createdById;
@override final  String? createdByName;
 final  List<String> _coHostIds;
@override@JsonKey() List<String> get coHostIds {
  if (_coHostIds is EqualUnmodifiableListView) return _coHostIds;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_coHostIds);
}

 final  List<String> _coHostNames;
@override@JsonKey() List<String> get coHostNames {
  if (_coHostNames is EqualUnmodifiableListView) return _coHostNames;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_coHostNames);
}

 final  List<EventGuest> _guests;
@override@JsonKey() List<EventGuest> get guests {
  if (_guests is EqualUnmodifiableListView) return _guests;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_guests);
}

@override final  String? myRsvp;

/// Create a copy of Event
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$EventCopyWith<_Event> get copyWith => __$EventCopyWithImpl<_Event>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$EventToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Event&&(identical(other.id, id) || other.id == id)&&(identical(other.title, title) || other.title == title)&&(identical(other.description, description) || other.description == description)&&(identical(other.startDatetime, startDatetime) || other.startDatetime == startDatetime)&&(identical(other.endDatetime, endDatetime) || other.endDatetime == endDatetime)&&(identical(other.location, location) || other.location == location)&&(identical(other.whatsappLink, whatsappLink) || other.whatsappLink == whatsappLink)&&(identical(other.partifulLink, partifulLink) || other.partifulLink == partifulLink)&&(identical(other.otherLink, otherLink) || other.otherLink == otherLink)&&(identical(other.rsvpEnabled, rsvpEnabled) || other.rsvpEnabled == rsvpEnabled)&&(identical(other.createdById, createdById) || other.createdById == createdById)&&(identical(other.createdByName, createdByName) || other.createdByName == createdByName)&&const DeepCollectionEquality().equals(other._coHostIds, _coHostIds)&&const DeepCollectionEquality().equals(other._coHostNames, _coHostNames)&&const DeepCollectionEquality().equals(other._guests, _guests)&&(identical(other.myRsvp, myRsvp) || other.myRsvp == myRsvp));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,title,description,startDatetime,endDatetime,location,whatsappLink,partifulLink,otherLink,rsvpEnabled,createdById,createdByName,const DeepCollectionEquality().hash(_coHostIds),const DeepCollectionEquality().hash(_coHostNames),const DeepCollectionEquality().hash(_guests),myRsvp);

@override
String toString() {
  return 'Event(id: $id, title: $title, description: $description, startDatetime: $startDatetime, endDatetime: $endDatetime, location: $location, whatsappLink: $whatsappLink, partifulLink: $partifulLink, otherLink: $otherLink, rsvpEnabled: $rsvpEnabled, createdById: $createdById, createdByName: $createdByName, coHostIds: $coHostIds, coHostNames: $coHostNames, guests: $guests, myRsvp: $myRsvp)';
}


}

/// @nodoc
abstract mixin class _$EventCopyWith<$Res> implements $EventCopyWith<$Res> {
  factory _$EventCopyWith(_Event value, $Res Function(_Event) _then) = __$EventCopyWithImpl;
@override @useResult
$Res call({
 String id, String title, String description, DateTime startDatetime, DateTime endDatetime, String location, String whatsappLink, String partifulLink, String otherLink, bool rsvpEnabled, String? createdById, String? createdByName, List<String> coHostIds, List<String> coHostNames, List<EventGuest> guests, String? myRsvp
});




}
/// @nodoc
class __$EventCopyWithImpl<$Res>
    implements _$EventCopyWith<$Res> {
  __$EventCopyWithImpl(this._self, this._then);

  final _Event _self;
  final $Res Function(_Event) _then;

/// Create a copy of Event
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? title = null,Object? description = null,Object? startDatetime = null,Object? endDatetime = null,Object? location = null,Object? whatsappLink = null,Object? partifulLink = null,Object? otherLink = null,Object? rsvpEnabled = null,Object? createdById = freezed,Object? createdByName = freezed,Object? coHostIds = null,Object? coHostNames = null,Object? guests = null,Object? myRsvp = freezed,}) {
  return _then(_Event(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,description: null == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String,startDatetime: null == startDatetime ? _self.startDatetime : startDatetime // ignore: cast_nullable_to_non_nullable
as DateTime,endDatetime: null == endDatetime ? _self.endDatetime : endDatetime // ignore: cast_nullable_to_non_nullable
as DateTime,location: null == location ? _self.location : location // ignore: cast_nullable_to_non_nullable
as String,whatsappLink: null == whatsappLink ? _self.whatsappLink : whatsappLink // ignore: cast_nullable_to_non_nullable
as String,partifulLink: null == partifulLink ? _self.partifulLink : partifulLink // ignore: cast_nullable_to_non_nullable
as String,otherLink: null == otherLink ? _self.otherLink : otherLink // ignore: cast_nullable_to_non_nullable
as String,rsvpEnabled: null == rsvpEnabled ? _self.rsvpEnabled : rsvpEnabled // ignore: cast_nullable_to_non_nullable
as bool,createdById: freezed == createdById ? _self.createdById : createdById // ignore: cast_nullable_to_non_nullable
as String?,createdByName: freezed == createdByName ? _self.createdByName : createdByName // ignore: cast_nullable_to_non_nullable
as String?,coHostIds: null == coHostIds ? _self._coHostIds : coHostIds // ignore: cast_nullable_to_non_nullable
as List<String>,coHostNames: null == coHostNames ? _self._coHostNames : coHostNames // ignore: cast_nullable_to_non_nullable
as List<String>,guests: null == guests ? _self._guests : guests // ignore: cast_nullable_to_non_nullable
as List<EventGuest>,myRsvp: freezed == myRsvp ? _self.myRsvp : myRsvp // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}

// dart format on
