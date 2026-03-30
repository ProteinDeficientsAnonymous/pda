import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/join_form_question.dart';
import 'package:pda/providers/join_form_admin_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';

class JoinFormConfigScreen extends ConsumerWidget {
  const JoinFormConfigScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final questionsAsync = ref.watch(joinFormAdminProvider);

    return AppScaffold(
      child: questionsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Failed to load: $e')),
        data: (questions) => _JoinFormConfigBody(questions: questions),
      ),
    );
  }
}

class _JoinFormConfigBody extends ConsumerStatefulWidget {
  final List<JoinFormQuestion> questions;

  const _JoinFormConfigBody({required this.questions});

  @override
  ConsumerState<_JoinFormConfigBody> createState() =>
      _JoinFormConfigBodyState();
}

class _JoinFormConfigBodyState extends ConsumerState<_JoinFormConfigBody> {
  late List<JoinFormQuestion> _questions;

  @override
  void initState() {
    super.initState();
    _questions = List.of(widget.questions);
  }

  @override
  void didUpdateWidget(covariant _JoinFormConfigBody oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.questions != widget.questions) {
      _questions = List.of(widget.questions);
    }
  }

  Future<void> _addQuestion() async {
    final result = await showDialog<_QuestionFormResult>(
      context: context,
      builder: (_) => const _QuestionFormDialog(),
    );
    if (result == null) return;
    try {
      await ref
          .read(joinFormAdminProvider.notifier)
          .addQuestion(
            label: result.label,
            fieldType: result.fieldType,
            options: result.options,
            required: result.required,
          );
      if (mounted) showSnackBar(context, 'question added');
    } catch (e) {
      if (mounted) showErrorSnackBar(context, 'Failed to add question: $e');
    }
  }

  Future<void> _editQuestion(JoinFormQuestion q) async {
    final result = await showDialog<_QuestionFormResult>(
      context: context,
      builder: (_) => _QuestionFormDialog(question: q),
    );
    if (result == null) return;
    try {
      await ref
          .read(joinFormAdminProvider.notifier)
          .updateQuestion(
            id: q.id,
            label: result.label,
            fieldType: result.fieldType,
            options: result.options,
            required: result.required,
          );
      if (mounted) showSnackBar(context, 'question updated');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'Failed to update question: $e');
      }
    }
  }

  Future<void> _deleteQuestion(JoinFormQuestion q) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Delete question'),
            content: Text(
              'Delete "${q.label}"? Existing answers will '
              'still show on old requests.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Delete'),
              ),
            ],
          ),
    );
    if (confirmed != true) return;
    try {
      await ref.read(joinFormAdminProvider.notifier).deleteQuestion(q.id);
      if (mounted) showSnackBar(context, 'question deleted');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'Failed to delete question: $e');
      }
    }
  }

  Future<void> _onReorder(int oldIndex, int newIndex) async {
    if (newIndex > oldIndex) newIndex -= 1;
    final item = _questions.removeAt(oldIndex);
    _questions.insert(newIndex, item);
    setState(() {});
    try {
      await ref
          .read(joinFormAdminProvider.notifier)
          .reorder(_questions.map((q) => q.id).toList());
    } catch (e) {
      if (mounted) showErrorSnackBar(context, 'Failed to reorder: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Join form questions',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                'Name and phone are always shown. Configure additional '
                'questions below — drag to reorder.',
                style: TextStyle(color: Colors.grey[700], fontSize: 14),
              ),
              const SizedBox(height: 24),
              if (_questions.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 32),
                  child: Center(
                    child: Text(
                      'no custom questions yet',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ),
                )
              else
                ReorderableListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: _questions.length,
                  onReorder: _onReorder,
                  itemBuilder: (context, index) {
                    final q = _questions[index];
                    return _QuestionCard(
                      key: ValueKey(q.id),
                      question: q,
                      onEdit: () => _editQuestion(q),
                      onDelete: () => _deleteQuestion(q),
                    );
                  },
                ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _addQuestion,
                icon: const Icon(Icons.add),
                label: const Text('Add question'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuestionCard extends StatelessWidget {
  final JoinFormQuestion question;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  const _QuestionCard({
    super.key,
    required this.question,
    required this.onEdit,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          question.fieldType == 'select'
              ? Icons.list_outlined
              : Icons.short_text_outlined,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        title: Text(question.label),
        subtitle: Row(
          children: [
            Text(question.fieldType),
            if (question.required) ...[
              const SizedBox(width: 8),
              Text(
                'required',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.primary,
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              tooltip: 'Edit question',
              icon: const Icon(Icons.edit_outlined, size: 20),
              onPressed: onEdit,
            ),
            IconButton(
              tooltip: 'Delete question',
              icon: Icon(
                Icons.delete_outline,
                size: 20,
                color: Theme.of(context).colorScheme.error,
              ),
              onPressed: onDelete,
            ),
          ],
        ),
      ),
    );
  }
}

class _QuestionFormResult {
  final String label;
  final String fieldType;
  final List<String> options;
  final bool required;

  const _QuestionFormResult({
    required this.label,
    required this.fieldType,
    required this.options,
    required this.required,
  });
}

class _QuestionFormDialog extends StatefulWidget {
  final JoinFormQuestion? question;

  const _QuestionFormDialog({this.question});

  @override
  State<_QuestionFormDialog> createState() => _QuestionFormDialogState();
}

class _QuestionFormDialogState extends State<_QuestionFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _labelCtrl;
  late String _fieldType;
  late bool _required;
  late List<TextEditingController> _optionCtrls;

  @override
  void initState() {
    super.initState();
    _labelCtrl = TextEditingController(text: widget.question?.label ?? '');
    _fieldType = widget.question?.fieldType ?? 'text';
    _required = widget.question?.required ?? false;
    _optionCtrls =
        (widget.question?.options ?? [])
            .map((o) => TextEditingController(text: o))
            .toList();
  }

  @override
  void dispose() {
    _labelCtrl.dispose();
    for (final c in _optionCtrls) {
      c.dispose();
    }
    super.dispose();
  }

  void _addOption() {
    setState(() => _optionCtrls.add(TextEditingController()));
  }

  void _removeOption(int index) {
    setState(() {
      _optionCtrls[index].dispose();
      _optionCtrls.removeAt(index);
    });
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final options =
        _fieldType == 'select'
            ? _optionCtrls
                .map((c) => c.text.trim())
                .where((o) => o.isNotEmpty)
                .toList()
            : <String>[];
    Navigator.of(context).pop(
      _QuestionFormResult(
        label: _labelCtrl.text.trim(),
        fieldType: _fieldType,
        options: options,
        required: _required,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isEditing = widget.question != null;
    return AlertDialog(
      title: Text(isEditing ? 'Edit question' : 'Add question'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _labelCtrl,
                decoration: const InputDecoration(labelText: 'Question label'),
                autofocus: true,
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'Required';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _fieldType,
                decoration: const InputDecoration(labelText: 'Field type'),
                items: const [
                  DropdownMenuItem(value: 'text', child: Text('Text')),
                  DropdownMenuItem(value: 'select', child: Text('Dropdown')),
                ],
                onChanged: (val) => setState(() => _fieldType = val ?? 'text'),
              ),
              const SizedBox(height: 12),
              SwitchListTile(
                title: const Text('Required'),
                value: _required,
                contentPadding: EdgeInsets.zero,
                onChanged: (val) => setState(() => _required = val),
              ),
              if (_fieldType == 'select') ...[
                const SizedBox(height: 12),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Options',
                    style: TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(height: 8),
                for (var i = 0; i < _optionCtrls.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _optionCtrls[i],
                            decoration: InputDecoration(
                              hintText: 'Option ${i + 1}',
                              isDense: true,
                            ),
                          ),
                        ),
                        IconButton(
                          tooltip: 'Remove option',
                          icon: const Icon(Icons.close, size: 18),
                          onPressed: () => _removeOption(i),
                        ),
                      ],
                    ),
                  ),
                TextButton.icon(
                  onPressed: _addOption,
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Add option'),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _submit,
          child: Text(isEditing ? 'Save' : 'Add'),
        ),
      ],
    );
  }
}
