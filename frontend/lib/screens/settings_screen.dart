import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pda/providers/accessibility_preferences_provider.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/calendar_provider.dart'
    show calendarTokenProvider;
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/loading_button.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;
    final displayName = user?.displayName ?? '';
    final phone = user?.phoneNumber ?? '';
    final email = user?.email ?? '';
    final photoUrl = user?.profilePhotoUrl ?? '';
    final showPhone = user?.showPhone ?? true;
    final showEmail = user?.showEmail ?? true;

    return AppScaffold(
      maxWidth: 600,
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          _ProfileAvatar(
            initials: _initials(displayName, email),
            photoUrl: photoUrl,
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
            value: phone,
          ),
          _SettingsTile(
            icon: Icons.alternate_email_outlined,
            label: 'email',
            value: email.trim().isEmpty ? 'not set' : email,
            onTap: () => _showEditEmailDialog(context, ref, email),
          ),
          const SizedBox(height: 24),
          const _SectionHeader(label: 'security'),
          const SizedBox(height: 12),
          _SettingsTile(
            icon: Icons.key_outlined,
            label: 'change password',
            onTap: () => _showChangePasswordDialog(context, ref),
          ),
          const SizedBox(height: 24),
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
            value: showPhone,
            onChanged:
                (val) => ref
                    .read(authProvider.notifier)
                    .updateProfile(showPhone: val),
          ),
          _PrivacyToggle(
            icon: Icons.email_outlined,
            label: 'show email on profile',
            value: showEmail,
            onChanged:
                (val) => ref
                    .read(authProvider.notifier)
                    .updateProfile(showEmail: val),
          ),
          const SizedBox(height: 24),
          const _SectionHeader(label: 'calendar'),
          const SizedBox(height: 12),
          _SettingsTile(
            icon: Icons.event_outlined,
            label: 'subscribe to PDA calendar',
            value:
                'get a personal link for Google Calendar, Apple Calendar, etc.',
            onTap: () => _handleCalendarSubscribe(context, ref),
          ),
          const SizedBox(height: 24),
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
          _AccessibilitySection(),
        ],
      ),
    );
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
      builder:
          (_) => _EditFieldDialog(
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
      if (context.mounted) {
        showSnackBar(context, 'name updated ✓');
      }
    } catch (e) {
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
      builder:
          (_) => _EditFieldDialog(
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
      if (context.mounted) {
        showSnackBar(context, 'email updated ✓');
      }
    } catch (e) {
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
      if (context.mounted) {
        showSnackBar(
          context,
          'calendar feed URL copied! paste it into your calendar app to subscribe',
        );
      }
    } catch (e) {
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
      builder: (_) => _ChangePasswordDialog(ref: ref),
    );
  }
}

class _ProfileAvatar extends ConsumerStatefulWidget {
  final String initials;
  final String photoUrl;

  const _ProfileAvatar({required this.initials, required this.photoUrl});

  @override
  ConsumerState<_ProfileAvatar> createState() => _ProfileAvatarState();
}

class _ProfileAvatarState extends ConsumerState<_ProfileAvatar> {
  bool _uploading = false;

  Future<void> _pickAndUpload() async {
    final picker = ImagePicker();
    final image = await picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 512,
      maxHeight: 512,
      imageQuality: 80,
    );
    if (image == null) return;

    setState(() => _uploading = true);
    try {
      await ref.read(authProvider.notifier).uploadProfilePhoto(image);
      // Evict old cached image so the new one loads immediately.
      if (widget.photoUrl.isNotEmpty) {
        imageCache.evict(NetworkImage(widget.photoUrl));
      }
      if (mounted) showSnackBar(context, 'photo updated ✓');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t upload photo — try again');
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final hasPhoto = widget.photoUrl.isNotEmpty;

    return Center(
      child: Semantics(
        button: true,
        label: 'change profile photo',
        child: InkWell(
          onTap: _uploading ? null : _pickAndUpload,
          customBorder: const CircleBorder(),
          child: Stack(
            children: [
              if (hasPhoto)
                CircleAvatar(
                  radius: 48,
                  backgroundImage: NetworkImage(widget.photoUrl),
                )
              else
                CircleAvatar(
                  radius: 48,
                  backgroundColor: cs.primaryContainer,
                  child: Text(
                    widget.initials,
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: cs.onPrimaryContainer,
                    ),
                  ),
                ),
              Positioned(
                bottom: 0,
                right: 0,
                child: CircleAvatar(
                  radius: 16,
                  backgroundColor: cs.surface,
                  child:
                      _uploading
                          ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                          : Icon(
                            Icons.add_a_photo_outlined,
                            size: 16,
                            color: cs.onSurfaceVariant,
                          ),
                ),
              ),
            ],
          ),
        ),
      ),
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

class _EditFieldDialog extends StatefulWidget {
  final String title;
  final String label;
  final String initialValue;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;

  const _EditFieldDialog({
    required this.title,
    required this.label,
    required this.initialValue,
    this.keyboardType = TextInputType.text,
    this.validator,
  });

  @override
  State<_EditFieldDialog> createState() => _EditFieldDialogState();
}

class _EditFieldDialogState extends State<_EditFieldDialog> {
  late final TextEditingController _controller;
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialValue);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: Form(
        key: _formKey,
        child: TextFormField(
          controller: _controller,
          keyboardType: widget.keyboardType,
          autofocus: true,
          textInputAction: TextInputAction.done,
          decoration: InputDecoration(labelText: widget.label),
          validator: widget.validator,
          onFieldSubmitted: (_) {
            if (_formKey.currentState!.validate()) {
              Navigator.of(context).pop(_controller.text.trim());
            }
          },
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              Navigator.of(context).pop(_controller.text.trim());
            }
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}

class _AccessibilitySection extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefsAsync = ref.watch(accessibilityPreferencesNotifierProvider);
    final prefs = prefsAsync.valueOrNull;
    final dyslexiaOn = prefs?.dyslexiaFriendlyFont ?? false;
    final textScale = prefs?.textScaleFactor ?? 1.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _PrivacyToggle(
          icon: Icons.text_fields_outlined,
          label: 'dyslexia-friendly font',
          value: dyslexiaOn,
          onChanged: (_) {
            ref
                .read(accessibilityPreferencesNotifierProvider.notifier)
                .toggleDyslexiaFont();
          },
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            const Icon(Icons.format_size_outlined, size: 20),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('text size', style: TextStyle(fontSize: 14)),
                  const SizedBox(height: 8),
                  SegmentedButton<double>(
                    segments: const [
                      ButtonSegment(value: 1.0, label: Text('normal')),
                      ButtonSegment(value: 1.15, label: Text('medium')),
                      ButtonSegment(value: 1.3, label: Text('large')),
                    ],
                    selected: {textScale},
                    showSelectedIcon: false,
                    onSelectionChanged: (selection) {
                      ref
                          .read(
                            accessibilityPreferencesNotifierProvider.notifier,
                          )
                          .setTextScale(selection.first);
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ChangePasswordDialog extends StatefulWidget {
  final WidgetRef ref;

  const _ChangePasswordDialog({required this.ref});

  @override
  State<_ChangePasswordDialog> createState() => _ChangePasswordDialogState();
}

class _ChangePasswordDialogState extends State<_ChangePasswordDialog> {
  final _formKey = GlobalKey<FormState>();
  final _currentCtrl = TextEditingController();
  final _newCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  final _newFocus = FocusNode();
  final _confirmFocus = FocusNode();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    _confirmCtrl.dispose();
    _newFocus.dispose();
    _confirmFocus.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.ref
          .read(authProvider.notifier)
          .changePassword(
            currentPassword: _currentCtrl.text,
            newPassword: _newCtrl.text,
          );
      if (mounted) {
        Navigator.of(context).pop();
        showSnackBar(context, 'password updated ✓');
      }
    } catch (e) {
      setState(() {
        _error = ApiError.from(e).message;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('change password'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_error != null) ...[
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
              const SizedBox(height: 12),
            ],
            TextFormField(
              controller: _currentCtrl,
              obscureText: true,
              autofocus: true,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(labelText: 'Current password'),
              validator: (v) {
                if (v == null || v.isEmpty) return 'Required';
                return null;
              },
              onFieldSubmitted: (_) => _newFocus.requestFocus(),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _newCtrl,
              focusNode: _newFocus,
              obscureText: true,
              textInputAction: TextInputAction.next,
              decoration: const InputDecoration(labelText: 'New password'),
              validator: v.all([
                v.required(),
                (val) =>
                    (val != null && val.length < 8)
                        ? 'Must be at least 8 characters'
                        : null,
                (val) =>
                    (val != null && val.length > 128)
                        ? 'Max 128 characters'
                        : null,
                (val) =>
                    (val != null && val == _currentCtrl.text)
                        ? 'New password must differ from current'
                        : null,
              ]),
              onFieldSubmitted: (_) => _confirmFocus.requestFocus(),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _confirmCtrl,
              focusNode: _confirmFocus,
              obscureText: true,
              textInputAction: TextInputAction.done,
              decoration: const InputDecoration(
                labelText: 'Confirm new password',
              ),
              validator: (v) {
                if (v != _newCtrl.text) return 'Passwords do not match';
                return null;
              },
              onFieldSubmitted: (_) => _loading ? null : _submit(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _loading ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        LoadingButton(label: 'Update', onPressed: _submit, loading: _loading),
      ],
    );
  }
}
