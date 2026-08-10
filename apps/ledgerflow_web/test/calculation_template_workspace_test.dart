import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/data/workspace_data.dart';
import 'package:ledgerflow_web/features/workspace_pages.dart';

void main() {
  testWidgets('creates an ordered calculation template with a filtered book', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final calls = <JsonMap>[];

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: CalculationTemplateWorkspacePage(
            templates: const [],
            components: const [
              {
                'component_code': 'ROAD_LINEHAUL',
                'component_name': 'Road linehaul',
                'is_active': true,
              },
              {
                'component_code': 'FUEL_SURCHARGE',
                'component_name': 'Fuel surcharge',
                'is_active': true,
              },
            ],
            rateBooks: const [
              {
                'id': 21,
                'rate_book_code': 'ROAD_LINEHAUL_ES_2026',
                'rate_book_name': 'Spain road linehaul',
                'charge_component_code': 'ROAD_LINEHAUL',
                'version_number': 1,
                'status': 'PUBLISHED',
              },
              {
                'id': 22,
                'rate_book_code': 'FUEL_ES_2026',
                'rate_book_name': 'Spain fuel',
                'charge_component_code': 'FUEL_SURCHARGE',
                'version_number': 1,
                'status': 'PUBLISHED',
              },
            ],
            live: true,
            onMutation:
                ({
                  required method,
                  required path,
                  body,
                  required successMessage,
                }) async {
                  calls.add({'method': method, 'path': path, 'body': body});
                  return true;
                },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'New template'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Template code'),
      'ROAD_STANDARD_ES',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Template name'),
      'Spain road standard',
    );
    await tester.tap(find.widgetWithText(TextButton, 'Add step'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('template-step-component-0')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Road linehaul (ROAD_LINEHAUL)').last);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('template-step-rate-book-0')));
    await tester.pumpAndSettle();
    expect(find.textContaining('Spain road linehaul'), findsOneWidget);
    expect(find.textContaining('Spain fuel'), findsNothing);
    await tester.tap(find.textContaining('Spain road linehaul').last);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Save draft'));
    await tester.pumpAndSettle();

    expect(calls, hasLength(1));
    expect(calls.single['method'], 'POST');
    expect(
      calls.single['path'],
      '/api/v1/charge-management/calculation-templates',
    );
    final body = calls.single['body'] as JsonMap;
    expect(body['template_code'], 'ROAD_STANDARD_ES');
    expect(body['status'], 'DRAFT');
    final steps = body['steps'] as List<dynamic>;
    expect(steps.single['charge_component_code'], 'ROAD_LINEHAUL');
    expect(steps.single['rate_book_id'], 21);
  });
}
