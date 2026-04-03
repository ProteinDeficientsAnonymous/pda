import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/survey_admin_provider.dart';
import 'package:pda/utils/app_icons.dart';
import 'package:pda/utils/share.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/screens/survey_question_form_dialog.dart';

IconData _fieldTypeIcon(String type) {
  return switch (type) {
    FieldType.textarea => Icons.notes_outlined,
    FieldType.select => Icons.radio_button_checked_outlined,
    FieldType.multiselect => Icons.checklist_outlined,
    FieldType.dropdown => Icons.arrow_drop_down_circle_outlined,
    FieldType.number => Icons.pin_outlined,
    FieldType.yesNo => Icons.toggle_on_outlined,
    FieldType.rating => Icons.star_outline_rounded,
    FieldType.datetimePoll => Icons.event_outlined,
    _ => Icons.short_text_outlined,
  };
}

class SurveyBuilderScreen extends ConsumerWidget {
  final String surveyId;

  const SurveyBuilderScreen({super.key, required this.surveyId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final surveyAsync = ref.watch(surveyQuestionsProvider(surveyId));

    return AppScaffold(
      child: surveyAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            const Center(child: Text('couldn\'t load survey — try refreshing')),
        data: (survey) => _BuilderBody(survey: survey),
      ),
    );
  }
}

class _BuilderBody extends ConsumerStatefulWidget {
  final Survey survey;

  const _BuilderBody({required this.survey});

  @override
  ConsumerState<_BuilderBody> createState() => _BuilderBodyState();
}

class _BuilderBodyState extends ConsumerState<_BuilderBody> {
  late List<SurveyQuestion> _questions;

  @override
  void initState() {
    super.initState();
    _questions = List.of(widget.survey.questions);
  }

  @override
  void didUpdateWidget(covariant _BuilderBody oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.survey != widget.survey) {
      _questions = List.of(widget.survey.questions);
    }
  }

  Future<void> _addQuestion() async {
    final result = await showDialog<SurveyQuestionFormResult>(
      context: context,
      builder: (_) => const SurveyQuestionFormDialog(),
    );
    if (result == null) return;
    try {
      await ref
          .read(surveyQuestionsProvider(widget.survey.id).notifier)
          .addQuestion(
            label: result.label,
            fieldType: result.fieldType,
            options: result.options,
            required: result.required,
          );
      if (mounted) showSnackBar(context, 'question added');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t add question — try again');
      }
    }
  }

  Future<void> _editQuestion(SurveyQuestion q) async {
    final result = await showDialog<SurveyQuestionFormResult>(
      context: context,
      builder: (_) => SurveyQuestionFormDialog(question: q),
    );
    if (result == null) return;
    try {
      await ref
          .read(surveyQuestionsProvider(widget.survey.id).notifier)
          .updateQuestion(
            questionId: q.id,
            label: result.label,
            fieldType: result.fieldType,
            options: result.options,
            required: result.required,
          );
      if (mounted) showSnackBar(context, 'question updated');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t update question — try again');
      }
    }
  }

  Future<void> _deleteQuestion(SurveyQuestion q) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('delete question'),
        content: Text(
          'Delete "${q.label}"? Existing responses will '
          'still show their answers.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: const Text('delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ref
          .read(surveyQuestionsProvider(widget.survey.id).notifier)
          .deleteQuestion(q.id);
      if (mounted) showSnackBar(context, 'question deleted');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t delete question — try again');
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
          .read(surveyQuestionsProvider(widget.survey.id).notifier)
          .reorder(_questions.map((q) => q.id).toList());
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t reorder — try again');
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(widget.survey.title, style: theme.textTheme.headlineSmall),
              if (widget.survey.description.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  widget.survey.description,
                  style: TextStyle(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ],
              const SizedBox(height: 4),
              Text(
                '/surveys/${widget.survey.slug} · ${widget.survey.visibility}',
                style: TextStyle(
                  fontSize: 12,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  OutlinedButton.icon(
                    onPressed: () =>
                        context.go('/surveys/${widget.survey.slug}'),
                    icon: const Icon(Icons.visibility_outlined, size: 18),
                    label: const Text('preview'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () {
                      final link = Uri.base
                          .replace(
                            path: '/surveys/${widget.survey.slug}',
                            query: '',
                          )
                          .toString();
                      shareUrl(link, subject: widget.survey.title);
                    },
                    icon: const Icon(AppIcons.share, size: 18),
                    label: const Text('share'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => context.go(
                      '/admin/surveys/${widget.survey.id}/responses',
                    ),
                    icon: const Icon(Icons.bar_chart_rounded, size: 18),
                    label: Text('${widget.survey.responseCount} responses'),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text('questions', style: theme.textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                'drag to reorder',
                style: TextStyle(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 16),
              if (_questions.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 32),
                  child: Center(
                    child: Text(
                      'no questions yet — add one below',
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
                label: const Text('add question'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _QuestionCard extends StatelessWidget {
  final SurveyQuestion question;
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
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          _fieldTypeIcon(question.fieldType),
          color: theme.colorScheme.onSurfaceVariant,
        ),
        title: Text(question.label),
        subtitle: Row(
          children: [
            Text(
              surveyFieldTypeLabels[question.fieldType] ?? question.fieldType,
            ),
            if (question.required) ...[
              const SizedBox(width: 8),
              Text(
                'required',
                style: TextStyle(
                  color: theme.colorScheme.primary,
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
              tooltip: 'edit question',
              icon: const Icon(Icons.edit_outlined, size: 20),
              onPressed: onEdit,
            ),
            IconButton(
              tooltip: 'delete question',
              icon: Icon(
                Icons.delete_outline,
                size: 20,
                color: theme.colorScheme.error,
              ),
              onPressed: onDelete,
            ),
          ],
        ),
      ),
    );
  }
}
