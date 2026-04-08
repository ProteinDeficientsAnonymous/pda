import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class BulkAddForm extends StatelessWidget {
  final TextEditingController controller;
  final VoidCallback onChanged;

  const BulkAddForm({
    super.key,
    required this.controller,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'One phone number per line. Members will be prompted to set a display name and password on first login.',
          style: TextStyle(fontSize: 13, color: Colors.grey),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: controller,
          maxLines: 8,
          onChanged: (_) => onChanged(),
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: '+12125551234\n+13105559876\n…',
            alignLabelWithHint: true,
          ),
          style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
        ),
      ],
    );
  }
}

class BulkAddResults extends StatelessWidget {
  final Map<String, dynamic> results;

  const BulkAddResults({super.key, required this.results});

  @override
  Widget build(BuildContext context) {
    final rows = (results['results'] as List).cast<Map<String, dynamic>>();
    final created = results['created'] as int;
    final failed = results['failed'] as int;
    final origin = Uri.base.origin;

    return SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$created created${failed > 0 ? ', $failed failed' : ''}',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: failed > 0
                  ? Theme.of(context).colorScheme.error
                  : Theme.of(context).colorScheme.primary,
            ),
          ),
          if (created > 0) ...[
            const SizedBox(height: 12),
            const Text('Login links (share with each new member):'),
            const SizedBox(height: 6),
            ...rows
                .where(
                  (r) => r['success'] == true && r['magic_link_token'] != null,
                )
                .map(
                  (r) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: MagicLinkRow(
                      phone: r['phone_number'] as String,
                      url: '$origin/magic-login/${r['magic_link_token']}',
                    ),
                  ),
                ),
          ],
          if (failed > 0) ...[
            const SizedBox(height: 12),
            const Text(
              'Errors:',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            ...rows
                .where((r) => r['success'] == false)
                .map(
                  (r) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text(
                      'Row ${r['row']}: ${r['phone_number']} — ${r['error']}',
                      style: TextStyle(
                        fontSize: 13,
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}

class MagicLinkRow extends StatelessWidget {
  final String phone;
  final String url;

  const MagicLinkRow({super.key, required this.phone, required this.url});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(phone, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        const SizedBox(height: 2),
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade300),
            borderRadius: BorderRadius.circular(6),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  url,
                  style: const TextStyle(fontSize: 11, fontFamily: 'monospace'),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 6),
              InkWell(
                onTap: () => Clipboard.setData(ClipboardData(text: url)),
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.all(4),
                  child: Icon(
                    Icons.content_copy_outlined,
                    size: 14,
                    color: Colors.grey.shade600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
