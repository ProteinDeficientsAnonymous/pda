import 'package:pda/providers/notification_provider.dart';

/// Overrides unreadCountProvider with a silent stream that never polls.
/// Include this in any widget/screen test that renders AppScaffold with an
/// authenticated user, to prevent pending timer failures.
final silentNotificationsOverride = unreadCountProvider.overrideWith(
  (ref) => const Stream<int>.empty(),
);
