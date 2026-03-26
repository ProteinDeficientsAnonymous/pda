import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';

class EditablePage {
  final String slug;
  final String content;
  final String visibility;
  final DateTime updatedAt;

  const EditablePage({
    required this.slug,
    required this.content,
    required this.visibility,
    required this.updatedAt,
  });

  factory EditablePage.fromJson(Map<String, dynamic> json) => EditablePage(
    slug: json['slug'] as String,
    content: json['content'] as String,
    visibility: json['visibility'] as String,
    updatedAt: DateTime.parse(json['updated_at'] as String),
  );
}

class EditablePageNotifier extends FamilyAsyncNotifier<EditablePage, String> {
  @override
  Future<EditablePage> build(String arg) async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/pages/$arg/');
    return EditablePage.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> saveContent(String content) async {
    final api = ref.read(apiClientProvider);
    final response = await api.patch(
      '/api/community/pages/$arg/',
      data: {'content': content},
    );
    state = AsyncData(
      EditablePage.fromJson(response.data as Map<String, dynamic>),
    );
  }

  Future<void> saveVisibility(String visibility) async {
    final api = ref.read(apiClientProvider);
    final response = await api.patch(
      '/api/community/pages/$arg/',
      data: {'visibility': visibility},
    );
    state = AsyncData(
      EditablePage.fromJson(response.data as Map<String, dynamic>),
    );
  }
}

final editablePageProvider =
    AsyncNotifierProviderFamily<EditablePageNotifier, EditablePage, String>(
      EditablePageNotifier.new,
    );
