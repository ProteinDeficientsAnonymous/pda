import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/secure_storage.dart';

import '../helpers/fake_secure_storage.dart';

class MockApiClient extends Mock implements ApiClient {}

// Notifier that resolves immediately with null (no network) so authProvider
// doesn't block event_provider tests.
class _InstantAuthNotifier extends AuthNotifier {
  @override
  Future<User?> build() async => null;

  @override
  Future<void> logout() async {
    state = const AsyncData(null);
  }
}

final _eventJson = {
  'id': 'evt-1',
  'title': 'Movie Night',
  'description': 'Watch a film together',
  'start_datetime': '2026-04-01T19:00:00Z',
  'end_datetime': '2026-04-01T21:00:00Z',
  'location': 'The usual spot',
  'whatsapp_link': '',
  'partiful_link': '',
  'other_link': '',
  'rsvp_enabled': false,
  'created_by_id': null,
  'created_by_name': null,
  'co_host_ids': <String>[],
  'co_host_names': <String>[],
  'guests': <dynamic>[],
  'my_rsvp': null,
};

/// Builds a [ProviderContainer] and subscribes a listener to [eventsProvider]
/// so the provider stays alive and actually runs (auto-dispose won't kill it).
/// Retry is disabled so that FutureProvider errors settle immediately as
/// AsyncError rather than looping through Riverpod 3's retry mechanism.
ProviderContainer _makeContainer(MockApiClient mockApi) {
  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith(() => _InstantAuthNotifier()),
      secureStorageProvider.overrideWithValue(
        SecureStorageService.withStorage(FakeSecureStorage()),
      ),
      apiClientProvider.overrideWithValue(mockApi),
    ],
    retry: (_, __) => null,
  );
  // Keep eventsProvider alive by subscribing a listener.
  container.listen(eventsProvider, (_, __) {});
  return container;
}

void main() {
  late MockApiClient mockApi;

  setUp(() {
    mockApi = MockApiClient();
  });

  test('returns list of events on success', () async {
    when(() => mockApi.get('/api/community/events/')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/api/community/events/'),
        statusCode: 200,
        data: [_eventJson],
      ),
    );

    final container = _makeContainer(mockApi);
    addTearDown(container.dispose);

    final result = await container.read(eventsProvider.future);
    expect(result.length, 1);
    expect(result.first.title, 'Movie Night');
  });

  test('returns empty list when API returns empty array', () async {
    when(() => mockApi.get('/api/community/events/')).thenAnswer(
      (_) async => Response(
        requestOptions: RequestOptions(path: '/api/community/events/'),
        statusCode: 200,
        data: <dynamic>[],
      ),
    );

    final container = _makeContainer(mockApi);
    addTearDown(container.dispose);

    final result = await container.read(eventsProvider.future);
    expect(result, isEmpty);
  });

  test('propagates error on network failure', () async {
    when(() => mockApi.get('/api/community/events/')).thenThrow(
      DioException(
        requestOptions: RequestOptions(path: '/api/community/events/'),
        type: DioExceptionType.connectionError,
      ),
    );

    final container = _makeContainer(mockApi);
    addTearDown(container.dispose);

    // Retry is disabled on the container so the provider settles immediately
    // to AsyncError. Use try/catch to wait for completion, then inspect state.
    try {
      await container.read(eventsProvider.future);
    } catch (_) {
      // ignore — waiting for the provider to settle
    }
    final state = container.read(eventsProvider);
    expect(state.hasError, isTrue);
    expect(state.error, isA<DioException>());
  });

  test('refetches when auth state changes', () async {
    var callCount = 0;
    when(() => mockApi.get('/api/community/events/')).thenAnswer((_) async {
      callCount++;
      return Response(
        requestOptions: RequestOptions(path: '/api/community/events/'),
        statusCode: 200,
        data: <dynamic>[],
      );
    });

    final container = _makeContainer(mockApi);
    addTearDown(container.dispose);

    // Initial fetch
    await container.read(eventsProvider.future);
    final countAfterFirst = callCount;

    // Invalidate auth → eventsProvider watches authProvider, so it should
    // also re-fetch.
    container.invalidate(authProvider);
    // Wait for auth rebuild
    await container.read(authProvider.future);
    // eventsProvider should have been re-triggered
    await container.read(eventsProvider.future);

    expect(callCount, greaterThan(countAfterFirst));
  });
}
