import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/data/workspace_data.dart';
import 'package:ledgerflow_web/features/workspace_pages.dart';

void main() {
  testWidgets('live rate-book workspace uses public mutation paths', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1400));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final calls = <Map<String, dynamic>>[];

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: RateBookWorkspace(
            rateBooks: _liveRateBooks,
            live: true,
            onMutation:
                ({
                  required method,
                  required path,
                  body,
                  required successMessage,
                }) async {
                  calls.add({
                    'method': method,
                    'path': path,
                    'body': body,
                    'success': successMessage,
                  });
                  return true;
                },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(OutlinedButton, 'Edit draft'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate-book name'),
      'Atlantic 2026 draft revision',
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Save draft'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(OutlinedButton, 'New draft').first);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Create draft'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Publish draft'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Publish'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'New rate book'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate-book code'),
      'EU_TRUCK_2026',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Rate-book name'),
      'EU Truck 2026',
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Create rate book'));
    await tester.pumpAndSettle();

    expect(calls, hasLength(4));
    expect(calls[0]['method'], 'PUT');
    expect(
      calls[0]['path'],
      '/api/v1/charge-management/rate-books/12/workspace',
    );
    expect(calls[0]['body']['rate_book_name'], 'Atlantic 2026 draft revision');
    expect(calls[0]['body']['expected_lock_version'], 1);
    expect(calls[0]['body']['entries'][0]['mode'], 'OCEAN');
    expect(calls[0]['body']['entries'][0]['priority'], 50);
    expect(calls[0]['body']['entries'][0]['minimum_amount'], '25.00');

    expect(calls[1]['method'], 'POST');
    expect(
      calls[1]['path'],
      '/api/v1/charge-management/rate-books/12/versions',
    );
    expect(calls[1]['body']['rate_book_code'], 'ATLANTIC_2026');
    expect(calls[1]['body']['status'], 'DRAFT');

    expect(calls[2]['method'], 'POST');
    expect(calls[2]['path'], '/api/v1/charge-management/rate-books/12/publish');

    expect(calls[3]['method'], 'POST');
    expect(calls[3]['path'], '/api/v1/charge-management/rate-books');
    expect(calls[3]['body']['rate_book_code'], 'EU_TRUCK_2026');
    expect(calls[3]['body']['rate_book_name'], 'EU Truck 2026');
  });

  testWidgets('demo mode is read-only and immutable versions are visible', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1380, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: RateBookWorkspace(
            rateBooks: _publishedOnlyRateBooks,
            live: false,
            onMutation:
                ({
                  required method,
                  required path,
                  body,
                  required successMessage,
                }) async {
                  return true;
                },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('Demo mode is read-only.'), findsOneWidget);
    expect(find.text('Immutable version'), findsOneWidget);

    final newRateBook = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'New rate book').first,
    );
    final editDraft = tester.widget<OutlinedButton>(
      find.widgetWithText(OutlinedButton, 'Edit draft'),
    );
    final publishDraft = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Publish draft'),
    );

    expect(newRateBook.onPressed, isNull);
    expect(editDraft.onPressed, isNull);
    expect(publishDraft.onPressed, isNull);
  });
}

final List<JsonMap> _liveRateBooks = [
  {
    'id': 12,
    'rate_book_code': 'ATLANTIC_2026',
    'rate_book_name': 'Atlantic 2026 draft',
    'description': 'Draft revision for Atlantic ocean lanes.',
    'currency': 'USD',
    'status': 'DRAFT',
    'version_number': 2,
    'lock_version': 1,
    'valid_from': '2026-02-01',
    'valid_to': '2026-12-31',
    'calculation_basis': 'PER_CONTAINER',
    'entries': [
      {
        'id': 101,
        'charge_component_code': 'BASE_FREIGHT',
        'origin_code': 'ESBCN',
        'destination_code': 'USNYC',
        'equipment_type': '40HC',
        'basis': 'FLAT',
        'currency': 'USD',
        'rate_amount': '1850.00',
        'mode': 'OCEAN',
        'priority': 50,
        'minimum_amount': '25.00',
        'validity_from': '2026-02-01',
        'validity_to': '2026-12-31',
        'is_active': true,
      },
    ],
    'is_active': true,
  },
  {
    'id': 11,
    'rate_book_code': 'ATLANTIC_2026',
    'rate_book_name': 'Atlantic 2026',
    'description': 'Published Atlantic base rates.',
    'currency': 'USD',
    'status': 'PUBLISHED',
    'version_number': 1,
    'lock_version': 2,
    'valid_from': '2026-01-01',
    'valid_to': '2026-12-31',
    'calculation_basis': 'PER_CONTAINER',
    'published_at': '2026-01-10T08:00:00Z',
    'entries': [
      {
        'id': 91,
        'charge_component_code': 'BASE_FREIGHT',
        'origin_code': 'ESBCN',
        'destination_code': 'USNYC',
        'equipment_type': '40HC',
        'basis': 'FLAT',
        'currency': 'USD',
        'rate_amount': '1760.00',
        'validity_from': '2026-01-01',
        'validity_to': '2026-12-31',
        'is_active': true,
      },
    ],
    'is_active': true,
  },
];

final List<JsonMap> _publishedOnlyRateBooks = [
  {
    'id': 41,
    'rate_book_code': 'PACIFIC_2026',
    'rate_book_name': 'Pacific 2026',
    'description': 'Published Pacific contract rates.',
    'currency': 'USD',
    'status': 'PUBLISHED',
    'version_number': 3,
    'lock_version': 4,
    'valid_from': '2026-01-01',
    'valid_to': '2026-12-31',
    'calculation_basis': 'PER_CONTAINER',
    'published_at': '2026-03-02T12:00:00Z',
    'entries': [
      {
        'id': 301,
        'charge_component_code': 'BASE_FREIGHT',
        'origin_code': 'CNSHA',
        'destination_code': 'USLAX',
        'equipment_type': '40HC',
        'basis': 'FLAT',
        'currency': 'USD',
        'rate_amount': '2100.00',
        'validity_from': '2026-01-01',
        'validity_to': '2026-12-31',
        'is_active': true,
      },
    ],
    'is_active': true,
  },
];
