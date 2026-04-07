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
  late bool _showCost;

  @override
  void initState() {
    super.initState();
    _showCost = widget.initialShowCost;
  }

  @override
  void didUpdateWidget(EventFormLinksAndCostSection old) {
    super.didUpdateWidget(old);
    if (widget.initialShowCost && !old.initialShowCost) {
      _showCost = true;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(),
        const SizedBox(height: 8),
        Text('links', style: theme.textTheme.labelLarge),
        const SizedBox(height: 12),
        TextFormField(
          controller: widget.whatsappLink,
          decoration: const InputDecoration(
            labelText: 'whatsapp group link (optional)',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.chat_outlined),
          ),
          keyboardType: TextInputType.url,
          validator: (val) {
            if (val == null || val.trim().isEmpty) return null;
            final normalized = widget.normalizeUrl(val.trim());
            final uri = Uri.tryParse(normalized);
            if (uri == null || !uri.hasAuthority) return 'Enter a valid URL';
            final host = uri.host;
            final isWhatsApp =
                host.contains('whatsapp.com') ||
                host == 'wa.me' ||
                host == 'whats.app';
            if (!isWhatsApp) return 'Must be a WhatsApp link';
            return null;
          },
        ),
        const SizedBox(height: 12),
        TextFormField(
          controller: widget.partifulLink,
          decoration: InputDecoration(
            labelText: 'partiful link (optional)',
            border: const OutlineInputBorder(),
            prefixIcon: const Icon(Icons.celebration_outlined),
            helperText:
                widget.rsvpEnabled && widget.partifulLink.text.trim().isNotEmpty
                ? 'consider using app RSVPs instead of partiful'
                : null,
            helperStyle: TextStyle(color: theme.colorScheme.tertiary),
          ),
          keyboardType: TextInputType.url,
          validator: (val) {
            if (val == null || val.trim().isEmpty) return null;
            final normalized = widget.normalizeUrl(val.trim());
            final uri = Uri.tryParse(normalized);
            if (uri == null || !uri.hasAuthority) return 'Enter a valid URL';
            if (!uri.host.contains('partiful.com')) {
              return 'Must be a Partiful link (partiful.com/...)';
            }
            return null;
          },
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
        const SizedBox(height: 16),
        ..._buildCostSection(theme),
      ],
    );
  }

  List<Widget> _buildCostSection(ThemeData theme) {
    if (!_showCost) {
      return [
        const Divider(),
        Center(
          child: TextButton.icon(
            onPressed: () => setState(() => _showCost = true),
            icon: const Icon(Icons.attach_money, size: 18),
            label: const Text('add cost'),
          ),
        ),
      ];
    }
    return [
      Row(
        children: [
          Text(
            'cost & payment',
            style: theme.textTheme.labelLarge?.copyWith(
              color: theme.colorScheme.primary,
            ),
          ),
          const Spacer(),
          TextButton(
            onPressed: () {
              setState(() {
                _showCost = false;
                widget.price.clear();
                widget.venmoLink.clear();
                widget.cashappLink.clear();
                widget.zelleInfo.clear();
              });
            },
            child: const Text('remove'),
          ),
        ],
      ),
      const SizedBox(height: 4),
      Text(
        'costs should only cover shared orders or direct expenses — no fees or markups',
        style: TextStyle(
          fontSize: 12,
          color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
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
    ];
  }
}
