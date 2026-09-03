import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/features/ledgerflow_shell.dart';
import 'package:ledgerflow_web/main.dart';

void main() {
  testWidgets('shows the disconnected shell everywhere without sample data', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(800, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const LedgerFlowApp());
    await tester.pumpAndSettle();

    void expectDisconnectedShell() {
      expect(find.byType(LedgerFlowShell), findsOneWidget);
      expect(find.byType(LedgerFlowLogo), findsWidgets);
      expect(
        find.byKey(const ValueKey('ledgerflow-application-scale')),
        findsNothing,
      );
      expect(find.text('Connect LedgerFlow'), findsOneWidget);
      expect(
        find.textContaining('No sample or cached records'),
        findsOneWidget,
      );
      expect(find.text('Connect API'), findsWidgets);
      expect(find.text('API connected'), findsNothing);
      expect(find.text('Charge operations'), findsNothing);
      expect(find.text('No quote requests are available.'), findsNothing);
      expect(find.text('No records are available.'), findsNothing);
      expect(find.text('No profiles are available.'), findsNothing);
      expect(find.text('No FX rates are available.'), findsNothing);
      expect(find.text('QR-2026-00814'), findsNothing);
      expect(find.text('CONTAINER_FLAT - Container flat rate'), findsNothing);
      expect(find.text('SHIPMENT -> HOUSE'), findsNothing);
      expect(find.text('GLOBAL: all'), findsNothing);
      expect(find.text('SHIPMENT_ACTUAL_DEPARTURE_DATE'), findsNothing);
    }

    expectDisconnectedShell();

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Quotes'));
    await tester.pumpAndSettle();
    expectDisconnectedShell();

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView).first, const Offset(0, -260));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Components'));
    await tester.pumpAndSettle();
    expectDisconnectedShell();

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView).first, const Offset(0, -280));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Profiles'));
    await tester.pumpAndSettle();
    expectDisconnectedShell();

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView).first, const Offset(0, -300));
    await tester.pumpAndSettle();
    await tester.tap(find.text('FX & dates'));
    await tester.pumpAndSettle();
    expectDisconnectedShell();
  });
}
