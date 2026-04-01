import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/document.dart';
import 'package:pda/providers/auth_provider.dart';

class DocFoldersNotifier extends AsyncNotifier<List<DocFolder>> {
  @override
  Future<List<DocFolder>> build() async {
    ref.watch(authProvider);
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/docs/folders/');
    final list = response.data as List<dynamic>;
    return list
        .map((e) => DocFolder.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> createFolder({required String name, String? parentId}) async {
    final api = ref.read(apiClientProvider);
    await api.post(
      '/api/community/docs/folders/',
      data: {'name': name, if (parentId != null) 'parent_id': parentId},
    );
    ref.invalidateSelf();
  }

  Future<void> updateFolder(String folderId, {String? name}) async {
    final api = ref.read(apiClientProvider);
    await api.patch(
      '/api/community/docs/folders/$folderId/',
      data: {if (name != null) 'name': name},
    );
    ref.invalidateSelf();
  }

  Future<void> deleteFolder(String folderId) async {
    final api = ref.read(apiClientProvider);
    await api.delete('/api/community/docs/folders/$folderId/');
    ref.invalidateSelf();
  }

  Future<void> reorderFolders(List<String> ids) async {
    final api = ref.read(apiClientProvider);
    await api.put('/api/community/docs/folders/reorder/', data: {'ids': ids});
    ref.invalidateSelf();
  }

  Future<void> createDocument({
    required String title,
    required String folderId,
  }) async {
    final api = ref.read(apiClientProvider);
    await api.post(
      '/api/community/docs/',
      data: {'title': title, 'folder_id': folderId},
    );
    ref.invalidateSelf();
  }

  Future<void> deleteDocument(String docId) async {
    final api = ref.read(apiClientProvider);
    await api.delete('/api/community/docs/$docId/');
    ref.invalidateSelf();
  }

  Future<void> reorderDocuments(List<String> ids) async {
    final api = ref.read(apiClientProvider);
    await api.put('/api/community/docs/reorder/', data: {'ids': ids});
    ref.invalidateSelf();
  }
}

final docFoldersProvider =
    AsyncNotifierProvider<DocFoldersNotifier, List<DocFolder>>(
      DocFoldersNotifier.new,
    );

class DocDetailNotifier extends FamilyAsyncNotifier<Document, String> {
  @override
  Future<Document> build(String arg) async {
    ref.watch(authProvider);
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/docs/$arg/');
    return Document.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> save({String? title, String? content}) async {
    final api = ref.read(apiClientProvider);
    final response = await api.patch(
      '/api/community/docs/$arg/',
      data: {
        if (title != null) 'title': title,
        if (content != null) 'content': content,
      },
    );
    state = AsyncData(Document.fromJson(response.data as Map<String, dynamic>));
  }
}

final docDetailProvider =
    AsyncNotifierProviderFamily<DocDetailNotifier, Document, String>(
      DocDetailNotifier.new,
    );
