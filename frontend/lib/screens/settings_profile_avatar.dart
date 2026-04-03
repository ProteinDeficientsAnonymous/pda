import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/photo_crop_dialog.dart';

class SettingsProfileAvatar extends ConsumerStatefulWidget {
  final String initials;
  final String photoUrl;

  const SettingsProfileAvatar({
    super.key,
    required this.initials,
    required this.photoUrl,
  });

  @override
  ConsumerState<SettingsProfileAvatar> createState() =>
      _SettingsProfileAvatarState();
}

class _SettingsProfileAvatarState extends ConsumerState<SettingsProfileAvatar> {
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

    final rawBytes = await image.readAsBytes();
    if (!mounted) return;
    final croppedBytes = await showPhotoCropDialog(
      context: context,
      imageBytes: rawBytes,
    );
    if (croppedBytes == null) return;

    final croppedFile = XFile.fromData(
      croppedBytes,
      name: image.name,
      mimeType: image.mimeType,
    );

    setState(() => _uploading = true);
    try {
      await ref.read(authProvider.notifier).uploadProfilePhoto(croppedFile);
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
