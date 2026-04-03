import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/guidelines_provider.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/secure_storage.dart';
import 'package:dio/dio.dart';

import '../helpers/fake_secure_storage.dart';

class MockApiClient extends Mock implements ApiClient {}

final _guidelinesJson = {
  'content': '# Community Guidelines\nBe kind.',
  'updated_at': '2026-01-15T12:00:00Z',
};

void main() {
  late MockApiClient mockApi;
  late ProviderContainer container;

  setUp(() {
    mockApi = MockApiClient();
    container = ProviderContainer(
      overrides: [
        secureStorageProvider.overrideWithValue(
          SecureStorageService.withStorage(FakeSecureStorage()),
        ),
        apiClientProvider.overrideWithValue(mockApi),
      ],
      retry: (_, __) => null,
    );
  });

  tearDown(() => container.dispose());

  group('guidelinesProvider', () {
    test('returns Guidelines on success', () async {
      when(() => mockApi.get('/api/community/guidelines/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/community/guidelines/'),
          statusCode: 200,
          data: _guidelinesJson,
        ),
      );

      final result = await container.read(guidelinesProvider.future);
      expect(result.content, '# Community Guidelines\nBe kind.');
    });

    test('propagates error on failure', () async {
      when(() => mockApi.get('/api/community/guidelines/')).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/community/guidelines/'),
          type: DioExceptionType.connectionError,
        ),
      );

      await expectLater(
        container.read(guidelinesProvider.future),
        throwsA(isA<DioException>()),
      );
    });
  });

  group('GuidelinesNotifier', () {
    test('build loads content from API', () async {
      when(() => mockApi.get('/api/community/guidelines/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/community/guidelines/'),
          statusCode: 200,
          data: _guidelinesJson,
        ),
      );

      final result = await container.read(guidelinesNotifierProvider.future);
      expect(result.content, contains('Guidelines'));
    });

    test('saveContent patches and updates state', () async {
      when(() => mockApi.get('/api/community/guidelines/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/community/guidelines/'),
          statusCode: 200,
          data: _guidelinesJson,
        ),
      );
      when(
        () => mockApi.patch(
          '/api/community/guidelines/',
          data: any(named: 'data'),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/community/guidelines/'),
          statusCode: 200,
          data: {
            'content': 'Updated content',
            'updated_at': '2026-02-01T12:00:00Z',
          },
        ),
      );

      await container.read(guidelinesNotifierProvider.future);
      await container
          .read(guidelinesNotifierProvider.notifier)
          .saveContent('Updated content');

      final state = container.read(guidelinesNotifierProvider);
      expect(state.value?.content, 'Updated content');
    });
  });
}
