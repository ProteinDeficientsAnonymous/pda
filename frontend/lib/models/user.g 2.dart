// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_Role _$RoleFromJson(Map<String, dynamic> json) => _Role(
  id: json['id'] as String,
  name: json['name'] as String,
  isDefault: json['is_default'] as bool? ?? false,
  permissions:
      (json['permissions'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ??
      const [],
);

Map<String, dynamic> _$RoleToJson(_Role instance) => <String, dynamic>{
  'id': instance.id,
  'name': instance.name,
  'is_default': instance.isDefault,
  'permissions': instance.permissions,
};

_User _$UserFromJson(Map<String, dynamic> json) => _User(
  id: json['id'] as String,
  phoneNumber: json['phone_number'] as String,
  displayName: json['display_name'] as String? ?? '',
  email: json['email'] as String? ?? '',
  isSuperuser: json['is_superuser'] as bool? ?? false,
  needsOnboarding: json['needs_onboarding'] as bool? ?? false,
  roles:
      (json['roles'] as List<dynamic>?)
          ?.map((e) => Role.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
);

Map<String, dynamic> _$UserToJson(_User instance) => <String, dynamic>{
  'id': instance.id,
  'phone_number': instance.phoneNumber,
  'display_name': instance.displayName,
  'email': instance.email,
  'is_superuser': instance.isSuperuser,
  'needs_onboarding': instance.needsOnboarding,
  'roles': instance.roles.map((e) => e.toJson()).toList(),
};
