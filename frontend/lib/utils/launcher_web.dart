import 'package:logging/logging.dart';
import 'package:web/web.dart' as web;

final _log = Logger('openUrl');

const _safeSchemes = {'http', 'https', 'tel', 'mailto', 'sms', 'whatsapp'};

void openUrl(String url) {
  final uri = Uri.tryParse(url);
  if (uri == null || !_safeSchemes.contains(uri.scheme)) {
    _log.warning('Refusing to open URL with unsafe scheme: $url');
    return;
  }
  web.window.open(url, '_blank');
}

void openLocationInMaps(String location) {
  final url = 'https://maps.google.com/?q=${Uri.encodeComponent(location)}';
  web.window.open(url, '_blank');
}
