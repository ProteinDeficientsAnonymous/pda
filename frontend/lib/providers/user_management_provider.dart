import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('UserManagement');

final usersProvider = FutureProvider<List<User>>((ref) async {
  final api = ref.watch(apiClientProvider);
  try {
    final response = await api.get('/api/auth/users/');
    final list = response.data as List<dynamic>;
    return list.map((e) => User.fromJson(e as Map<String, dynamic>)).toList();
  } on DioException catch (e) {
    if (e.response?.statusCode == 403) {
      throw const _PermissionException();
    }
    rethrow;
  }
});

class _PermissionException implements Exception {
  const _PermissionException();

  @override
  String toString() => "You don't have permission to view members.";
}

final rolesProvider = FutureProvider<List<Role>>((ref) async {
  final api = ref.watch(apiClientProvider);
  final response = await api.get('/api/auth/roles/');
  final list = response.data as List<dynamic>;
  return list.map((e) => Role.fromJson(e as Map<String, dynamic>)).toList();
});

class UserManagementNotifier extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<Map<String, dynamic>> createUser({
    required String phoneNumber,
    String displayName = '',
    String email = '',
    String? roleId,
  }) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.post(
        '/api/auth/create-user/',
        data: {
          'phone_number': phoneNumber,
          'display_name': displayName,
          'email': email,
          if (roleId != null) 'role_id': roleId,
        },
      );
      ref.invalidate(usersProvider);
      _log.info('created user $phoneNumber');
      return response.data as Map<String, dynamic>;
    } catch (e, st) {
      _log.warning('failed to create user $phoneNumber', e, st);
      rethrow;
    }
  }

  Future<Map<String, dynamic>> bulkCreateUsers(
    List<String> phoneNumbers,
  ) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.post(
        '/api/auth/bulk-create-users/',
        data: {'phone_numbers': phoneNumbers},
      );
      ref.invalidate(usersProvider);
      _log.info('bulk created ${phoneNumbers.length} users');
      return response.data as Map<String, dynamic>;
    } catch (e, st) {
      _log.warning('failed to bulk create ${phoneNumbers.length} users', e, st);
      rethrow;
    }
  }

  Future<void> deleteUser(String userId) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.delete('/api/auth/users/$userId/');
      ref.invalidate(usersProvider);
      _log.info('deleted user $userId');
    } catch (e, st) {
      _log.warning('failed to delete user $userId', e, st);
      rethrow;
    }
  }

  Future<String> resetPassword(String userId) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.post(
        '/api/auth/users/$userId/reset-password/',
      );
      _log.info('reset password for user $userId');
      return response.data['magic_link_token'] as String;
    } catch (e, st) {
      _log.warning('failed to reset password for user $userId', e, st);
      rethrow;
    }
  }

  Future<String> generateMagicLink(String userId) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.post('/api/auth/users/$userId/magic-link/');
      _log.info('generated magic link for user $userId');
      return response.data['magic_link_token'] as String;
    } catch (e, st) {
      _log.warning('failed to generate magic link for user $userId', e, st);
      rethrow;
    }
  }

  Future<void> togglePause(String userId, {required bool paused}) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.patch('/api/auth/users/$userId/', data: {'is_paused': paused});
      ref.invalidate(usersProvider);
      _log.info('${paused ? 'paused' : 'unpaused'} user $userId');
    } catch (e, st) {
      _log.warning('failed to toggle pause for user $userId', e, st);
      rethrow;
    }
  }

  Future<void> updateUserRoles(String userId, List<String> roleIds) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.patch(
        '/api/auth/users/$userId/roles/',
        data: {'role_ids': roleIds},
      );
      ref.invalidate(usersProvider);
      _log.info('updated roles for user $userId');
    } catch (e, st) {
      _log.warning('failed to update roles for user $userId', e, st);
      rethrow;
    }
  }

  Future<void> createRole(String name, List<String> permissions) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.post(
        '/api/auth/roles/',
        data: {'name': name, 'permissions': permissions},
      );
      ref.invalidate(rolesProvider);
      _log.info('created role $name');
    } catch (e, st) {
      _log.warning('failed to create role $name', e, st);
      rethrow;
    }
  }

  Future<void> updateRole(String roleId, List<String> permissions) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.patch(
        '/api/auth/roles/$roleId/',
        data: {'permissions': permissions},
      );
      ref.invalidate(rolesProvider);
      ref.invalidate(usersProvider);
      _log.info('updated role $roleId');
    } catch (e, st) {
      _log.warning('failed to update role $roleId', e, st);
      rethrow;
    }
  }

  Future<void> deleteRole(String roleId) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.delete('/api/auth/roles/$roleId/');
      ref.invalidate(rolesProvider);
      ref.invalidate(usersProvider);
      _log.info('deleted role $roleId');
    } catch (e, st) {
      _log.warning('failed to delete role $roleId', e, st);
      rethrow;
    }
  }
}

final userManagementProvider =
    AsyncNotifierProvider<UserManagementNotifier, void>(
      UserManagementNotifier.new,
    );
