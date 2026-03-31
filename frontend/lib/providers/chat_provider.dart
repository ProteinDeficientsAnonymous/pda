import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/user.dart' as pda;
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_client.dart' show apiClientProvider;
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

/// Holds the connected [StreamChatClient] or null if chat is unavailable.
final streamClientProvider = AsyncNotifierProvider<StreamClientNotifier, StreamChatClient?>(
  StreamClientNotifier.new,
);

class StreamClientNotifier extends AsyncNotifier<StreamChatClient?> {
  @override
  Future<StreamChatClient?> build() async {
    final pda.User? pdaUser = ref.watch(authProvider).valueOrNull;
    if (pdaUser == null) return null;

    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/chat/token/');
    final data = response.data as Map<String, dynamic>;

    final apiKey = data['api_key'] as String;
    final token = data['token'] as String;
    final userId = data['user_id'] as String;
    final displayName = pdaUser.displayName.isNotEmpty
        ? pdaUser.displayName
        : pdaUser.phoneNumber;

    final client = StreamChatClient(apiKey, logLevel: Level.WARNING);
    await client.connectUser(
      User(id: userId, extraData: {'name': displayName}),
      token,
    );

    ref.onDispose(() {
      client.disconnectUser();
      client.dispose();
    });

    return client;
  }
}
