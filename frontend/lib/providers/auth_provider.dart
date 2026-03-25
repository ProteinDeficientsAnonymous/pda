import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/user.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/secure_storage.dart';

final secureStorageProvider = Provider<SecureStorageService>((_) => SecureStorageService());

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(ref.watch(secureStorageProvider)),
);

class AuthNotifier extends AsyncNotifier<User?> {
  @override
  Future<User?> build() async {
    final storage = ref.watch(secureStorageProvider);
    final token = await storage.getAccessToken();
    if (token == null) return null;
    try {
      final api = ref.watch(apiClientProvider);
      final response = await api.get('/api/auth/me/');
      return User.fromJson(response.data as Map<String, dynamic>);
    } catch (_) {
      await storage.clearTokens();
      return null;
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncLoading();
    final api = ref.watch(apiClientProvider);
    final storage = ref.watch(secureStorageProvider);
    try {
      final response = await api.post(
        '/api/auth/login/',
        data: {'email': email, 'password': password},
      );
      await storage.saveTokens(
        access: response.data['access'] as String,
        refresh: response.data['refresh'] as String,
      );
      final meResponse = await api.get('/api/auth/me/');
      state = AsyncData(User.fromJson(meResponse.data as Map<String, dynamic>));
    } catch (e, st) {
      state = AsyncError(e, st);
    }
  }

  Future<void> logout() async {
    final storage = ref.watch(secureStorageProvider);
    await storage.clearTokens();
    state = const AsyncData(null);
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, User?>(AuthNotifier.new);
