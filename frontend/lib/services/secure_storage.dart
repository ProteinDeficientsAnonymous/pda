import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:logging/logging.dart';

final _log = Logger('SecureStorage');

class SecureStorageService {
  SecureStorageService() : _storage = const FlutterSecureStorage();
  SecureStorageService.withStorage(this._storage);

  final FlutterSecureStorage _storage;
  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';

  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    try {
      await Future.wait([
        _storage.write(key: _accessKey, value: access),
        _storage.write(key: _refreshKey, value: refresh),
      ]);
    } catch (e) {
      _log.warning('Storage write failed, clearing and retrying', e);
      await _clearAll();
      await Future.wait([
        _storage.write(key: _accessKey, value: access),
        _storage.write(key: _refreshKey, value: refresh),
      ]);
    }
  }

  Future<String?> getAccessToken() => _readWithRetry(_accessKey);

  Future<String?> getRefreshToken() => _readWithRetry(_refreshKey);

  /// Retries once on failure to handle transient WebCrypto OperationErrors
  /// that occur on Flutter web when the encryption key isn't immediately ready.
  Future<String?> _readWithRetry(String key) async {
    try {
      return await _storage.read(key: key);
    } catch (e) {
      _log.warning('Failed to read $key, retrying once', e);
      await Future<void>.delayed(const Duration(milliseconds: 50));
      try {
        return await _storage.read(key: key);
      } catch (e2) {
        _log.warning('Failed to read $key after retry', e2);
        return null;
      }
    }
  }

  Future<void> clearTokens() async {
    await Future.wait([
      _storage.delete(key: _accessKey),
      _storage.delete(key: _refreshKey),
    ]);
  }

  Future<void> _clearAll() async {
    try {
      await _storage.deleteAll();
    } catch (e, st) {
      _log.warning('Failed to clear all storage', e, st);
    }
  }
}
