import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ledgerflow_web/core/api_client.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/features/transaction_workspaces.dart';

void main() {
  testWidgets('shows every contract binding and disables edit on release', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: ContractManagementWorkspace(
            contracts: [
              {
                ..._contracts.single,
                'status': 'RELEASED',
                'company_id': 10,
                'customer_id': 20,
                'vendor_id': 30,
                'forwarder_id': 40,
                'carrier_id': 50,
              },
            ],
            components: _components,
            rateBooks: _rateBooks,
            calculationTemplates: const [],
            calculationProfiles: const [],
            allocationProfiles: const [],
            live: true,
            client: null,
            onReload: () async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('Company 10'), findsWidgets);
    expect(find.textContaining('Customer 20'), findsWidgets);
    expect(find.textContaining('Vendor 30'), findsWidgets);
    expect(find.textContaining('Forwarder 40'), findsWidgets);
    expect(find.textContaining('Carrier 50'), findsWidgets);
    final edit = tester.widget<OutlinedButton>(
      find.widgetWithText(OutlinedButton, 'Edit'),
    );
    expect(edit.onPressed, isNull);
  });

  testWidgets(
    'contract editor supports header templates without adding lines',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1440, 1200));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        MaterialApp(
          theme: LedgerFlowDesign.theme,
          home: Scaffold(
            body: Builder(
              builder: (context) => FilledButton(
                onPressed: () => showDialog<void>(
                  context: context,
                  builder: (_) => ContractEditorDialog(
                    components: _components,
                    rateBooks: _rateBooks,
                    calculationTemplates: _calculationTemplates,
                    calculationProfiles: const [],
                    allocationProfiles: const [],
                  ),
                ),
                child: const Text('Open contract editor'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Open contract editor'));
      await tester.pumpAndSettle();

      expect(find.text('Default calculation template'), findsOneWidget);
      expect(find.text('Contract selection priority'), findsOneWidget);
      expect(find.text('Add route'), findsOneWidget);
      expect(find.text('Add direct line'), findsOneWidget);
      expect(find.text('Line 1'), findsNothing);

      await tester.tap(find.text('Add route'));
      await tester.pumpAndSettle();
      expect(find.text('Template route 1'), findsOneWidget);
      expect(find.text('Calculation template'), findsOneWidget);
      expect(find.text('Charge component'), findsNothing);
    },
  );

  testWidgets('contract editor preserves all binding IDs on submit', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    late http.Request captured;
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        captured = request;
        return http.Response(
          jsonEncode({
            'contract': {'id': 99},
          }),
          200,
        );
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: ContractManagementWorkspace(
            contracts: const [],
            components: _components,
            rateBooks: _rateBooks,
            calculationTemplates: _calculationTemplates,
            calculationProfiles: const [],
            allocationProfiles: const [],
            live: true,
            client: client,
            onReload: () async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'New contract'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextFormField, 'Contract number'),
      'con-001',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Contract name'),
      'Multi-binding contract',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Company ID'),
      '10',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Customer ID'),
      '20',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Vendor ID'),
      '30',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Forwarder ID'),
      '40',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Carrier ID'),
      '50',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Payer reference'),
      'payer-ref',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Payee reference'),
      'payee-ref',
    );
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Create contract'));
    await tester.pumpAndSettle();

    final body = jsonDecode(captured.body) as Map<String, dynamic>;
    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/v1/charge-management/contracts');
    expect(body['contract_number'], 'CON-001');
    expect(body['company_id'], 10);
    expect(body['customer_id'], 20);
    expect(body['vendor_id'], 30);
    expect(body['forwarder_id'], 40);
    expect(body['carrier_id'], 50);
  });

  testWidgets('determines contracts, rates, and shows real provenance', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1300));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var rated = false;
    final calls = <String>[];
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        if (request.url.path.endsWith('/workspace')) {
          return http.Response(
            jsonEncode({
              'quote_request': _quote,
              'options': rated ? [_ratedOption] : <Object>[],
              'offers': <Object>[],
              'commitments': <Object>[],
              'charge_documents': <Object>[],
            }),
            200,
          );
        }
        if (request.url.path.endsWith('/determine-contracts')) {
          return http.Response(
            jsonEncode({
              'quote_request_id': 9,
              'payer_contracts': <Object>[],
              'payee_contracts': [_contracts.single],
            }),
            200,
          );
        }
        if (request.url.path.endsWith('/rate')) {
          rated = true;
          return http.Response(
            jsonEncode({
              'quote_request': _quote,
              'options': [_ratedOption],
            }),
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
          body: TransactionQuoteWorkspace(
            quotes: [_quote],
            contracts: _contracts,
            live: true,
            client: client,
            onReload: () async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(
      find.widgetWithText(OutlinedButton, 'Determine contracts'),
    );
    await tester.pumpAndSettle();
    expect(find.text('ROAD-CUSTOMER-20'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Rate charges'));
    await tester.pumpAndSettle();

    expect(find.text('ROAD_FREIGHT_FTL'), findsOneWidget);
    expect(find.text('EUR 950.00'), findsOneWidget);
    expect(find.text('7 / line 71'), findsOneWidget);
    expect(find.text('Book 4 · row 44'), findsOneWidget);
    expect(find.text('3 / 31'), findsOneWidget);
    expect(find.text('STATISTICAL'), findsOneWidget);
    expect(
      calls,
      contains(
        'POST /api/v1/charge-management/quote-requests/9/determine-contracts',
      ),
    );
    expect(
      calls,
      contains('POST /api/v1/charge-management/quote-requests/9/rate'),
    );
  });

  testWidgets('disables rank options for awarded quotes', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient(
        (_) async => http.Response(
          jsonEncode({
            'quote_request': {..._quote, 'status': 'AWARDED'},
            'options': [_ratedOption],
            'offers': <Object>[],
            'commitments': <Object>[],
            'charge_documents': <Object>[],
          }),
          200,
        ),
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: TransactionQuoteWorkspace(
            quotes: [
              {..._quote, 'status': 'AWARDED'},
            ],
            contracts: _contracts,
            live: true,
            client: client,
            onReload: () async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final rank = tester.widget<OutlinedButton>(
      find.widgetWithText(OutlinedButton, 'Rank options'),
    );
    expect(rank.onPressed, isNull);
  });

  testWidgets('clears determined contracts after rate reloads workspace', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var rated = false;
    final calls = <String>[];
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        if (request.method == 'GET' &&
            request.url.path.endsWith('/workspace')) {
          return http.Response(
            jsonEncode({
              'quote_request': {..._quote, 'status': 'RATED'},
              'options': rated ? <Object>[] : <Object>[],
              'offers': <Object>[],
              'commitments': <Object>[],
              'charge_documents': <Object>[],
            }),
            200,
          );
        }
        if (request.url.path.endsWith('/determine-contracts')) {
          return http.Response(
            jsonEncode({
              'quote_request_id': 9,
              'payer_contracts': <Object>[],
              'payee_contracts': [_contracts.single],
            }),
            200,
          );
        }
        if (request.url.path.endsWith('/rate')) {
          rated = true;
          return http.Response(
            jsonEncode({
              'quote_request': {..._quote, 'status': 'RATED'},
              'options': <Object>[],
            }),
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
          body: TransactionQuoteWorkspace(
            quotes: [_quote],
            contracts: _contracts,
            live: true,
            client: client,
            onReload: () async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(
      find.widgetWithText(OutlinedButton, 'Determine contracts'),
    );
    await tester.pumpAndSettle();
    expect(find.text('ROAD-CUSTOMER-20'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Rate charges'));
    await tester.pumpAndSettle();

    expect(find.text('ROAD-CUSTOMER-20'), findsNothing);
    expect(
      calls,
      contains('POST /api/v1/charge-management/quote-requests/9/rate'),
    );
  });

  testWidgets('imports quote JSON with all caller IDs on submit', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final originalPicker = _safeCurrentPicker();
    addTearDown(() {
      if (originalPicker != null) {
        FilePicker.platform = originalPicker;
      }
    });

    final imported = <String, dynamic>{
      'request_number': 'ROAD-Q-IMPORTED',
      'source_object_type': 'ROAD_SHIPMENT',
      'source_object_id': 'SHIP-99',
      'company_id': 10,
      'customer_id': 20,
      'vendor_id': 30,
      'forwarder_id': 40,
      'carrier_id': 50,
      'origin_code': 'FRPAR',
      'destination_code': 'DEBER',
      'mode': 'ROAD',
      'charge_context': 'ROAD',
    };
    final bytes = Uint8List.fromList(utf8.encode(jsonEncode(imported)));
    FilePicker.platform = _TestFilePicker(
      FilePickerResult([
        PlatformFile(name: 'request.json', size: bytes.length, bytes: bytes),
      ]),
    );

    late http.Request captured;
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        captured = request;
        return http.Response(
          jsonEncode({
            'quote_request': {'id': 99, ...imported},
          }),
          200,
        );
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: TransactionQuoteWorkspace(
            quotes: const [],
            contracts: _contracts,
            live: true,
            client: client,
            onReload: () async {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(FilledButton, 'New request'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, 'Upload JSON'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Create request'));
    await tester.pumpAndSettle();

    final body = jsonDecode(captured.body) as Map<String, dynamic>;
    expect(captured.method, 'POST');
    expect(captured.url.path, '/api/v1/charge-management/quote-requests');
    expect(body['request_number'], 'ROAD-Q-IMPORTED');
    expect(body['source_object_type'], 'ROAD_SHIPMENT');
    expect(body['source_object_id'], 'SHIP-99');
    expect(body['company_id'], 10);
    expect(body['customer_id'], 20);
    expect(body['vendor_id'], 30);
    expect(body['forwarder_id'], 40);
    expect(body['carrier_id'], 50);
  });

  testWidgets('reloads the selected quote after the chosen record is removed', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final quoteOne = Map<String, dynamic>.from(_quote);
    final quoteTwo = {
      ..._quote,
      'id': 10,
      'request_number': 'ROAD-Q-10',
      'origin_code': 'FRPAR',
      'destination_code': 'BEANR',
    };
    var quotes = [quoteOne, quoteTwo];
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
          final quote = id == 10 ? quoteTwo : quoteOne;
          return http.Response(
            jsonEncode({
              'quote_request': quote,
              'options': <Object>[],
              'offers': <Object>[],
              'commitments': <Object>[],
              'charge_documents': <Object>[],
            }),
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
          body: StatefulBuilder(
            builder: (context, setState) {
              rebuild = setState;
              return TransactionQuoteWorkspace(
                quotes: quotes,
                contracts: _contracts,
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

    await tester.tap(find.text('ROAD-Q-10').last);
    await tester.pumpAndSettle();
    expect(
      calls,
      contains('GET /api/v1/charge-management/quote-requests/10/workspace'),
    );

    quotes = [quoteOne];
    rebuild(() {});
    await tester.pumpAndSettle();

    expect(
      calls.where((call) => call.endsWith('/workspace')).toList(),
      equals([
        'GET /api/v1/charge-management/quote-requests/9/workspace',
        'GET /api/v1/charge-management/quote-requests/10/workspace',
        'GET /api/v1/charge-management/quote-requests/9/workspace',
      ]),
    );
  });

  testWidgets('deletes an unawarded quote after confirmation', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1100));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final calls = <String>[];
    var reloads = 0;
    final client = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        if (request.method == 'GET' &&
            request.url.path.endsWith('/workspace')) {
          return http.Response(
            jsonEncode({
              'quote_request': _quote,
              'options': <Object>[],
              'offers': <Object>[],
              'commitments': <Object>[],
              'charge_documents': <Object>[],
            }),
            200,
          );
        }
        return http.Response(jsonEncode(_quote), 200);
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: TransactionQuoteWorkspace(
            quotes: [_quote],
            contracts: _contracts,
            live: true,
            client: client,
            onReload: () async => reloads += 1,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.widgetWithText(OutlinedButton, 'Delete'));
    await tester.pumpAndSettle();
    expect(find.text('Delete ROAD-Q-9?'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Delete quote'));
    await tester.pumpAndSettle();

    expect(
      calls,
      contains('DELETE /api/v1/charge-management/quote-requests/9'),
    );
    expect(reloads, 1);
  });

  testWidgets('quote request editor exposes JSON import and typed inputs', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1400, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: Builder(
            builder: (context) => FilledButton(
              onPressed: () => showDialog<void>(
                context: context,
                builder: (_) => QuoteRequestEditorDialog(quote: _quote),
              ),
              child: const Text('Open'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Open'));
    await tester.pumpAndSettle();

    expect(find.text('Upload JSON'), findsOneWidget);
    expect(find.text('Typed operational dates'), findsOneWidget);
    expect(find.text('Advanced calculation inputs'), findsOneWidget);
    expect(find.text('ROAD_ACTUAL_PICKUP_DATE'), findsOneWidget);
  });
}

final _components = <Map<String, dynamic>>[
  {
    'id': 1,
    'component_code': 'ROAD_FREIGHT_FTL',
    'component_name': 'Road freight FTL',
    'is_active': true,
  },
];

final _rateBooks = <Map<String, dynamic>>[
  {
    'id': 4,
    'rate_book_code': 'ROAD-2026',
    'rate_book_name': 'Road 2026',
    'charge_component_code': 'ROAD_FREIGHT_FTL',
    'status': 'PUBLISHED',
    'is_active': true,
  },
];

final _calculationTemplates = <Map<String, dynamic>>[
  {
    'id': 3,
    'template_code': 'ROAD_STANDARD',
    'template_name': 'Road standard charges',
    'status': 'PUBLISHED',
    'is_active': true,
  },
];

final _contracts = <Map<String, dynamic>>[
  {
    'id': 7,
    'contract_number': 'ROAD-CUSTOMER-20',
    'contract_name': 'Road customer contract',
    'contract_role': 'PAYEE',
    'status': 'DRAFT',
    'customer_id': 20,
    'currency': 'EUR',
    'lines': [
      {
        'id': 71,
        'line_number': 10,
        'charge_component_code': 'ROAD_FREIGHT_FTL',
        'rate_book_id': 4,
        'mode': 'ROAD',
        'priority': 100,
        'is_active': true,
      },
    ],
  },
];

final _quote = <String, dynamic>{
  'id': 9,
  'request_number': 'ROAD-Q-9',
  'status': 'REQUESTED',
  'source_object_type': 'ROAD_SHIPMENT',
  'source_object_id': 'SHIP-9',
  'customer_id': 20,
  'origin_code': 'ESBCN',
  'destination_code': 'ESMAD',
  'mode': 'ROAD',
  'equipment_type': 'CURTAINSIDER',
  'service_level': 'STANDARD',
  'currency': 'EUR',
  'quantity': '1',
  'requested_service_date': '2026-08-15',
  'charge_context': 'ROAD',
  'context': <String, dynamic>{},
  'calculation_inputs': {'DISTANCE_KM': '620'},
  'component_calculation_inputs': <String, dynamic>{},
  'date_values': [
    {'date_type': 'ROAD_ACTUAL_PICKUP_DATE', 'date_value': '2026-08-15'},
  ],
};

final _ratedOption = <String, dynamic>{
  'id': 90,
  'quote_request_id': 9,
  'option_name': 'ROAD-CUSTOMER-20',
  'payee_contract_id': 7,
  'payer_total_amount': '0.00',
  'payee_total_amount': '950.00',
  'margin_amount': '950.00',
  'margin_percent': '100.00',
  'lines': [
    {
      'id': 901,
      'relationship_role': 'PAYEE',
      'charge_component_code': 'ROAD_FREIGHT_FTL',
      'basis': 'FLAT',
      'quantity': '1',
      'amount': '950.00',
      'currency': 'EUR',
      'source_contract_id': 7,
      'source_contract_line_id': 71,
      'source_rate_book_id': 4,
      'source_rate_book_entry_id': 44,
      'source_calculation_template_id': 3,
      'source_calculation_template_step_id': 31,
    },
    {
      'id': 902,
      'relationship_role': 'PAYEE',
      'charge_component_code': 'ROAD_INTERNAL_COST_REFERENCE',
      'basis': 'DISTANCE',
      'quantity': '620',
      'amount': '384.40',
      'currency': 'EUR',
      'source_contract_id': 7,
      'source_rate_book_id': 5,
      'source_rate_book_entry_id': 55,
      'source_calculation_template_id': 3,
      'source_calculation_template_step_id': 32,
      'is_statistical': true,
    },
  ],
};

FilePicker? _safeCurrentPicker() {
  try {
    return FilePicker.platform;
  } catch (_) {
    return null;
  }
}

class _TestFilePicker extends FilePicker {
  _TestFilePicker(this.result);

  final FilePickerResult? result;

  @override
  Future<FilePickerResult?> pickFiles({
    String? dialogTitle,
    String? initialDirectory,
    FileType type = FileType.any,
    List<String>? allowedExtensions,
    Function(FilePickerStatus)? onFileLoading,
    bool allowCompression = false,
    int compressionQuality = 0,
    bool allowMultiple = false,
    bool withData = false,
    bool withReadStream = false,
    bool lockParentWindow = false,
    bool readSequential = false,
  }) async {
    return result;
  }
}
