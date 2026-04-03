import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:pda/config/constants.dart';

part 'user.freezed.dart';
part 'user.g.dart';

@freezed
abstract class Role with _$Role {
  const factory Role({
    required String id,
    required String name,
    @Default(false) bool isDefault,
    @Default([]) List<String> permissions,
  }) = _Role;

  factory Role.fromJson(Map<String, dynamic> json) => _$RoleFromJson(json);
}

@freezed
abstract class User with _$User {
  const User._();

  const factory User({
    required String id,
    required String phoneNumber,
    @Default('') String displayName,
    @Default('') String email,
    @Default(false) bool isSuperuser,
    @Default(false) bool needsOnboarding,
    @Default('') String profilePhotoUrl,
    @Default(true) bool showPhone,
    @Default(true) bool showEmail,
    @Default(false) bool isPaused,
    @Default([]) List<Role> roles,
  }) = _User;

  factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);

  bool hasPermission(String permission) {
    if (isSuperuser) return true;
    return roles.any(
      (r) =>
          (r.name == RoleName.admin && r.isDefault) ||
          r.permissions.contains(permission),
    );
  }

  bool get hasAnyAdminPermission =>
      hasPermission(Permission.manageEvents) ||
      hasPermission(Permission.manageUsers) ||
      hasPermission(Permission.approveJoinRequests) ||
      hasPermission(Permission.manageWhatsapp) ||
      hasPermission(Permission.editJoinQuestions) ||
      hasPermission(Permission.manageDocs);
}
