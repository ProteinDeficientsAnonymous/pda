import 'package:flutter/material.dart';
import 'package:pda/widgets/app_scaffold.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const AppScaffold(
      title: 'Settings',
      child: Center(child: Text('Settings coming soon.')),
    );
  }
}
