import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('HomePage');

class HomePage {
  final String content;
  final String joinContent;
  final String donateUrl;
  final DateTime updatedAt;

  const HomePage({
    required this.content,
    required this.joinContent,
    required this.donateUrl,
    required this.updatedAt,
  });

  factory HomePage.fromJson(Map<String, dynamic> json) => HomePage(
    content: json['content'] as String,
    joinContent: json['join_content'] as String,
    donateUrl: json['donate_url'] as String? ?? '',
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
    try {
      final response = await api.patch(
        '/api/community/home/',
        data: {'content': content},
      );
      state = AsyncData(
        HomePage.fromJson(response.data as Map<String, dynamic>),
      );
      _log.info('saved home content');
    } catch (e, st) {
      _log.warning('failed to save home content', e, st);
      rethrow;
    }
  }

  Future<void> saveJoinContent(String joinContent) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.patch(
        '/api/community/home/',
        data: {'join_content': joinContent},
      );
      state = AsyncData(
        HomePage.fromJson(response.data as Map<String, dynamic>),
      );
      _log.info('saved join content');
    } catch (e, st) {
      _log.warning('failed to save join content', e, st);
      rethrow;
    }
  }

  Future<void> saveDonateUrl(String donateUrl) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.patch(
        '/api/community/home/',
        data: {'donate_url': donateUrl},
      );
      state = AsyncData(
        HomePage.fromJson(response.data as Map<String, dynamic>),
      );
      _log.info('saved donate URL');
    } catch (e, st) {
      _log.warning('failed to save donate URL', e, st);
      rethrow;
    }
  }
}

final homePageNotifierProvider =
    AsyncNotifierProvider<HomePageNotifier, HomePage>(HomePageNotifier.new);
