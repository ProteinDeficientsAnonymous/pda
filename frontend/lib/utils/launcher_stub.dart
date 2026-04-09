import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';

void openUrl(String url) {
  final uri = Uri.tryParse(url);
  if (uri != null) launchUrl(uri, mode: LaunchMode.externalApplication);
}

void openLocationInMaps(String location) {
  final url = 'geo:0,0?q=${Uri.encodeComponent(location)}';
  final uri = Uri.tryParse(url);
  if (uri != null) launchUrl(uri, mode: LaunchMode.externalApplication);
}

/// Opens the native SMS app with [phoneNumber] as recipient and [body]
/// pre-filled. Returns true if the app launched successfully.
Future<bool> sendSms({required String phoneNumber, required String body}) {
  // iOS and macOS use `&body=`; Android and other platforms use `?body=`
  final separator =
      (defaultTargetPlatform == TargetPlatform.iOS ||
          defaultTargetPlatform == TargetPlatform.macOS)
      ? '&body='
      : '?body=';
  final uri = Uri.parse(
    'sms:$phoneNumber$separator${Uri.encodeComponent(body)}',
  );
  return launchUrl(uri);
}
