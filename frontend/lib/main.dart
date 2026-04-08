import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:mcp_toolkit/mcp_toolkit.dart';
import 'package:pda/config/app_theme.dart';
import 'package:pda/providers/accessibility_preferences_provider.dart';
import 'package:pda/router/app_router.dart';
import 'package:pda/services/app_logger.dart';
import 'package:pda/services/error_reporter.dart';
import 'package:pda/services/secure_storage.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  MCPToolkitBinding.instance
    ..initialize()
    ..initializeFlutterToolkit();
  setupLogging();
  final reporter = ErrorReporter(SecureStorageService());
  setupErrorHandlers(
    onError: (error, stackTrace) {
      reporter.report(error: error, stackTrace: stackTrace, context: 'global');
    },
  );
  usePathUrlStrategy();
  runApp(const ProviderScope(child: PdaApp()));
}

class PdaApp extends ConsumerWidget {
  const PdaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final prefsAsync = ref.watch(accessibilityPreferencesProvider);
    final prefs = prefsAsync.value;
    final dyslexiaMode = prefs?.dyslexiaFriendlyFont ?? false;
    final textScaleFactor = prefs?.textScaleFactor ?? 1.0;

    return MaterialApp.router(
      title: 'protein deficients anonymous',
      theme: buildAppTheme(dyslexiaMode: dyslexiaMode),
      routerConfig: router,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [Locale('en')],
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(
            context,
          ).copyWith(textScaler: TextScaler.linear(textScaleFactor)),
          child: child!,
        );
      },
    );
  }
}
