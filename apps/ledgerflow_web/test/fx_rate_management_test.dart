import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/data/workspace_data.dart';
import 'package:ledgerflow_web/features/management_workspaces.dart';

void main() {
  testWidgets('creates an FX rate from a loaded source option', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1320, 1080));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    String? capturedMethod;
    String? capturedPath;
    JsonMap? capturedBody;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: FxDateManagementHub(
          data: WorkspaceData.demo(),
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async {
                capturedMethod = method;
                capturedPath = path;
                capturedBody = body;
                return true;
              },
          loadAssignments: null,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('FX rates').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('New rate'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextFormField, 'Source currency'),
      'eur',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Target currency'),
      'usd',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate date'),
      '2026-08-09',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate'),
      '1.2345',
    );

    await tester.tap(find.text('Create rate'));
    await tester.pumpAndSettle();

    expect(capturedMethod, 'POST');
    expect(capturedPath, '/api/v1/charge-management/fx-rates');
    expect(capturedBody?['source_id'], 1);
    expect(capturedBody?['source_currency'], 'EUR');
    expect(capturedBody?['target_currency'], 'USD');
    expect(capturedBody?['rate_date'], '2026-08-09');
    expect(capturedBody?['rate'], '1.2345');
    expect(capturedBody?['rate_type'], 'MID');
    expect(capturedBody?['conversion_method'], 'DIRECT');
  });

  testWidgets('updates the selected FX rate', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1320, 1080));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    String? capturedMethod;
    String? capturedPath;
    JsonMap? capturedBody;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: FxDateManagementHub(
          data: WorkspaceData.demo(),
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async {
                capturedMethod = method;
                capturedPath = path;
                capturedBody = body;
                return true;
              },
          loadAssignments: null,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('FX rates').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('FX rate actions'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Edit rate').last);
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate'),
      '1.2000',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Conversion method'),
      'treasury',
    );

    await tester.tap(find.text('Save rate'));
    await tester.pumpAndSettle();

    expect(capturedMethod, 'PUT');
    expect(capturedPath, '/api/v1/charge-management/fx-rates/1');
    expect(capturedBody?['source_id'], 1);
    expect(capturedBody?['rate'], '1.2000');
    expect(capturedBody?['conversion_method'], 'TREASURY');
    expect(capturedBody?['metadata_json'], isA<Map<String, dynamic>>());
  });

  testWidgets('deactivates the selected FX rate', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1320, 1080));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    String? capturedMethod;
    String? capturedPath;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: FxDateManagementHub(
          data: WorkspaceData.demo(),
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async {
                capturedMethod = method;
                capturedPath = path;
                return true;
              },
          loadAssignments: null,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('FX rates').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byTooltip('FX rate actions'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Deactivate').last);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Deactivate'));
    await tester.pumpAndSettle();

    expect(capturedMethod, 'DELETE');
    expect(capturedPath, '/api/v1/charge-management/fx-rates/1');
  });

  testWidgets('falls back to numeric source id when no FX sources are loaded', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1320, 1080));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    JsonMap? capturedBody;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: FxDateManagementHub(
          data: const WorkspaceData({'fxRates': []}),
          live: true,
          onMutation:
              ({
                required method,
                required path,
                body,
                required successMessage,
              }) async {
                capturedBody = body;
                return true;
              },
          loadAssignments: null,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('FX rates').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('New rate'));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('FX rate sources are maintained via API'),
      findsOne,
    );

    await tester.enterText(
      find.widgetWithText(TextFormField, 'Source ID'),
      '77',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Source currency'),
      'GBP',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Target currency'),
      'USD',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate date'),
      '2026-08-09',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate'),
      '1.5000',
    );

    await tester.tap(find.text('Create rate'));
    await tester.pumpAndSettle();

    expect(capturedBody?['source_id'], 77);
    expect(capturedBody?['source_currency'], 'GBP');
    expect(capturedBody?['target_currency'], 'USD');
  });

  testWidgets('validates source id, pair, date, and positive rate', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1320, 1080));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var mutationCount = 0;

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: FxDateManagementHub(
          data: const WorkspaceData({'fxRates': []}),
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
          loadAssignments: null,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('FX rates').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('New rate'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextFormField, 'Source ID'),
      '0',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Source currency'),
      'USD',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Target currency'),
      'USD',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate date'),
      '2026/08/09',
    );
    await tester.enterText(find.widgetWithText(TextFormField, 'Rate'), '0');

    await tester.tap(find.text('Create rate'));
    await tester.pumpAndSettle();

    expect(find.text('Enter a positive source ID'), findsOneWidget);
    expect(find.text('Currencies must differ'), findsOneWidget);
    expect(find.text('Use YYYY-MM-DD'), findsOneWidget);
    expect(find.text('Enter a positive rate'), findsOneWidget);
    expect(mutationCount, 0);
  });
}
