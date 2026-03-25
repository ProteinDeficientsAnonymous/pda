import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';

final usersProvider = FutureProvider<List<User>>((ref) async {
  final api = ref.watch(apiClientProvider);
  final response = await api.get('/api/auth/users/');
  final list = response.data as List<dynamic>;
  return list.map((e) => User.fromJson(e as Map<String, dynamic>)).toList();
});

class UserManagementNotifier extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> deleteUser(String userId) async {
    final api = ref.read(apiClientProvider);
    await api.delete('/api/auth/users/$userId/');
    ref.invalidate(usersProvider);
  }

  Future<String> resetPassword(String userId) async {
    final api = ref.read(apiClientProvider);
    final response = await api.post('/api/auth/users/$userId/reset-password/');
    return response.data['temporary_password'] as String;
  }
}

final userManagementProvider =
    AsyncNotifierProvider<UserManagementNotifier, void>(UserManagementNotifier.new);
