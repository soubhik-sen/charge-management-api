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
  static const defaultToken = String.fromEnvironment('LEDGERFLOW_API_TOKEN');

  final String baseUrl;
  final String token;
  final http.Client _httpClient;

  static const _defaultPageSize = 100;
  static const _maxListRequests = 100;

  static const _resources = <String, String>{
    'components': '/api/v1/charge-management/components',
    'rateBooks': '/api/v1/charge-management/rate-books',
    'calculationTemplates': '/api/v1/charge-management/calculation-templates',
    'quotes': '/api/v1/charge-management/quote-requests',
    'documents': '/api/v1/charge-management/charge-documents',
    'invoices': '/api/v1/charge-management/invoices',
    'fxRates': '/api/v1/charge-management/fx-rates',
    'dateProfiles': '/api/v1/charge-management/business-date-profiles',
    'allocationProfiles': '/api/v1/charge-management/allocation-profiles',
    'calculationProfiles': '/api/v1/charge-management/calculation-profiles',
    'contracts': '/api/v1/charge-management/contracts',
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
    '/api/v1/charge-management/business-date-profiles/$profileId/assignments',
  );

  Future<List<JsonMap>> _list(String path) async {
    final items = <JsonMap>[];
    var offset = 0;

    for (
      var requestCount = 0;
      requestCount < _maxListRequests;
      requestCount++
    ) {
      final response = await _httpClient.get(
        _pagedUri(path, limit: _defaultPageSize, offset: offset),
        headers: _headers,
      );
      if (response.statusCode < 200 || response.statusCode >= 300) {
        throw LedgerFlowApiException.fromResponse(response);
      }
      final page = _parseListPage(response.body);
      items.addAll(page.items);

      if (items.length >= page.total) {
        return List.unmodifiable(items);
      }

      final nextOffset = page.offset + page.limit;
      if (page.limit <= 0 || nextOffset <= offset) {
        break;
      }
      offset = nextOffset;
    }

    throw const LedgerFlowApiException(
      'The API returned too many list pages or an invalid pagination sequence.',
    );
  }

  Uri _pagedUri(String path, {required int limit, required int offset}) {
    final uri = Uri.parse('$baseUrl$path');
    final queryParameters = Map<String, String>.from(uri.queryParameters);
    queryParameters['limit'] = '$limit';
    queryParameters['offset'] = '$offset';
    return uri.replace(queryParameters: queryParameters);
  }

  _ListPage _parseListPage(String responseBody) {
    final payload = jsonDecode(responseBody);
    if (payload is! Map<String, dynamic> || payload['items'] is! List) {
      throw const LedgerFlowApiException(
        'The API returned an unexpected list response.',
      );
    }
    final total = _readInt(payload['total']);
    final limit = _readInt(payload['limit']);
    final offset = _readInt(payload['offset']);
    if (total == null || limit == null || offset == null) {
      throw const LedgerFlowApiException(
        'The API returned an unexpected list response.',
      );
    }
    return _ListPage(
      items: (payload['items'] as List)
          .whereType<Map<String, dynamic>>()
          .map(JsonMap.from)
          .toList(growable: false),
      total: total,
      limit: limit,
      offset: offset,
    );
  }

  int? _readInt(dynamic value) => switch (value) {
    int number => number,
    String text => int.tryParse(text),
    _ => null,
  };

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

class _ListPage {
  const _ListPage({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
  });

  final List<JsonMap> items;
  final int total;
  final int limit;
  final int offset;
}
