import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('Guidelines');

class Guidelines {
  final String content;
  final DateTime updatedAt;

  const Guidelines({required this.content, required this.updatedAt});

  factory Guidelines.fromJson(Map<String, dynamic> json) => Guidelines(
    content: json['content'] as String,
    updatedAt: DateTime.parse(json['updated_at'] as String),
  );
}

final guidelinesProvider = FutureProvider<Guidelines>((ref) async {
  final api = ref.read(apiClientProvider);
  final response = await api.get('/api/community/guidelines/');
  return Guidelines.fromJson(response.data as Map<String, dynamic>);
});

class GuidelinesNotifier extends AsyncNotifier<Guidelines> {
  @override
  Future<Guidelines> build() async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/guidelines/');
    return Guidelines.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> saveContent(String content) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.patch(
        '/api/community/guidelines/',
        data: {'content': content},
      );
      state = AsyncData(
        Guidelines.fromJson(response.data as Map<String, dynamic>),
      );
      ref.invalidate(guidelinesProvider);
      _log.info('saved guidelines content');
    } catch (e, st) {
      _log.warning('failed to save guidelines content', e, st);
      rethrow;
    }
  }
}

final guidelinesNotifierProvider =
    AsyncNotifierProvider<GuidelinesNotifier, Guidelines>(
      GuidelinesNotifier.new,
    );
