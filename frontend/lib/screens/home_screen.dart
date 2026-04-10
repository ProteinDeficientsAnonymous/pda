import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/home_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/launcher.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/autosave_mixin.dart';
import 'package:pda/widgets/deferred_quill_editor.dart';
import 'package:pda/widgets/html_content_viewer.dart';
import 'package:pda/widgets/save_cancel_button_row.dart';
import 'package:pda/config/constants.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).value;
    final canEdit = user?.hasPermission(Permission.editHomepage) ?? false;
    final isLoggedIn = user != null;
    final homeAsync = ref.watch(homePageNotifierProvider);

    return AppScaffold(
      child: homeAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _HomeBody(
          content: '',
          contentHtml: '',
          joinContent: '',
          joinContentHtml: '',
          donateUrl: '',
          canEdit: canEdit,
          isLoggedIn: isLoggedIn,
        ),
        data: (home) => _HomeBody(
          content: home.content,
          contentHtml: home.contentHtml,
          joinContent: home.joinContent,
          joinContentHtml: home.joinContentHtml,
          donateUrl: home.donateUrl,
          canEdit: canEdit,
          isLoggedIn: isLoggedIn,
        ),
      ),
    );
  }
}

class _HomeBody extends StatelessWidget {
  final String content;
  final String contentHtml;
  final String joinContent;
  final String joinContentHtml;
  final String donateUrl;
  final bool canEdit;
  final bool isLoggedIn;

  const _HomeBody({
    required this.content,
    required this.contentHtml,
    required this.joinContent,
    required this.joinContentHtml,
    required this.donateUrl,
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
                contentHtml: contentHtml,
                canEdit: canEdit,
                onSave: (text) => ProviderScope.containerOf(
                  context,
                ).read(homePageNotifierProvider.notifier).saveContent(text),
              ),
              if (donateUrl.isNotEmpty || canEdit) ...[
                _DonateCta(donateUrl: donateUrl, canEdit: canEdit),
              ],
              if (!isLoggedIn || canEdit) ...[
                const Divider(height: 32),
                _EditableSection(
                  content: joinContent,
                  contentHtml: joinContentHtml,
                  canEdit: canEdit,
                  onSave: (text) => ProviderScope.containerOf(context)
                      .read(homePageNotifierProvider.notifier)
                      .saveJoinContent(text),
                  footer: !isLoggedIn
                      ? Padding(
                          padding: const EdgeInsets.fromLTRB(24, 8, 24, 40),
                          child: FilledButton(
                            onPressed: () => context.go('/join'),
                            style: FilledButton.styleFrom(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 32,
                                vertical: 16,
                              ),
                            ),
                            child: const Text(
                              'request to join',
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

class _DonateCta extends ConsumerStatefulWidget {
  final String donateUrl;
  final bool canEdit;

  const _DonateCta({required this.donateUrl, required this.canEdit});

  @override
  ConsumerState<_DonateCta> createState() => _DonateCtaState();
}

class _DonateCtaState extends ConsumerState<_DonateCta> {
  bool _editing = false;
  late final TextEditingController _controller;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.donateUrl);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final raw = _controller.text.trim();
      final url = raw.isNotEmpty && !raw.contains('://') ? 'https://$raw' : raw;
      await ProviderScope.containerOf(
        context,
      ).read(homePageNotifierProvider.notifier).saveDonateUrl(url);
      if (mounted) setState(() => _editing = false);
    } catch (e) {
      if (!mounted) return;
      showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _cancel() {
    _controller.text = widget.donateUrl;
    setState(() => _editing = false);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.canEdit) ...[
            Row(
              children: [
                const Text(
                  'Donate button',
                  style: TextStyle(fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                if (!_editing)
                  FilledButton.tonal(
                    onPressed: () => setState(() => _editing = true),
                    child: const Text('Edit'),
                  ),
                if (_editing)
                  SaveCancelButtonRow(
                    saving: _saving,
                    onSave: _save,
                    onCancel: _cancel,
                  ),
              ],
            ),
            if (_editing) ...[
              const SizedBox(height: 8),
              TextField(
                controller: _controller,
                maxLength: FieldLimit.url,
                decoration: const InputDecoration(
                  labelText: 'Donate URL',
                  hintText: 'https://example.com/donate',
                ),
                keyboardType: TextInputType.url,
              ),
              const SizedBox(height: 8),
            ] else
              const SizedBox(height: 12),
          ],
          if (widget.donateUrl.isNotEmpty)
            Center(
              child: Semantics(
                button: true,
                label: 'Donate',
                child: FilledButton(
                  onPressed: () => openUrl(widget.donateUrl),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 32,
                      vertical: 16,
                    ),
                  ),
                  child: const Text('Donate', style: TextStyle(fontSize: 16)),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _EditableSection extends ConsumerStatefulWidget {
  final String content;
  final String contentHtml;
  final bool canEdit;
  final Future<void> Function(String) onSave;
  final Widget? footer;

  const _EditableSection({
    required this.content,
    required this.contentHtml,
    required this.canEdit,
    required this.onSave,
    this.footer,
  });

  @override
  ConsumerState<_EditableSection> createState() => _EditableSectionState();
}

class _EditableSectionState extends ConsumerState<_EditableSection>
    with AutosaveMixin {
  bool _editing = false;
  late String _json;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _json = widget.content;
    if (widget.canEdit) {
      initAutosaveCallback(onSave: widget.onSave);
    }
  }

  @override
  void dispose() {
    disposeAutosave();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await widget.onSave(_json);
      if (mounted) setState(() => _editing = false);
    } catch (e) {
      if (!mounted) return;
      showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _cancel() {
    setState(() {
      _json = widget.content;
      _editing = false;
    });
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
                if (_editing) ...[
                  AutosaveIndicator(status: autosaveStatus),
                  const SizedBox(width: 12),
                ],
                if (!_editing)
                  FilledButton.tonal(
                    onPressed: () => setState(() => _editing = true),
                    child: const Text('Edit'),
                  ),
                if (_editing)
                  SaveCancelButtonRow(
                    saving: _saving,
                    onSave: _save,
                    onCancel: _cancel,
                  ),
              ],
            ),
          ),
        if (_editing)
          DeferredQuillEditor(
            jsonContent: _json,
            editing: true,
            hintText: 'Write content…',
            onChanged: (v) {
              _json = v;
              triggerAutosave(v);
            },
          )
        else
          HtmlContentViewer(html: widget.contentHtml),
        if (!_editing && widget.footer != null) widget.footer!,
      ],
    );
  }
}
