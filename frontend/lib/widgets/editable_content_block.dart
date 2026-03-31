import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/auth_provider.dart';
import '../config/constants.dart';
import '../providers/editable_page_provider.dart';
import '../services/api_error.dart';
import '../utils/snackbar.dart';
import 'autosave_mixin.dart';
import 'quill_content_editor.dart';
import 'save_cancel_button_row.dart';

class EditableContentBlock extends ConsumerStatefulWidget {
  const EditableContentBlock({super.key, required this.slug});

  final String slug;

  @override
  ConsumerState<EditableContentBlock> createState() =>
      _EditableContentBlockState();
}

class _EditableContentBlockState extends ConsumerState<EditableContentBlock>
    with AutosaveMixin {
  late String _json;
  bool _jsonInitialized = false;
  bool _editing = false;
  bool _saving = false;
  bool _autosaveInitialized = false;

  void _maybeInitAutosave(bool canEdit) {
    if (_autosaveInitialized || !canEdit) return;
    _autosaveInitialized = true;
    initAutosaveCallback(
      onSave:
          (text) => ref
              .read(editablePageProvider(widget.slug).notifier)
              .saveContent(text),
    );
  }

  @override
  void dispose() {
    disposeAutosave();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ref
          .read(editablePageProvider(widget.slug).notifier)
          .saveContent(_json);
      if (mounted) setState(() => _editing = false);
    } catch (e) {
      if (!mounted) return;
      showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _cancelEdit(String savedContent) {
    setState(() {
      _json = savedContent;
      _editing = false;
    });
  }

  Future<void> _changeVisibility(String visibility) async {
    try {
      await ref
          .read(editablePageProvider(widget.slug).notifier)
          .saveVisibility(visibility);
    } catch (e) {
      if (!mounted) return;
      showErrorSnackBar(context, ApiError.from(e).message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).valueOrNull;
    final canEdit = user?.hasPermission(Permission.editGuidelines) ?? false;
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
      data: (page) {
        // Initialize _json once from the loaded page content.
        if (!_jsonInitialized) {
          _json = page.content;
          _jsonInitialized = true;
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (canEdit)
              _AdminToolbar(
                page: page,
                onVisibilityChange: _changeVisibility,
                editing: _editing,
                saving: _saving,
                autosaveStatus: autosaveStatus,
                onEdit: () => setState(() => _editing = true),
                onSave: _save,
                onCancel: () => _cancelEdit(page.content),
              ),
            Expanded(
              child: QuillContentEditor(
                jsonContent: _json,
                editing: _editing,
                expands: true,
                hintText: 'Enter page content…',
                onChanged:
                    canEdit
                        ? (v) {
                          _json = v;
                          triggerAutosave(v);
                        }
                        : null,
              ),
            ),
          ],
        );
      },
    );
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
              DropdownMenuItem(
                value: PageVisibility.public_,
                child: Text('Public'),
              ),
              DropdownMenuItem(
                value: PageVisibility.membersOnly,
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
          else
            SaveCancelButtonRow(
              saving: saving,
              onSave: onSave,
              onCancel: onCancel,
            ),
        ],
      ),
    );
  }
}
