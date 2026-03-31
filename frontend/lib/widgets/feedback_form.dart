import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/config/api_config.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/feedback_provider.dart';
import 'package:pda/utils/user_agent.dart';

class FeedbackForm extends ConsumerStatefulWidget {
  final String currentRoute;
  final String userAgent;
  final String appVersion;
  final VoidCallback onClose;

  const FeedbackForm({
    super.key,
    required this.currentRoute,
    this.userAgent = '',
    this.appVersion = '',
    required this.onClose,
  });

  @override
  ConsumerState<FeedbackForm> createState() => _FeedbackFormState();
}

class _FeedbackFormState extends ConsumerState<FeedbackForm> {
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _isBug = false;
  bool _isFeatureRequest = false;
  String _userAgent = '';
  String _appVersion = '';

  @override
  void initState() {
    super.initState();
    _userAgent =
        widget.userAgent.isNotEmpty ? widget.userAgent : getUserAgent();
    _appVersion = widget.appVersion.isNotEmpty ? widget.appVersion : gitSha;
  }

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    final user = ref.read(authProvider).valueOrNull;

    await ref
        .read(feedbackProvider.notifier)
        .submit(
          FeedbackSubmission(
            title: _titleController.text.trim(),
            description: _descriptionController.text.trim(),
            feedbackTypes: [
              if (_isBug) 'bug',
              if (_isFeatureRequest) 'feature request',
            ],
            currentRoute: widget.currentRoute,
            userAgent: _userAgent,
            userDisplayName: user?.displayName ?? '',
            userPhone: user?.phoneNumber ?? '',
            appVersion: _appVersion,
          ),
        );

    if (!mounted) return;

    final state = ref.read(feedbackProvider);
    if (state.hasError) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("couldn't submit feedback — try again")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = ref.watch(feedbackProvider).isLoading;
    final isWide = MediaQuery.sizeOf(context).width >= 500;

    return SizedBox(
      width: isWide ? 420 : double.infinity,
      child: Card(
        margin: const EdgeInsets.all(16),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'report a bug or share feedback',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 4,
                    runSpacing: 0,
                    children: [
                      const Text('this is a:'),
                      Checkbox(
                        value: _isBug,
                        semanticLabel: 'bug',
                        onChanged:
                            isLoading
                                ? null
                                : (v) => setState(() => _isBug = v ?? false),
                      ),
                      const Text('bug'),
                      Checkbox(
                        value: _isFeatureRequest,
                        semanticLabel: 'feature request',
                        onChanged:
                            isLoading
                                ? null
                                : (v) => setState(
                                  () => _isFeatureRequest = v ?? false,
                                ),
                      ),
                      const Text('feature request'),
                    ],
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    controller: _titleController,
                    decoration: const InputDecoration(
                      labelText: 'Title',
                      hintText: 'what happened?',
                    ),
                    validator:
                        (v) =>
                            (v == null || v.trim().isEmpty) ? 'required' : null,
                    textInputAction: TextInputAction.next,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _descriptionController,
                    decoration: const InputDecoration(
                      labelText: 'Description',
                      hintText: 'tell us more...',
                    ),
                    maxLines: 4,
                    textInputAction: TextInputAction.newline,
                  ),
                  const SizedBox(height: 16),
                  _MetadataSection(
                    route: widget.currentRoute,
                    appVersion: _appVersion,
                  ),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: isLoading ? null : widget.onClose,
                        child: const Text('cancel'),
                      ),
                      const SizedBox(width: 8),
                      FilledButton(
                        onPressed: isLoading ? null : _submit,
                        child:
                            isLoading
                                ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                                : const Text('submit'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _MetadataSection extends StatelessWidget {
  final String route;
  final String appVersion;

  const _MetadataSection({required this.route, required this.appVersion});

  @override
  Widget build(BuildContext context) {
    final chips = <String>[
      if (route.isNotEmpty) route,
      if (appVersion.isNotEmpty) 'v$appVersion',
    ];

    if (chips.isEmpty) return const SizedBox.shrink();

    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children:
          chips
              .map(
                (label) => Chip(
                  label: Text(label, style: const TextStyle(fontSize: 12)),
                  visualDensity: VisualDensity.compact,
                ),
              )
              .toList(),
    );
  }
}
