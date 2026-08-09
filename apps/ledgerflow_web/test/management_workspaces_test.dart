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
}
