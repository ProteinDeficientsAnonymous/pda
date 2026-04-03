import 'package:dio/dio.dart';
import 'package:logging/logging.dart';
import 'package:pda/config/api_config.dart';
import 'package:pda/services/secure_storage.dart';

final _log = Logger('ErrorReporter');

/// Reports frontend errors to the backend via authenticated POST.
///
/// Uses its own [Dio] instance to avoid circular dependency with [ApiClient].
/// Falls back to local logging when the report cannot be delivered.
class ErrorReporter {
  ErrorReporter(this._storage) : _dio = Dio(BaseOptions(baseUrl: apiBaseUrl));

  /// Creates an [ErrorReporter] with an injected [Dio] instance.
  ErrorReporter.withDio(this._storage, this._dio);

  final SecureStorageService _storage;
  final Dio _dio;

  /// Reports an error to the backend.
  ///
  /// Silently skips if no access token is available (user not logged in).
  /// Catches and locally logs any failure to deliver the report.
  Future<void> report({
    required String error,
    String stackTrace = '',
    String context = '',
  }) async {
    final token = await _storage.getAccessToken();
    if (token == null) return;

    try {
      await _dio.post(
        '/api/community/error-report/',
        data: {
          'error': error,
          'stack_trace': stackTrace.length > 10000
              ? stackTrace.substring(0, 10000)
              : stackTrace,
          'context': context,
        },
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
    } catch (e) {
      _log.warning('Failed to report error to backend: $e');
    }
  }
}
