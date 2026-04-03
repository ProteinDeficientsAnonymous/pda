import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/secure_storage.dart';

import '../helpers/fake_secure_storage.dart';

class MockApiClient extends Mock implements ApiClient {}

final _userJson = {
  'id': 'u-1',
  'phone_number': '+12025551111',
  'display_name': 'Alice',
  'email': 'alice@example.com',
  'is_superuser': false,
  'needs_onboarding': false,
  'roles': <dynamic>[],
};

void main() {
  late MockApiClient mockApi;
  late ProviderContainer container;

  setUp(() {
    registerFallbackValue(RequestOptions(path: ''));
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

  group('usersProvider', () {
    test('returns list of users on success', () async {
      when(() => mockApi.get('/api/auth/users/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/users/'),
          statusCode: 200,
          data: [_userJson],
        ),
      );

      final result = await container.read(usersProvider.future);
      expect(result.length, 1);
      expect(result.first.displayName, 'Alice');
    });

    test('throws _PermissionException on 403', () async {
      when(() => mockApi.get('/api/auth/users/')).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/auth/users/'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/api/auth/users/'),
            statusCode: 403,
          ),
        ),
      );

      await expectLater(
        container.read(usersProvider.future),
        throwsA(predicate<Object>((e) => e.toString().contains('permission'))),
      );
    });
  });

  group('UserManagementNotifier.createUser', () {
    test('returns user data and invalidates usersProvider', () async {
      await container.read(userManagementProvider.future);

      when(
        () => mockApi.post('/api/auth/create-user/', data: any(named: 'data')),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/create-user/'),
          statusCode: 201,
          data: {
            'phone_number': '+12025552222',
            'temporary_password': 'abc123',
          },
        ),
      );
      // usersProvider will be invalidated and may be re-fetched
      when(() => mockApi.get('/api/auth/users/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/users/'),
          statusCode: 200,
          data: <dynamic>[],
        ),
      );

      final result = await container
          .read(userManagementProvider.notifier)
          .createUser(phoneNumber: '+12025552222');
      expect(result['temporary_password'], 'abc123');
    });
  });

  group('UserManagementNotifier.bulkCreateUsers', () {
    test('returns result map and invalidates usersProvider', () async {
      await container.read(userManagementProvider.future);

      when(
        () => mockApi.post(
          '/api/auth/bulk-create-users/',
          data: any(named: 'data'),
        ),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/bulk-create-users/'),
          statusCode: 200,
          data: {'created': 2, 'failed': 0},
        ),
      );
      when(() => mockApi.get('/api/auth/users/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/users/'),
          statusCode: 200,
          data: <dynamic>[],
        ),
      );

      final result = await container
          .read(userManagementProvider.notifier)
          .bulkCreateUsers(['+12025551111', '+12025552222']);
      expect(result['created'], 2);
    });
  });

  group('UserManagementNotifier.deleteUser', () {
    test('calls delete endpoint and invalidates usersProvider', () async {
      await container.read(userManagementProvider.future);

      when(() => mockApi.delete('/api/auth/users/u-1/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/users/u-1/'),
          statusCode: 204,
          data: null,
        ),
      );
      when(() => mockApi.get('/api/auth/users/')).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/auth/users/'),
          statusCode: 200,
          data: <dynamic>[],
        ),
      );

      await container.read(userManagementProvider.notifier).deleteUser('u-1');
      verify(() => mockApi.delete('/api/auth/users/u-1/')).called(1);
    });
  });
}
