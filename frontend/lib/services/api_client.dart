import 'package:dio/dio.dart';
import 'package:pda/config/api_config.dart';
import 'package:pda/services/secure_storage.dart';

class ApiClient {
  late final Dio _dio;
  final SecureStorageService _storage;

  ApiClient(this._storage) {
    _dio = Dio(BaseOptions(baseUrl: apiBaseUrl));
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.getAccessToken();
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            final refreshed = await _tryRefresh();
            if (refreshed) {
              final token = await _storage.getAccessToken();
              error.requestOptions.headers['Authorization'] = 'Bearer $token';
              final response = await _dio.fetch(error.requestOptions);
              return handler.resolve(response);
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
      final response = await Dio(BaseOptions(baseUrl: apiBaseUrl)).post(
        '/api/auth/refresh/',
        data: {'refresh': refresh},
      );
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

  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) =>
      _dio.get(path, queryParameters: queryParameters);

  Future<Response> post(String path, {dynamic data}) => _dio.post(path, data: data);
}
