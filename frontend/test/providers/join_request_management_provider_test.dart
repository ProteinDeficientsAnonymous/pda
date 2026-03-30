import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/join_request_management_provider.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/secure_storage.dart';

import '../helpers/fake_secure_storage.dart';

class MockApiClient extends Mock implements ApiClient {}

final _requestJson = {
  'id': 'jr-1',
  'display_name': 'Sam Green',
  'phone_number': '+12025559999',
  'answers': [
    {
      'question_id': 'q1',
      'label': 'Why do you want to join?',
      'answer': 'I love animals',
    },
  ],
  'submitted_at': '2026-03-01T10:00:00Z',
  'status': 'pending',
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
    );
  });

  tearDown(() => container.dispose());

  group('joinRequestsProvider', () {
    test('returns list of join requests on success', () async {
      when(() => mockApi.get('/api/community/join-requests/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/community/join-requests/'),
          statusCode: 200,
          data: [_requestJson],
        ),
      );

      final result = await container.read(joinRequestsProvider.future);
      expect(result.length, 1);
      expect(result.first.displayName, 'Sam Green');
      expect(result.first.status, 'pending');
    });

    test('throws _PermissionException on 403', () async {
      when(() => mockApi.get('/api/community/join-requests/')).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/community/join-requests/'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(
              path: '/api/community/join-requests/',
            ),
            statusCode: 403,
          ),
        ),
      );

      final state = await container
          .read(joinRequestsProvider.future)
          .then(
            (_) => container.read(joinRequestsProvider),
            onError: (_) => container.read(joinRequestsProvider),
          );
      expect(state.hasError, isTrue);
      expect(state.error.toString(), contains('permission'));
    });

    test('rethrows other DioExceptions', () async {
      when(() => mockApi.get('/api/community/join-requests/')).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/community/join-requests/'),
          type: DioExceptionType.connectionError,
        ),
      );

      final state = await container
          .read(joinRequestsProvider.future)
          .then(
            (_) => container.read(joinRequestsProvider),
            onError: (_) => container.read(joinRequestsProvider),
          );
      expect(state.hasError, isTrue);
    });
  });
}
