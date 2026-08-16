import 'package:flutter/material.dart';

import 'core/design.dart';
import 'features/ledgerflow_shell.dart';

void main() {
  final configuredScale = double.tryParse(
    const String.fromEnvironment('LEDGERFLOW_UI_SCALE', defaultValue: '1.0'),
  );
  runApp(LedgerFlowApp(scale: configuredScale ?? 1.0));
}

class LedgerFlowApp extends StatelessWidget {
  const LedgerFlowApp({this.scale = 1.0, super.key}) : assert(scale > 0);

  final double scale;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'LedgerFlow',
      debugShowCheckedModeBanner: false,
      theme: LedgerFlowDesign.theme,
      builder: (context, child) => _ScaledApplicationViewport(
        scale: scale,
        child: child ?? const SizedBox.shrink(),
      ),
      home: const LedgerFlowShell(),
    );
  }
}

class _ScaledApplicationViewport extends StatelessWidget {
  const _ScaledApplicationViewport({required this.scale, required this.child});

  final double scale;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (scale == 1) return child;
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth / scale;
        final height = constraints.maxHeight / scale;
        return ClipRect(
          child: OverflowBox(
            alignment: Alignment.topLeft,
            minWidth: width,
            maxWidth: width,
            minHeight: height,
            maxHeight: height,
            child: Transform.scale(
              key: const ValueKey('ledgerflow-application-scale'),
              scale: scale,
              alignment: Alignment.topLeft,
              child: SizedBox(width: width, height: height, child: child),
            ),
          ),
        );
      },
    );
  }
}
