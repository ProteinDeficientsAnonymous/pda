import 'package:flutter/material.dart';

/// Generic wrapper that loads a deferred Dart library before building a screen.
///
/// Usage in GoRouter route builders:
/// ```dart
/// import 'package:pda/screens/foo_screen.dart' deferred as foo_screen;
///
/// builder: (_, __) => DeferredScreen(
///   loader: foo_screen.loadLibrary,
///   builder: () => const foo_screen.FooScreen(),
/// ),
/// ```
class DeferredScreen extends StatefulWidget {
  const DeferredScreen({
    super.key,
    required this.loader,
    required this.builder,
  });

  final Future<void> Function() loader;
  final Widget Function() builder;

  @override
  State<DeferredScreen> createState() => _DeferredScreenState();
}

class _DeferredScreenState extends State<DeferredScreen> {
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    widget.loader().then((_) {
      if (mounted) setState(() => _loaded = true);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    return widget.builder();
  }
}
