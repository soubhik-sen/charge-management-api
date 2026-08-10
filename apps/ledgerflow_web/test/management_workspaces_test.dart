import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/data/workspace_data.dart';
import 'package:ledgerflow_web/features/management_workspaces.dart';

void main() {
  testWidgets('creates a component through the public API callback', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1300, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    JsonMap? captured;
    String? capturedPath;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: ComponentManagementWorkspace(
          records: const [],
          calculationProfiles: const [],
          allocationProfiles: const [],
          businessDateProfiles: const [],
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async {
                capturedPath = path;
                captured = body;
                return true;
              },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('New component'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Component code'),
      'SECURITY',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Component name'),
      'Security fee',
    );
    await tester.tap(find.text('Save component'));
    await tester.pumpAndSettle();

    expect(capturedPath, '/api/v1/charge-management/components');
    expect(captured?['component_code'], 'SECURITY');
    expect(captured?['business_date_policy_mode'], 'LEGACY_BASIS');
    expect(captured?['business_date_profile_id'], isNull);
  });

  testWidgets('expands a component row inline and exposes edit', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: ComponentManagementWorkspace(
          records: const [
            {
              'id': 7,
              'component_code': 'DROP_OFF',
              'component_name': 'Drop Off',
              'category': 'DESTINATION',
              'charge_context': 'DESTINATION',
              'default_party_role': 'BOTH',
              'calculation_basis': 'PER_CONTAINER',
              'charge_date_basis': 'DOCUMENT_DATE',
              'business_date_policy_mode': 'LEGACY_BASIS',
              'default_calculation_profile_id': 11,
              'is_active': true,
            },
          ],
          calculationProfiles: const [
            {
              'id': 11,
              'profile_code': 'PER_CONTAINER',
              'profile_name': 'Rate per container',
            },
          ],
          allocationProfiles: const [],
          businessDateProfiles: const [],
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async => true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Default profile usage'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('component-row-7')));
    await tester.pumpAndSettle();

    expect(find.text('Default profile usage'), findsOneWidget);
    expect(find.text('PER_CONTAINER - Rate per container'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Edit defaults'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Edit defaults'));
    await tester.pumpAndSettle();
    expect(find.text('Edit component'), findsOneWidget);
    expect(find.text('DESTINATION'), findsWidgets);
  });

  testWidgets('uses a compact component table on narrow screens', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(700, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: ComponentManagementWorkspace(
          records: const [
            {
              'id': 8,
              'component_code': 'PORT_FEE',
              'component_name': 'Port Fee',
              'category': 'PORT',
              'charge_context': 'DESTINATION',
              'default_party_role': 'PAYEE',
              'calculation_basis': 'FLAT',
              'is_active': true,
            },
          ],
          calculationProfiles: const [],
          allocationProfiles: const [],
          businessDateProfiles: const [],
          live: false,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async => true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Category'), findsNothing);
    expect(find.text('Context'), findsNothing);
    final row = find.byKey(const ValueKey('component-row-8'));
    await tester.ensureVisible(row);
    await tester.pumpAndSettle();
    await tester.tap(row);
    await tester.pumpAndSettle();

    expect(find.text('Classification'), findsOneWidget);
    expect(find.text('Category'), findsOneWidget);
    expect(find.text('DESTINATION'), findsOneWidget);
  });

  testWidgets('creates a calculation profile with an initial draft', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1300, 1050));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    JsonMap? captured;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: ProfileManagementHub(
          data: WorkspaceData.demo(),
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async {
                captured = body;
                return true;
              },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'New'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Profile code'),
      'WEIGHT_RATE',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Profile name'),
      'Weight based rate',
    );
    await tester.tap(find.text('Create profile'));
    await tester.pumpAndSettle();

    expect(captured?['profile_code'], 'WEIGHT_RATE');
    final initial = captured?['initial_version'] as JsonMap?;
    expect(initial?['calculation_method'], 'RATE_TIMES_PRODUCT');
    expect(initial?['factors'], hasLength(1));
  });

  testWidgets('requires a published profile for an explicit date override', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1300, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    var mutationCount = 0;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: ComponentManagementWorkspace(
          records: const [],
          calculationProfiles: const [],
          allocationProfiles: const [],
          businessDateProfiles: const [],
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async {
                mutationCount++;
                return true;
              },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('New component'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Component code'),
      'OVERRIDE_TEST',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Component name'),
      'Override test',
    );
    await tester.tap(find.text('LEGACY_BASIS'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('PROFILE_OVERRIDE').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Save component'));
    await tester.pumpAndSettle();

    expect(
      find.text('Business-date profile is required for this policy'),
      findsOneWidget,
    );
    expect(mutationCount, 0);
  });

  testWidgets('creates an effective allocation profile with driver policy', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1300, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    JsonMap? captured;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: ProfileManagementHub(
          data: WorkspaceData.demo(),
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async {
                captured = body;
                return true;
              },
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Allocation'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'New'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Profile code'),
      'ALLOC_EFFECTIVE',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Profile name'),
      'Effective allocation',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Effective from'),
      '2026-01-01',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Effective to'),
      '2026-12-31',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Source-to-house driver'),
      'WEIGHT',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'House-to-item driver'),
      'VALUE',
    );
    await tester.tap(find.text('BLOCK').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('EQUAL').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Create profile'));
    await tester.pumpAndSettle();

    final initial = captured?['initial_version'] as JsonMap?;
    expect(initial?['effective_from'], '2026-01-01');
    expect(initial?['effective_to'], '2026-12-31');
    expect(initial?['missing_driver_policy'], 'EQUAL');
  });
}
