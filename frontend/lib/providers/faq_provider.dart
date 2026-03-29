import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';

class FAQ {
  final String content;
  final DateTime updatedAt;

  const FAQ({required this.content, required this.updatedAt});

  factory FAQ.fromJson(Map<String, dynamic> json) => FAQ(
    content: json['content'] as String,
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
    final response = await api.patch(
      '/api/community/faq/',
      data: {'content': content},
    );
    state = AsyncData(FAQ.fromJson(response.data as Map<String, dynamic>));
  }
}

final faqNotifierProvider = AsyncNotifierProvider<FaqNotifier, FAQ>(
  FaqNotifier.new,
);
