import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ledgerflow_web/core/api_client.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/data/workspace_data.dart';
import 'package:ledgerflow_web/features/caller_mappings_workspace.dart';

void main() {
  testWidgets('previews raw caller attributes with the selected profile', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    JsonMap? requestBody;
    final apiClient = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: MockClient((request) async {
        expect(
          request.url.path,
          '/api/v1/charge-management/caller-mapping-profiles/21/preview',
        );
        expect(request.headers['Authorization'], 'Bearer test-token');
        requestBody = JsonMap.from(
          jsonDecode(request.body) as Map<String, dynamic>,
        );
        return http.Response(
          jsonEncode({
            'profile_code': 'TMS_V2_ROAD',
            'caller_system_code': 'ACME_TMS',
            'schema_version': '2',
            'dimension_values': {'DELIVERY_ZONE': 'CENTRAL'},
            'standard_fields': <String, dynamic>{},
          }),
          200,
        );
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: CallerMappingsWorkspace(
            pricingDimensions: _pricingDimensions,
            callerMappingProfiles: _profiles,
            live: true,
            client: apiClient,
            onMutation:
                ({
                  required method,
                  required path,
                  body,
                  required successMessage,
                }) async => true,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byIcon(Icons.lock_outline), findsWidgets);
    await tester.tap(find.text('Profiles'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, 'Preview'));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.widgetWithText(TextFormField, 'Caller attributes JSON'),
      '{"shipment":{"deliveryZone":"central"}}',
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Run preview'));
    await tester.pumpAndSettle();

    expect(requestBody, {
      'caller_attributes': {
        'shipment': {'deliveryZone': 'central'},
      },
    });
    expect(find.text('Normalized preview'), findsOneWidget);
    expect(find.textContaining('"DELIVERY_ZONE": "CENTRAL"'), findsOneWidget);
  });
}

final List<JsonMap> _pricingDimensions = [
  {
    'id': 1,
    'dimension_code': 'ORIGIN_CODE',
    'dimension_name': 'Origin',
    'data_type': 'STRING',
    'built_in_field': 'origin_code',
    'is_system': true,
    'is_active': true,
  },
  {
    'id': 8,
    'dimension_code': 'DELIVERY_ZONE',
    'dimension_name': 'Delivery zone',
    'description': 'Canonical last-mile pricing zone.',
    'data_type': 'STRING',
    'allowed_values': ['CENTRAL', 'NORTH'],
    'built_in_field': null,
    'is_system': false,
    'is_active': true,
  },
];

final List<JsonMap> _profiles = [
  {
    'id': 21,
    'profile_code': 'TMS_V2_ROAD',
    'profile_name': 'TMS road schema v2',
    'caller_system_code': 'ACME_TMS',
    'schema_version': '2',
    'canonical_dimension_codes': ['DELIVERY_ZONE'],
    'mappings': [
      {
        'source_attribute': 'shipment.deliveryZone',
        'dimension_code': 'DELIVERY_ZONE',
        'required': true,
        'default_value': null,
        'value_map': {'central': 'CENTRAL'},
      },
    ],
    'is_active': true,
  },
];
