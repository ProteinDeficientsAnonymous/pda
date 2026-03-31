import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/chat_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:stream_chat_flutter/stream_chat_flutter.dart';

class ChatScreen extends ConsumerWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final clientAsync = ref.watch(streamClientProvider);

    return AppScaffold(
      child: clientAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => const Center(
          child: Text('couldn\'t load chat — try refreshing'),
        ),
        data: (client) {
          if (client == null) {
            return const Center(child: Text('sign in to use chat'));
          }
          return StreamChat(
            client: client,
            child: _ChannelList(client: client),
          );
        },
      ),
    );
  }
}

class _ChannelList extends StatelessWidget {
  const _ChannelList({required this.client});

  final StreamChatClient client;

  @override
  Widget build(BuildContext context) {
    return StreamChannelListView(
      controller: StreamChannelListController(
        client: client,
        filter: Filter.in_('members', [client.state.currentUser!.id]),
        channelStateSort: const [SortOption.desc('last_message_at')],
      ),
      onChannelTap: (channel) => context.push('/chat/${channel.id}'),
      emptyBuilder: (_) => const Center(
        child: Text('no conversations yet 🌿'),
      ),
    );
  }
}
