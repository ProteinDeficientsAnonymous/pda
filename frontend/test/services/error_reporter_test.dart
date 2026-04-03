import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:logging/logging.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/services/error_reporter.dart';
import 'package:pda/services/secure_storage.dart';

import '../helpers/fake_secure_storage.dart';

class MockDio extends Mock implements Dio {}

void main() {
  late SecureStorageService storage;
  late MockDio mockDio;
  late ErrorReporter reporter;

  setUp(() {
    storage = SecureStorageService.withStorage(FakeSecureStorage());
    mockDio = MockDio();
    reporter = ErrorReporter.withDio(storage, mockDio);
  });

  group('ErrorReporter', () {
    test('posts error data to backend when token is available', () async {
      await storage.saveTokens(access: 'test-token', refresh: 'refresh');
      when(
        () => mockDio.post(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenAnswer(
        (_) async =>
            Response(requestOptions: RequestOptions(), statusCode: 201),
      );

      await reporter.report(
        error: 'Test error',
        stackTrace: 'at line 42',
        context: '/calendar',
      );

      final captured = verify(
        () => mockDio.post(
          captureAny(),
          data: captureAny(named: 'data'),
          options: captureAny(named: 'options'),
        ),
      ).captured;
      expect(captured[0], '/api/community/error-report/');
      final data = captured[1] as Map<String, String>;
      expect(data['error'], 'Test error');
      expect(data['stack_trace'], 'at line 42');
      expect(data['context'], '/calendar');
    });

    test('does not post when no token is available', () async {
      await reporter.report(error: 'Test error');

      verifyNever(
        () => mockDio.post(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      );
    });

    test('falls back to local logging when post fails', () async {
      await storage.saveTokens(access: 'test-token', refresh: 'refresh');
      when(
        () => mockDio.post(
          any(),
          data: any(named: 'data'),
          options: any(named: 'options'),
        ),
      ).thenThrow(
        DioException(
          requestOptions: RequestOptions(),
          type: DioExceptionType.connectionError,
        ),
      );

      final records = <LogRecord>[];
      Logger.root.onRecord.listen(records.add);

      // Should not throw
      await reporter.report(error: 'Test error');

      // Should have logged the fallback warning
      expect(
        records.any(
          (r) =>
              r.level == Level.WARNING &&
              r.message.contains('Failed to report error to backend'),
        ),
        isTrue,
      );
    });
  });
}
