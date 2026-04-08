import 'dart:async';
import 'dart:js_interop';

import 'package:logging/logging.dart';
import 'package:pda/config/api_config.dart';
import 'package:web/web.dart' as web;

final _log = Logger('NotificationSSE');

class NotificationSseClient {
  web.EventSource? _source;
  Timer? _reconnectTimer;
  int _retryCount = 0;
  bool _closed = false;

  final String _token;
  final void Function() _onNotification;

  NotificationSseClient({
    required String token,
    required void Function() onNotification,
  }) : _token = token,
       _onNotification = onNotification {
    _connect();
  }

  bool get isConnected => _source?.readyState == web.EventSource.OPEN;

  void _connect() {
    if (_closed) return;
    final url = '$apiBaseUrl/api/notifications/stream/?token=$_token';
    _source = web.EventSource(url);

    _source!.addEventListener(
      'connected',
      (web.Event _) {
        _retryCount = 0;
        _log.info('SSE connected');
      }.toJS,
    );

    _source!.addEventListener(
      'notification',
      (web.Event _) {
        _retryCount = 0;
        _onNotification();
      }.toJS,
    );

    _source!.onerror = (web.Event _) {
      _source?.close();
      _source = null;
      _scheduleReconnect();
    }.toJS;
  }

  void _scheduleReconnect() {
    if (_closed) return;
    final delay = Duration(seconds: _backoffSeconds());
    _log.info('SSE reconnecting in ${delay.inSeconds}s');
    _reconnectTimer = Timer(delay, _connect);
  }

  int _backoffSeconds() {
    _retryCount++;
    // Exponential backoff: 1, 2, 4, 8, 16, 30 (max)
    return (1 << (_retryCount - 1)).clamp(1, 30);
  }

  void close() {
    _closed = true;
    _source?.close();
    _source = null;
    _reconnectTimer?.cancel();
  }
}
