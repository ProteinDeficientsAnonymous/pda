import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/services/secure_storage.dart';

import '../helpers/fake_secure_storage.dart';

class MockApiClient extends Mock implements ApiClient {}

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

  group('AuthNotifier.login', () {
    test('sets InvalidCredentials error on 401', () async {
      // Wait for build() to complete before calling login()
      await container.read(authProvider.future);

      when(
        () => mockApi.post('/api/auth/login/', data: any(named: 'data')),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/auth/login/'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/api/auth/login/'),
            statusCode: 401,
            data: {'detail': 'Invalid credentials'},
          ),
        ),
      );

      await container.read(authProvider.notifier).login('a@b.c', 'wrong');

      final state = container.read(authProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<InvalidCredentials>());
    });

    test('sets NetworkError on connection failure', () async {
      await container.read(authProvider.future);

      when(
        () => mockApi.post('/api/auth/login/', data: any(named: 'data')),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/auth/login/'),
          type: DioExceptionType.connectionError,
        ),
      );

      await container.read(authProvider.notifier).login('a@b.c', 'pass');

      final state = container.read(authProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<NetworkError>());
    });

    test('sets ServerError on 500', () async {
      await container.read(authProvider.future);

      when(
        () => mockApi.post('/api/auth/login/', data: any(named: 'data')),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/auth/login/'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/api/auth/login/'),
            statusCode: 500,
          ),
        ),
      );

      await container.read(authProvider.notifier).login('a@b.c', 'pass');

      final state = container.read(authProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<ServerError>());
    });
  });
}
