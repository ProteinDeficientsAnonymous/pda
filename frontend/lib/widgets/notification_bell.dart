import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/notification.dart';
import 'package:pda/providers/notification_provider.dart';

class NotificationBell extends ConsumerWidget {
  const NotificationBell({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final unreadAsync = ref.watch(unreadCountProvider);
    final count = unreadAsync.value ?? 0;

    return IconButton(
      tooltip: 'notifications',
      icon: Badge(
        isLabelVisible: count > 0,
        label: Text(count > 99 ? '99+' : '$count'),
        child: const Icon(Icons.notifications_outlined),
      ),
      onPressed: () => _showNotificationsSheet(context, ref),
    );
  }

  void _showNotificationsSheet(BuildContext context, WidgetRef ref) {
    // Refresh list whenever sheet opens
    ref.invalidate(notificationsProvider);

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _NotificationsSheet(),
    );
  }
}

class _NotificationsSheet extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(notificationsProvider);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'notifications',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  TextButton(
                    onPressed: () async {
                      await markAllNotificationsRead(ref);
                    },
                    child: const Text('mark all as read'),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            notificationsAsync.when(
              loading: () => const Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ),
              error: (_, __) => const Padding(
                padding: EdgeInsets.all(24),
                child: Text('couldn\'t load notifications — try again'),
              ),
              data: (notifications) => _NotificationList(
                notifications: notifications,
                onClose: () => Navigator.of(context).pop(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NotificationList extends ConsumerWidget {
  final List<AppNotification> notifications;
  final VoidCallback onClose;

  const _NotificationList({required this.notifications, required this.onClose});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (notifications.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 32),
        child: Center(child: Text('no notifications yet 🌿')),
      );
    }

    return ConstrainedBox(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.6,
      ),
      child: ListView.builder(
        shrinkWrap: true,
        itemCount: notifications.length,
        itemBuilder: (context, index) {
          final n = notifications[index];
          return _NotificationTile(
            notification: n,
            onTap: () async {
              await markNotificationRead(ref, n.id);
              if (!context.mounted) return;
              if ((n.notificationType == NotificationType.eventInvite ||
                      n.notificationType == NotificationType.cohostAdded) &&
                  n.eventId != null) {
                onClose();
                context.go('/events/${n.eventId}');
              } else if (n.notificationType == NotificationType.joinRequest) {
                onClose();
                context.go('/join-requests');
              } else if (n.notificationType ==
                  NotificationType.magicLinkRequest) {
                onClose();
                if (n.relatedUserId != null) {
                  context.go('/members/${n.relatedUserId}');
                } else {
                  context.go('/members');
                }
              }
            },
          );
        },
      ),
    );
  }
}

class _NotificationTile extends StatelessWidget {
  final AppNotification notification;
  final VoidCallback onTap;

  const _NotificationTile({required this.notification, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        notification.isRead
            ? Icons.notifications_none_outlined
            : Icons.notifications_active_outlined,
        color: notification.isRead
            ? Theme.of(context).colorScheme.onSurfaceVariant
            : Theme.of(context).colorScheme.primary,
      ),
      title: Text(
        notification.message,
        style: TextStyle(
          fontWeight: notification.isRead ? FontWeight.normal : FontWeight.bold,
        ),
      ),
      onTap: onTap,
    );
  }
}
