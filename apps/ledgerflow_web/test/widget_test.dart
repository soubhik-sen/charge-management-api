import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ledgerflow_web/features/ledgerflow_shell.dart';
import 'package:ledgerflow_web/main.dart';

void main() {
  testWidgets('opens the compact demo workspace and navigates to quotes', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(800, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const LedgerFlowApp());
    await tester.pumpAndSettle();

    expect(find.byType(LedgerFlowShell), findsOneWidget);
    expect(find.text('Charge operations'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Quotes'));
    await tester.pumpAndSettle();

    expect(find.text('QR-2026-00814'), findsWidgets);
    expect(find.text('Ranked options'), findsOneWidget);
  });
}
