import 'package:flutter/material.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/screens/calendar/event_form_collapsible_section.dart';
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
    if (val.trim().length > FieldLimit.url) {
      return 'Max ${FieldLimit.url} characters';
    }
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
    if (val.trim().length > FieldLimit.url) {
      return 'Max ${FieldLimit.url} characters';
    }
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
        const Divider(height: 40, thickness: 0.5),
        EventFormCollapsibleSection(
          title: 'links',
          initiallyExpanded: _linksExpanded,
          onExpansionChanged: (val) => setState(() => _linksExpanded = val),
          children: [
            const SizedBox(height: 4),
            TextFormField(
              controller: widget.whatsappLink,
              decoration: const InputDecoration(
                labelText: 'whatsapp group link (optional)',
                prefixIcon: Icon(Icons.chat_outlined),
              ),
              keyboardType: TextInputType.url,
              validator: _validateWhatsapp,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: widget.partifulLink,
              decoration: InputDecoration(
                labelText: 'partiful link (optional)',
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
            const SizedBox(height: 16),
            TextFormField(
              controller: widget.otherLink,
              decoration: const InputDecoration(
                labelText: 'other link (optional)',
                prefixIcon: Icon(Icons.link),
              ),
              keyboardType: TextInputType.url,
              validator: v.all([
                v.optionalUrl(httpsOnly: true),
                v.maxLength(FieldLimit.url),
              ]),
            ),
          ],
        ),
        const Divider(height: 40, thickness: 0.5),
        EventFormCollapsibleSection(
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
            Card(
              margin: EdgeInsets.zero,
              elevation: 0,
              color: theme.colorScheme.surfaceContainerHighest.withValues(
                alpha: 0.4,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.info_outline,
                          size: 16,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'costs should only cover shared orders or direct expenses — no fees or markups',
                            style: TextStyle(
                              fontSize: 12,
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: widget.price,
                      decoration: const InputDecoration(
                        labelText: 'cost',
                        hintText: 'e.g. \$5 for groceries',
                        prefixIcon: Icon(Icons.attach_money),
                      ),
                      validator: v.maxLength(FieldLimit.shortText),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: widget.venmoLink,
                      decoration: const InputDecoration(
                        labelText: 'venmo handle',
                        hintText: 'username',
                        prefixText: '@',
                      ),
                      validator: v.maxLength(FieldLimit.paymentHandle),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: widget.cashappLink,
                      decoration: const InputDecoration(
                        labelText: 'cash app handle',
                        hintText: 'username',
                        prefixText: r'$',
                      ),
                      validator: v.maxLength(FieldLimit.paymentHandle),
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: widget.zelleInfo,
                      decoration: const InputDecoration(
                        labelText: 'zelle (email or phone)',
                        prefixIcon: Icon(Icons.account_balance_outlined),
                      ),
                      validator: v.maxLength(FieldLimit.shortText),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const Divider(height: 40, thickness: 0.5),
      ],
    );
  }
}
