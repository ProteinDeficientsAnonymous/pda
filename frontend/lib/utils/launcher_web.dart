import 'package:logging/logging.dart';
import 'package:web/web.dart' as web;

final _log = Logger('openUrl');

const _safeSchemes = {'http', 'https', 'tel', 'mailto', 'sms', 'whatsapp'};

// window.open() breaks under COOP: same-origin — use an anchor click instead.
void _openExternal(String url) {
  final a = web.document.createElement('a') as web.HTMLAnchorElement
    ..href = url
    ..target = '_blank'
    ..rel = 'noopener noreferrer';
  web.document.body?.append(a);
  a.click();
  a.remove();
}

void openUrl(String url) {
  final uri = Uri.tryParse(url);
  if (uri == null || !_safeSchemes.contains(uri.scheme)) {
    _log.warning('Refusing to open URL with unsafe scheme: $url');
    return;
  }
  _openExternal(url);
}

void openLocationInMaps(String location) {
  final url =
      'https://www.google.com/maps/search/?api=1&query=${Uri.encodeComponent(location)}';
  _openExternal(url);
}
