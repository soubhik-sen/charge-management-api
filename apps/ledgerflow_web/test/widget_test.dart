import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ledgerflow_web/core/design.dart';
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
    expect(find.byType(LedgerFlowLogo), findsWidgets);
    final applicationScale = tester.widget<Transform>(
      find.byKey(const ValueKey('ledgerflow-application-scale')),
    );
    expect(applicationScale.transform.storage.first, closeTo(0.8, 0.001));
    expect(find.text('Charge operations'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Quotes'));
    await tester.pumpAndSettle();

    expect(find.text('QR-2026-00814'), findsWidgets);
    expect(find.text('Ranked options'), findsOneWidget);
  });

  testWidgets('shows component maintenance and protects demo writes', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(800, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const LedgerFlowApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView).first, const Offset(0, -260));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Components'));
    await tester.pumpAndSettle();

    expect(find.text('What a component controls'), findsOneWidget);
    expect(find.text('Default profile usage'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('component-row-1')));
    await tester.pumpAndSettle();
    expect(find.text('Default profile usage'), findsOneWidget);
    expect(find.text('CONTAINER_FLAT - Container flat rate'), findsOneWidget);
    final create = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'New component'),
    );
    expect(create.onPressed, isNull);
  });

  testWidgets('shows versioned calculation and allocation management', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(800, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const LedgerFlowApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView).first, const Offset(0, -280));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Profiles'));
    await tester.pumpAndSettle();

    expect(find.text('How calculation profiles are used'), findsOneWidget);
    expect(find.text('Version history'), findsOneWidget);
    expect(find.text('CONTAINER_COUNT - CONTAINER_COUNT'), findsOneWidget);

    await tester.tap(find.text('Allocation'));
    await tester.pumpAndSettle();
    expect(find.text('How allocation profiles are used'), findsOneWidget);
    expect(find.text('SHIPMENT -> HOUSE'), findsOneWidget);
  });

  testWidgets('shows business-date steps and assignment usage', (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const LedgerFlowApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(ListView).first, const Offset(0, -300));
    await tester.pumpAndSettle();
    await tester.tap(find.text('FX & dates'));
    await tester.pumpAndSettle();

    expect(find.text('How business-date profiles are used'), findsOneWidget);
    expect(find.text('Assignment scopes'), findsOneWidget);
    expect(find.text('GLOBAL: all'), findsOneWidget);
    expect(find.text('SHIPMENT_ACTUAL_DEPARTURE_DATE'), findsOneWidget);
  });
}
