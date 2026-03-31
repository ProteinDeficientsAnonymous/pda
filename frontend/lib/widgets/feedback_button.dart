import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/feedback_provider.dart';
import 'package:pda/widgets/feedback_form.dart';

class FeedbackButton extends ConsumerStatefulWidget {
  final String currentRoute;
  final String userAgent;
  final String appVersion;

  const FeedbackButton({
    super.key,
    required this.currentRoute,
    this.userAgent = '',
    this.appVersion = '',
  });

  @override
  ConsumerState<FeedbackButton> createState() => _FeedbackButtonState();
}

class _FeedbackButtonState extends ConsumerState<FeedbackButton> {
  bool _isOpen = false;
  bool _wasLoading = false;

  @override
  Widget build(BuildContext context) {
    ref.listen(feedbackProvider, (previous, next) {
      if (_wasLoading && next.hasValue && !next.isLoading) {
        setState(() => _isOpen = false);
        final messenger = ScaffoldMessenger.of(context);
        messenger.showSnackBar(
          SnackBar(
            content: GestureDetector(
              onTap: messenger.hideCurrentSnackBar,
              child: const Text('feedback submitted — thanks! 🌱'),
            ),
            duration: const Duration(seconds: 2),
          ),
        );
      }
      _wasLoading = next.isLoading;
    });

    return Stack(
      children: [
        if (_isOpen) ...[
          Positioned.fill(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: () => setState(() => _isOpen = false),
              child: ColoredBox(color: Colors.black.withValues(alpha: 0.3)),
            ),
          ),
          Positioned(
            bottom: 80,
            right: 16,
            child: FeedbackForm(
              currentRoute: widget.currentRoute,
              userAgent: widget.userAgent,
              appVersion: widget.appVersion,
              onClose: () => setState(() => _isOpen = false),
            ),
          ),
        ],
        Positioned(
          bottom: 16,
          right: 16,
          child: FloatingActionButton.small(
            tooltip: 'Submit feedback',
            onPressed: () => setState(() => _isOpen = !_isOpen),
            child: const Icon(Icons.help_outline),
          ),
        ),
      ],
    );
  }
}
