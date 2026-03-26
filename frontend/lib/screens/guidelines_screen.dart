import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:markdown_toolbar/markdown_toolbar.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/guidelines_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

class GuidelinesScreen extends ConsumerWidget {
  const GuidelinesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;
    final canEdit = user?.hasPermission('manage_guidelines') ?? false;
    final guidelinesAsync = ref.watch(guidelinesNotifierProvider);

    return AppScaffold(
      child: guidelinesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error:
            (e, _) => Center(
              child: Text(
                'Failed to load guidelines.',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
        data:
            (guidelines) =>
                _GuidelinesBody(content: guidelines.content, canEdit: canEdit),
      ),
    );
  }
}

class _GuidelinesBody extends ConsumerStatefulWidget {
  final String content;
  final bool canEdit;

  const _GuidelinesBody({required this.content, required this.canEdit});

  @override
  ConsumerState<_GuidelinesBody> createState() => _GuidelinesBodyState();
}

class _GuidelinesBodyState extends ConsumerState<_GuidelinesBody> {
  bool _editing = false;
  late final TextEditingController _controller;
  late final FocusNode _focusNode;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.content);
    _focusNode = FocusNode();
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ref
          .read(guidelinesNotifierProvider.notifier)
          .saveContent(_controller.text);
      if (mounted) setState(() => _editing = false);
    } on DioException catch (e) {
      if (!mounted) return;
      final detail =
          (e.response?.data as Map?)?['detail'] ?? 'Failed to save guidelines.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(detail.toString())));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _cancelEdit() {
    _controller.text =
        ref.read(guidelinesNotifierProvider).valueOrNull?.content ??
        widget.content;
    setState(() => _editing = false);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _buildHeader(context),
        if (_editing) _buildToolbar(),
        Expanded(child: _editing ? _buildEditor() : _buildViewer(context)),
      ],
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
      child: Row(
        children: [
          Expanded(
            child: Text(
              'Community Guidelines',
              style: Theme.of(
                context,
              ).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
            ),
          ),
          if (widget.canEdit && !_editing)
            FilledButton.tonal(
              onPressed: () => setState(() => _editing = true),
              child: const Text('Edit'),
            ),
          if (_editing) ...[
            TextButton(
              onPressed: _saving ? null : _cancelEdit,
              child: const Text('Cancel'),
            ),
            const SizedBox(width: 8),
            FilledButton(
              onPressed: _saving ? null : _save,
              child:
                  _saving
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

  Widget _buildToolbar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: MarkdownToolbar(
        useIncludedTextField: false,
        controller: _controller,
        focusNode: _focusNode,
        hideImage: true,
        hideCheckbox: true,
        hideHorizontalRule: true,
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
        decoration: const InputDecoration(
          border: OutlineInputBorder(),
          hintText: 'Write community guidelines in Markdown…',
          alignLabelWithHint: true,
        ),
        style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
      ),
    );
  }

  Widget _buildViewer(BuildContext context) {
    final content =
        ref.watch(guidelinesNotifierProvider).valueOrNull?.content ??
        widget.content;
    if (content.trim().isEmpty) {
      return Center(
        child: Text(
          'No guidelines have been posted yet.',
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      );
    }
    return Markdown(data: content, padding: const EdgeInsets.all(24));
  }
}
