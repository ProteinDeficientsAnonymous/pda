import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/notification_provider.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/secure_storage.dart';

import '../helpers/fake_secure_storage.dart';

class MockApiClient extends Mock implements ApiClient {}

class _AuthedNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => const User(
    id: 'user-1',
    displayName: 'Test User',
    phoneNumber: '+1234567890',
  );

  @override
  Future<void> logout() async {
    state = const AsyncData(null);
  }
}

class _GuestNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {}
}

final _notificationJson = {
  'id': 'notif-1',
  'notification_type': 'event_invite',
  'event_id': 'evt-1',
  'message': 'Alice invited you to Party',
  'is_read': false,
  'created_at': '2026-04-01T10:00:00Z',
};

ProviderContainer _makeContainer(MockApiClient mockApi, {bool authed = true}) {
  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith(
        () => authed ? _AuthedNotifier() : _GuestNotifier(),
      ),
      secureStorageProvider.overrideWithValue(
        SecureStorageService.withStorage(FakeSecureStorage()),
      ),
      apiClientProvider.overrideWithValue(mockApi),
    ],
    retry: (_, __) => null,
  );
  container.listen(notificationsProvider, (_, __) {});
  return container;
}

void main() {
  late MockApiClient mockApi;

  setUp(() {
    mockApi = MockApiClient();
  });

  group('notificationsProvider', () {
    test('returns list of notifications on success', () async {
      when(() => mockApi.get('/api/notifications/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/notifications/'),
          statusCode: 200,
          data: [_notificationJson],
        ),
      );

      final container = _makeContainer(mockApi);
      addTearDown(container.dispose);

      final result = await container.read(notificationsProvider.future);
      expect(result.length, 1);
      expect(result.first.message, 'Alice invited you to Party');
      expect(result.first.isRead, false);
      expect(result.first.notificationType, 'event_invite');
    });

    test('returns empty list when unauthenticated', () async {
      final container = _makeContainer(mockApi, authed: false);
      addTearDown(container.dispose);

      final result = await container.read(notificationsProvider.future);
      expect(result, isEmpty);
      verifyNever(() => mockApi.get(any()));
    });

    test('propagates error on API failure', () async {
      when(() => mockApi.get('/api/notifications/')).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/notifications/'),
          type: DioExceptionType.connectionError,
        ),
      );

      final container = _makeContainer(mockApi);
      addTearDown(container.dispose);

      await expectLater(
        container.read(notificationsProvider.future),
        throwsA(isA<DioException>()),
      );
    });
  });
}
