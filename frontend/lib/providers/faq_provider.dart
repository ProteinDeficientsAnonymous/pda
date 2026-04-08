import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('FAQ');

class FAQ {
  final String content;
  final String contentHtml;
  final DateTime updatedAt;

  const FAQ({
    required this.content,
    required this.contentHtml,
    required this.updatedAt,
  });

  factory FAQ.fromJson(Map<String, dynamic> json) => FAQ(
    content: json['content'] as String,
    contentHtml: json['content_html'] as String? ?? '',
    updatedAt: DateTime.parse(json['updated_at'] as String),
  );
}

class FaqNotifier extends AsyncNotifier<FAQ> {
  @override
  Future<FAQ> build() async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/faq/');
    return FAQ.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> saveContent(String content) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.patch(
        '/api/community/faq/',
        data: {'content': content},
      );
      state = AsyncData(FAQ.fromJson(response.data as Map<String, dynamic>));
      _log.info('saved FAQ content');
    } catch (e, st) {
      _log.warning('failed to save FAQ content', e, st);
      rethrow;
    }
  }
}

final faqNotifierProvider = AsyncNotifierProvider<FaqNotifier, FAQ>(
  FaqNotifier.new,
);
