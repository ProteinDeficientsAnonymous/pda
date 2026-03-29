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

  Future<String?> getAccessToken() async {
    try {
      return await _storage.read(key: _accessKey);
    } catch (e) {
      _log.warning('Failed to read access token, clearing storage', e);
      await _clearAll();
      return null;
    }
  }

  Future<String?> getRefreshToken() async {
    try {
      return await _storage.read(key: _refreshKey);
    } catch (e) {
      _log.warning('Failed to read refresh token, clearing storage', e);
      await _clearAll();
      return null;
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
    } catch (_) {
      // If deleteAll also fails, nothing more we can do
    }
  }
}
