import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('WhatsAppConfig');

class WhatsAppConfig {
  final String botUrl;
  final String groupId;
  final bool hasSecret;

  const WhatsAppConfig({
    required this.botUrl,
    required this.groupId,
    required this.hasSecret,
  });

  factory WhatsAppConfig.fromJson(Map<String, dynamic> json) => WhatsAppConfig(
    botUrl: json['bot_url'] as String? ?? '',
    groupId: json['group_id'] as String? ?? '',
    hasSecret: json['has_secret'] as bool? ?? false,
  );
}

class WhatsAppConfigNotifier extends AsyncNotifier<WhatsAppConfig> {
  @override
  Future<WhatsAppConfig> build() async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/whatsapp/config/');
    return WhatsAppConfig.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> save({
    String? botUrl,
    String? botSecret,
    String? groupId,
  }) async {
    final api = ref.read(apiClientProvider);
    final data = <String, dynamic>{};
    if (botUrl != null) data['bot_url'] = botUrl;
    if (botSecret != null) data['bot_secret'] = botSecret;
    if (groupId != null) data['group_id'] = groupId;
    try {
      final response = await api.patch(
        '/api/community/whatsapp/config/',
        data: data,
      );
      state = AsyncData(
        WhatsAppConfig.fromJson(response.data as Map<String, dynamic>),
      );
      _log.info('saved whatsapp config');
    } catch (e, st) {
      _log.warning('failed to save whatsapp config', e, st);
      rethrow;
    }
  }
}

final whatsAppConfigProvider =
    AsyncNotifierProvider<WhatsAppConfigNotifier, WhatsAppConfig>(
      WhatsAppConfigNotifier.new,
    );

/// Fetches bot connection status. Auto-disposes so each visit re-checks.
final whatsAppStatusProvider = FutureProvider.autoDispose<bool>((ref) async {
  final api = ref.read(apiClientProvider);
  final response = await api.get('/api/community/whatsapp/status/');
  return (response.data as Map<String, dynamic>)['connected'] as bool? ?? false;
});
