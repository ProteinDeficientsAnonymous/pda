import 'package:logging/logging.dart';
import 'package:web/web.dart' as web;

final _log = Logger('openUrl');

const _safeSchemes = {'http', 'https', 'tel', 'mailto', 'sms', 'whatsapp'};

// Must be called synchronously from a user gesture (e.g. InkWell.onTap).
// window.open from a direct user gesture is reliable under COOP: same-origin —
// the anchor-click workaround removed the anchor before Chrome committed the
// navigation in the cross-origin-isolated codepath, leaving about:blank.
void _openExternal(String url) {
  web.window.open(url, '_blank', 'noopener,noreferrer');
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
