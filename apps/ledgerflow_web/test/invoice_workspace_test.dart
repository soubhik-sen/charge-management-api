import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ledgerflow_web/core/api_client.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/features/workspace_pages.dart';

void main() {
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
          body: InvoiceWorkspace(invoices: [_invoice('APPROVED')], live: true),
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
