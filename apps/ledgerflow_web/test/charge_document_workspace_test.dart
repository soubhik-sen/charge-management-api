import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ledgerflow_web/core/api_client.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/features/workspace_pages.dart';

void main() {
  testWidgets('executes approve export and reversal through public endpoints', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1800, 1500));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var status = 'ESTIMATED';
    String? reversalReason;
    final calls = <String>[];
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        if (request.method == 'GET' &&
            request.url.path.endsWith('/workspace')) {
          return http.Response(jsonEncode(_workspace(status)), 200);
        }
        if (request.url.path.endsWith('/approve')) {
          status = 'APPROVED';
          return http.Response(
            jsonEncode({'document': _document(status)}),
            200,
          );
        }
        if (request.url.path.endsWith('/post-export')) {
          status = 'EXPORTED';
          return http.Response(
            jsonEncode({
              'document': _document(status),
              'export_number': 'EXP-00000001',
              'target_system': 'INTERNAL_LEDGER',
              'status': 'POSTED',
              'payload_json': _document(status),
            }),
            200,
          );
        }
        if (request.url.path.endsWith('/reverse')) {
          reversalReason =
              (jsonDecode(request.body) as Map<String, dynamic>)['reason']
                  as String;
          status = 'REVERSED';
          return http.Response(
            jsonEncode({'document': _document(status)}),
            200,
          );
        }
        return http.Response('{}', 200);
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: ChargeDocumentWorkspace(
            documents: [_document(status)],
            live: true,
            client: client,
            onReload: () async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Document status permits approval'), findsOneWidget);
    expect(find.text('7 / line 71'), findsOneWidget);
    expect(find.text('4 / 44'), findsOneWidget);
    expect(find.text('3 / 31'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Approve'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Approve').last);
    await tester.pumpAndSettle();

    expect(
      calls,
      contains('POST /api/v1/charge-management/charge-documents/12/approve'),
    );
    expect(find.text('APPROVED'), findsWidgets);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Export'));
    await tester.pumpAndSettle();

    expect(find.text('EXP-00000001'), findsWidgets);
    expect(find.textContaining('INTERNAL_LEDGER payload'), findsOneWidget);
    expect(
      calls,
      contains(
        'POST /api/v1/charge-management/charge-documents/12/post-export',
      ),
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Close'));
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(OutlinedButton, 'Reverse'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byType(TextFormField),
      'Customer cancelled movement',
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Reverse document'));
    await tester.pumpAndSettle();

    expect(reversalReason, 'Customer cancelled movement');
    expect(
      calls,
      contains('POST /api/v1/charge-management/charge-documents/12/reverse'),
    );
    expect(find.text('REVERSED'), findsWidgets);
  });

  testWidgets('shows authoritative blocker and disables approval', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final blocked = _workspace('ESTIMATED')
      ..['approval_ready'] = false
      ..['approval_checks'] = [
        {
          'code': 'STATUS_ELIGIBLE',
          'label': 'Document status permits approval',
          'passed': true,
          'detail': 'Status ESTIMATED is eligible for approval.',
        },
        {
          'code': 'LINE_PROCESSING_COMPLETE',
          'label': 'Calculations and allocations are complete',
          'passed': false,
          'detail':
              'Charge document cannot be approved while line 10 has failed calculation.',
        },
      ];
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient(
        (_) async => http.Response(jsonEncode(blocked), 200),
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: ChargeDocumentWorkspace(
            documents: [_document('ESTIMATED')],
            live: true,
            client: client,
            onReload: () async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('failed calculation'), findsOneWidget);
    final approve = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Approve'),
    );
    expect(approve.onPressed, isNull);
  });

  testWidgets('deletes an editable charge document after confirmation', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final document = _document('ESTIMATED')
      ..['quote_request_id'] = null
      ..['quote_option_id'] = null
      ..['lines'] = <Object>[];
    final workspace = _workspace('ESTIMATED')
      ..['document'] = document
      ..['source_quote_option'] = null;
    final calls = <String>[];
    var reloads = 0;
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        if (request.method == 'GET') {
          return http.Response(jsonEncode(workspace), 200);
        }
        return http.Response(jsonEncode({'document': document}), 200);
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: ChargeDocumentWorkspace(
            documents: [document],
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
    expect(find.textContaining('permanently deletes'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Delete document'));
    await tester.pumpAndSettle();

    expect(
      calls,
      contains('DELETE /api/v1/charge-management/charge-documents/12'),
    );
    expect(reloads, 1);
  });

  testWidgets(
    'reloads the selected charge document after the chosen record is removed',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1500, 1100));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final documentOne = Map<String, dynamic>.from(_document('ESTIMATED'));
      final documentTwo = {
        ..._document('ESTIMATED'),
        'id': 13,
        'document_number': 'CHG-00000013',
        'quote_request_id': 10,
        'quote_option_id': 91,
      };
      var documents = [documentOne, documentTwo];
      final calls = <String>[];
      late StateSetter rebuild;
      final client = LedgerFlowApiClient(
        baseUrl: 'https://api.example.test',
        token: 'test-token',
        httpClient: MockClient((request) async {
          calls.add('${request.method} ${request.url.path}');
          if (request.method == 'GET' &&
              request.url.path.endsWith('/workspace')) {
            final id = int.parse(request.url.pathSegments[4]);
            final document = id == 13 ? documentTwo : documentOne;
            final workspace = _workspace(document['status'] as String);
            workspace['document'] = document;
            return http.Response(jsonEncode(workspace), 200);
          }
          return http.Response('{}', 200);
        }),
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: LedgerFlowDesign.theme,
          home: Scaffold(
            body: StatefulBuilder(
              builder: (context, setState) {
                rebuild = setState;
                return ChargeDocumentWorkspace(
                  documents: documents,
                  live: true,
                  client: client,
                  onReload: () async {},
                );
              },
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('CHG-00000013').last);
      await tester.pumpAndSettle();

      documents = [documentOne];
      rebuild(() {});
      await tester.pumpAndSettle();

      expect(
        calls.where((call) => call.endsWith('/workspace')).toList(),
        equals([
          'GET /api/v1/charge-management/charge-documents/12/workspace',
          'GET /api/v1/charge-management/charge-documents/13/workspace',
          'GET /api/v1/charge-management/charge-documents/12/workspace',
        ]),
      );
    },
  );
}

Map<String, dynamic> _workspace(String status) => {
  'document': _document(status),
  'invoices': <Object>[],
  'match_results': <Object>[],
  'source_quote_option': {
    'id': 90,
    'option_name': 'Road customer option',
    'lines': [
      {
        'id': 501,
        'source_contract_id': 7,
        'source_contract_line_id': 71,
        'source_rate_book_id': 4,
        'source_rate_book_entry_id': 44,
        'source_calculation_template_id': 3,
        'source_calculation_template_step_id': 31,
      },
    ],
  },
  'approval_ready': !{'DISPUTED', 'EXPORTED', 'REVERSED'}.contains(status),
  'approval_checks': [
    {
      'code': 'STATUS_ELIGIBLE',
      'label': 'Document status permits approval',
      'passed': !{'DISPUTED', 'EXPORTED', 'REVERSED'}.contains(status),
      'detail': 'Status $status is eligible for approval.',
    },
    {
      'code': 'LINE_PROCESSING_COMPLETE',
      'label': 'Calculations and allocations are complete',
      'passed': true,
      'detail': 'No line has pending or failed processing.',
    },
  ],
};

Map<String, dynamic> _document(String status) => {
  'id': 12,
  'document_number': 'CHG-00000012',
  'quote_request_id': 9,
  'quote_option_id': 90,
  'source_object_type': 'ROAD_SHIPMENT',
  'source_object_id': 'SHIP-9',
  'document_date': '2026-08-15',
  'company_id': 10,
  'customer_id': 20,
  'currency': 'EUR',
  'status': status,
  'payer_total_amount': '0.00',
  'payee_total_amount': '950.00',
  'margin_amount': '950.00',
  'approved_at': status == 'ESTIMATED' ? null : '2026-08-15T10:00:00Z',
  'exported_at': status == 'EXPORTED' ? '2026-08-15T10:05:00Z' : null,
  'reversed_at': status == 'REVERSED' ? '2026-08-15T10:10:00Z' : null,
  'reversal_reason': status == 'REVERSED'
      ? 'Customer cancelled movement'
      : null,
  'lines': [
    {
      'id': 101,
      'line_number': 10,
      'source': 'QUOTE',
      'source_quote_option_line_id': 501,
      'charge_component_code': 'ROAD_FREIGHT_FTL',
      'description': 'Road freight FTL',
      'relationship_role': 'PAYEE',
      'line_role': 'POSTING',
      'target_level': 'HEADER',
      'basis': 'FLAT',
      'currency': 'EUR',
      'source_currency': 'EUR',
      'source_amount': '950.00',
      'rate_amount': '950.00',
      'expected_amount': '950.00',
      'actual_amount': null,
      'approved_amount': status == 'ESTIMATED' ? null : '950.00',
      'status': status,
      'calculation_mode': 'PROFILE',
      'calculation_status': 'CALCULATED',
      'allocation_mode': 'NONE',
      'allocation_status': 'NOT_REQUIRED',
      'calculation_input_snapshot_json': {'DISTANCE_KM': '620'},
    },
  ],
};
