import 'package:dio/dio.dart';
import 'package:logging/logging.dart';
import 'package:pda/config/api_config.dart';
import 'package:pda/services/secure_storage.dart';

final _log = Logger('ApiClient');

class ApiClient {
  late final Dio _dio;
  final SecureStorageService _storage;

  ApiClient(this._storage) {
    _dio = Dio(
      BaseOptions(baseUrl: apiBaseUrl, contentType: Headers.jsonContentType),
    );

    // Logging interceptor — logs request/response/error without sensitive data.
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          _log.info('${options.method} ${options.path}');
          return handler.next(options);
        },
        onResponse: (response, handler) {
          _log.info(
            '${response.requestOptions.method} ${response.requestOptions.path}'
            ' -> ${response.statusCode}',
          );
          return handler.next(response);
        },
        onError: (error, handler) {
          _log.warning(
            '${error.requestOptions.method} ${error.requestOptions.path}'
            ' -> ${error.response?.statusCode ?? "no response"}',
          );
          return handler.next(error);
        },
      ),
    );

    // Auth interceptor — adds JWT and handles token refresh.
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          try {
            final token = await _storage.getAccessToken();
            if (token != null) {
              options.headers['Authorization'] = 'Bearer $token';
            }
          } catch (e) {
            _log.warning('Failed to read access token from storage', e);
          }
          return handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            if (error.requestOptions.extra['_retried'] == true) {
              return handler.next(error);
            }
            final refreshed = await _tryRefresh();
            if (refreshed) {
              try {
                final token = await _storage.getAccessToken();
                final opts = error.requestOptions;
                opts.headers['Authorization'] = 'Bearer $token';
                opts.extra['_retried'] = true;
                final response = await _dio.fetch(opts);
                return handler.resolve(response);
              } catch (e) {
                _log.warning('Failed to retry after token refresh', e);
              }
            }
          }
          return handler.next(error);
        },
      ),
    );
  }

  Future<bool> _tryRefresh() async {
    final refresh = await _storage.getRefreshToken();
    if (refresh == null) return false;
    try {
      final response = await Dio(
        BaseOptions(
          baseUrl: apiBaseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        ),
      ).post('/api/auth/refresh/', data: {'refresh': refresh});
      await _storage.saveTokens(
        access: response.data['access'] as String,
        refresh: refresh,
      );
      return true;
    } catch (_) {
      await _storage.clearTokens();
      return false;
    }
  }

  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    String? accessToken,
  }) {
    final options =
        accessToken != null
            ? Options(headers: {'Authorization': 'Bearer $accessToken'})
            : null;
    return _dio.get(path, queryParameters: queryParameters, options: options);
  }

  Future<Response> post(String path, {dynamic data}) =>
      _dio.post(path, data: data);

  Future<Response> patch(String path, {dynamic data}) =>
      _dio.patch(path, data: data);

  Future<Response> delete(String path) => _dio.delete(path);
}
