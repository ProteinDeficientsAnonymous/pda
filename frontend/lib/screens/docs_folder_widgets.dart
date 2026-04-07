import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/document.dart';
import 'package:pda/providers/docs_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';

final _log = Logger('DocsFolders');

class DocsFolderContent extends ConsumerWidget {
  final DocFolder folder;
  final bool canManage;

  const DocsFolderContent({
    super.key,
    required this.folder,
    required this.canManage,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final allDocs = folder.documents;
    final subFolders = folder.children;
    final hasContent = allDocs.isNotEmpty || subFolders.isNotEmpty;

    if (!hasContent) {
      return const Center(
        child: Text(
          'this folder is empty 🌿',
          style: TextStyle(fontSize: 14, color: Colors.grey),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        ...allDocs.map((doc) => DocsDocTile(doc: doc, canManage: canManage)),
        ...subFolders.map(
          (sub) => DocsSubFolderSection(subFolder: sub, canManage: canManage),
        ),
      ],
    );
  }
}

class DocsSubFolderSection extends ConsumerWidget {
  final DocFolder subFolder;
  final bool canManage;

  const DocsSubFolderSection({
    super.key,
    required this.subFolder,
    required this.canManage,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 16),
        Row(
          children: [
            Icon(Icons.folder_outlined, size: 18, color: cs.primary),
            const SizedBox(width: 8),
            Text(
              subFolder.name.toLowerCase(),
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: cs.primary,
              ),
            ),
            const Spacer(),
            if (canManage) DocsFolderMenuButton(folderId: subFolder.id),
          ],
        ),
        const Divider(height: 8),
        if (subFolder.documents.isEmpty)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text(
              'no docs here yet',
              style: TextStyle(fontSize: 13, color: Colors.grey),
            ),
          ),
        ...subFolder.documents.map(
          (doc) => DocsDocTile(doc: doc, canManage: canManage),
        ),
      ],
    );
  }
}

class DocsDocTile extends ConsumerWidget {
  final DocumentSummary doc;
  final bool canManage;

  const DocsDocTile({super.key, required this.doc, required this.canManage});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      leading: const Icon(Icons.description_outlined),
      title: Text(doc.title),
      trailing: canManage
          ? IconButton(
              icon: const Icon(Icons.delete_outline, size: 20),
              tooltip: 'delete document',
              onPressed: () => _confirmDelete(context, ref),
            )
          : null,
      onTap: () => context.push('/docs/${doc.id}'),
    );
  }

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('delete document'),
        content: Text('Delete "${doc.title}"? This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('delete'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;
    try {
      await ref.read(docFoldersProvider.notifier).deleteDocument(doc.id);
    } catch (e, st) {
      _log.warning('failed to delete document', e, st);
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }
}

class DocsFolderMenuButton extends ConsumerWidget {
  final String folderId;

  const DocsFolderMenuButton({super.key, required this.folderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return PopupMenuButton<String>(
      icon: const Icon(Icons.more_vert, size: 18),
      tooltip: 'folder options',
      onSelected: (value) {
        if (value == 'delete') _confirmDeleteFolder(context, ref);
      },
      itemBuilder: (_) => const [
        PopupMenuItem(value: 'delete', child: Text('delete folder')),
      ],
    );
  }

  Future<void> _confirmDeleteFolder(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('delete folder'),
        content: const Text(
          'Delete this folder and all its documents? This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('delete'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;
    try {
      await ref.read(docFoldersProvider.notifier).deleteFolder(folderId);
    } catch (e, st) {
      _log.warning('failed to delete folder', e, st);
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }
}
