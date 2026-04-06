import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:pda/screens/calendar/event_form_field_sections.dart';

class EventFormPhotoSection extends StatelessWidget {
  final String existingPhotoUrl;
  final XFile? selectedPhoto;
  final bool removePhoto;
  final VoidCallback onPickPhoto;
  final VoidCallback onRemovePhoto;

  const EventFormPhotoSection({
    super.key,
    required this.existingPhotoUrl,
    required this.selectedPhoto,
    required this.removePhoto,
    required this.onPickPhoto,
    required this.onRemovePhoto,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final hasExisting = existingPhotoUrl.isNotEmpty && !removePhoto;
    final hasSelected = selectedPhoto != null;
    final hasPhoto = hasSelected || hasExisting;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Stack(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: hasSelected
                  ? FutureBuilder<List<int>>(
                      future: selectedPhoto!.readAsBytes(),
                      builder: (ctx, snap) {
                        if (!snap.hasData) {
                          return const SizedBox(
                            height: 160,
                            child: Center(child: CircularProgressIndicator()),
                          );
                        }
                        return Image.memory(
                          snap.data! as dynamic,
                          fit: BoxFit.contain,
                        );
                      },
                    )
                  : hasExisting
                  ? Image.network(existingPhotoUrl, fit: BoxFit.contain)
                  : InkWell(
                      onTap: onPickPhoto,
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        height: 130,
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: cs.surfaceContainerHighest.withValues(
                            alpha: 0.3,
                          ),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: cs.outline.withValues(alpha: 0.2),
                          ),
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.add_photo_alternate_outlined,
                              size: 32,
                              color: cs.onSurfaceVariant.withValues(alpha: 0.5),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'add a cover photo',
                              style: TextStyle(
                                fontSize: 13,
                                color: cs.onSurfaceVariant.withValues(
                                  alpha: 0.5,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
            ),
            if (hasPhoto)
              Positioned(
                top: 8,
                right: 8,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    EventFormPhotoButton(
                      tooltip: 'change photo',
                      icon: Icons.photo_outlined,
                      onPressed: onPickPhoto,
                    ),
                    const SizedBox(width: 4),
                    EventFormPhotoButton(
                      tooltip: 'remove photo',
                      icon: Icons.close,
                      onPressed: hasExisting && !hasSelected
                          ? () async {
                              final confirmed = await showDialog<bool>(
                                context: context,
                                builder: (_) => AlertDialog(
                                  title: const Text('remove photo'),
                                  content: const Text(
                                    'Remove the cover photo? This cannot be undone.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.of(context).pop(false),
                                      child: const Text('cancel'),
                                    ),
                                    FilledButton(
                                      onPressed: () =>
                                          Navigator.of(context).pop(true),
                                      child: const Text('remove'),
                                    ),
                                  ],
                                ),
                              );
                              if (confirmed == true) onRemovePhoto();
                            }
                          : onRemovePhoto,
                    ),
                  ],
                ),
              ),
          ],
        ),
        const SizedBox(height: 16),
      ],
    );
  }
}
