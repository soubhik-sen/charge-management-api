import 'dart:convert';

import 'package:http/http.dart' as http;

import '../data/workspace_data.dart';

class LedgerFlowApiClient {
  LedgerFlowApiClient({
    required String baseUrl,
    required this.token,
    http.Client? httpClient,
  }) : baseUrl = baseUrl.replaceFirst(RegExp(r'/+$'), ''),
       _httpClient = httpClient ?? http.Client();

  static const defaultBaseUrl = String.fromEnvironment(
    'LEDGERFLOW_API_URL',
    defaultValue: 'http://localhost:8000',
  );

  final String baseUrl;
  final String token;
  final http.Client _httpClient;

  static const _resources = <String, String>{
    'components': '/api/v1/charge-management/components?limit=100&offset=0',
    'rateBooks': '/api/v1/charge-management/rate-books?limit=100&offset=0',
    'quotes': '/api/v1/charge-management/quote-requests?limit=100&offset=0',
    'documents':
        '/api/v1/charge-management/charge-documents?limit=100&offset=0',
    'invoices': '/api/v1/charge-management/invoices?limit=100&offset=0',
    'fxRates': '/api/v1/charge-management/fx-rates?limit=100&offset=0',
    'dateProfiles':
        '/api/v1/charge-management/business-date-profiles?limit=100&offset=0',
    'allocationProfiles':
        '/api/v1/charge-management/allocation-profiles?limit=100&offset=0',
    'calculationProfiles':
        '/api/v1/charge-management/calculation-profiles?limit=100&offset=0',
    'contracts': '/api/v1/charge-management/contracts?limit=100&offset=0',
  };

  Future<WorkspaceData> loadWorkspace() async {
    final loaded = await Future.wait(
      _resources.entries.map(
        (entry) async => MapEntry(entry.key, await _list(entry.value)),
      ),
    );
    return WorkspaceData(Map.fromEntries(loaded));
  }

  Future<JsonMap> requestJson(
    String method,
    String path, {
    JsonMap? body,
  }) async {
    final request = http.Request(
      method.toUpperCase(),
      Uri.parse('$baseUrl$path'),
    )..headers.addAll(_headers);
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }
    final streamed = await _httpClient.send(request);
    final response = await http.Response.fromStream(streamed);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw LedgerFlowApiException.fromResponse(response);
    }
    if (response.body.trim().isEmpty) return <String, dynamic>{};
    final payload = jsonDecode(response.body);
    if (payload is! Map<String, dynamic>) {
      throw const LedgerFlowApiException(
        'The API returned an unexpected object response.',
      );
    }
    return JsonMap.from(payload);
  }

  Future<List<JsonMap>> loadBusinessDateAssignments(int profileId) => _list(
    '/api/v1/charge-management/business-date-profiles/$profileId/assignments'
    '?limit=100&offset=0',
  );

  Future<List<JsonMap>> _list(String path) async {
    final response = await _httpClient.get(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
    );
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw LedgerFlowApiException.fromResponse(response);
    }
    final payload = jsonDecode(response.body);
    if (payload is! Map<String, dynamic> || payload['items'] is! List) {
      throw const LedgerFlowApiException(
        'The API returned an unexpected list response.',
      );
    }
    return (payload['items'] as List)
        .whereType<Map<String, dynamic>>()
        .map(JsonMap.from)
        .toList(growable: false);
  }

  Map<String, String> get _headers => {
    'Accept': 'application/json',
    'Authorization': 'Bearer $token',
  };
}

class LedgerFlowApiException implements Exception {
  const LedgerFlowApiException(this.message, {this.statusCode});

  factory LedgerFlowApiException.fromResponse(http.Response response) {
    var detail = 'Request failed with status ${response.statusCode}.';
    try {
      final payload = jsonDecode(response.body);
      if (payload is Map<String, dynamic> && payload['detail'] != null) {
        detail = payload['detail'].toString();
      }
    } on FormatException {
      // Keep the status-based message when the server response is not JSON.
    }
    return LedgerFlowApiException(detail, statusCode: response.statusCode);
  }

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}
