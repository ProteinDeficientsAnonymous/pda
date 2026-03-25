import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';

class JoinRequestNotifier extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> submit({
    required String name,
    required String email,
    required String pronouns,
    required String howTheyHeard,
    required String whyJoin,
  }) async {
    state = const AsyncLoading();
    final api = ref.watch(apiClientProvider);
    try {
      await api.post(
        '/api/community/join-request/',
        data: {
          'name': name,
          'email': email,
          'pronouns': pronouns,
          'how_they_heard': howTheyHeard,
          'why_join': whyJoin,
        },
      );
      state = const AsyncData(null);
    } catch (e, st) {
      state = AsyncError(e, st);
    }
  }
}

final joinRequestProvider = AsyncNotifierProvider<JoinRequestNotifier, void>(
  JoinRequestNotifier.new,
);
