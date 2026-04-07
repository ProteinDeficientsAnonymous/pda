import 'package:flutter/material.dart';
import 'package:pda/utils/validators.dart' as v;

class EventFormLinksAndCostSection extends StatefulWidget {
  final TextEditingController whatsappLink;
  final TextEditingController partifulLink;
  final TextEditingController otherLink;
  final TextEditingController price;
  final TextEditingController venmoLink;
  final TextEditingController cashappLink;
  final TextEditingController zelleInfo;
  final bool rsvpEnabled;
  final bool initialShowCost;
  final String Function(String) normalizeUrl;

  const EventFormLinksAndCostSection({
    super.key,
    required this.whatsappLink,
    required this.partifulLink,
    required this.otherLink,
    required this.price,
    required this.venmoLink,
    required this.cashappLink,
    required this.zelleInfo,
    required this.rsvpEnabled,
    required this.initialShowCost,
    required this.normalizeUrl,
  });

  @override
  State<EventFormLinksAndCostSection> createState() =>
      _EventFormLinksAndCostSectionState();
}

class _EventFormLinksAndCostSectionState
    extends State<EventFormLinksAndCostSection> {
  bool _linksExpanded = false;
  bool _costExpanded = false;

  @override
  void initState() {
    super.initState();
    _linksExpanded = _hasAnyLink();
    _costExpanded = widget.initialShowCost;
  }

  @override
  void didUpdateWidget(EventFormLinksAndCostSection old) {
    super.didUpdateWidget(old);
    if (widget.initialShowCost && !old.initialShowCost) {
      _costExpanded = true;
    }
  }

  bool _hasAnyLink() =>
      widget.whatsappLink.text.isNotEmpty ||
      widget.partifulLink.text.isNotEmpty ||
      widget.otherLink.text.isNotEmpty;

  String? _validateWhatsapp(String? val) {
    if (val == null || val.trim().isEmpty) return null;
    final normalized = widget.normalizeUrl(val.trim());
    final uri = Uri.tryParse(normalized);
    if (uri == null || !uri.hasAuthority) return 'Enter a valid URL';
    final host = uri.host;
    final isWhatsApp =
        host.contains('whatsapp.com') || host == 'wa.me' || host == 'whats.app';
    if (!isWhatsApp) return 'Must be a WhatsApp link';
    return null;
  }

  String? _validatePartiful(String? val) {
    if (val == null || val.trim().isEmpty) return null;
    final normalized = widget.normalizeUrl(val.trim());
    final uri = Uri.tryParse(normalized);
    if (uri == null || !uri.hasAuthority) return 'Enter a valid URL';
    if (!uri.host.contains('partiful.com')) {
      return 'Must be a Partiful link (partiful.com/...)';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(),
        _CollapsibleSection(
          title: 'links',
          initiallyExpanded: _linksExpanded,
          onExpansionChanged: (val) => setState(() => _linksExpanded = val),
          children: [
            const SizedBox(height: 4),
            TextFormField(
              controller: widget.whatsappLink,
              decoration: const InputDecoration(
                labelText: 'whatsapp group link (optional)',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.chat_outlined),
              ),
              keyboardType: TextInputType.url,
              validator: _validateWhatsapp,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: widget.partifulLink,
              decoration: InputDecoration(
                labelText: 'partiful link (optional)',
                border: const OutlineInputBorder(),
                prefixIcon: const Icon(Icons.celebration_outlined),
                helperText:
                    widget.rsvpEnabled &&
                        widget.partifulLink.text.trim().isNotEmpty
                    ? 'consider using app RSVPs instead of partiful'
                    : null,
                helperStyle: TextStyle(color: theme.colorScheme.tertiary),
              ),
              keyboardType: TextInputType.url,
              validator: _validatePartiful,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: widget.otherLink,
              decoration: const InputDecoration(
                labelText: 'other link (optional)',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.link),
              ),
              keyboardType: TextInputType.url,
              validator: v.optionalUrl(httpsOnly: true),
            ),
          ],
        ),
        const Divider(),
        _CollapsibleSection(
          title: 'cost & payment',
          initiallyExpanded: _costExpanded,
          onExpansionChanged: (val) {
            setState(() => _costExpanded = val);
            if (!val) {
              widget.price.clear();
              widget.venmoLink.clear();
              widget.cashappLink.clear();
              widget.zelleInfo.clear();
            }
          },
          children: [
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: theme.colorScheme.secondaryContainer.withValues(
                  alpha: 0.4,
                ),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.info_outline,
                    size: 16,
                    color: theme.colorScheme.onSecondaryContainer,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'costs should only cover shared orders or direct expenses — no fees or markups',
                      style: TextStyle(
                        fontSize: 12,
                        color: theme.colorScheme.onSecondaryContainer,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: widget.price,
              decoration: const InputDecoration(
                labelText: 'cost',
                hintText: 'e.g. \$5 for groceries',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.attach_money),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: widget.venmoLink,
              decoration: const InputDecoration(
                labelText: 'venmo handle',
                hintText: 'username',
                border: OutlineInputBorder(),
                prefixText: '@',
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: widget.cashappLink,
              decoration: const InputDecoration(
                labelText: 'cash app handle',
                hintText: 'username',
                border: OutlineInputBorder(),
                prefixText: r'$',
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: widget.zelleInfo,
              decoration: const InputDecoration(
                labelText: 'zelle (email or phone)',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.account_balance_outlined),
              ),
            ),
          ],
        ),
        const Divider(),
      ],
    );
  }
}

class _CollapsibleSection extends StatefulWidget {
  final String title;
  final bool initiallyExpanded;
  final ValueChanged<bool> onExpansionChanged;
  final List<Widget> children;

  const _CollapsibleSection({
    required this.title,
    required this.initiallyExpanded,
    required this.onExpansionChanged,
    required this.children,
  });

  @override
  State<_CollapsibleSection> createState() => _CollapsibleSectionState();
}

class _CollapsibleSectionState extends State<_CollapsibleSection> {
  late bool _expanded;

  @override
  void initState() {
    super.initState();
    _expanded = widget.initiallyExpanded;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
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
                Icon(
                  _expanded ? Icons.expand_less : Icons.expand_more,
                  size: 20,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ],
            ),
          ),
        ),
        if (_expanded) ...[...widget.children, const SizedBox(height: 8)],
      ],
    );
  }
}
