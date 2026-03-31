import 'package:flutter/material.dart';

import '../widgets/app_scaffold.dart';
import '../widgets/editable_content_block.dart';

class DonateScreen extends StatelessWidget {
  const DonateScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const AppScaffold(
      maxWidth: 800,
      child: EditableContentBlock(slug: 'donate'),
    );
  }
}
