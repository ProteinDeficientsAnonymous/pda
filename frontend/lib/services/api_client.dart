import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:logging/logging.dart';
import 'package:pda/config/api_config.dart';
import 'package:pda/services/secure_storage.dart';

final _log = Logger('ApiClient');

class ApiClient {
  late final Dio _dio;
  final SecureStorageService _storage;
  final VoidCallback? _onSessionExpired;
  Completer<String?>? _refreshLock;

  ApiClient(this._storage, {VoidCallback? onSessionExpired})
    : _onSessionExpired = onSessionExpired {
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

    // Auth interceptor — adds JWT and handles token refresh with locking.
    _dio.interceptors.add(
      QueuedInterceptorsWrapper(
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
          if (error.response?.statusCode != 401) {
            return handler.next(error);
          }
          if (error.requestOptions.extra['_retried'] == true) {
            return handler.next(error);
          }

          String? newToken;
          if (_refreshLock != null) {
            // Another request is already refreshing — wait for it.
            newToken = await _refreshLock!.future;
          } else {
            _refreshLock = Completer<String?>();
            newToken = await _tryRefresh();
            _refreshLock!.complete(newToken);
            _refreshLock = null;
          }

          if (newToken != null) {
            try {
              final response = await _retryWithToken(
                error.requestOptions,
                newToken,
              );
              return handler.resolve(response);
            } catch (e) {
              _log.warning('Failed to retry after token refresh', e);
            }
          }

          return handler.next(error);
        },
      ),
    );
  }

  Future<Response> _retryWithToken(RequestOptions opts, String token) {
    opts.headers['Authorization'] = 'Bearer $token';
    opts.extra['_retried'] = true;
    return _dio.fetch(opts);
  }

  Future<String?> _tryRefresh() async {
    final refresh = await _storage.getRefreshToken();
    if (refresh == null) {
      _onSessionExpired?.call();
      return null;
    }
    try {
      final response = await Dio(
        BaseOptions(
          baseUrl: apiBaseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        ),
      ).post('/api/auth/refresh/', data: {'refresh': refresh});
      final newToken = response.data['access'] as String;
      await _storage.saveTokens(access: newToken, refresh: refresh);
      return newToken;
    } catch (_) {
      await _storage.clearTokens();
      _onSessionExpired?.call();
      return null;
    }
  }

  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    String? accessToken,
  }) {
    final options = accessToken != null
        ? Options(headers: {'Authorization': 'Bearer $accessToken'})
        : null;
    return _dio.get(path, queryParameters: queryParameters, options: options);
  }

  Future<Response> post(String path, {dynamic data}) =>
      _dio.post(path, data: data);

  Future<Response> put(String path, {dynamic data}) =>
      _dio.put(path, data: data);

  Future<Response> patch(String path, {dynamic data}) =>
      _dio.patch(path, data: data);

  Future<Response> delete(String path) => _dio.delete(path);
}
