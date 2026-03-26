import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:markdown_toolbar/markdown_toolbar.dart';

import '../providers/auth_provider.dart';
import '../providers/editable_page_provider.dart';
import 'autosave_mixin.dart';

class EditableContentBlock extends ConsumerStatefulWidget {
  const EditableContentBlock({super.key, required this.slug});

  final String slug;

  @override
  ConsumerState<EditableContentBlock> createState() =>
      _EditableContentBlockState();
}

class _EditableContentBlockState extends ConsumerState<EditableContentBlock>
    with AutosaveMixin {
  late final TextEditingController _controller;
  late final FocusNode _focusNode;
  bool _editing = false;
  bool _saving = false;
  bool _autosaveInitialized = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
    _focusNode = FocusNode();
  }

  void _maybeInitAutosave(bool canEdit) {
    if (_autosaveInitialized || !canEdit) return;
    _autosaveInitialized = true;
    initAutosave(
      controller: _controller,
      onSave:
          (text) => ref
              .read(editablePageProvider(widget.slug).notifier)
              .saveContent(text),
    );
  }

  @override
  void dispose() {
    disposeAutosave();
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ref
          .read(editablePageProvider(widget.slug).notifier)
          .saveContent(_controller.text);
      if (mounted) setState(() => _editing = false);
    } on DioException catch (e) {
      if (!mounted) return;
      final detail =
          (e.response?.data as Map?)?['detail'] as String? ?? 'Save failed.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(detail)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _cancelEdit() {
    final currentContent =
        ref.read(editablePageProvider(widget.slug)).valueOrNull?.content ?? '';
    _controller.text = currentContent;
    setState(() => _editing = false);
  }

  Future<void> _changeVisibility(String visibility) async {
    try {
      await ref
          .read(editablePageProvider(widget.slug).notifier)
          .saveVisibility(visibility);
    } on DioException catch (e) {
      if (!mounted) return;
      final detail =
          (e.response?.data as Map?)?['detail'] as String? ??
          'Failed to update visibility.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(detail)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).valueOrNull;
    final canEdit = user?.hasPermission('manage_guidelines') ?? false;
    _maybeInitAutosave(canEdit);
    final pageAsync = ref.watch(editablePageProvider(widget.slug));

    return pageAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) {
        final isMembersOnly =
            e is DioException && e.response?.statusCode == 403;
        return Center(
          child: Text(
            isMembersOnly
                ? 'This page is for members only.'
                : 'Failed to load page.',
          ),
        );
      },
      data:
          (page) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (canEdit)
                _AdminToolbar(
                  page: page,
                  onVisibilityChange: _changeVisibility,
                  editing: _editing,
                  saving: _saving,
                  autosaveStatus: autosaveStatus,
                  onEdit: () {
                    _controller.text = page.content;
                    setState(() => _editing = true);
                  },
                  onSave: _save,
                  onCancel: _cancelEdit,
                ),
              if (_editing) _buildToolbar(context),
              Expanded(
                child: _editing ? _buildEditor() : _buildViewer(context, page),
              ),
            ],
          ),
    );
  }

  Widget _buildToolbar(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: MarkdownToolbar(
        useIncludedTextField: false,
        controller: _controller,
        focusNode: _focusNode,
        hideImage: true,
        hideCheckbox: true,
        hideHorizontalRule: true,
        hideHeading: true,
        collapsable: false,
        backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
        iconColor: Theme.of(context).colorScheme.onSurface,
      ),
    );
  }

  Widget _buildEditor() {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: TextField(
        controller: _controller,
        focusNode: _focusNode,
        maxLines: null,
        expands: true,
        textAlignVertical: TextAlignVertical.top,
        inputFormatters: [LengthLimitingTextInputFormatter(50000)],
        decoration: const InputDecoration(
          border: OutlineInputBorder(),
          hintText: 'Enter page content…',
          alignLabelWithHint: true,
        ),
        style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
      ),
    );
  }

  Widget _buildViewer(BuildContext context, EditablePage page) {
    final content =
        ref.watch(editablePageProvider(widget.slug)).valueOrNull?.content ??
        page.content;
    if (content.trim().isEmpty) {
      final user = ref.read(authProvider).valueOrNull;
      final canEdit = user?.hasPermission('manage_guidelines') ?? false;
      return Center(
        child: Text(
          canEdit ? 'No content yet. Click Edit to add some.' : 'Coming soon.',
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      );
    }
    return Markdown(data: content, padding: const EdgeInsets.all(24));
  }
}

class _AdminToolbar extends StatelessWidget {
  const _AdminToolbar({
    required this.page,
    required this.onVisibilityChange,
    required this.editing,
    required this.saving,
    required this.autosaveStatus,
    required this.onEdit,
    required this.onSave,
    required this.onCancel,
  });

  final EditablePage page;
  final void Function(String) onVisibilityChange;
  final bool editing;
  final bool saving;
  final AutosaveStatus autosaveStatus;
  final VoidCallback onEdit;
  final VoidCallback onSave;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      child: Row(
        children: [
          const Icon(Icons.admin_panel_settings, size: 16),
          const SizedBox(width: 8),
          Text('Admin', style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(width: 16),
          DropdownButton<String>(
            value: page.visibility,
            isDense: true,
            items: const [
              DropdownMenuItem(value: 'public', child: Text('Public')),
              DropdownMenuItem(
                value: 'members_only',
                child: Text('Members only'),
              ),
            ],
            onChanged: (v) {
              if (v != null) onVisibilityChange(v);
            },
          ),
          const Spacer(),
          if (editing) ...[
            AutosaveIndicator(status: autosaveStatus),
            const SizedBox(width: 12),
          ],
          if (!editing)
            FilledButton.tonal(onPressed: onEdit, child: const Text('Edit'))
          else ...[
            TextButton(
              onPressed: saving ? null : onCancel,
              child: const Text('Cancel'),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: saving ? null : onSave,
              child:
                  saving
                      ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                      : const Text('Save'),
            ),
          ],
        ],
      ),
    );
  }
}
