import 'package:flutter/material.dart';

class EventFormCollapsibleSection extends StatefulWidget {
  final String title;
  final bool initiallyExpanded;
  final ValueChanged<bool> onExpansionChanged;
  final List<Widget> children;

  const EventFormCollapsibleSection({
    super.key,
    required this.title,
    required this.initiallyExpanded,
    required this.onExpansionChanged,
    required this.children,
  });

  @override
  State<EventFormCollapsibleSection> createState() =>
      _EventFormCollapsibleSectionState();
}

class _EventFormCollapsibleSectionState
    extends State<EventFormCollapsibleSection> {
  late bool _expanded;

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(left: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            onTap: () {
              setState(() => _expanded = !_expanded);
              widget.onExpansionChanged(_expanded);
            },
            borderRadius: BorderRadius.circular(4),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(
                children: [
                  Text(widget.title, style: theme.textTheme.labelLarge),
                  const Spacer(),
                  Padding(
                    padding: const EdgeInsets.only(right: 12),
                    child: Text(
                      _expanded ? '×' : '–',
                      style: theme.textTheme.titleMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (_expanded) ...[...widget.children, const SizedBox(height: 8)],
        ],
      ),
    );
  }
}
