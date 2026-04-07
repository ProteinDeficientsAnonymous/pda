import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/document.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('Docs');

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
    try {
      await api.post(
        '/api/community/docs/folders/',
        data: {'name': name, if (parentId != null) 'parent_id': parentId},
      );
      ref.invalidateSelf();
      _log.info('created folder $name');
    } catch (e, st) {
      _log.warning('failed to create folder $name', e, st);
      rethrow;
    }
  }

  Future<void> updateFolder(String folderId, {String? name}) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.patch(
        '/api/community/docs/folders/$folderId/',
        data: {if (name != null) 'name': name},
      );
      ref.invalidateSelf();
      _log.info('updated folder $folderId');
    } catch (e, st) {
      _log.warning('failed to update folder $folderId', e, st);
      rethrow;
    }
  }

  Future<void> deleteFolder(String folderId) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.delete('/api/community/docs/folders/$folderId/');
      ref.invalidateSelf();
      _log.info('deleted folder $folderId');
    } catch (e, st) {
      _log.warning('failed to delete folder $folderId', e, st);
      rethrow;
    }
  }

  Future<void> reorderFolders(List<String> ids) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.put('/api/community/docs/folders/reorder/', data: {'ids': ids});
      ref.invalidateSelf();
    } catch (e, st) {
      _log.warning('failed to reorder folders', e, st);
      rethrow;
    }
  }

  Future<void> createDocument({
    required String title,
    required String folderId,
  }) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.post(
        '/api/community/docs/',
        data: {'title': title, 'folder_id': folderId},
      );
      ref.invalidateSelf();
      _log.info('created document "$title" in folder $folderId');
    } catch (e, st) {
      _log.warning('failed to create document "$title"', e, st);
      rethrow;
    }
  }

  Future<void> deleteDocument(String docId) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.delete('/api/community/docs/$docId/');
      ref.invalidateSelf();
      _log.info('deleted document $docId');
    } catch (e, st) {
      _log.warning('failed to delete document $docId', e, st);
      rethrow;
    }
  }

  Future<void> reorderDocuments(List<String> ids) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.put('/api/community/docs/reorder/', data: {'ids': ids});
      ref.invalidateSelf();
    } catch (e, st) {
      _log.warning('failed to reorder documents', e, st);
      rethrow;
    }
  }
}

final docFoldersProvider =
    AsyncNotifierProvider<DocFoldersNotifier, List<DocFolder>>(
      DocFoldersNotifier.new,
    );

class DocDetailNotifier extends AsyncNotifier<Document> {
  DocDetailNotifier(this._docId);
  final String _docId;

  @override
  Future<Document> build() async {
    ref.watch(authProvider);
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/docs/$_docId/');
    return Document.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> save({String? title, String? content}) async {
    final api = ref.read(apiClientProvider);
    try {
      final response = await api.patch(
        '/api/community/docs/$_docId/',
        data: {
          if (title != null) 'title': title,
          if (content != null) 'content': content,
        },
      );
      state = AsyncData(
        Document.fromJson(response.data as Map<String, dynamic>),
      );
      _log.info('saved document $_docId');
    } catch (e, st) {
      _log.warning('failed to save document $_docId', e, st);
      rethrow;
    }
  }
}

final docDetailProvider =
    AsyncNotifierProvider.family<DocDetailNotifier, Document, String>(
      (arg) => DocDetailNotifier(arg),
    );
