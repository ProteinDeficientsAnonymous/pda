import 'package:share_plus/share_plus.dart';

void shareUrl(String url, {String? subject}) {
  Share.share(url, subject: subject);
}
