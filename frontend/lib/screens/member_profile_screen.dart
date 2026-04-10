import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/approval_credentials_dialog.dart';
import 'package:pda/widgets/profile_avatar.dart';

final _log = Logger('MemberProfile');

final _memberProfileProvider =
    FutureProvider.family<Map<String, dynamic>, String>((ref, userId) async {
      final api = ref.watch(apiClientProvider);
      final response = await api.get('/api/auth/users/$userId/profile/');
      return response.data as Map<String, dynamic>;
    });

class MemberProfileScreen extends ConsumerWidget {
  final String userId;

  const MemberProfileScreen({super.key, required this.userId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileAsync = ref.watch(_memberProfileProvider(userId));

    return AppScaffold(
      maxWidth: 600,
      child: profileAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(
          child: Text('couldn\'t load profile — try refreshing'),
        ),
        data: (data) => _ProfileBody(data: data, userId: userId),
      ),
    );
  }
}

class _ProfileBody extends ConsumerWidget {
  final Map<String, dynamic> data;
  final String userId;

  const _ProfileBody({required this.data, required this.userId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final name = (data['display_name'] as String?) ?? '';
    final phone = (data['phone_number'] as String?) ?? '';
    final email = (data['email'] as String?) ?? '';
    final photoUrl = (data['profile_photo_url'] as String?) ?? '';

    final user = ref.watch(authProvider).value;
    final canManageUsers = user?.hasPermission(Permission.manageUsers) ?? false;

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Center(child: ProfileAvatar(photoUrl: photoUrl, radius: 48)),
        const SizedBox(height: 16),
        Center(
          child: Text(
            name.isNotEmpty ? name : phone,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        const SizedBox(height: 32),
        if (phone.isNotEmpty)
          _InfoTile(
            icon: Icons.phone_outlined,
            label: 'phone',
            value: phone,
            copyable: true,
          ),
        if (email.isNotEmpty)
          _InfoTile(
            icon: Icons.email_outlined,
            label: 'email',
            value: email,
            copyable: true,
          ),
        if (phone.isEmpty && email.isEmpty)
          Center(
            child: Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'contact info is private',
                style: TextStyle(
                  fontSize: 13,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                ),
              ),
            ),
          ),
        if (canManageUsers) ...[
          const SizedBox(height: 32),
          _MagicLinkButton(userId: userId, phoneNumber: phone),
        ],
      ],
    );
  }
}

class _MagicLinkButton extends ConsumerStatefulWidget {
  final String userId;
  final String phoneNumber;

  const _MagicLinkButton({required this.userId, required this.phoneNumber});

  @override
  ConsumerState<_MagicLinkButton> createState() => _MagicLinkButtonState();
}

class _MagicLinkButtonState extends ConsumerState<_MagicLinkButton> {
  bool _loading = false;

  Future<void> _handleTap() async {
    setState(() => _loading = true);
    try {
      final notifier = ref.read(userManagementProvider.notifier);
      final token = await notifier.generateMagicLink(widget.userId);
      _log.info('generated magic link for user ${widget.userId}');
      if (!mounted) return;
      showDialog<void>(
        context: context,
        builder: (_) => ApprovalCredentialsDialog(
          title: 'magic sign-in link',
          magicLinkToken: token,
          phoneNumber: widget.phoneNumber,
        ),
      );
    } catch (e, st) {
      _log.warning('failed to generate magic link', e, st);
      if (!mounted) return;
      showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FilledButton.icon(
      onPressed: _loading ? null : _handleTap,
      icon: _loading
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.link),
      label: const Text('send magic link'),
    );
  }
}

class _InfoTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final bool copyable;

  const _InfoTile({
    required this.icon,
    required this.label,
    required this.value,
    this.copyable = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: theme.colorScheme.outline.withValues(alpha: 0.15),
          ),
        ),
        child: Row(
          children: [
            Icon(icon, size: 20, color: theme.colorScheme.onSurfaceVariant),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 11,
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(value, style: const TextStyle(fontSize: 15)),
                ],
              ),
            ),
            if (copyable)
              IconButton(
                icon: const Icon(Icons.content_copy_outlined, size: 16),
                tooltip: 'copy',
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: value));
                  showSnackBar(context, 'copied ✓');
                },
              ),
          ],
        ),
      ),
    );
  }
}
