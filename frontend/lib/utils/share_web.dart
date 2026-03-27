import 'package:web/web.dart' as web;

void shareUrl(String url, {String? subject}) {
  final nav = web.window.navigator;
  if (nav.canShare(web.ShareData(url: url, title: subject ?? ''))) {
    nav.share(web.ShareData(url: url, title: subject ?? ''));
  } else {
    web.window.open(url, '_blank');
  }
}
