import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/join_request_provider.dart';
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

  Future<void> submitJoinRequest() async {
    await container
        .read(joinRequestProvider.notifier)
        .submit(
          displayName: 'Test Person',
          phoneNumber: '+12025551234',
          answers: {'q1': 'Testing'},
        );
  }

  group('JoinRequestNotifier.submit', () {
    test('sets ValidationError with detail for 400 response', () async {
      await container.read(joinRequestProvider.future);

      when(
        () => mockApi.post(
          '/api/community/join-request/',
          data: any(named: 'data'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/community/join-request/'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(
              path: '/api/community/join-request/',
            ),
            statusCode: 400,
            data: {'detail': 'display_name and why_join are required.'},
          ),
        ),
      );

      await submitJoinRequest();

      final state = container.read(joinRequestProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<ValidationError>());
      expect(
        (state.error! as ValidationError).detail,
        'display_name and why_join are required.',
      );
    });

    test('sets NetworkError on connection failure', () async {
      await container.read(joinRequestProvider.future);

      when(
        () => mockApi.post(
          '/api/community/join-request/',
          data: any(named: 'data'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/community/join-request/'),
          type: DioExceptionType.connectionError,
        ),
      );

      await submitJoinRequest();

      final state = container.read(joinRequestProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<NetworkError>());
    });

    test('sets ServerError on 500', () async {
      await container.read(joinRequestProvider.future);

      when(
        () => mockApi.post(
          '/api/community/join-request/',
          data: any(named: 'data'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/community/join-request/'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(
              path: '/api/community/join-request/',
            ),
            statusCode: 500,
          ),
        ),
      );

      await submitJoinRequest();

      final state = container.read(joinRequestProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<ServerError>());
    });
  });
}
