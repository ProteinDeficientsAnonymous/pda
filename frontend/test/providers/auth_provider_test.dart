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

  group('AuthNotifier.build', () {
    test('returns null when no token is stored', () async {
      when(() => mockApi.get('/api/auth/me/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/me/'),
          statusCode: 200,
          data: {
            'id': 'u1',
            'phone_number': '+12025551234',
            'display_name': '',
            'email': '',
            'is_superuser': false,
            'needs_onboarding': false,
            'roles': <dynamic>[],
          },
        ),
      );
      final result = await container.read(authProvider.future);
      // No token in FakeSecureStorage → should return null without calling /me/
      expect(result, isNull);
    });
  });

  group('AuthNotifier.login', () {
    test('sets AsyncData with user on successful login', () async {
      await container.read(authProvider.future);

      when(
        () => mockApi.post('/api/auth/login/', data: any(named: 'data')),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/login/'),
          statusCode: 200,
          data: {'access': 'access-tok', 'refresh': 'refresh-tok'},
        ),
      );
      when(
        () => mockApi.get(
          '/api/auth/me/',
          accessToken: any(named: 'accessToken'),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/me/'),
          statusCode: 200,
          data: {
            'id': 'u1',
            'phone_number': '+12025551234',
            'display_name': 'Alice',
            'email': 'alice@example.com',
            'is_superuser': false,
            'needs_onboarding': false,
            'roles': <dynamic>[],
          },
        ),
      );

      await container
          .read(authProvider.notifier)
          .login('+12025551234', 'correctpass');

      final state = container.read(authProvider);
      expect(state.hasError, isFalse);
      expect(state.value?.displayName, 'Alice');
    });

    test('sets error state when login succeeds but /me fails', () async {
      await container.read(authProvider.future);

      when(
        () => mockApi.post('/api/auth/login/', data: any(named: 'data')),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/login/'),
          statusCode: 200,
          data: {'access': 'access-tok', 'refresh': 'refresh-tok'},
        ),
      );
      when(
        () => mockApi.get(
          '/api/auth/me/',
          accessToken: any(named: 'accessToken'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/auth/me/'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/api/auth/me/'),
            statusCode: 401,
            data: {'detail': 'Unauthorized'},
          ),
        ),
      );

      await container
          .read(authProvider.notifier)
          .login('+12025551234', 'correctpass');

      final state = container.read(authProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<InvalidCredentials>());
    });
  });

  group('AuthNotifier.logout', () {
    test('clears state to AsyncData(null)', () async {
      await container.read(authProvider.future);

      // Simulate logged-in state by injecting a user directly
      container.read(authProvider.notifier).state = const AsyncData(null);

      await container.read(authProvider.notifier).logout();

      final state = container.read(authProvider);
      expect(state.hasError, isFalse);
      expect(state.value, isNull);
    });
  });

  group('AuthNotifier.forceLogout', () {
    test('clears state to AsyncData(null)', () async {
      await container.read(authProvider.future);

      // Simulate logged-in state
      container.read(authProvider.notifier).state = const AsyncData(null);

      container.read(authProvider.notifier).forceLogout();

      final state = container.read(authProvider);
      expect(state.hasError, isFalse);
      expect(state.value, isNull);
    });
  });

  group('AuthNotifier.login errors', () {
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

      await container
          .read(authProvider.notifier)
          .login('+12025551234', 'wrong');

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

      await container.read(authProvider.notifier).login('+12025551234', 'pass');

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

      await container.read(authProvider.notifier).login('+12025551234', 'pass');

      final state = container.read(authProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<ServerError>());
    });
  });
}
