import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/widgets/app_scaffold.dart';

void main() {
  testWidgets(
    'nav drawer has semanticLabel to avoid route warning on macOS/iOS',
    (tester) async {
      // Use narrow viewport so drawer is shown instead of wide nav
      tester.view.physicalSize = const Size(400, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final router = GoRouter(
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            name: 'home',
            builder: (_, __) => const AppScaffold(child: Placeholder()),
          ),
        ],
      );
      addTearDown(router.dispose);

      await tester.pumpWidget(
        ProviderScope(child: MaterialApp.router(routerConfig: router)),
      );

      // Open the drawer
      final scaffoldState = tester.state<ScaffoldState>(find.byType(Scaffold));
      scaffoldState.openDrawer();
      await tester.pumpAndSettle();

      final drawer = tester.widget<Drawer>(find.byType(Drawer));
      expect(
        drawer.semanticLabel,
        isNotNull,
        reason:
            'Drawer must have a semanticLabel to avoid '
            '"self-labelled route missing label" warning on macOS/iOS',
      );
      expect(drawer.semanticLabel, isNotEmpty);
    },
    variant: TargetPlatformVariant.only(TargetPlatform.macOS),
  );
}
