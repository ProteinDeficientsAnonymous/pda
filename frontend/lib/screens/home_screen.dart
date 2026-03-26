import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:markdown_toolbar/markdown_toolbar.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/home_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

const _defaultContent = '''
# Protein Deficients Anonymous

A collective liberation community.

## Who we are

Protein Deficients Anonymous (PDA) is a vegan community grounded in collective liberation. We believe that the liberation of animals, humans, and the earth are deeply interconnected. We organize, share resources, and build solidarity across movements.

## Our values

- 🌱 **Collective liberation** — Animal liberation and human liberation are inseparable.
- 🤝 **Mutual aid** — We support each other materially, not just ideologically.
- 🌍 **Intersectionality** — We center those most impacted by systems of oppression.
- ✊ **Direct action** — We take action in the world, not just in conversation.
''';

const _defaultJoinContent = '''
## Want to join us?

PDA is a vetted community. We review join requests to ensure alignment with our values and capacity to welcome new members.
''';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;
    final canEdit = user?.hasPermission('manage_guidelines') ?? false;
    final isLoggedIn = user != null;
    final homeAsync = ref.watch(homePageNotifierProvider);

    return AppScaffold(
      child: homeAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error:
            (_, __) => _HomeBody(
              content: _defaultContent,
              joinContent: _defaultJoinContent,
              canEdit: canEdit,
              isLoggedIn: isLoggedIn,
            ),
        data:
            (home) => _HomeBody(
              content:
                  home.content.trim().isEmpty ? _defaultContent : home.content,
              joinContent:
                  home.joinContent.trim().isEmpty
                      ? _defaultJoinContent
                      : home.joinContent,
              canEdit: canEdit,
              isLoggedIn: isLoggedIn,
            ),
      ),
    );
  }
}

class _HomeBody extends StatelessWidget {
  final String content;
  final String joinContent;
  final bool canEdit;
  final bool isLoggedIn;

  const _HomeBody({
    required this.content,
    required this.joinContent,
    required this.canEdit,
    required this.isLoggedIn,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 800),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _EditableSection(
                content: content,
                defaultContent: _defaultContent,
                canEdit: canEdit,
                onSave:
                    (text) => ProviderScope.containerOf(
                      context,
                    ).read(homePageNotifierProvider.notifier).saveContent(text),
              ),
              if (!isLoggedIn || canEdit) ...[
                const Divider(height: 32),
                _EditableSection(
                  content: joinContent,
                  defaultContent: _defaultJoinContent,
                  canEdit: canEdit,
                  onSave:
                      (text) => ProviderScope.containerOf(context)
                          .read(homePageNotifierProvider.notifier)
                          .saveJoinContent(text),
                  footer:
                      !isLoggedIn
                          ? Padding(
                            padding: const EdgeInsets.fromLTRB(24, 8, 24, 40),
                            child: ElevatedButton(
                              onPressed: () => context.go('/join'),
                              style: ElevatedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 32,
                                  vertical: 16,
                                ),
                              ),
                              child: const Text(
                                'Request to join',
                                style: TextStyle(fontSize: 16),
                              ),
                            ),
                          )
                          : null,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _EditableSection extends ConsumerStatefulWidget {
  final String content;
  final String defaultContent;
  final bool canEdit;
  final Future<void> Function(String) onSave;
  final Widget? footer;

  const _EditableSection({
    required this.content,
    required this.defaultContent,
    required this.canEdit,
    required this.onSave,
    this.footer,
  });

  @override
  ConsumerState<_EditableSection> createState() => _EditableSectionState();
}

class _EditableSectionState extends ConsumerState<_EditableSection> {
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
      await widget.onSave(_controller.text);
      if (mounted) setState(() => _editing = false);
    } on DioException catch (e) {
      if (!mounted) return;
      final detail = (e.response?.data as Map?)?['detail'] ?? 'Failed to save.';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(detail.toString())));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _cancel() {
    _controller.text = widget.content;
    setState(() => _editing = false);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (widget.canEdit)
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
            child: Row(
              children: [
                const Spacer(),
                if (!_editing)
                  FilledButton.tonal(
                    onPressed: () => setState(() => _editing = true),
                    child: const Text('Edit'),
                  ),
                if (_editing) ...[
                  TextButton(
                    onPressed: _saving ? null : _cancel,
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
          ),
        if (_editing) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: MarkdownToolbar(
              useIncludedTextField: false,
              controller: _controller,
              focusNode: _focusNode,
              hideImage: true,
              hideCheckbox: true,
              hideHorizontalRule: true,
              collapsable: false,
              backgroundColor:
                  Theme.of(context).colorScheme.surfaceContainerHighest,
              iconColor: Theme.of(context).colorScheme.onSurface,
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(24),
            child: TextField(
              controller: _controller,
              focusNode: _focusNode,
              maxLines: null,
              minLines: 5,
              inputFormatters: [LengthLimitingTextInputFormatter(50000)],
              decoration: const InputDecoration(
                border: OutlineInputBorder(),
                hintText: 'Write content in Markdown…',
                alignLabelWithHint: true,
              ),
              style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
            ),
          ),
        ] else ...[
          Markdown(
            data: widget.content,
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 16),
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
          ),
          if (widget.footer != null) widget.footer!,
        ],
      ],
    );
  }
}
