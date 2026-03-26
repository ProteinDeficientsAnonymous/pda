import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';

class HomePage {
  final String content;
  final String joinContent;
  final DateTime updatedAt;

  const HomePage({
    required this.content,
    required this.joinContent,
    required this.updatedAt,
  });

  factory HomePage.fromJson(Map<String, dynamic> json) => HomePage(
    content: json['content'] as String,
    joinContent: json['join_content'] as String,
    updatedAt: DateTime.parse(json['updated_at'] as String),
  );
}

class HomePageNotifier extends AsyncNotifier<HomePage> {
  @override
  Future<HomePage> build() async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/home/');
    return HomePage.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> saveContent(String content) async {
    final api = ref.read(apiClientProvider);
    final response = await api.patch(
      '/api/community/home/',
      data: {'content': content},
    );
    state = AsyncData(HomePage.fromJson(response.data as Map<String, dynamic>));
  }

  Future<void> saveJoinContent(String joinContent) async {
    final api = ref.read(apiClientProvider);
    final response = await api.patch(
      '/api/community/home/',
      data: {'join_content': joinContent},
    );
    state = AsyncData(HomePage.fromJson(response.data as Map<String, dynamic>));
  }
}

final homePageNotifierProvider =
    AsyncNotifierProvider<HomePageNotifier, HomePage>(HomePageNotifier.new);
