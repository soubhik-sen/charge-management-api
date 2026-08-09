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

  test('loads workspace resources across all server pages', () async {
    final componentOffsets = <String>[];
    final client = MockClient((request) async {
      expect(request.headers['Authorization'], 'Bearer test-token');

      if (request.url.path == '/api/v1/charge-management/components') {
        final offset = request.url.queryParameters['offset'] ?? '0';
        componentOffsets.add(offset);
        final start = int.parse(offset);
        final end = (start + 100).clamp(0, 205);
        return http.Response(
          jsonEncode({
            'items': [
              for (var id = start + 1; id <= end; id++)
                {'id': id, 'component_code': 'COMP-$id'},
            ],
            'total': 205,
            'limit': 100,
            'offset': start,
          }),
          200,
        );
      }

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

    expect(componentOffsets, ['0', '100', '200']);
    expect(data['components'], hasLength(205));
    expect(data['components'].first['component_code'], 'COMP-1');
    expect(data['components'].last['component_code'], 'COMP-205');
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

  test(
    'sends authenticated JSON mutations with the requested method',
    () async {
      late http.Request captured;
      final client = MockClient((request) async {
        captured = request;
        return http.Response(
          jsonEncode({'id': 42, 'component_code': 'SECURITY'}),
          201,
        );
      });
      final api = LedgerFlowApiClient(
        baseUrl: 'https://api.example.test/',
        token: 'write-token',
        httpClient: client,
      );

      final result = await api.requestJson(
        'POST',
        '/api/v1/charge-management/components',
        body: {'component_code': 'SECURITY', 'component_name': 'Security fee'},
      );

      expect(captured.method, 'POST');
      expect(captured.url.path, '/api/v1/charge-management/components');
      expect(captured.headers['Authorization'], 'Bearer write-token');
      expect(captured.headers['Content-Type'], contains('application/json'));
      expect(jsonDecode(captured.body)['component_name'], 'Security fee');
      expect(result['id'], 42);
    },
  );

  test('loads business-date assignments for the selected profile', () async {
    late Uri requested;
    final client = MockClient((request) async {
      requested = request.url;
      return http.Response(
        jsonEncode({
          'items': [
            {'id': 9, 'scope_type': 'GLOBAL'},
          ],
          'total': 1,
          'limit': 100,
          'offset': 0,
        }),
        200,
      );
    });
    final api = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: client,
    );

    final assignments = await api.loadBusinessDateAssignments(7);

    expect(
      requested.path,
      '/api/v1/charge-management/business-date-profiles/7/assignments',
    );
    expect(assignments.single['scope_type'], 'GLOBAL');
  });

  test('fails when pagination metadata does not advance safely', () async {
    final client = MockClient((request) async {
      return http.Response(
        jsonEncode({
          'items': [
            {'id': 9, 'scope_type': 'GLOBAL'},
          ],
          'total': 200,
          'limit': 100,
          'offset': 0,
        }),
        200,
      );
    });
    final api = LedgerFlowApiClient(
      baseUrl: 'https://api.example.test',
      token: 'test-token',
      httpClient: client,
    );

    await expectLater(
      api.loadBusinessDateAssignments(7),
      throwsA(
        isA<LedgerFlowApiException>().having(
          (error) => error.message,
          'message',
          'The API returned too many list pages or an invalid pagination sequence.',
        ),
      ),
    );
  });
}
