import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/document.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/docs_provider.dart';
import 'package:pda/screens/docs_folder_widgets.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';

final _log = Logger('DocsScreen');

class DocsScreen extends ConsumerWidget {
  const DocsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final foldersAsync = ref.watch(docFoldersProvider);

    return AppScaffold(
      child: foldersAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            const Center(child: Text('couldn\'t load docs — try refreshing')),
        data: (folders) => _DocsBody(folders: folders),
      ),
    );
  }
}

class _DocsBody extends ConsumerStatefulWidget {
  final List<DocFolder> folders;

  const _DocsBody({required this.folders});

  @override
  ConsumerState<_DocsBody> createState() => _DocsBodyState();
}

class _DocsBodyState extends ConsumerState<_DocsBody>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: widget.folders.length, vsync: this);
  }

  @override
  void didUpdateWidget(covariant _DocsBody old) {
    super.didUpdateWidget(old);
    if (old.folders.length != widget.folders.length) {
      final clamped = _tabController.index.clamp(
        0,
        (widget.folders.length - 1).clamp(0, widget.folders.length),
      );
      _tabController.dispose();
      _tabController = TabController(
        length: widget.folders.length,
        vsync: this,
        initialIndex: clamped,
      );
      setState(() {});
    }
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  bool get _canManage {
    final user = ref.read(authProvider).value;
    return user?.hasPermission(Permission.manageDocs) ?? false;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (widget.folders.isEmpty) {
      return _EmptyState(canManage: _canManage);
    }

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
          child: Row(
            children: [
              Expanded(
                child: Text('docs', style: theme.textTheme.headlineSmall),
              ),
              if (_canManage)
                PopupMenuButton<String>(
                  icon: const Icon(Icons.add),
                  tooltip: 'add',
                  onSelected: (value) {
                    if (value == 'folder') _showCreateFolderDialog();
                    if (value == 'doc') _showCreateDocDialog();
                  },
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'folder', child: Text('folder')),
                    PopupMenuItem(value: 'doc', child: Text('document')),
                  ],
                ),
            ],
          ),
        ),
        if (widget.folders.length > 1)
          TabBar(
            controller: _tabController,
            isScrollable: true,
            tabs: widget.folders
                .map((f) => Tab(text: f.name.toLowerCase()))
                .toList(),
          ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: widget.folders
                .map((f) => DocsFolderContent(folder: f, canManage: _canManage))
                .toList(),
          ),
        ),
      ],
    );
  }

  void _showCreateFolderDialog() {
    final controller = TextEditingController();
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('new folder'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Folder name'),
          onSubmitted: (_) => _submitFolder(ctx, controller),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('cancel'),
          ),
          FilledButton(
            onPressed: () => _submitFolder(ctx, controller),
            child: const Text('create'),
          ),
        ],
      ),
    );
  }

  Future<void> _submitFolder(
    BuildContext ctx,
    TextEditingController controller,
  ) async {
    final name = controller.text.trim();
    if (name.isEmpty) return;
    Navigator.pop(ctx);
    try {
      await ref.read(docFoldersProvider.notifier).createFolder(name: name);
    } catch (e, st) {
      _log.warning('failed to create folder', e, st);
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    }
  }

  void _showCreateDocDialog() {
    if (widget.folders.isEmpty) return;
    final controller = TextEditingController();
    final currentFolder = widget.folders[_tabController.index];

    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('new document'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Document title'),
          onSubmitted: (_) => _submitDoc(ctx, controller, currentFolder.id),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('cancel'),
          ),
          FilledButton(
            onPressed: () => _submitDoc(ctx, controller, currentFolder.id),
            child: const Text('create'),
          ),
        ],
      ),
    );
  }

  Future<void> _submitDoc(
    BuildContext ctx,
    TextEditingController controller,
    String folderId,
  ) async {
    final title = controller.text.trim();
    if (title.isEmpty) return;
    Navigator.pop(ctx);
    try {
      await ref
          .read(docFoldersProvider.notifier)
          .createDocument(title: title, folderId: folderId);
    } catch (e, st) {
      _log.warning('failed to create document', e, st);
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    }
  }
}

class _EmptyState extends ConsumerWidget {
  final bool canManage;

  const _EmptyState({required this.canManage});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text('no docs yet 🌿', style: TextStyle(fontSize: 16)),
          if (canManage) ...[
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: () => _createFirstFolder(context, ref),
              icon: const Icon(Icons.create_new_folder_outlined),
              label: const Text('create a folder'),
            ),
          ],
        ],
      ),
    );
  }

  void _createFirstFolder(BuildContext context, WidgetRef ref) {
    final controller = TextEditingController();
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('new folder'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Folder name'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('cancel'),
          ),
          FilledButton(
            onPressed: () async {
              final name = controller.text.trim();
              if (name.isEmpty) return;
              Navigator.pop(ctx);
              try {
                await ref
                    .read(docFoldersProvider.notifier)
                    .createFolder(name: name);
              } catch (e, st) {
                _log.warning('failed to create first folder', e, st);
                if (context.mounted) {
                  showErrorSnackBar(context, ApiError.from(e).message);
                }
              }
            },
            child: const Text('create'),
          ),
        ],
      ),
    );
  }
}
