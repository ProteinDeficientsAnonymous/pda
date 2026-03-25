import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/router/app_router.dart';

void main() {
  runApp(const ProviderScope(child: PdaApp()));
}

class PdaApp extends ConsumerWidget {
  const PdaApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'Protein Deficients Anonymous',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2E7D32),
        ),
        useMaterial3: true,
      ),
      routerConfig: router,
    );
  }
}
