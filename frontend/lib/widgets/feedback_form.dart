import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/feedback_provider.dart';

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
  final List<FeedbackAttachment> _attachments = [];
  bool _submitted = false;

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  Future<void> _pickFiles() async {
    final result = await FilePicker.platform.pickFiles(
      allowMultiple: true,
      type: FileType.custom,
      allowedExtensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt'],
      withData: true,
    );
    if (result == null) return;

    for (final file in result.files) {
      if (_attachments.length >= 5) break;
      if (file.bytes == null) continue;
      if (file.bytes!.lengthInBytes > 5 * 1024 * 1024) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text("'${file.name}' is too large — max 5MB per file"),
            ),
          );
        }
        continue;
      }

      setState(() {
        _attachments.add(
          FeedbackAttachment(
            filename: file.name,
            contentType: _contentType(file.extension ?? ''),
            base64Data: base64Encode(file.bytes!),
          ),
        );
      });
    }
  }

  String _contentType(String ext) {
    return switch (ext.toLowerCase()) {
      'png' => 'image/png',
      'jpg' || 'jpeg' => 'image/jpeg',
      'gif' => 'image/gif',
      'webp' => 'image/webp',
      'pdf' => 'application/pdf',
      'txt' => 'text/plain',
      _ => 'application/octet-stream',
    };
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
            currentRoute: widget.currentRoute,
            userAgent: widget.userAgent,
            userDisplayName: user?.displayName ?? '',
            userPhone: user?.phoneNumber ?? '',
            appVersion: widget.appVersion,
            attachments: _attachments,
          ),
        );

    if (!mounted) return;

    final state = ref.read(feedbackProvider);
    if (state.hasError) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("couldn't submit feedback — try again")),
      );
    } else {
      setState(() => _submitted = true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = ref.watch(feedbackProvider).isLoading;
    final isWide = MediaQuery.sizeOf(context).width >= 500;

    if (_submitted) {
      return _SuccessView(onClose: widget.onClose);
    }

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
                  const SizedBox(height: 16),
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
                    appVersion: widget.appVersion,
                  ),
                  const SizedBox(height: 12),
                  _AttachmentsSection(
                    attachments: _attachments,
                    onPick: _pickFiles,
                    onRemove: (i) => setState(() => _attachments.removeAt(i)),
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

class _AttachmentsSection extends StatelessWidget {
  final List<FeedbackAttachment> attachments;
  final VoidCallback onPick;
  final void Function(int) onRemove;

  const _AttachmentsSection({
    required this.attachments,
    required this.onPick,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (attachments.isNotEmpty) ...[
          for (var i = 0; i < attachments.length; i++)
            ListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.attach_file, size: 18),
              title: Text(
                attachments[i].filename,
                style: const TextStyle(fontSize: 13),
              ),
              trailing: IconButton(
                icon: const Icon(Icons.close, size: 18),
                tooltip: 'Remove ${attachments[i].filename}',
                onPressed: () => onRemove(i),
              ),
            ),
          const SizedBox(height: 4),
        ],
        if (attachments.length < 5)
          TextButton.icon(
            onPressed: onPick,
            icon: const Icon(Icons.add_photo_alternate_outlined, size: 18),
            label: const Text('add screenshots or files'),
          ),
      ],
    );
  }
}

class _SuccessView extends StatelessWidget {
  final VoidCallback onClose;

  const _SuccessView({required this.onClose});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 420,
      child: Card(
        margin: const EdgeInsets.all(16),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('feedback submitted — thanks! 🌱'),
              const SizedBox(height: 16),
              TextButton(onPressed: onClose, child: const Text('close')),
            ],
          ),
        ),
      ),
    );
  }
}
