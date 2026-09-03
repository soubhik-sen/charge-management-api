import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ledgerflow_web/core/api_client.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/features/workspace_pages.dart';

void main() {
  testWidgets(
    'shows a live new invoice action and submits a structured draft',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1600, 1200));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      var reloads = 0;
      Map<String, dynamic>? captured;
      final calls = <String>[];
      final document = _document();
      final created = _invoice('ESTIMATED');
      final invoiceDate = DateTime.now().toIso8601String().substring(0, 10);
      final client = LedgerFlowApiClient(
        baseUrl: 'https://api.example.test',
        token: 'test-token',
        httpClient: MockClient((request) async {
          calls.add('${request.method} ${request.url.path}');
          if (request.method == 'POST' &&
              request.url.path == '/api/v1/charge-management/invoices') {
            captured = jsonDecode(request.body) as Map<String, dynamic>;
            return http.Response(jsonEncode(created), 200);
          }
          if (request.method == 'GET' &&
              request.url.path ==
                  '/api/v1/charge-management/invoices/21/workspace') {
            return http.Response(
              jsonEncode(_invoiceWorkspaceResponse(created, document)),
              200,
            );
          }
          return http.Response(jsonEncode(created), 200);
        }),
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: LedgerFlowDesign.theme,
          home: Scaffold(
            body: InvoiceWorkspace(
              invoices: const [],
              documents: [document],
              components: [_component()],
              live: true,
              client: client,
              onReload: () async => reloads++,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final newInvoice = tester.widget<FilledButton>(
        find.widgetWithText(FilledButton, 'New invoice'),
      );
      expect(newInvoice.onPressed, isNotNull);

      await tester.tap(find.widgetWithText(FilledButton, 'New invoice'));
      await tester.pumpAndSettle();
      expect(find.text('Create invoice'), findsWidgets);
      await tester.tap(find.byType(DropdownButtonFormField<int>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('CD-2026-01482  |  ESTIMATED  |  EUR').last);
      await tester.pumpAndSettle();
      await tester.tap(find.byType(DropdownButtonFormField<String>).first);
      await tester.pumpAndSettle();
      expect(find.text('Supplier invoice'), findsWidgets);
      expect(find.text('Customer invoice'), findsWidgets);
      await tester.tap(find.text('Supplier invoice').last);
      await tester.pumpAndSettle();
      expect(find.text('Road freight FTL (ROAD_FREIGHT_FTL)'), findsOneWidget);
      await tester.enterText(find.byType(TextFormField).at(0), 'INV-00001234');
      await tester.enterText(find.byType(TextFormField).at(3), '500.00');
      await tester.tap(find.widgetWithText(FilledButton, 'Create invoice'));
      await tester.pumpAndSettle();

      expect(captured?['charge_document_id'], 12);
      expect(captured?['invoice_type'], 'SUPPLIER');
      expect(captured?['invoice_number'], 'INV-00001234');
      expect(captured?['invoice_date'], invoiceDate);
      expect(captured?['currency'], 'EUR');
      expect(captured?['lines'], isA<List>());
      expect(
        (captured?['lines'] as List).first['charge_component_code'],
        'ROAD_FREIGHT_FTL',
      );
      expect((captured?['lines'] as List).first['amount'], '500.00');
      expect(calls, contains('POST /api/v1/charge-management/invoices'));
      expect(reloads, 1);
    },
  );

  testWidgets('matches a live invoice and reloads after posting the match', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var reloads = 0;
    final calls = <String>[];
    final invoice = _invoice('REVIEW');
    final document = _document(status: 'REVIEW');
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        if (request.method == 'GET' &&
            request.url.path ==
                '/api/v1/charge-management/invoices/21/workspace') {
          return http.Response(
            jsonEncode(_invoiceWorkspaceResponse(invoice, document)),
            200,
          );
        }
        if (request.method == 'POST' &&
            request.url.path == '/api/v1/charge-management/invoices/21/match') {
          return http.Response(jsonEncode(invoice), 200);
        }
        return http.Response(jsonEncode(invoice), 200);
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: InvoiceWorkspace(
            invoices: [invoice],
            documents: [document],
            components: [_component()],
            live: true,
            client: client,
            onReload: () async => reloads++,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'Match invoice'));
    await tester.pumpAndSettle();

    expect(calls, contains('POST /api/v1/charge-management/invoices/21/match'));
    expect(reloads, 1);
  });

  testWidgets('deletes an editable invoice after confirmation', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final calls = <String>[];
    var reloads = 0;
    final invoice = _invoice('ESTIMATED');
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        return http.Response(jsonEncode(invoice), 200);
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: InvoiceWorkspace(
            invoices: [invoice],
            documents: [_document(status: 'ESTIMATED')],
            components: [_component()],
            live: true,
            client: client,
            onReload: () async => reloads++,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(OutlinedButton, 'Delete'));
    await tester.pumpAndSettle();
    expect(find.textContaining('reconciliation results'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Delete invoice'));
    await tester.pumpAndSettle();

    expect(calls, contains('DELETE /api/v1/charge-management/invoices/21'));
    expect(reloads, 1);
  });

  testWidgets('disables invoice deletion after document approval', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: InvoiceWorkspace(
            invoices: [_invoice('APPROVED')],
            documents: [_document(status: 'APPROVED')],
            components: [_component()],
            live: true,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final button = tester.widget<OutlinedButton>(
      find.widgetWithText(OutlinedButton, 'Delete'),
    );
    expect(button.onPressed, isNull);
  });
}

Map<String, dynamic> _invoice(String documentStatus) => {
  'id': 21,
  'charge_document_id': 12,
  'charge_document_number': 'CHG-00000012',
  'charge_document_status': documentStatus,
  'invoice_number': 'INV-00000021',
  'invoice_type': 'SUPPLIER',
  'invoice_date': '2026-08-15',
  'currency': 'EUR',
  'status': 'MATCHED',
  'total_amount': '475.00',
  'lines': [
    {
      'charge_component_code': 'ROAD_FREIGHT_FTL',
      'description': 'Road freight FTL',
      'amount': '475.00',
      'expected_amount': '475.00',
      'variance_amount': '0.00',
      'status': 'MATCHED',
    },
  ],
};

Map<String, dynamic> _document({String status = 'ESTIMATED'}) => {
  'id': 12,
  'document_number': 'CD-2026-01482',
  'status': status,
  'currency': 'EUR',
  'source_object_type': 'QUOTE',
  'source_object_id': 482,
  'lines': [
    {
      'charge_component_code': 'ROAD_FREIGHT_FTL',
      'description': 'Road freight FTL',
      'expected_amount': '475.00',
      'relationship_role': 'PAYER',
      'line_role': 'POSTING',
    },
  ],
};

Map<String, dynamic> _component() => {
  'id': 1,
  'component_code': 'ROAD_FREIGHT_FTL',
  'component_name': 'Road freight FTL',
  'is_active': true,
};

Map<String, dynamic> _invoiceWorkspaceResponse(
  Map<String, dynamic> invoice,
  Map<String, dynamic> document,
) => {
  'invoice': invoice,
  'charge_document': document,
  'match_results': [
    {
      'charge_component_code': 'ROAD_FREIGHT_FTL',
      'description': 'Road freight FTL',
      'charge_line_id': 7001,
      'invoice_amount': '475.00',
      'expected_amount': '475.00',
      'variance_amount': '0.00',
      'match_status': 'MATCHED',
    },
  ],
};
