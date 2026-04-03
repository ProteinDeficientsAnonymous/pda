import 'dart:convert';

import 'package:web/web.dart' as web;

void downloadFile(String content, String filename, String mimeType) {
  final bytes = utf8.encode(content);
  final dataUri = 'data:$mimeType;charset=utf-8;base64,${base64Encode(bytes)}';
  final anchor = web.document.createElement('a') as web.HTMLAnchorElement
    ..href = dataUri
    ..download = filename
    ..style.display = 'none';
  web.document.body!.append(anchor);
  anchor.click();
  anchor.remove();
}
