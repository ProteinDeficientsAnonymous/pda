import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/chat_provider.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

class ChatChannelScreen extends ConsumerWidget {
  const ChatChannelScreen({required this.channelId, super.key});

  final String channelId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final clientAsync = ref.watch(streamClientProvider);

    return clientAsync.when(
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => const Scaffold(
        body: Center(child: Text('couldn\'t load chat — try refreshing')),
      ),
      data: (client) {
        if (client == null) {
          return const Scaffold(
            body: Center(child: Text('sign in to use chat')),
          );
        }
        final channel = client.channel('messaging', id: channelId);
        return StreamChat(
          client: client,
          child: StreamChannel(
            channel: channel,
            child: const _ChannelView(),
          ),
        );
      },
    );
  }
}

class _ChannelView extends StatelessWidget {
  const _ChannelView();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const StreamChannelHeader(),
      body: Column(
        children: [
          Expanded(
            child: StreamMessageListView(
              onMessageTap: (message) {},
            ),
          ),
          const StreamMessageInput(),
        ],
      ),
    );
  }
}
