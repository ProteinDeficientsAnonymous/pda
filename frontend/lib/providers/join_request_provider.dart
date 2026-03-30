import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';

class JoinRequestNotifier extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> submit({
    required String displayName,
    required String phoneNumber,
    required Map<String, String> answers,
  }) async {
    state = const AsyncLoading();
    final api = ref.read(apiClientProvider);
    try {
      await api.post(
        '/api/community/join-request/',
        data: {
          'display_name': displayName,
          'phone_number': phoneNumber,
          'answers': answers,
        },
      );
      state = const AsyncData(null);
    } catch (e, st) {
      state = AsyncError(ApiError.from(e), st);
    }
  }
}

final joinRequestProvider = AsyncNotifierProvider<JoinRequestNotifier, void>(
  JoinRequestNotifier.new,
);
