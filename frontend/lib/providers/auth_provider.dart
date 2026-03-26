import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/user.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/services/secure_storage.dart';

final _log = Logger('AuthProvider');

final secureStorageProvider = Provider<SecureStorageService>(
  (_) => SecureStorageService(),
);

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(ref.watch(secureStorageProvider)),
);

class AuthNotifier extends AsyncNotifier<User?> {
  @override
  Future<User?> build() async {
    final storage = ref.watch(secureStorageProvider);
    try {
      final token = await storage.getAccessToken();
      if (token == null) return null;
      final api = ref.watch(apiClientProvider);
      final response = await api.get('/api/auth/me/');
      return User.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      _log.warning('Token refresh failed, clearing session', e);
      await storage.clearTokens();
      return null;
    }
  }

  Future<void> login(String phoneNumber, String password) async {
    state = const AsyncLoading();
    final api = ref.watch(apiClientProvider);
    final storage = ref.watch(secureStorageProvider);
    try {
      final response = await api.post(
        '/api/auth/login/',
        data: {'phone_number': phoneNumber, 'password': password},
      );
      await storage.saveTokens(
        access: response.data['access'] as String,
        refresh: response.data['refresh'] as String,
      );
      final meResponse = await api.get('/api/auth/me/');
      state = AsyncData(User.fromJson(meResponse.data as Map<String, dynamic>));
      _log.info('Login successful');
    } catch (e, st) {
      _log.warning('Login failed', e);
      state = AsyncError(ApiError.from(e), st);
    }
  }

  Future<void> updateProfile({String? displayName, String? email}) async {
    final api = ref.watch(apiClientProvider);
    final data = <String, dynamic>{};
    if (displayName != null) data['display_name'] = displayName;
    if (email != null) data['email'] = email;
    final response = await api.patch('/api/auth/me/', data: data);
    state = AsyncData(User.fromJson(response.data as Map<String, dynamic>));
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    final api = ref.watch(apiClientProvider);
    await api.post(
      '/api/auth/change-password/',
      data: {'current_password': currentPassword, 'new_password': newPassword},
    );
  }

  Future<void> completeOnboarding({
    required String displayName,
    String? email,
    required String newPassword,
  }) async {
    final api = ref.watch(apiClientProvider);
    final data = <String, dynamic>{
      'display_name': displayName,
      'new_password': newPassword,
    };
    if (email != null && email.isNotEmpty) data['email'] = email;
    final response = await api.post(
      '/api/auth/complete-onboarding/',
      data: data,
    );
    state = AsyncData(User.fromJson(response.data as Map<String, dynamic>));
  }

  Future<void> logout() async {
    final storage = ref.watch(secureStorageProvider);
    await storage.clearTokens();
    state = const AsyncData(null);
    _log.info('User logged out');
  }
}

final authProvider = AsyncNotifierProvider<AuthNotifier, User?>(
  AuthNotifier.new,
);
