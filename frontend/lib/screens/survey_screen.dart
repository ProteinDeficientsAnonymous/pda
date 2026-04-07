import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/survey_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/screens/survey_question_field.dart';

final _log = Logger('Survey');

class SurveyScreen extends ConsumerWidget {
  final String slug;

  const SurveyScreen({super.key, required this.slug});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final surveyAsync = ref.watch(surveyBySlugProvider(slug));

    return AppScaffold(
      maxWidth: 600,
      child: surveyAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(
          child: Text('couldn\'t find that survey — it may be closed'),
        ),
        data: (survey) => _SurveyForm(survey: survey),
      ),
    );
  }
}

class _SurveyForm extends ConsumerStatefulWidget {
  final Survey survey;

  const _SurveyForm({required this.survey});

  @override
  ConsumerState<_SurveyForm> createState() => _SurveyFormState();
}

class _SurveyFormState extends ConsumerState<_SurveyForm> {
  final _formKey = GlobalKey<FormState>();
  final Map<String, String> _answers = {};
  bool _submitting = false;
  bool _submitted = false;

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();

    setState(() => _submitting = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.post(
        '/api/community/surveys/view/${widget.survey.slug}/respond/',
        data: {'answers': _answers},
      );
      setState(() => _submitted = true);
      ref.invalidate(surveyBySlugProvider(widget.survey.slug));
      _log.info('submitted survey response');
    } catch (e, st) {
      _log.warning('failed to submit survey response', e, st);
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t submit — try again');
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_submitted) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.check_circle_outline_rounded,
                size: 56,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                'thanks for your feedback! 🌱',
                style: theme.textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    final isUpdate = widget.survey.myResponseId != null;
    final isFinalized = widget.survey.pollResult != null;

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
                const SizedBox(height: 8),
                Text(
                  widget.survey.description,
                  style: TextStyle(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ],
              if (isFinalized) ...[
                const SizedBox(height: 16),
                _PollResultBanner(pollResult: widget.survey.pollResult!),
              ],
              const SizedBox(height: 24),
              Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ...widget.survey.questions.map(
                      (q) => Padding(
                        padding: const EdgeInsets.only(bottom: 20),
                        child: SurveyQuestionField(
                          question: q,
                          survey: widget.survey,
                          isFinalized: isFinalized,
                          onSaved: (value) {
                            if (value != null && value.isNotEmpty) {
                              _answers[q.id] = value;
                            }
                          },
                        ),
                      ),
                    ),
                    if (!isFinalized) ...[
                      const SizedBox(height: 8),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: _submitting ? null : _submit,
                          child: _submitting
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : Text(isUpdate ? 'update vote' : 'submit'),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PollResultBanner extends StatelessWidget {
  final PollResult pollResult;

  const _PollResultBanner({required this.pollResult});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dt = pollResult.winningDatetime.toLocal();
    final formatted = DateFormat('EEEE, MMMM d · h:mm a').format(dt);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(
            Icons.check_circle_rounded,
            color: theme.colorScheme.primary,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'time chosen!',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: theme.colorScheme.onPrimaryContainer,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  formatted.toLowerCase(),
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onPrimaryContainer,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
