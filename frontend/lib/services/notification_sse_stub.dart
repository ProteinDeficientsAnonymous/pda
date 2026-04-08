class NotificationSseClient {
  NotificationSseClient({
    required String token,
    required void Function() onNotification,
  });

  bool get isConnected => false;

  void close() {}
}
