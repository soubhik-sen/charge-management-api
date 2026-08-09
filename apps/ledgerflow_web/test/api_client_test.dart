import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ledgerflow_web/core/api_client.dart';

void main() {
  test('loads all module lists with the bearer token', () async {
    final requested = <Uri>[];
    final client = MockClient((request) async {
      requested.add(request.url);
      expect(request.headers['Authorization'], 'Bearer test-token');
      return http.Response(
        jsonEncode({
          'items': <Object>[],
          'total': 0,
          'limit': 100,
          'offset': 0,
        }),
        200,
      );
    });

    final data = await LedgerFlowApiClient(
      baseUrl: 'https://api.example.test/',
      token: 'test-token',
      httpClient: client,
    ).loadWorkspace();

    expect(requested, hasLength(10));
    expect(requested.every((uri) => uri.host == 'api.example.test'), isTrue);
    expect(data['components'], isEmpty);
  });

  test('surfaces API detail errors', () async {
    final client = MockClient(
      (_) async => http.Response(jsonEncode({'detail': 'Token expired'}), 401),
    );
    final api = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'expired',
      httpClient: client,
    );

    await expectLater(
      api.loadWorkspace(),
      throwsA(
        isA<LedgerFlowApiException>().having(
          (error) => error.message,
          'message',
          'Token expired',
        ),
      ),
    );
  });
}
