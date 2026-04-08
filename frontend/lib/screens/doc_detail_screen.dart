import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/docs_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/autosave_mixin.dart';
import 'package:pda/widgets/deferred_quill_editor.dart';
import 'package:pda/widgets/html_content_viewer.dart';

class DocDetailScreen extends ConsumerStatefulWidget {
  final String docId;

  const DocDetailScreen({super.key, required this.docId});

  @override
  ConsumerState<DocDetailScreen> createState() => _DocDetailScreenState();
}

class _DocDetailScreenState extends ConsumerState<DocDetailScreen>
    with AutosaveMixin<DocDetailScreen> {
  bool _editing = false;
  String? _pendingContent;
  late TextEditingController _titleController;
  bool _titleInitialized = false;

  @override
  void initState() {
    super.initState();
    _titleController = TextEditingController();
    initAutosaveCallback(
      onSave: (content) async {
        await ref
            .read(docDetailProvider(widget.docId).notifier)
            .save(content: content);
      },
    );
  }

  @override
  void dispose() {
    _titleController.dispose();
    disposeAutosave();
    super.dispose();
  }

  bool get _canManage {
    final user = ref.read(authProvider).value;
    return user?.hasPermission(Permission.manageDocs) ?? false;
  }

  @override
  Widget build(BuildContext context) {
    final docAsync = ref.watch(docDetailProvider(widget.docId));

    return AppScaffold(
      child: docAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(
          child: Text('couldn\'t load document — try refreshing'),
        ),
        data: (doc) {
          if (!_titleInitialized) {
            _titleController.text = doc.title;
            _titleInitialized = true;
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildToolbar(context),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (_editing)
                        TextField(
                          controller: _titleController,
                          style: Theme.of(context).textTheme.headlineSmall,
                          decoration: const InputDecoration(
                            border: InputBorder.none,
                            hintText: 'document title',
                          ),
                        )
                      else
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: Text(
                            doc.title,
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                        ),
                      if (_editing)
                        DeferredQuillEditor(
                          jsonContent: doc.content,
                          editing: true,
                          onChanged: (content) {
                            _pendingContent = content;
                            triggerAutosave(content);
                          },
                          expands: false,
                          hintText: 'start writing...',
                        )
                      else
                        HtmlContentViewer(html: doc.contentHtml),
                      const SizedBox(height: 48),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildToolbar(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 16, 0),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back),
            tooltip: 'back to docs',
            onPressed: () => context.go('/docs'),
          ),
          const Spacer(),
          AutosaveIndicator(status: autosaveStatus),
          const SizedBox(width: 8),
          if (_canManage)
            _editing
                ? Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextButton(
                        onPressed: _cancelEdit,
                        child: Text(
                          'cancel',
                          style: TextStyle(color: cs.onSurfaceVariant),
                        ),
                      ),
                      const SizedBox(width: 8),
                      FilledButton(
                        onPressed: _saveAndExit,
                        child: const Text('done'),
                      ),
                    ],
                  )
                : IconButton(
                    icon: const Icon(Icons.edit_outlined),
                    tooltip: 'edit document',
                    onPressed: () => setState(() => _editing = true),
                  ),
        ],
      ),
    );
  }

  void _cancelEdit() {
    _pendingContent = null;
    ref.invalidate(docDetailProvider(widget.docId));
    final doc = ref.read(docDetailProvider(widget.docId)).value;
    if (doc != null) _titleController.text = doc.title;
    setState(() => _editing = false);
  }

  Future<void> _saveAndExit() async {
    final newTitle = _titleController.text.trim();
    final doc = ref.read(docDetailProvider(widget.docId)).value;

    final titleChanged =
        doc != null && newTitle != doc.title && newTitle.isNotEmpty;
    final contentChanged = _pendingContent != null;

    if (titleChanged || contentChanged) {
      await ref
          .read(docDetailProvider(widget.docId).notifier)
          .save(
            title: titleChanged ? newTitle : null,
            content: contentChanged ? _pendingContent : null,
          );
      ref.invalidate(docFoldersProvider);
    }

    _pendingContent = null;
    setState(() => _editing = false);
  }
}
