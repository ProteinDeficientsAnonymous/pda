import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:pda/models/join_request.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/join_request_management_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

const _filters = ['All', 'Pending', 'Approved', 'Rejected'];

class JoinRequestsScreen extends ConsumerStatefulWidget {
  const JoinRequestsScreen({super.key});

  @override
  ConsumerState<JoinRequestsScreen> createState() => _JoinRequestsScreenState();
}

class _JoinRequestsScreenState extends ConsumerState<JoinRequestsScreen> {
  String _selectedFilter = 'All';

  List<JoinRequest> _applyFilter(List<JoinRequest> requests) {
    if (_selectedFilter == 'All') return requests;
    return requests
        .where((r) => r.status.toLowerCase() == _selectedFilter.toLowerCase())
        .toList();
  }

  Future<void> _updateStatus(String id, String status) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.patch(
        '/api/community/join-requests/$id/',
        data: {'status': status},
      );
      ref.invalidate(joinRequestsProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Failed to update status: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final requestsAsync = ref.watch(joinRequestsProvider);

    return AppScaffold(
      title: 'Join Requests',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _FilterChips(
            selected: _selectedFilter,
            onSelected: (filter) => setState(() => _selectedFilter = filter),
          ),
          Expanded(
            child: requestsAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error:
                  (e, _) =>
                      Center(child: Text('Failed to load join requests: $e')),
              data: (requests) {
                final filtered = _applyFilter(requests);
                if (filtered.isEmpty) {
                  return const Center(
                    child: Padding(
                      padding: EdgeInsets.all(32),
                      child: Text(
                        'No join requests found.',
                        style: TextStyle(fontSize: 16, color: Colors.grey),
                      ),
                    ),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(24),
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder:
                      (context, index) => _JoinRequestCard(
                        request: filtered[index],
                        onApprove:
                            () => _updateStatus(filtered[index].id, 'approved'),
                        onReject:
                            () => _updateStatus(filtered[index].id, 'rejected'),
                      ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterChips extends StatelessWidget {
  final String selected;
  final ValueChanged<String> onSelected;

  const _FilterChips({required this.selected, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
      child: Wrap(
        spacing: 8,
        children:
            _filters.map((filter) {
              final isSelected = selected == filter;
              return FilterChip(
                label: Text(filter),
                selected: isSelected,
                onSelected: (_) => onSelected(filter),
              );
            }).toList(),
      ),
    );
  }
}

class _JoinRequestCard extends StatelessWidget {
  final JoinRequest request;
  final VoidCallback onApprove;
  final VoidCallback onReject;

  const _JoinRequestCard({
    required this.request,
    required this.onApprove,
    required this.onReject,
  });

  Color _statusColor(String status) {
    if (status == 'approved') return Colors.green;
    if (status == 'rejected') return Colors.red;
    return Colors.orange;
  }

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('MMM d, yyyy');
    final statusColor = _statusColor(request.status);

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    request.name,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                _StatusBadge(status: request.status, color: statusColor),
              ],
            ),
            const SizedBox(height: 4),
            Text(request.email, style: const TextStyle(color: Colors.grey)),
            if (request.pronouns.isNotEmpty) ...[
              const SizedBox(height: 2),
              Text(
                request.pronouns,
                style: const TextStyle(color: Colors.grey, fontSize: 13),
              ),
            ],
            const SizedBox(height: 12),
            _InfoRow(label: 'Why they want to join', value: request.whyJoin),
            const SizedBox(height: 6),
            _InfoRow(
              label: 'How they heard about us',
              value: request.howTheyHeard,
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Submitted ${dateFmt.format(request.submittedAt.toLocal())}',
                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                ),
                if (request.status == 'pending')
                  _ActionButtons(onApprove: onApprove, onReject: onReject),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  final String status;
  final Color color;

  const _StatusBadge({required this.status, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Text(
        status,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: Colors.grey,
          ),
        ),
        const SizedBox(height: 2),
        Text(value, style: const TextStyle(fontSize: 14, height: 1.4)),
      ],
    );
  }
}

class _ActionButtons extends StatelessWidget {
  final VoidCallback onApprove;
  final VoidCallback onReject;

  const _ActionButtons({required this.onApprove, required this.onReject});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        OutlinedButton(
          onPressed: onReject,
          style: OutlinedButton.styleFrom(
            foregroundColor: Colors.red,
            side: const BorderSide(color: Colors.red),
          ),
          child: const Text('Reject'),
        ),
        const SizedBox(width: 8),
        FilledButton(
          onPressed: onApprove,
          style: FilledButton.styleFrom(backgroundColor: Colors.green),
          child: const Text('Approve'),
        ),
      ],
    );
  }
}
