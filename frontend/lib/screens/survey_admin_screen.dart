import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/survey_admin_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/config/constants.dart';

class SurveyAdminScreen extends ConsumerWidget {
  const SurveyAdminScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final surveysAsync = ref.watch(surveyAdminProvider);

    return AppScaffold(
      child: surveysAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(
          child: Text('couldn\'t load surveys — try refreshing'),
        ),
        data: (surveys) => _SurveyAdminBody(surveys: surveys),
      ),
    );
  }
}

class _SurveyAdminBody extends ConsumerWidget {
  final List<Survey> surveys;

  const _SurveyAdminBody({required this.surveys});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Row(
          children: [
            Expanded(
              child: Text('surveys', style: theme.textTheme.headlineSmall),
            ),
            FilledButton.icon(
              onPressed: () => _createSurvey(context, ref),
              icon: const Icon(Icons.add),
              label: const Text('new survey'),
            ),
          ],
        ),
        const SizedBox(height: 20),
        if (surveys.isEmpty)
          Center(
            child: Padding(
              padding: const EdgeInsets.only(top: 48),
              child: Column(
                children: [
                  Icon(
                    Icons.poll_outlined,
                    size: 48,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.3),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'no surveys yet 🌿',
                    style: theme.textTheme.bodyLarge?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ...surveys.map(
            (s) => _SurveyCard(
              survey: s,
              onTap: () => context.go('/admin/surveys/${s.id}'),
              onToggle: () => _toggleActive(context, ref, s),
              onDelete: () => _deleteSurvey(context, ref, s),
            ),
          ),
      ],
    );
  }

  Future<void> _createSurvey(BuildContext context, WidgetRef ref) async {
    final result = await showDialog<_CreateSurveyResult>(
      context: context,
      builder: (_) => const _CreateSurveyDialog(),
    );
    if (result == null) return;
    try {
      final survey = await ref
          .read(surveyAdminProvider.notifier)
          .createSurvey(
            title: result.title,
            slug: result.slug,
            visibility: result.visibility,
          );
      if (context.mounted) {
        showSnackBar(context, 'survey created 🌱');
        context.go('/admin/surveys/${survey.id}');
      }
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, 'couldn\'t create survey — try again');
      }
    }
  }

  Future<void> _toggleActive(
    BuildContext context,
    WidgetRef ref,
    Survey survey,
  ) async {
    try {
      await ref.read(surveyAdminProvider.notifier).updateSurvey(survey.id, {
        'is_active': !survey.isActive,
      });
      if (context.mounted) {
        showSnackBar(
          context,
          survey.isActive ? 'survey paused' : 'survey active ✓',
        );
      }
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, 'couldn\'t update survey — try again');
      }
    }
  }

  Future<void> _deleteSurvey(
    BuildContext context,
    WidgetRef ref,
    Survey survey,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('delete survey'),
        content: Text(
          'Delete "${survey.title}" and all its responses? '
          'This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
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
      await ref.read(surveyAdminProvider.notifier).deleteSurvey(survey.id);
      if (context.mounted) showSnackBar(context, 'survey deleted');
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, 'couldn\'t delete survey — try again');
      }
    }
  }
}

class _SurveyCard extends StatelessWidget {
  final Survey survey;
  final VoidCallback onTap;
  final VoidCallback onToggle;
  final VoidCallback onDelete;

  const _SurveyCard({
    required this.survey,
    required this.onTap,
    required this.onToggle,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        onTap: onTap,
        leading: Icon(
          survey.isActive ? Icons.poll_outlined : Icons.pause_circle_outline,
          color: survey.isActive
              ? theme.colorScheme.primary
              : theme.colorScheme.onSurface.withValues(alpha: 0.4),
        ),
        title: Text(survey.title),
        subtitle: Text(
          '/${survey.slug} · ${survey.responseCount} responses · ${survey.visibility}',
          style: const TextStyle(fontSize: 12),
        ),
        trailing: PopupMenuButton<String>(
          onSelected: (value) {
            if (value == 'toggle') onToggle();
            if (value == 'delete') onDelete();
          },
          itemBuilder: (_) => [
            PopupMenuItem(
              value: 'toggle',
              child: Text(survey.isActive ? 'pause' : 'activate'),
            ),
            const PopupMenuItem(value: 'delete', child: Text('delete')),
          ],
        ),
      ),
    );
  }
}

class _CreateSurveyResult {
  final String title;
  final String slug;
  final String visibility;

  _CreateSurveyResult({
    required this.title,
    required this.slug,
    required this.visibility,
  });
}

class _CreateSurveyDialog extends StatefulWidget {
  const _CreateSurveyDialog();

  @override
  State<_CreateSurveyDialog> createState() => _CreateSurveyDialogState();
}

class _CreateSurveyDialogState extends State<_CreateSurveyDialog> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _slugController = TextEditingController();
  String _visibility = PageVisibility.public_;

  @override
  void initState() {
    super.initState();
    _titleController.addListener(_autoSlug);
  }

  @override
  void dispose() {
    _titleController.removeListener(_autoSlug);
    _titleController.dispose();
    _slugController.dispose();
    super.dispose();
  }

  void _autoSlug() {
    final title = _titleController.text;
    _slugController.text = title
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'^-+|-+$'), '');
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('new survey'),
      content: SizedBox(
        width: 400,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _titleController,
                decoration: const InputDecoration(
                  labelText: 'title',
                  border: OutlineInputBorder(),
                ),
                validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
                autofocus: true,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _slugController,
                decoration: const InputDecoration(
                  labelText: 'url slug',
                  border: OutlineInputBorder(),
                  prefixText: '/surveys/',
                ),
                validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _visibility,
                decoration: const InputDecoration(
                  labelText: 'visibility',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(
                    value: PageVisibility.public_,
                    child: Text('public'),
                  ),
                  DropdownMenuItem(
                    value: PageVisibility.membersOnly,
                    child: Text('members only'),
                  ),
                ],
                onChanged: (v) =>
                    setState(() => _visibility = v ?? PageVisibility.public_),
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              Navigator.of(context).pop(
                _CreateSurveyResult(
                  title: _titleController.text,
                  slug: _slugController.text,
                  visibility: _visibility,
                ),
              );
            }
          },
          child: const Text('create'),
        ),
      ],
    );
  }
}
