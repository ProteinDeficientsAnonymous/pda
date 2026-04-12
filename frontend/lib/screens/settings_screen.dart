import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/calendar_provider.dart'
    show calendarTokenProvider;
import 'package:pda/screens/settings_dialogs.dart';
import 'package:pda/screens/settings_profile_avatar.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/app_scaffold.dart';

final _log = Logger('Settings');

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).value;

    return AppScaffold(
      maxWidth: 600,
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          ..._buildProfileSection(context, ref, user),
          const SizedBox(height: 24),
          ..._buildSecuritySection(context, ref),
          const SizedBox(height: 24),
          ..._buildPrivacySection(context, ref, user),
          const SizedBox(height: 24),
          ..._buildCalendarSection(context, ref, user),
          const SizedBox(height: 24),
          ..._buildAccessibilitySection(context),
        ],
      ),
    );
  }

  List<Widget> _buildProfileSection(
    BuildContext context,
    WidgetRef ref,
    User? user,
  ) {
    final displayName = user?.displayName ?? '';
    final email = user?.email ?? '';
    return [
      SettingsProfileAvatar(
        initials: _initials(displayName, email),
        photoUrl: user?.profilePhotoUrl ?? '',
      ),
      const SizedBox(height: 32),
      const _SectionHeader(label: 'profile'),
      const SizedBox(height: 12),
      _SettingsTile(
        icon: Icons.face_outlined,
        label: 'name',
        value: displayName.trim().isEmpty ? 'not set' : displayName,
        onTap: () => _showEditNameDialog(context, ref, displayName),
      ),
      _SettingsTile(
        icon: Icons.phone_iphone_outlined,
        label: 'phone',
        value: user?.phoneNumber ?? '',
      ),
      _SettingsTile(
        icon: Icons.alternate_email_outlined,
        label: 'email',
        value: email.trim().isEmpty ? 'not set' : email,
        onTap: () => _showEditEmailDialog(context, ref, email),
      ),
    ];
  }

  List<Widget> _buildSecuritySection(BuildContext context, WidgetRef ref) {
    return [
      const _SectionHeader(label: 'security'),
      const SizedBox(height: 12),
      _SettingsTile(
        icon: Icons.key_outlined,
        label: 'change password',
        onTap: () => _showChangePasswordDialog(context, ref),
      ),
    ];
  }

  List<Widget> _buildPrivacySection(
    BuildContext context,
    WidgetRef ref,
    User? user,
  ) {
    return [
      const _SectionHeader(label: 'privacy'),
      const SizedBox(height: 4),
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(
          'only logged-in PDA members can see your profile',
          style: TextStyle(
            fontSize: 12,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
      _PrivacyToggle(
        icon: Icons.phone_outlined,
        label: 'show phone number on profile',
        value: user?.showPhone ?? true,
        onChanged: (val) =>
            ref.read(authProvider.notifier).updateProfile(showPhone: val),
      ),
      _PrivacyToggle(
        icon: Icons.email_outlined,
        label: 'show email on profile',
        value: user?.showEmail ?? true,
        onChanged: (val) =>
            ref.read(authProvider.notifier).updateProfile(showEmail: val),
      ),
    ];
  }

  List<Widget> _buildCalendarSection(
    BuildContext context,
    WidgetRef ref,
    User? user,
  ) {
    return [
      const _SectionHeader(label: 'calendar'),
      const SizedBox(height: 12),
      _SettingsTile(
        icon: Icons.event_outlined,
        label: 'subscribe to PDA calendar',
        value: 'get a personal link for Google Calendar, Apple Calendar, etc.',
        onTap: () => _handleCalendarSubscribe(context, ref),
      ),
      const SizedBox(height: 12),
      _WeekStartToggle(
        weekStart: user?.weekStart ?? 'sunday',
        onChanged: (val) =>
            ref.read(authProvider.notifier).updateProfile(weekStart: val),
      ),
    ];
  }

  List<Widget> _buildAccessibilitySection(BuildContext context) {
    return [
      const _SectionHeader(label: 'accessibility'),
      const SizedBox(height: 4),
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(
          'adjust text settings for easier reading',
          style: TextStyle(
            fontSize: 12,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
      const SettingsAccessibilitySection(),
    ];
  }

  String _initials(String displayName, String email) {
    if (displayName.isNotEmpty) {
      final parts = displayName.trim().split(RegExp(r'\s+'));
      final f = parts.first[0].toUpperCase();
      final l = parts.length > 1 ? parts.last[0].toUpperCase() : '';
      return '$f$l';
    }
    if (email.isNotEmpty) return email[0].toUpperCase();
    return '?';
  }

  Future<void> _showEditNameDialog(
    BuildContext context,
    WidgetRef ref,
    String? current,
  ) async {
    final result = await showDialog<String>(
      context: context,
      builder: (_) => SettingsEditFieldDialog(
        title: 'edit name',
        label: 'Display name',
        initialValue: current ?? '',
        keyboardType: TextInputType.name,
        validator: v.displayName(),
      ),
    );
    if (result == null || !context.mounted) return;
    try {
      await ref.read(authProvider.notifier).updateProfile(displayName: result);
      _log.info('name updated');
      if (context.mounted) {
        showSnackBar(context, 'name updated ✓');
      }
    } catch (e, st) {
      _log.warning('failed to update name', e, st);
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  Future<void> _showEditEmailDialog(
    BuildContext context,
    WidgetRef ref,
    String? current,
  ) async {
    final result = await showDialog<String>(
      context: context,
      builder: (_) => SettingsEditFieldDialog(
        title: 'edit email',
        label: 'Email address',
        initialValue: current ?? '',
        keyboardType: TextInputType.emailAddress,
        validator: v.optionalEmail(),
      ),
    );
    if (result == null || !context.mounted) return;
    try {
      await ref.read(authProvider.notifier).updateProfile(email: result);
      _log.info('email updated');
      if (context.mounted) {
        showSnackBar(context, 'email updated ✓');
      }
    } catch (e, st) {
      _log.warning('failed to update email', e, st);
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  Future<void> _handleCalendarSubscribe(
    BuildContext context,
    WidgetRef ref,
  ) async {
    try {
      final api = ref.read(apiClientProvider);
      final existingToken = await ref.read(calendarTokenProvider.future);
      String feedUrl;
      if (existingToken.isNotEmpty) {
        final resp = await api.get('/api/community/calendar/token/');
        final data = resp.data as Map<String, dynamic>;
        feedUrl = data['feed_url'] as String;
      } else {
        final resp = await api.post('/api/community/calendar/token/');
        final data = resp.data as Map<String, dynamic>;
        feedUrl = data['feed_url'] as String;
        ref.invalidate(calendarTokenProvider);
      }
      await Clipboard.setData(ClipboardData(text: feedUrl));
      _log.info('calendar feed URL copied');
      if (context.mounted) {
        showSnackBar(
          context,
          'calendar feed URL copied! paste it into your calendar app to subscribe',
        );
      }
    } catch (e, st) {
      _log.warning('failed to get calendar feed URL', e, st);
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  Future<void> _showChangePasswordDialog(
    BuildContext context,
    WidgetRef ref,
  ) async {
    await showDialog<void>(
      context: context,
      builder: (_) => SettingsChangePasswordDialog(ref: ref),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String label;

  const _SectionHeader({required this.label});

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: Theme.of(context).textTheme.labelLarge?.copyWith(
        color: Theme.of(context).colorScheme.primary,
      ),
    );
  }
}

class _PrivacyToggle extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _PrivacyToggle({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SwitchListTile(
      secondary: Icon(icon, size: 20),
      title: Text(label, style: const TextStyle(fontSize: 14)),
      value: value,
      contentPadding: EdgeInsets.zero,
      dense: true,
      onChanged: onChanged,
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? value;
  final VoidCallback? onTap;

  const _SettingsTile({
    required this.icon,
    required this.label,
    this.value,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          icon,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        title: Text(label),
        subtitle: value != null ? Text(value!) : null,
        trailing: onTap != null ? const Icon(Icons.chevron_right) : null,
        onTap: onTap,
      ),
    );
  }
}

class _WeekStartToggle extends StatelessWidget {
  final String weekStart;
  final ValueChanged<String> onChanged;

  const _WeekStartToggle({required this.weekStart, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(
          Icons.calendar_view_week_outlined,
          size: 20,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: 12),
        const Text('week starts on', style: TextStyle(fontSize: 14)),
        const Spacer(),
        SegmentedButton<String>(
          segments: const [
            ButtonSegment(value: 'sunday', label: Text('sunday')),
            ButtonSegment(value: 'monday', label: Text('monday')),
          ],
          selected: {weekStart},
          onSelectionChanged: (s) => onChanged(s.first),
          showSelectedIcon: false,
          style: const ButtonStyle(visualDensity: VisualDensity.compact),
        ),
      ],
    );
  }
}
