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

class EditablePageNotifier extends AsyncNotifier<EditablePage> {
  EditablePageNotifier(this._slug);
  final String _slug;

  @override
  Future<EditablePage> build() async {
    // Watch auth so the page refetches once the token is available.
    ref.watch(authProvider);
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/pages/$_slug/');
    return EditablePage.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> saveContent(String content) async {
    final api = ref.read(apiClientProvider);
    final response = await api.patch(
      '/api/community/pages/$_slug/',
      data: {'content': content},
    );
    state = AsyncData(
      EditablePage.fromJson(response.data as Map<String, dynamic>),
    );
  }

  Future<void> saveVisibility(String visibility) async {
    final api = ref.read(apiClientProvider);
    final response = await api.patch(
      '/api/community/pages/$_slug/',
      data: {'visibility': visibility},
    );
    state = AsyncData(
      EditablePage.fromJson(response.data as Map<String, dynamic>),
    );
  }
}

final editablePageProvider =
    AsyncNotifierProvider.family<EditablePageNotifier, EditablePage, String>(
      (arg) => EditablePageNotifier(arg),
    );
