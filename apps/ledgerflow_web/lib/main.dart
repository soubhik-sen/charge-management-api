import 'package:flutter/material.dart';

import 'core/design.dart';
import 'features/ledgerflow_shell.dart';

void main() {
  runApp(const LedgerFlowApp());
}

class LedgerFlowApp extends StatelessWidget {
  const LedgerFlowApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LedgerFlow',
      debugShowCheckedModeBanner: false,
      theme: LedgerFlowDesign.theme,
      home: const LedgerFlowShell(),
    );
  }
}
