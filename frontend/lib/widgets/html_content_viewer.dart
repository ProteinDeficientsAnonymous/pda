import 'package:flutter/material.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';

/// Renders pre-rendered HTML content with minimal overhead.
///
/// Used in read-only mode for all rich-text content pages so that
/// flutter_quill is not loaded until an admin taps "edit".
class HtmlContentViewer extends StatelessWidget {
  const HtmlContentViewer({super.key, required this.html});

  final String html;

  @override
  Widget build(BuildContext context) {
    if (html.isEmpty) return const SizedBox.shrink();

    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.all(24),
      child: HtmlWidget(html, textStyle: theme.textTheme.bodyMedium),
    );
  }
}
