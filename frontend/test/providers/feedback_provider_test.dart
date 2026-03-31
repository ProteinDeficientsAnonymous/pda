import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/feedback_provider.dart';
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

  group('FeedbackNotifier.submit', () {
    test('posts feedback payload to /api/community/feedback/', () async {
      await container.read(feedbackProvider.future);

      when(
        () =>
            mockApi.post('/api/community/feedback/', data: any(named: 'data')),
      ).thenAnswer(
        (_) async => Response(
          requestOptions: RequestOptions(path: '/api/community/feedback/'),
          statusCode: 201,
          data: {'html_url': 'https://github.com/leahpeker/pda/issues/1'},
        ),
      );

      await container
          .read(feedbackProvider.notifier)
          .submit(
            const FeedbackSubmission(
              title: 'Bug report',
              description: 'Something broke',
              currentRoute: '/calendar',
              userAgent: 'Mozilla/5.0',
              appVersion: '1.0.0+1',
            ),
          );

      final state = container.read(feedbackProvider);
      expect(state.hasValue, isTrue);

      final captured =
          verify(
                () => mockApi.post(
                  '/api/community/feedback/',
                  data: captureAny(named: 'data'),
                ),
              ).captured.single
              as Map<String, dynamic>;

      expect(captured['title'], 'Bug report');
      expect(captured['description'], 'Something broke');
      expect(captured['metadata']['route'], '/calendar');
      expect(captured['metadata']['user_agent'], 'Mozilla/5.0');
      expect(captured['metadata']['app_version'], '1.0.0+1');
    });

    test('sets error state on API failure', () async {
      await container.read(feedbackProvider.future);

      when(
        () =>
            mockApi.post('/api/community/feedback/', data: any(named: 'data')),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(path: '/api/community/feedback/'),
          type: DioExceptionType.badResponse,
          response: Response(
            requestOptions: RequestOptions(path: '/api/community/feedback/'),
            statusCode: 503,
            data: {'detail': 'Feedback submission is not configured.'},
          ),
        ),
      );

      await container
          .read(feedbackProvider.notifier)
          .submit(
            const FeedbackSubmission(
              title: 'Bug report',
              description: 'Details',
            ),
          );

      final state = container.read(feedbackProvider);
      expect(state.hasError, isTrue);
      expect(state.error, isA<ApiError>());
    });
  });
}
