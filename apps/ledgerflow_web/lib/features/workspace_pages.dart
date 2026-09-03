import 'dart:convert';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/design.dart';
import '../core/reference_values.dart';
import '../data/workspace_data.dart';
import 'transaction_record_list.dart';

typedef WorkspaceMutation =
    Future<bool> Function({
      required String method,
      required String path,
      JsonMap? body,
      required String successMessage,
    });

class OperationsDashboard extends StatelessWidget {
  const OperationsDashboard({
    required this.data,
    required this.onOpen,
    super.key,
  });

  final WorkspaceData data;
  final ValueChanged<int> onOpen;

  @override
  Widget build(BuildContext context) {
    final quotes = data['quotes'];
    final documents = data['documents'];
    final invoices = data['invoices'];
    final openQuotes = quotes
        .where((item) => !_terminal(_text(item, 'status')))
        .length;
    final approvals = documents.where((item) {
      final status = _text(item, 'status').toUpperCase();
      return status.contains('APPROVAL') || status == 'REVIEW';
    }).length;
    final variance = invoices.fold<double>(0, (sum, invoice) {
      return sum +
          _rows(invoice, 'lines').fold<double>(0, (lineSum, line) {
            return lineSum + _number(line['variance_amount']);
          });
    });
    final payeeTotal = documents.fold<double>(
      0,
      (sum, item) => sum + _number(item['payee_total_amount']),
    );
    final marginTotal = documents.fold<double>(
      0,
      (sum, item) => sum + _number(item['margin_amount']),
    );
    final margin = payeeTotal == 0 ? 0 : marginTotal / payeeTotal * 100;

    return PageCanvas(
      title: 'Charge operations',
      subtitle:
          'Monitor quoting, charge calculation, approvals, and invoice reconciliation.',
      trailing: FilledButton.icon(
        onPressed: () => onOpen(1),
        icon: const Icon(Icons.add),
        label: const Text('New quote'),
      ),
      children: [
        ResponsiveMetricGrid(
          children: [
            MetricCard(
              label: 'Open quotes',
              value: '$openQuotes',
              detail: '${quotes.length} total requests',
              icon: Icons.request_quote_outlined,
              color: LedgerFlowDesign.teal,
            ),
            MetricCard(
              label: 'Awaiting approval',
              value: '$approvals',
              detail: '${documents.length} charge documents',
              icon: Icons.approval_outlined,
              color: LedgerFlowDesign.warning,
            ),
            MetricCard(
              label: 'Invoice variance',
              value: _money(variance, currency: 'USD'),
              detail: '${invoices.length} invoices monitored',
              icon: Icons.difference_outlined,
              color: LedgerFlowDesign.danger,
            ),
            MetricCard(
              label: 'Projected margin',
              value: '${margin.toStringAsFixed(1)}%',
              detail: _money(marginTotal, currency: 'USD'),
              icon: Icons.trending_up,
              color: LedgerFlowDesign.success,
            ),
          ],
        ),
        const SizedBox(height: 16),
        ResponsiveColumns(
          leftFlex: 3,
          rightFlex: 2,
          left: SurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionHeading(
                  title: 'Charge volume & margin',
                  subtitle: 'Six-month operating trend',
                ),
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  height: 255,
                  child: CustomPaint(painter: _TrendPainter()),
                ),
              ],
            ),
          ),
          right: SurfaceCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SectionHeading(
                  title: 'Approval queue',
                  subtitle: 'Exception-first review',
                  action: TextButton(
                    onPressed: () => onOpen(3),
                    child: const Text('View all'),
                  ),
                ),
                const SizedBox(height: 8),
                if (documents.isEmpty)
                  const EmptyState(
                    message: 'No charge documents require review.',
                  )
                else
                  ...documents
                      .take(4)
                      .map((document) => _QueueRow(document: document)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        SurfaceCard(
          padding: EdgeInsets.zero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 16, 18, 8),
                child: SectionHeading(
                  title: 'Recent charge documents',
                  subtitle: 'Calculation and approval status',
                  action: TextButton(
                    onPressed: () => onOpen(3),
                    child: const Text('View all'),
                  ),
                ),
              ),
              _DocumentTable(documents: documents.take(6).toList()),
            ],
          ),
        ),
      ],
    );
  }
}

class QuoteWorkspace extends StatefulWidget {
  const QuoteWorkspace({required this.quotes, super.key});

  final List<JsonMap> quotes;

  @override
  State<QuoteWorkspace> createState() => _QuoteWorkspaceState();
}

class _QuoteWorkspaceState extends State<QuoteWorkspace> {
  int _selected = 0;

  @override
  Widget build(BuildContext context) {
    if (widget.quotes.isEmpty) {
      return const PageCanvas(
        title: 'Quotes',
        subtitle: 'Compare rated commercial options and award the best fit.',
        children: [EmptyState(message: 'No quote requests are available.')],
      );
    }
    final safeIndex = math.min(_selected, widget.quotes.length - 1);
    final quote = widget.quotes[safeIndex];
    final options = _rows(quote, 'options');
    final selectedOption = options.isEmpty ? null : options.first;
    return PageCanvas(
      title:
          '${_text(quote, 'origin_code')}  ->  ${_text(quote, 'destination_code')}',
      eyebrow:
          'Quotes / ${_text(quote, 'request_number', fallback: '#${quote['id']}')}',
      subtitle:
          '${_text(quote, 'equipment_type')}  |  ${_text(quote, 'mode')}  |  Requested ${_text(quote, 'requested_service_date')}',
      trailing: StatusPill(_text(quote, 'status')),
      children: [
        _RecordPicker(
          records: widget.quotes,
          selectedIndex: safeIndex,
          label: (item) =>
              _text(item, 'request_number', fallback: '#${item['id']}'),
          detail: (item) =>
              '${_text(item, 'origin_code')} -> ${_text(item, 'destination_code')}',
          onSelected: (index) => setState(() => _selected = index),
        ),
        const SizedBox(height: 16),
        const _LifecycleStrip(
          steps: ['Request', 'Contracts', 'Rated', 'Ranked', 'Awarded'],
          activeIndex: 3,
        ),
        const SizedBox(height: 16),
        ResponsiveColumns(
          leftFlex: 3,
          rightFlex: 1,
          left: Column(
            children: [
              SurfaceCard(
                padding: EdgeInsets.zero,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.all(18),
                      child: SectionHeading(
                        title: 'Ranked options',
                        subtitle:
                            'Commercial outcome, service score, and policy compliance',
                      ),
                    ),
                    if (options.isEmpty)
                      const Padding(
                        padding: EdgeInsets.fromLTRB(18, 0, 18, 18),
                        child: EmptyState(
                          message:
                              'This request has no ranked options yet. Rate the quote through the API workspace.',
                        ),
                      )
                    else
                      _OptionComparison(options: options),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SurfaceCard(
                padding: EdgeInsets.zero,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(18),
                      child: SectionHeading(
                        title:
                            'Charge lines${selectedOption == null ? '' : ' - ${_text(selectedOption, 'option_name')}'}',
                        subtitle: 'Payer, payee, and margin breakdown',
                      ),
                    ),
                    _QuoteLineTable(
                      lines: selectedOption == null
                          ? const []
                          : _rows(selectedOption, 'lines'),
                    ),
                  ],
                ),
              ),
            ],
          ),
          right: Column(
            children: [
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeading(title: 'Request details'),
                    const SizedBox(height: 14),
                    DetailRow(
                      label: 'Origin',
                      value: _text(quote, 'origin_code'),
                    ),
                    DetailRow(
                      label: 'Destination',
                      value: _text(quote, 'destination_code'),
                    ),
                    DetailRow(
                      label: 'Equipment',
                      value: _text(quote, 'equipment_type'),
                    ),
                    DetailRow(
                      label: 'Service date',
                      value: _text(quote, 'requested_service_date'),
                    ),
                    DetailRow(
                      label: 'Currency',
                      value: _text(quote, 'currency'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeading(title: 'Matched contracts'),
                    const SizedBox(height: 12),
                    const _ContractTile(
                      type: 'BUY',
                      code: 'PAY-ATLANTIC-26',
                      party: 'BlueWave Shipping',
                    ),
                    const Divider(height: 24),
                    const _ContractTile(
                      type: 'SELL',
                      code: 'SELL-ATLAS-26',
                      party: 'Atlas Retail',
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class ChargeDocumentWorkspace extends StatefulWidget {
  const ChargeDocumentWorkspace({
    required this.documents,
    required this.live,
    required this.client,
    required this.onReload,
    super.key,
  });

  final List<JsonMap> documents;
  final bool live;
  final LedgerFlowApiClient? client;
  final Future<void> Function() onReload;

  @override
  State<ChargeDocumentWorkspace> createState() =>
      _ChargeDocumentWorkspaceState();
}

class _ChargeDocumentWorkspaceState extends State<ChargeDocumentWorkspace> {
  int _selected = 0;
  int _selectedLine = 0;
  bool _busy = false;
  JsonMap? _workspace;
  JsonMap? _lastExport;

  static const _mutableStatuses = <String>{
    'ESTIMATED',
    'ACCRUED',
    'ACTUAL',
    'DISPUTED',
  };

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadWorkspace());
  }

  @override
  void didUpdateWidget(covariant ChargeDocumentWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    final oldSelectedId = oldWidget.documents.isEmpty
        ? null
        : _asInt(
            oldWidget.documents[_selected.clamp(
              0,
              oldWidget.documents.length - 1,
            )]['id'],
          );
    if (_selected >= widget.documents.length) {
      _selected = widget.documents.isEmpty ? 0 : widget.documents.length - 1;
    }
    if (oldSelectedId != _selectedDocumentId || oldWidget.live != widget.live) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _loadWorkspace());
    }
  }

  int? get _selectedDocumentId => widget.documents.isEmpty
      ? null
      : _asInt(
          widget.documents[_selected.clamp(
            0,
            widget.documents.length - 1,
          )]['id'],
        );

  JsonMap? get _listDocument => widget.documents.isEmpty
      ? null
      : widget.documents[_selected.clamp(0, widget.documents.length - 1)];

  JsonMap? get _document {
    final nested = _workspace?['document'];
    return nested is Map<String, dynamic>
        ? JsonMap.from(nested)
        : _listDocument;
  }

  List<JsonMap> get _invoices => _rows(_workspace ?? const {}, 'invoices');
  List<JsonMap> get _matchResults =>
      _rows(_workspace ?? const {}, 'match_results');

  JsonMap? get _sourceQuoteOption {
    final nested = _workspace?['source_quote_option'];
    return nested is Map<String, dynamic> ? JsonMap.from(nested) : null;
  }

  List<JsonMap> get _approvalChecks {
    final checks = _rows(_workspace ?? const {}, 'approval_checks');
    if (checks.isNotEmpty) return checks;
    final document = _document;
    if (document == null) return const [];
    final statusValue = _text(document, 'status').toUpperCase();
    final blockedStatus = {
      'DISPUTED',
      'EXPORTED',
      'REVERSED',
    }.contains(statusValue);
    final blocker = _localProcessingBlocker(_rows(document, 'lines'));
    return [
      {
        'code': 'STATUS_ELIGIBLE',
        'label': 'Document status permits approval',
        'passed': !blockedStatus,
        'detail': blockedStatus
            ? 'Status $statusValue cannot be approved.'
            : 'Status $statusValue is eligible for approval.',
      },
      {
        'code': 'LINE_PROCESSING_COMPLETE',
        'label': 'Calculations and allocations are complete',
        'passed': blocker == null,
        'detail': blocker ?? 'No line has pending or failed processing.',
      },
    ];
  }

  bool get _approvalReady => _workspace?['approval_ready'] is bool
      ? _workspace!['approval_ready'] == true
      : _approvalChecks.every((check) => check['passed'] == true);

  Future<void> _loadWorkspace() async {
    final id = _selectedDocumentId;
    final client = widget.client;
    if (!widget.live || id == null || client == null) {
      if (mounted) setState(() => _workspace = null);
      return;
    }
    setState(() => _busy = true);
    try {
      final response = await client.requestJson(
        'GET',
        '/api/v1/charge-management/charge-documents/$id/workspace',
      );
      if (!mounted) return;
      setState(() {
        _workspace = response;
        final lines = _rows(_document ?? const {}, 'lines');
        _selectedLine = lines.isEmpty
            ? 0
            : _selectedLine.clamp(0, lines.length - 1);
      });
    } catch (error) {
      if (mounted) _showDocumentError(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<JsonMap?> _request(
    String method,
    String path, {
    JsonMap? body,
    required String success,
  }) async {
    final client = widget.client;
    if (client == null) return null;
    setState(() => _busy = true);
    try {
      final response = await client.requestJson(method, path, body: body);
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(success)));
      }
      await widget.onReload();
      await _loadWorkspace();
      return response;
    } catch (error) {
      if (mounted) _showDocumentError(error);
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showDocumentError(Object error) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Document action failed: $error'),
        backgroundColor: LedgerFlowDesign.danger,
      ),
    );
  }

  Future<void> _setStatus(JsonMap document) async {
    final statusValue = await showDialog<String>(
      context: context,
      builder: (_) => _DocumentStatusDialog(
        currentStatus: _text(document, 'status').toUpperCase(),
      ),
    );
    if (statusValue == null || statusValue == _text(document, 'status')) return;
    await _request(
      'PUT',
      '/api/v1/charge-management/charge-documents/${document['id']}/workspace',
      body: {'status': statusValue},
      success: 'Document status changed to $statusValue.',
    );
  }

  Future<void> _approve(JsonMap document) async {
    final confirmed = await _confirmAction(
      context,
      title: 'Approve ${_text(document, 'document_number')}?',
      message:
          'Approval locks the document and copies each line actual amount, or expected amount when actual is absent, into its approved amount.',
      action: 'Approve',
    );
    if (!confirmed) return;
    await _request(
      'POST',
      '/api/v1/charge-management/charge-documents/${document['id']}/approve',
      success: 'Charge document approved.',
    );
  }

  Future<void> _export(JsonMap document) async {
    final response = await _request(
      'POST',
      '/api/v1/charge-management/charge-documents/${document['id']}/post-export',
      success: _text(document, 'status').toUpperCase() == 'EXPORTED'
          ? 'Existing export batch loaded.'
          : 'Internal export batch created.',
    );
    if (response == null || !mounted) return;
    setState(() => _lastExport = response);
    await showDialog<void>(
      context: context,
      builder: (_) => _ExportResultDialog(export: response),
    );
  }

  Future<void> _reverse(JsonMap document) async {
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => _DocumentReversalDialog(
        documentNumber: _text(document, 'document_number'),
      ),
    );
    if (reason == null) return;
    await _request(
      'POST',
      '/api/v1/charge-management/charge-documents/${document['id']}/reverse',
      body: {'reason': reason},
      success: 'Charge document reversed.',
    );
  }

  Future<void> _deleteDocument(JsonMap document) async {
    final confirmed = await _confirmAction(
      context,
      title: 'Delete ${_text(document, 'document_number')}?',
      message:
          'This permanently deletes the charge document and its lines. Documents linked to quotes, invoices, commitments, derived pricing, approvals, or exports are protected by the API.',
      action: 'Delete document',
      destructive: true,
    );
    if (!confirmed) return;
    final client = widget.client;
    if (client == null) return;
    setState(() => _busy = true);
    try {
      await client.requestJson(
        'DELETE',
        '/api/v1/charge-management/charge-documents/${document['id']}',
      );
      if (!mounted) return;
      setState(() {
        _selected = math.max(0, _selected - 1);
        _selectedLine = 0;
        _workspace = null;
        _lastExport = null;
      });
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Charge document deleted.')));
      await widget.onReload();
    } catch (error) {
      if (mounted) _showDocumentError(error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  JsonMap? _sourceQuoteLine(JsonMap line) {
    final sourceLineId = _asInt(line['source_quote_option_line_id']);
    if (sourceLineId == null) return null;
    for (final sourceLine in _rows(_sourceQuoteOption ?? const {}, 'lines')) {
      if (_asInt(sourceLine['id']) == sourceLineId) return sourceLine;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final document = _document;
    if (document == null) {
      return PageCanvas(
        title: 'Charge documents',
        subtitle:
            'Inspect calculated charges, provenance, approvals, and export readiness.',
        children: [
          if (!widget.live)
            const Padding(
              padding: EdgeInsets.only(bottom: 16),
              child: Text(
                'Connect a live API to execute document lifecycle actions.',
                style: TextStyle(color: LedgerFlowDesign.muted),
              ),
            ),
          const EmptyState(message: 'No charge documents are available.'),
        ],
      );
    }
    final index = math.min(_selected, widget.documents.length - 1);
    final lines = _rows(document, 'lines');
    final lineIndex = lines.isEmpty
        ? 0
        : math.min(_selectedLine, lines.length - 1);
    final selectedLine = lines.isEmpty ? null : lines[lineIndex];
    final currency = _text(document, 'currency', fallback: 'USD');
    final payer = _number(document['payer_total_amount']);
    final payee = _number(document['payee_total_amount']);
    final margin = _number(document['margin_amount']);
    final marginPercent = payee == 0 ? 0 : margin / payee * 100;
    final statusValue = _text(document, 'status').toUpperCase();
    final mutable = _mutableStatuses.contains(statusValue);
    final canApprove =
        widget.live &&
        !_busy &&
        mutable &&
        statusValue != 'DISPUTED' &&
        _approvalReady;
    final canExport =
        widget.live && !_busy && {'APPROVED', 'EXPORTED'}.contains(statusValue);
    final canReverse =
        widget.live && !_busy && {'APPROVED', 'EXPORTED'}.contains(statusValue);
    final sourceLine = selectedLine == null
        ? null
        : _sourceQuoteLine(selectedLine);
    return PageCanvas(
      title: _text(
        document,
        'document_number',
        fallback: 'Charge document #${document['id']}',
      ),
      eyebrow: 'Charge documents',
      subtitle:
          '${_text(document, 'source_object_type')} ${_text(document, 'source_object_id')}  |  Document date ${_text(document, 'document_date')}',
      trailing: Wrap(
        spacing: 10,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          StatusPill(statusValue),
          OutlinedButton.icon(
            onPressed: widget.live && !_busy && mutable
                ? () => _setStatus(document)
                : null,
            icon: const Icon(Icons.edit_note_outlined),
            label: const Text('Set status'),
          ),
          FilledButton.icon(
            onPressed: canApprove ? () => _approve(document) : null,
            icon: const Icon(Icons.approval_outlined),
            label: const Text('Approve'),
          ),
          OutlinedButton.icon(
            onPressed: canExport ? () => _export(document) : null,
            icon: const Icon(Icons.outbox_outlined),
            label: Text(statusValue == 'EXPORTED' ? 'View export' : 'Export'),
          ),
          OutlinedButton.icon(
            onPressed: canReverse ? () => _reverse(document) : null,
            icon: const Icon(Icons.undo_outlined),
            label: const Text('Reverse'),
          ),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: LedgerFlowDesign.danger,
            ),
            onPressed: widget.live && !_busy && mutable
                ? () => _deleteDocument(document)
                : null,
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete'),
          ),
        ],
      ),
      children: [
        if (!widget.live) ...[
          const SurfaceCard(
            child: Text(
              'Demo mode is read-only. Connect the API to approve, export, reverse, or change document status.',
              style: TextStyle(color: LedgerFlowDesign.muted),
            ),
          ),
          const SizedBox(height: 16),
        ],
        if (_busy) const LinearProgressIndicator(minHeight: 2),
        if (_busy) const SizedBox(height: 10),
        TransactionRecordList(
          records: widget.documents,
          selectedIndex: index,
          searchHint: 'Search document, source, date, or status',
          emptyMessage: 'No charge documents are available.',
          searchText: (item) => [
            _text(item, 'document_number'),
            _text(item, 'source_object_type'),
            _text(item, 'source_object_id'),
            _text(item, 'document_date'),
            _text(item, 'status'),
          ].join(' '),
          status: (item) => _text(item, 'status'),
          columns: [
            TransactionListColumn(
              label: 'Document',
              flex: 2,
              value: (item) =>
                  _text(item, 'document_number', fallback: '#${item['id']}'),
            ),
            TransactionListColumn(
              label: 'Source',
              flex: 2,
              value: (item) =>
                  '${_text(item, 'source_object_type')} ${_text(item, 'source_object_id')}',
            ),
            TransactionListColumn(
              label: 'Document date',
              value: (item) =>
                  _text(item, 'document_date', fallback: 'Not set'),
            ),
            TransactionListColumn(
              label: 'Payee total',
              alignEnd: true,
              value: (item) => _money(
                _number(item['payee_total_amount']),
                currency: _text(item, 'currency', fallback: 'USD'),
              ),
            ),
            TransactionListColumn(
              label: 'Status',
              value: (item) => _text(item, 'status'),
              isStatus: true,
            ),
          ],
          onSelected: (value) {
            setState(() {
              _selected = value;
              _selectedLine = 0;
              _workspace = null;
              _lastExport = null;
            });
            WidgetsBinding.instance.addPostFrameCallback(
              (_) => _loadWorkspace(),
            );
          },
        ),
        const SizedBox(height: 16),
        ResponsiveMetricGrid(
          children: [
            MetricCard(
              label: 'Payer total',
              value: _money(payer, currency: currency),
              icon: Icons.call_made,
              color: LedgerFlowDesign.info,
            ),
            MetricCard(
              label: 'Payee total',
              value: _money(payee, currency: currency),
              icon: Icons.call_received,
              color: LedgerFlowDesign.teal,
            ),
            MetricCard(
              label: 'Margin',
              value: _money(margin, currency: currency),
              detail: '${marginPercent.toStringAsFixed(1)}%',
              icon: Icons.trending_up,
              color: LedgerFlowDesign.success,
            ),
            MetricCard(
              label: 'Charge lines',
              value: '${lines.length}',
              detail: 'Calculated and allocated',
              icon: Icons.table_rows_outlined,
              color: LedgerFlowDesign.warning,
            ),
          ],
        ),
        const SizedBox(height: 16),
        ResponsiveColumns(
          leftFlex: 3,
          rightFlex: 1,
          left: Column(
            children: [
              SurfaceCard(
                padding: EdgeInsets.zero,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.all(18),
                      child: SectionHeading(
                        title: 'Charge lines',
                        subtitle:
                            'Select a row to inspect calculation, allocation, date, and FX provenance',
                      ),
                    ),
                    _ChargeLineTable(
                      lines: lines,
                      selectedIndex: lineIndex,
                      onSelected: (value) =>
                          setState(() => _selectedLine = value),
                    ),
                  ],
                ),
              ),
              if (selectedLine != null) ...[
                const SizedBox(height: 16),
                _ProvenancePanel(
                  line: selectedLine,
                  sourceQuoteLine: sourceLine,
                ),
              ],
            ],
          ),
          right: Column(
            children: [
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeading(title: 'Document details'),
                    const SizedBox(height: 14),
                    DetailRow(
                      label: 'Source',
                      value:
                          '${_text(document, 'source_object_type')} ${_text(document, 'source_object_id')}',
                    ),
                    DetailRow(
                      label: 'Document date',
                      value: _text(document, 'document_date'),
                    ),
                    DetailRow(label: 'Currency', value: currency),
                    DetailRow(
                      label: 'Company / customer',
                      value:
                          '${_text(document, 'company_id', fallback: '—')} / ${_text(document, 'customer_id', fallback: '—')}',
                    ),
                    DetailRow(
                      label: 'Quote request',
                      value: _text(
                        document,
                        'quote_request_id',
                        fallback: 'Not linked',
                      ),
                    ),
                    DetailRow(
                      label: 'Quote option',
                      value: _text(
                        document,
                        'quote_option_id',
                        fallback: 'Not linked',
                      ),
                    ),
                    DetailRow(
                      label: 'Approved',
                      value: _text(document, 'approved_at', fallback: '—'),
                    ),
                    DetailRow(
                      label: 'Exported',
                      value: _text(document, 'exported_at', fallback: '—'),
                    ),
                    DetailRow(
                      label: 'Reversed',
                      value: _text(document, 'reversed_at', fallback: '—'),
                    ),
                    if (_text(document, 'reversal_reason').isNotEmpty)
                      DetailRow(
                        label: 'Reversal reason',
                        value: _text(document, 'reversal_reason'),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeading(title: 'Approval checks'),
                    const SizedBox(height: 12),
                    for (final check in _approvalChecks)
                      _CheckRow(
                        label: _text(check, 'label'),
                        detail: _text(check, 'detail'),
                        pass: check['passed'] == true,
                      ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: widget.live && !_busy
                            ? _loadWorkspace
                            : null,
                        icon: const Icon(Icons.refresh),
                        label: const Text('Refresh checks'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeading(title: 'Linked reconciliation'),
                    const SizedBox(height: 12),
                    DetailRow(label: 'Invoices', value: '${_invoices.length}'),
                    DetailRow(
                      label: 'Match results',
                      value: '${_matchResults.length}',
                    ),
                    DetailRow(
                      label: 'Source option',
                      value: _sourceQuoteOption == null
                          ? 'Direct / manual'
                          : _text(
                              _sourceQuoteOption!,
                              'option_name',
                              fallback: '#${_sourceQuoteOption!['id']}',
                            ),
                    ),
                  ],
                ),
              ),
              if (_lastExport != null) ...[
                const SizedBox(height: 16),
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeading(title: 'Last export result'),
                      const SizedBox(height: 12),
                      DetailRow(
                        label: 'Batch',
                        value: _text(_lastExport!, 'export_number'),
                      ),
                      DetailRow(
                        label: 'Target',
                        value: _text(_lastExport!, 'target_system'),
                      ),
                      DetailRow(
                        label: 'Status',
                        value: _text(_lastExport!, 'status'),
                      ),
                      const SizedBox(height: 8),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton(
                          onPressed: () => showDialog<void>(
                            context: context,
                            builder: (_) =>
                                _ExportResultDialog(export: _lastExport!),
                          ),
                          child: const Text('Inspect payload'),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class InvoiceWorkspace extends StatefulWidget {
  const InvoiceWorkspace({
    required this.invoices,
    this.documents = const [],
    this.components = const [],
    this.live = false,
    this.client,
    this.onReload,
    super.key,
  });

  final List<JsonMap> invoices;
  final List<JsonMap> documents;
  final List<JsonMap> components;
  final bool live;
  final LedgerFlowApiClient? client;
  final Future<void> Function()? onReload;

  @override
  State<InvoiceWorkspace> createState() => _InvoiceWorkspaceState();
}

class _InvoiceWorkspaceState extends State<InvoiceWorkspace> {
  int _selected = 0;
  bool _busy = false;
  bool _loadingWorkspace = false;
  int _workspaceLoadSequence = 0;
  int? _loadedInvoiceId;
  JsonMap? _workspace;

  @override
  void initState() {
    super.initState();
    _scheduleWorkspaceLoad();
  }

  @override
  void didUpdateWidget(covariant InvoiceWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selected >= widget.invoices.length) {
      _selected = math.max(0, widget.invoices.length - 1);
    }
    final selectedId = widget.invoices.isEmpty
        ? null
        : _asInt(widget.invoices[_selected]['id']);
    if (selectedId != _loadedInvoiceId || oldWidget.client != widget.client) {
      _workspace = null;
      _loadedInvoiceId = null;
      _scheduleWorkspaceLoad();
    }
  }

  void _scheduleWorkspaceLoad() {
    if (!widget.live || widget.client == null || widget.invoices.isEmpty) {
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || widget.invoices.isEmpty) return;
      _loadInvoiceWorkspace(widget.invoices[_selected]);
    });
  }

  Future<void> _loadInvoiceWorkspace(JsonMap invoice) async {
    final client = widget.client;
    final invoiceId = _asInt(invoice['id']);
    if (client == null || invoiceId == null) return;
    final requestSequence = ++_workspaceLoadSequence;
    setState(() => _loadingWorkspace = true);
    try {
      final workspace = await client.requestJson(
        'GET',
        '/api/v1/charge-management/invoices/$invoiceId/workspace',
      );
      if (!mounted || requestSequence != _workspaceLoadSequence) return;
      setState(() {
        _workspace = workspace;
        _loadedInvoiceId = invoiceId;
      });
    } catch (error) {
      if (mounted && requestSequence == _workspaceLoadSequence) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not load invoice reconciliation: $error'),
            backgroundColor: LedgerFlowDesign.danger,
          ),
        );
      }
    } finally {
      if (mounted && requestSequence == _workspaceLoadSequence) {
        setState(() => _loadingWorkspace = false);
      }
    }
  }

  Future<void> _createInvoice() async {
    final client = widget.client;
    if (client == null || widget.documents.isEmpty) return;
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (context) => _InvoiceCreateDialog(
        documents: widget.documents,
        components: widget.components,
      ),
    );
    if (payload == null) return;
    setState(() => _busy = true);
    try {
      await client.requestJson(
        'POST',
        '/api/v1/charge-management/invoices',
        body: payload,
      );
      if (!mounted) return;
      setState(() {
        _selected = 0;
        _workspace = null;
        _loadedInvoiceId = null;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Invoice created. Run Match invoice to reconcile it.'),
        ),
      );
      await widget.onReload?.call();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Invoice creation failed: $error'),
            backgroundColor: LedgerFlowDesign.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _matchInvoice(JsonMap invoice) async {
    final client = widget.client;
    final invoiceId = _asInt(invoice['id']);
    if (client == null || invoiceId == null) return;
    setState(() => _busy = true);
    try {
      await client.requestJson(
        'POST',
        '/api/v1/charge-management/invoices/$invoiceId/match',
      );
      await widget.onReload?.call();
      if (!mounted) return;
      await _loadInvoiceWorkspace(invoice);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Invoice matched.')));
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Invoice matching failed: $error'),
            backgroundColor: LedgerFlowDesign.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _newInvoiceButton() => FilledButton.icon(
    onPressed:
        widget.live &&
            !_busy &&
            widget.client != null &&
            widget.documents.isNotEmpty
        ? _createInvoice
        : null,
    icon: const Icon(Icons.add),
    label: const Text('New invoice'),
  );

  Future<void> _deleteInvoice(JsonMap invoice) async {
    final confirmed = await _confirmAction(
      context,
      title: 'Delete ${_text(invoice, 'invoice_number')}?',
      message:
          'This permanently deletes the invoice and its reconciliation results. The linked charge document is retained.',
      action: 'Delete invoice',
      destructive: true,
    );
    if (!confirmed) return;
    final client = widget.client;
    if (client == null) return;
    setState(() => _busy = true);
    try {
      await client.requestJson(
        'DELETE',
        '/api/v1/charge-management/invoices/${invoice['id']}',
      );
      if (!mounted) return;
      setState(() => _selected = math.max(0, _selected - 1));
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Invoice deleted.')));
      await widget.onReload?.call();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Invoice action failed: $error'),
            backgroundColor: LedgerFlowDesign.danger,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.invoices.isEmpty) {
      return PageCanvas(
        title: 'Invoice reconciliation',
        subtitle:
            'Match invoices to expected charge lines and resolve variances.',
        trailing: _newInvoiceButton(),
        children: [
          if (_busy) const LinearProgressIndicator(minHeight: 2),
          if (_busy) const SizedBox(height: 10),
          EmptyState(
            message: widget.documents.isEmpty
                ? 'Create a charge document before capturing an invoice.'
                : 'No invoices are available. Create one from a charge document.',
          ),
        ],
      );
    }
    final index = math.min(_selected, widget.invoices.length - 1);
    final listedInvoice = widget.invoices[index];
    final workspaceInvoice = _workspace?['invoice'];
    final invoice =
        _loadedInvoiceId == _asInt(listedInvoice['id']) &&
            workspaceInvoice is Map<String, dynamic>
        ? JsonMap.from(workspaceInvoice)
        : listedInvoice;
    final lines = _invoiceReconciliationRows(
      invoiceLines: _rows(invoice, 'lines'),
      matchResults: _rows(_workspace ?? const {}, 'match_results'),
    );
    final currency = _text(invoice, 'currency', fallback: 'USD');
    final total = _number(invoice['total_amount']);
    final expected = lines.fold<double>(
      0,
      (sum, line) => sum + _number(line['expected_amount']),
    );
    final variance = lines.fold<double>(
      0,
      (sum, line) => sum + _number(line['variance_amount']),
    );
    final matched = lines
        .where((line) => _text(line, 'status').toUpperCase() == 'MATCHED')
        .length;
    final exception = lines
        .where((line) => _number(line['variance_amount']).abs() > 0.001)
        .firstOrNull;
    final documentStatus = _text(
      _workspace?['charge_document'] is Map<String, dynamic>
          ? JsonMap.from(_workspace!['charge_document'] as Map<String, dynamic>)
          : invoice,
      _workspace?['charge_document'] is Map<String, dynamic>
          ? 'status'
          : 'charge_document_status',
      fallback: '',
    ).toUpperCase();
    final canDelete =
        widget.live &&
        !_busy &&
        !{'APPROVED', 'EXPORTED', 'REVERSED'}.contains(documentStatus);
    return PageCanvas(
      title: _text(
        invoice,
        'invoice_number',
        fallback: 'Invoice #${invoice['id']}',
      ),
      eyebrow: 'Invoices',
      subtitle:
          '${_text(invoice, 'invoice_type')}  |  ${_text(invoice, 'invoice_date')}  |  $currency',
      trailing: Wrap(
        spacing: 10,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          StatusPill(_text(invoice, 'status')),
          _newInvoiceButton(),
          FilledButton.icon(
            onPressed: widget.live && !_busy && widget.client != null
                ? () => _matchInvoice(invoice)
                : null,
            icon: const Icon(Icons.rule_folder_outlined),
            label: const Text('Match invoice'),
          ),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: LedgerFlowDesign.danger,
            ),
            onPressed: canDelete ? () => _deleteInvoice(invoice) : null,
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete'),
          ),
        ],
      ),
      children: [
        if (_busy || _loadingWorkspace)
          const LinearProgressIndicator(minHeight: 2),
        if (_busy || _loadingWorkspace) const SizedBox(height: 10),
        TransactionRecordList(
          records: widget.invoices,
          selectedIndex: index,
          searchHint: 'Search invoice, document, date, or status',
          emptyMessage: 'No invoices are available.',
          searchText: (item) => [
            _text(item, 'invoice_number'),
            _text(item, 'charge_document_number'),
            _text(item, 'invoice_type'),
            _text(item, 'invoice_date'),
            _text(item, 'currency'),
            _text(item, 'status'),
          ].join(' '),
          status: (item) => _text(item, 'status'),
          columns: [
            TransactionListColumn(
              label: 'Invoice',
              flex: 2,
              value: (item) =>
                  _text(item, 'invoice_number', fallback: '#${item['id']}'),
            ),
            TransactionListColumn(
              label: 'Charge document',
              flex: 2,
              value: (item) =>
                  _text(item, 'charge_document_number', fallback: 'Unlinked'),
            ),
            TransactionListColumn(
              label: 'Invoice date',
              value: (item) => _text(item, 'invoice_date', fallback: 'Not set'),
            ),
            TransactionListColumn(
              label: 'Total',
              alignEnd: true,
              value: (item) => _money(
                _number(item['total_amount']),
                currency: _text(item, 'currency', fallback: 'USD'),
              ),
            ),
            TransactionListColumn(
              label: 'Status',
              value: (item) => _text(item, 'status'),
              isStatus: true,
            ),
          ],
          onSelected: (value) {
            setState(() {
              _selected = value;
              _workspace = null;
              _loadedInvoiceId = null;
            });
            _loadInvoiceWorkspace(widget.invoices[value]);
          },
        ),
        const SizedBox(height: 16),
        ResponsiveMetricGrid(
          children: [
            MetricCard(
              label: 'Invoice total',
              value: _money(total, currency: currency),
              icon: Icons.receipt_long_outlined,
              color: LedgerFlowDesign.info,
            ),
            MetricCard(
              label: 'Expected total',
              value: _money(expected, currency: currency),
              icon: Icons.fact_check_outlined,
              color: LedgerFlowDesign.teal,
            ),
            MetricCard(
              label: 'Variance',
              value: _money(variance, currency: currency),
              detail: expected == 0
                  ? null
                  : '${(variance / expected * 100).toStringAsFixed(2)}%',
              icon: Icons.warning_amber_outlined,
              color: variance == 0
                  ? LedgerFlowDesign.success
                  : LedgerFlowDesign.danger,
            ),
            MetricCard(
              label: 'Matched lines',
              value: '$matched of ${lines.length}',
              icon: Icons.task_alt,
              color: LedgerFlowDesign.success,
            ),
          ],
        ),
        const SizedBox(height: 16),
        ResponsiveColumns(
          leftFlex: 3,
          rightFlex: 1,
          left: Column(
            children: [
              SurfaceCard(
                padding: EdgeInsets.zero,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Padding(
                      padding: EdgeInsets.all(18),
                      child: SectionHeading(
                        title: 'Line reconciliation',
                        subtitle:
                            'Exceptions are surfaced before matched lines',
                      ),
                    ),
                    _InvoiceLineTable(lines: lines, currency: currency),
                  ],
                ),
              ),
              if (exception != null) ...[
                const SizedBox(height: 16),
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Resolve variance',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: LedgerFlowDesign.danger,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        '${_text(exception, 'description')} differs by ${_money(_number(exception['variance_amount']), currency: currency)}.',
                        style: const TextStyle(color: LedgerFlowDesign.muted),
                      ),
                      const SizedBox(height: 16),
                      const Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          _ResolutionChoice(
                            title: 'Accept invoice amount',
                            detail: 'Use the supplier amount as final.',
                          ),
                          _ResolutionChoice(
                            title: 'Keep expected amount',
                            detail: 'Request a carrier credit note.',
                            selected: true,
                          ),
                          _ResolutionChoice(
                            title: 'Split difference',
                            detail: 'Allocate the variance between parties.',
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
          right: Column(
            children: [
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeading(title: 'Invoice details'),
                    const SizedBox(height: 14),
                    DetailRow(
                      label: 'Type',
                      value: _text(invoice, 'invoice_type'),
                    ),
                    DetailRow(
                      label: 'Invoice date',
                      value: _text(invoice, 'invoice_date'),
                    ),
                    DetailRow(
                      label: 'Charge document',
                      value: _text(
                        invoice,
                        'charge_document_number',
                        fallback: '#${invoice['charge_document_id']}',
                      ),
                    ),
                    DetailRow(label: 'Currency', value: currency),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              _MatchHealth(matched: matched, total: lines.length),
            ],
          ),
        ),
      ],
    );
  }
}

List<JsonMap> _invoiceReconciliationRows({
  required List<JsonMap> invoiceLines,
  required List<JsonMap> matchResults,
}) {
  if (matchResults.isEmpty) {
    return invoiceLines.indexed
        .map((entry) {
          final line = entry.$2;
          return JsonMap.from(line)
            ..putIfAbsent('line_number', () => entry.$1 + 1)
            ..putIfAbsent('invoiced_amount', () => line['amount'])
            ..putIfAbsent('status', () => 'CAPTURED');
        })
        .toList(growable: false);
  }
  final invoiceLinesByComponent = <String, JsonMap>{};
  for (final line in invoiceLines) {
    final code = _text(
      line,
      'charge_component_code',
      fallback: '',
    ).toUpperCase();
    if (code.isNotEmpty) invoiceLinesByComponent.putIfAbsent(code, () => line);
  }
  return matchResults.indexed
      .map((entry) {
        final result = entry.$2;
        final code = _text(
          result,
          'charge_component_code',
          fallback: '',
        ).toUpperCase();
        final invoiceLine = invoiceLinesByComponent[code] ?? const {};
        return <String, dynamic>{
          ...result,
          'line_number': entry.$1 + 1,
          'description': _text(invoiceLine, 'description', fallback: code),
          'matched_charge_line_id': result['charge_line_id'],
          'invoiced_amount': result['invoice_amount'],
          'status': result['match_status'],
        };
      })
      .toList(growable: false);
}

class _InvoiceCreateDialog extends StatefulWidget {
  const _InvoiceCreateDialog({
    required this.documents,
    required this.components,
  });

  final List<JsonMap> documents;
  final List<JsonMap> components;

  @override
  State<_InvoiceCreateDialog> createState() => _InvoiceCreateDialogState();
}

class _InvoiceCreateDialogState extends State<_InvoiceCreateDialog> {
  final _formKey = GlobalKey<FormState>();
  final _numberController = TextEditingController();
  late final TextEditingController _dateController;
  late int _documentId;
  String _invoiceType = 'SUPPLIER';
  List<_InvoiceDraftLine> _lines = [];

  JsonMap get _document => widget.documents.firstWhere(
    (item) => _asInt(item['id']) == _documentId,
    orElse: () => widget.documents.first,
  );

  String get _currency => _text(_document, 'currency', fallback: 'USD');

  @override
  void initState() {
    super.initState();
    _documentId = _asInt(widget.documents.first['id'])!;
    _dateController = TextEditingController(
      text: _formatIsoDate(DateTime.now()),
    );
    _replaceWithExpectedLines();
  }

  @override
  void dispose() {
    _numberController.dispose();
    _dateController.dispose();
    for (final line in _lines) {
      line.dispose();
    }
    super.dispose();
  }

  List<JsonMap> get _expectedDocumentLines {
    final expectedRole = _invoiceType == 'SUPPLIER' ? 'PAYER' : 'PAYEE';
    return _rows(_document, 'lines')
        .where((line) {
          final role = _text(line, 'relationship_role').toUpperCase();
          final lineRole = _text(
            line,
            'line_role',
            fallback: 'POSTING',
          ).toUpperCase();
          return role == expectedRole && lineRole == 'POSTING';
        })
        .toList(growable: false);
  }

  void _replaceWithExpectedLines() {
    for (final line in _lines) {
      line.dispose();
    }
    final aggregated = <String, _InvoiceDraftLine>{};
    for (final line in _expectedDocumentLines) {
      final code = _text(
        line,
        'charge_component_code',
        fallback: '',
      ).toUpperCase();
      if (code.isEmpty) continue;
      final existing = aggregated[code];
      if (existing == null) {
        aggregated[code] = _InvoiceDraftLine(
          componentCode: code,
          description: _text(line, 'description', fallback: code),
          amount: _number(line['expected_amount']).toStringAsFixed(2),
        );
      } else {
        final amount = _number(existing.amountController.text);
        existing.amountController.text =
            (amount + _number(line['expected_amount'])).toStringAsFixed(2);
      }
    }
    _lines = aggregated.values.toList(growable: true);
    if (_lines.isEmpty) _lines.add(_InvoiceDraftLine());
  }

  void _changeDocument(int? value) {
    if (value == null) return;
    setState(() {
      _documentId = value;
      _replaceWithExpectedLines();
    });
  }

  void _changeInvoiceType(String? value) {
    if (value == null) return;
    setState(() {
      _invoiceType = value;
      _replaceWithExpectedLines();
    });
  }

  void _addLine() => setState(() => _lines.add(_InvoiceDraftLine()));

  void _removeLine(int index) {
    if (_lines.length == 1) return;
    setState(() => _lines.removeAt(index).dispose());
  }

  Map<String, String> get _componentLabels {
    final labels = <String, String>{};
    for (final component in widget.components) {
      if (component['is_active'] == false) continue;
      final code = _text(
        component,
        'component_code',
        fallback: '',
      ).toUpperCase();
      if (code.isEmpty) continue;
      labels[code] =
          '${_text(component, 'component_name', fallback: code)} ($code)';
    }
    for (final line in _rows(_document, 'lines')) {
      final code = _text(
        line,
        'charge_component_code',
        fallback: '',
      ).toUpperCase();
      if (code.isEmpty) continue;
      labels.putIfAbsent(
        code,
        () => '${_text(line, 'description', fallback: code)} ($code)',
      );
    }
    return Map.fromEntries(
      labels.entries.toList()
        ..sort((left, right) => left.value.compareTo(right.value)),
    );
  }

  void _submit() {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    Navigator.pop<JsonMap>(context, {
      'charge_document_id': _documentId,
      'invoice_number': _numberController.text.trim(),
      'invoice_type': _invoiceType,
      'invoice_date': _dateController.text.trim(),
      'currency': _currency,
      'lines': [
        for (final line in _lines)
          {
            'charge_component_code': line.componentCode,
            'description': line.descriptionController.text.trim(),
            'amount': line.amountController.text.trim(),
          },
      ],
    });
  }

  @override
  Widget build(BuildContext context) {
    final expectedRole = _invoiceType == 'SUPPLIER' ? 'PAYER' : 'PAYEE';
    final hasExpectedLines = _expectedDocumentLines.isNotEmpty;
    final componentLabels = _componentLabels;
    return AlertDialog(
      title: const Text('Create invoice'),
      content: SizedBox(
        width: 900,
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.72,
          ),
          child: Form(
            key: _formKey,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Internal Accounts Payable capture. The selected document provides the expected charges used during matching.',
                    style: TextStyle(color: LedgerFlowDesign.muted),
                  ),
                  const SizedBox(height: 18),
                  DropdownButtonFormField<int>(
                    initialValue: _documentId,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Charge document',
                      helperText:
                          'Invoice currency is inherited from this document.',
                    ),
                    items: widget.documents
                        .map(
                          (document) => DropdownMenuItem<int>(
                            value: _asInt(document['id']),
                            child: Text(
                              '${_text(document, 'document_number')}  |  ${_text(document, 'status')}  |  ${_text(document, 'currency')}',
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(growable: false),
                    onChanged: _changeDocument,
                  ),
                  const SizedBox(height: 14),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final fields = [
                        DropdownButtonFormField<String>(
                          initialValue: _invoiceType,
                          decoration: const InputDecoration(
                            labelText: 'Invoice type',
                            helperText:
                                'Supplier matches PAYER; customer matches PAYEE.',
                          ),
                          items: const [
                            DropdownMenuItem(
                              value: 'SUPPLIER',
                              child: Text('Supplier invoice'),
                            ),
                            DropdownMenuItem(
                              value: 'CUSTOMER',
                              child: Text('Customer invoice'),
                            ),
                          ],
                          onChanged: _changeInvoiceType,
                        ),
                        TextFormField(
                          controller: _numberController,
                          decoration: const InputDecoration(
                            labelText: 'Invoice number',
                            helperText: 'Vendor or customer invoice reference.',
                          ),
                          validator: (value) =>
                              value == null || value.trim().isEmpty
                              ? 'Invoice number is required.'
                              : null,
                        ),
                        _DatePickerField(
                          controller: _dateController,
                          label: 'Invoice date',
                          help: 'Accounting date supplied on the invoice.',
                          validator: (value) =>
                              value == null || value.trim().isEmpty
                              ? 'Invoice date is required.'
                              : null,
                        ),
                      ];
                      if (constraints.maxWidth < 700) {
                        return Column(
                          children: [
                            for (final field in fields) ...[
                              field,
                              const SizedBox(height: 14),
                            ],
                          ],
                        );
                      }
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          for (
                            var index = 0;
                            index < fields.length;
                            index++
                          ) ...[
                            Expanded(child: fields[index]),
                            if (index < fields.length - 1)
                              const SizedBox(width: 12),
                          ],
                        ],
                      );
                    },
                  ),
                  if (!hasExpectedLines) ...[
                    const SizedBox(height: 4),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFF7E6),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        'This document has no $expectedRole posting charges. Add lines manually, or verify that the document contains the correct commercial side.',
                        style: const TextStyle(color: LedgerFlowDesign.warning),
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      const Expanded(
                        child: SectionHeading(
                          title: 'Invoice lines',
                          subtitle:
                              'Matching aggregates invoice amounts by charge component.',
                        ),
                      ),
                      TextButton.icon(
                        onPressed: _addLine,
                        icon: const Icon(Icons.add),
                        label: const Text('Add line'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  for (var index = 0; index < _lines.length; index++) ...[
                    _InvoiceDraftLineEditor(
                      key: ObjectKey(_lines[index]),
                      line: _lines[index],
                      componentLabels: componentLabels,
                      canRemove: _lines.length > 1,
                      onRemove: () => _removeLine(index),
                      onComponentChanged: (value) => setState(
                        () => _lines[index].componentCode = value ?? '',
                      ),
                    ),
                    if (index < _lines.length - 1) const SizedBox(height: 10),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _submit, child: const Text('Create invoice')),
      ],
    );
  }
}

class _InvoiceDraftLine {
  _InvoiceDraftLine({
    this.componentCode = '',
    String description = '',
    String amount = '',
  }) : descriptionController = TextEditingController(text: description),
       amountController = TextEditingController(text: amount);

  String componentCode;
  final TextEditingController descriptionController;
  final TextEditingController amountController;

  void dispose() {
    descriptionController.dispose();
    amountController.dispose();
  }
}

class _InvoiceDraftLineEditor extends StatelessWidget {
  const _InvoiceDraftLineEditor({
    required this.line,
    required this.componentLabels,
    required this.canRemove,
    required this.onRemove,
    required this.onComponentChanged,
    super.key,
  });

  final _InvoiceDraftLine line;
  final Map<String, String> componentLabels;
  final bool canRemove;
  final VoidCallback onRemove;
  final ValueChanged<String?> onComponentChanged;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: LedgerFlowDesign.canvas,
      border: Border.all(color: LedgerFlowDesign.border),
      borderRadius: BorderRadius.circular(12),
    ),
    child: LayoutBuilder(
      builder: (context, constraints) {
        final componentField = DropdownButtonFormField<String>(
          initialValue: line.componentCode.isEmpty ? null : line.componentCode,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Charge component'),
          items: componentLabels.entries
              .map(
                (entry) => DropdownMenuItem(
                  value: entry.key,
                  child: Text(entry.value, overflow: TextOverflow.ellipsis),
                ),
              )
              .toList(growable: false),
          validator: (value) => value == null || value.isEmpty
              ? 'Select a charge component.'
              : null,
          onChanged: onComponentChanged,
        );
        final descriptionField = TextFormField(
          controller: line.descriptionController,
          decoration: const InputDecoration(labelText: 'Description'),
        );
        final amountField = TextFormField(
          controller: line.amountController,
          decoration: const InputDecoration(labelText: 'Amount'),
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          validator: (value) => double.tryParse(value?.trim() ?? '') == null
              ? 'Enter a valid amount.'
              : null,
        );
        final removeButton = IconButton(
          tooltip: 'Remove line',
          onPressed: canRemove ? onRemove : null,
          icon: const Icon(Icons.delete_outline),
        );
        if (constraints.maxWidth < 680) {
          return Column(
            children: [
              componentField,
              const SizedBox(height: 10),
              descriptionField,
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(child: amountField),
                  const SizedBox(width: 8),
                  removeButton,
                ],
              ),
            ],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 3, child: componentField),
            const SizedBox(width: 10),
            Expanded(flex: 3, child: descriptionField),
            const SizedBox(width: 10),
            Expanded(child: amountField),
            const SizedBox(width: 4),
            removeButton,
          ],
        );
      },
    ),
  );
}

class RateBookWorkspace extends StatefulWidget {
  const RateBookWorkspace({
    required this.rateBooks,
    required this.components,
    this.pricingDimensions = const [],
    this.calculationProfiles = const [],
    this.allocationProfiles = const [],
    required this.live,
    required this.onMutation,
    super.key,
  });

  final List<JsonMap> rateBooks;
  final List<JsonMap> components;
  final List<JsonMap> pricingDimensions;
  final List<JsonMap> calculationProfiles;
  final List<JsonMap> allocationProfiles;
  final bool live;
  final WorkspaceMutation onMutation;

  @override
  State<RateBookWorkspace> createState() => _RateBookWorkspaceState();
}

class _RateBookWorkspaceState extends State<RateBookWorkspace> {
  final _search = TextEditingController();
  String? _selectedCode;
  int? _selectedBookId;
  int _selectedRate = 0;

  @override
  void initState() {
    super.initState();
    _search.addListener(_refresh);
    _adoptDefaultSelection();
  }

  @override
  void didUpdateWidget(covariant RateBookWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    _adoptDefaultSelection();
  }

  @override
  void dispose() {
    _search
      ..removeListener(_refresh)
      ..dispose();
    super.dispose();
  }

  void _refresh() => setState(() {});

  List<_RateBookFamily> get _families {
    final grouped = <String, List<JsonMap>>{};
    for (final book in widget.rateBooks) {
      final code = _text(book, 'rate_book_code', fallback: 'UNSPECIFIED');
      grouped.putIfAbsent(code, () => <JsonMap>[]).add(book);
    }
    final families = grouped.entries
        .map(
          (entry) => _RateBookFamily(
            code: entry.key,
            versions: _sortRateBooks(entry.value),
          ),
        )
        .toList(growable: false);
    families.sort(
      (left, right) => left.primaryName.toLowerCase().compareTo(
        right.primaryName.toLowerCase(),
      ),
    );
    return families;
  }

  _RateBookFamily? get _selectedFamily {
    final families = _families;
    if (families.isEmpty) return null;
    return families.cast<_RateBookFamily?>().firstWhere(
          (family) => family?.code == _selectedCode,
          orElse: () => families.first,
        ) ??
        families.first;
  }

  JsonMap? get _selectedBook {
    final family = _selectedFamily;
    if (family == null || family.versions.isEmpty) return null;
    return family.versions.cast<JsonMap?>().firstWhere(
          (book) => _asInt(book?['id']) == _selectedBookId,
          orElse: () => family.versions.first,
        ) ??
        family.versions.first;
  }

  void _adoptDefaultSelection() {
    final family = _selectedFamily;
    if (family == null) {
      _selectedCode = null;
      _selectedBookId = null;
      _selectedRate = 0;
      return;
    }
    _selectedCode ??= family.code;
    _selectedBookId ??= _asInt(family.versions.first['id']);
    final selectedExists = family.versions.any(
      (book) => _asInt(book['id']) == _selectedBookId,
    );
    if (!selectedExists) _selectedBookId = _asInt(family.versions.first['id']);
  }

  List<JsonMap> _filteredEntries(JsonMap book) {
    final entries = _rows(book, 'entries');
    final query = _search.text.trim().toLowerCase();
    if (query.isEmpty) return entries;
    return entries
        .where(
          (entry) => [
            _text(entry, 'charge_component_code'),
            _text(entry, 'origin_code'),
            _text(entry, 'destination_code'),
            _text(entry, 'equipment_type'),
            _text(entry, 'basis'),
            _text(entry, 'currency'),
            ..._stringMap(entry['dimension_values']).values,
          ].any((value) => value.toLowerCase().contains(query)),
        )
        .toList(growable: false);
  }

  bool _isDraft(JsonMap book) => _text(book, 'status').toUpperCase() == 'DRAFT';

  bool _isImmutable(JsonMap book) => !_isDraft(book);

  String _versionLabel(JsonMap book) =>
      'v${_asInt(book['version_number']) ?? 1}';

  Future<void> _createRateBook() async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (context) => _RateBookDialog(
        mode: _RateBookDialogMode.create,
        components: widget.components,
        pricingDimensions: widget.pricingDimensions,
        calculationProfiles: widget.calculationProfiles,
        allocationProfiles: widget.allocationProfiles,
      ),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'POST',
      path: '/api/v1/charge-management/rate-books',
      body: payload,
      successMessage: 'Rate book created.',
    );
  }

  Future<void> _createVersion(JsonMap source) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (context) => _RateBookDialog(
        mode: _RateBookDialogMode.newVersion,
        book: source,
        components: widget.components,
        pricingDimensions: widget.pricingDimensions,
        calculationProfiles: widget.calculationProfiles,
        allocationProfiles: widget.allocationProfiles,
      ),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'POST',
      path: '/api/v1/charge-management/rate-books/${source['id']}/versions',
      body: payload,
      successMessage: 'Draft rate-book version created.',
    );
  }

  Future<void> _editDraft(JsonMap book) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (context) => _RateBookDialog(
        mode: _RateBookDialogMode.editDraft,
        book: book,
        components: widget.components,
        pricingDimensions: widget.pricingDimensions,
        calculationProfiles: widget.calculationProfiles,
        allocationProfiles: widget.allocationProfiles,
      ),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'PUT',
      path: '/api/v1/charge-management/rate-books/${book['id']}/workspace',
      body: payload,
      successMessage: 'Draft rate book updated.',
    );
  }

  Future<void> _publishDraft(JsonMap book) async {
    final confirmed = await _confirmAction(
      context,
      title: 'Publish ${_versionLabel(book)}?',
      message:
          'This releases the draft and retires the previously published version for the same rate-book code.',
      action: 'Publish',
    );
    if (!confirmed) return;
    await widget.onMutation(
      method: 'POST',
      path: '/api/v1/charge-management/rate-books/${book['id']}/publish',
      successMessage: 'Draft rate book published.',
    );
  }

  @override
  Widget build(BuildContext context) {
    final family = _selectedFamily;
    final book = _selectedBook;
    if (widget.rateBooks.isEmpty || family == null || book == null) {
      return PageCanvas(
        title: 'Rate books',
        subtitle:
            'Maintain versioned, date-effective rate tables and applicability.',
        trailing: FilledButton.icon(
          onPressed: widget.live ? _createRateBook : null,
          icon: const Icon(Icons.add),
          label: const Text('New rate book'),
        ),
        children: [
          if (!widget.live) const _RateBookModeNotice(),
          if (!widget.live) const SizedBox(height: 16),
          const EmptyState(message: 'No rate books are available.'),
        ],
      );
    }
    final families = _families;
    final familyIndex = math.max(
      0,
      families.indexWhere((item) => item.code == family.code),
    );
    final entries = _filteredEntries(book);
    final rateIndex = entries.isEmpty
        ? 0
        : math.min(_selectedRate, entries.length - 1);
    final selectedRate = entries.isEmpty ? null : entries[rateIndex];
    final rowAttributeKeys = _rateBookAttributeKeys(book);
    final customDimensionCodes = _rateBookDimensionCodes(book);
    final pricingDimensions = _pricingDimensionViews(widget.pricingDimensions);
    final selectedCustomDimensions = _selectedPricingDimensions(
      pricingDimensions,
      customDimensionCodes,
    );
    final rowColumns = _rateBookColumns(
      book,
      widget.pricingDimensions,
      builtInKeys: rowAttributeKeys,
      customCodes: customDimensionCodes,
    );
    final publishedVersion = family.publishedVersion;
    final subtitleParts = [
      '${_text(book, 'currency')} ${_versionLabel(book)}',
      if (_text(book, 'charge_component_code', fallback: '').isNotEmpty)
        _text(book, 'charge_component_code'),
      if (book['valid_from'] != null || book['valid_to'] != null)
        'Valid ${_text(book, 'valid_from')} to ${_text(book, 'valid_to')}',
      if (publishedVersion != null) 'Published v$publishedVersion',
    ];
    return PageCanvas(
      title: _text(
        book,
        'rate_book_name',
        fallback: 'Rate book #${book['id']}',
      ),
      eyebrow: 'Rate books / ${_text(book, 'rate_book_code')}',
      subtitle: subtitleParts.join('  |  '),
      trailing: Wrap(
        spacing: 10,
        runSpacing: 10,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          StatusPill(_text(book, 'status')),
          FilledButton.icon(
            onPressed: widget.live ? _createRateBook : null,
            icon: const Icon(Icons.add),
            label: const Text('New rate book'),
          ),
          OutlinedButton.icon(
            onPressed: widget.live ? () => _createVersion(book) : null,
            icon: const Icon(Icons.copy_outlined),
            label: const Text('New draft'),
          ),
          OutlinedButton.icon(
            onPressed: widget.live && _isDraft(book)
                ? () => _editDraft(book)
                : null,
            icon: const Icon(Icons.edit_outlined),
            label: const Text('Edit draft'),
          ),
          FilledButton.tonalIcon(
            onPressed: widget.live && _isDraft(book)
                ? () => _publishDraft(book)
                : null,
            icon: const Icon(Icons.publish_outlined),
            label: const Text('Publish draft'),
          ),
        ],
      ),
      children: [
        if (!widget.live) const _RateBookModeNotice(),
        if (!widget.live) const SizedBox(height: 16),
        TransactionRecordList(
          records: families
              .map((item) {
                final latest = item.versions.first;
                return JsonMap.from({
                  'rate_book_code': item.code,
                  'rate_book_name': item.primaryName,
                  'charge_component_code': latest['charge_component_code'],
                  'currency': latest['currency'],
                  'status': latest['status'],
                  'version_number': latest['version_number'],
                  'valid_from': latest['valid_from'],
                  'valid_to': latest['valid_to'],
                  'published_version_number': item.publishedVersion,
                  'version_count': item.versions.length,
                });
              })
              .toList(growable: false),
          selectedIndex: familyIndex,
          searchHint: 'Search rate book, component, currency, or validity',
          emptyMessage: 'No rate books are available.',
          searchText: (item) => [
            _text(item, 'rate_book_code'),
            _text(item, 'rate_book_name'),
            _text(item, 'charge_component_code'),
            _text(item, 'currency'),
            _text(item, 'status'),
            _text(item, 'valid_from'),
            _text(item, 'valid_to'),
          ].join(' '),
          status: (item) => _text(item, 'status'),
          columns: [
            TransactionListColumn(
              label: 'Rate book',
              flex: 2,
              value: (item) => _text(item, 'rate_book_code'),
            ),
            TransactionListColumn(
              label: 'Name',
              flex: 2,
              value: (item) => _text(item, 'rate_book_name'),
            ),
            TransactionListColumn(
              label: 'Component',
              flex: 2,
              value: (item) => _text(
                item,
                'charge_component_code',
                fallback: 'Not assigned',
              ),
            ),
            TransactionListColumn(
              label: 'Currency',
              value: (item) => _text(item, 'currency'),
            ),
            TransactionListColumn(
              label: 'Version',
              value: (item) {
                final version = _asInt(item['version_number']) ?? 1;
                final count = _asInt(item['version_count']) ?? 1;
                return 'v$version of $count';
              },
            ),
            TransactionListColumn(
              label: 'Validity',
              flex: 2,
              value: (item) =>
                  '${_text(item, 'valid_from')} to ${_text(item, 'valid_to')}',
            ),
            TransactionListColumn(
              label: 'Status',
              value: (item) => _text(item, 'status'),
              isStatus: true,
            ),
          ],
          onSelected: (value) => setState(() {
            _selectedCode = families[value].code;
            _selectedBookId = _asInt(families[value].versions.first['id']);
            _selectedRate = 0;
          }),
        ),
        const SizedBox(height: 16),
        ResponsiveMetricGrid(
          children: [
            MetricCard(
              label: 'Entries',
              value: '${_rows(book, 'entries').length}',
              icon: Icons.table_chart_outlined,
              color: LedgerFlowDesign.teal,
            ),
            MetricCard(
              label: 'Currency',
              value: _text(book, 'currency'),
              icon: Icons.payments_outlined,
              color: LedgerFlowDesign.info,
            ),
            MetricCard(
              label: 'Versions',
              value: '${family.versions.length}',
              detail: publishedVersion == null
                  ? 'No version published'
                  : 'Published v$publishedVersion',
              icon: Icons.layers_outlined,
              color: LedgerFlowDesign.success,
            ),
            MetricCard(
              label: 'Mutability',
              value: _isDraft(book) ? 'Editable draft' : 'Immutable',
              detail: _isDraft(book)
                  ? 'Changes use the workspace endpoint'
                  : 'Create a new draft version to change content',
              icon: _isDraft(book)
                  ? Icons.edit_note_outlined
                  : Icons.lock_outline,
              color: _isDraft(book)
                  ? LedgerFlowDesign.warning
                  : LedgerFlowDesign.info,
            ),
          ],
        ),
        const SizedBox(height: 16),
        ResponsiveColumns(
          leftFlex: 3,
          rightFlex: 1,
          left: SurfaceCard(
            padding: EdgeInsets.zero,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.all(18),
                  child: Row(
                    children: [
                      const Expanded(
                        child: SectionHeading(
                          title: 'Rate entries',
                          subtitle:
                              'Lane, equipment, basis, validity, and profile resolution',
                        ),
                      ),
                      SizedBox(
                        width: 220,
                        child: TextField(
                          controller: _search,
                          decoration: const InputDecoration(
                            hintText: 'Search rates',
                            prefixIcon: Icon(Icons.search),
                            isDense: true,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                _RateTable(
                  entries: entries,
                  columns: rowColumns,
                  selectedIndex: rateIndex,
                  onSelected: (value) => setState(() => _selectedRate = value),
                ),
              ],
            ),
          ),
          right: Column(
            children: [
              SurfaceCard(
                child: selectedRate == null
                    ? const EmptyState(
                        message:
                            'Select a populated rate book to inspect a rate.',
                      )
                    : Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SectionHeading(title: 'Selected rate'),
                          const SizedBox(height: 14),
                          DetailRow(
                            label: 'Component',
                            value: _text(selectedRate, 'charge_component_code'),
                          ),
                          DetailRow(
                            label: 'Lane',
                            value:
                                '${_text(selectedRate, 'origin_code')} -> ${_text(selectedRate, 'destination_code')}',
                          ),
                          DetailRow(
                            label: 'Rate',
                            value:
                                _text(
                                  selectedRate,
                                  'basis',
                                ).toUpperCase().startsWith('PERCENT')
                                ? '${_text(selectedRate, 'rate_percent')}%'
                                : '${_text(selectedRate, 'currency')} ${_text(selectedRate, 'rate_amount')}',
                          ),
                          DetailRow(
                            label: 'Basis',
                            value: _text(selectedRate, 'basis'),
                          ),
                          DetailRow(
                            label: 'Equipment',
                            value: _text(selectedRate, 'equipment_type'),
                          ),
                          DetailRow(
                            label: 'Calculation profile',
                            value: _text(
                              selectedRate,
                              'calculation_profile_id',
                              fallback: 'Inherit',
                            ),
                          ),
                          DetailRow(
                            label: 'Allocation profile',
                            value: _text(
                              selectedRate,
                              'allocation_profile_id',
                              fallback: 'Inherit',
                            ),
                          ),
                          if (selectedCustomDimensions.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            const Text(
                              'Custom dimensions',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 4),
                            for (final dimension in selectedCustomDimensions)
                              DetailRow(
                                label: dimension.name,
                                value: _dimensionEntryValue(
                                  selectedRate,
                                  dimension,
                                ),
                              ),
                          ],
                          DetailRow(
                            label: 'Status',
                            value: selectedRate['is_active'] == false
                                ? 'INACTIVE'
                                : 'ACTIVE',
                          ),
                        ],
                      ),
              ),
              const SizedBox(height: 16),
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SectionHeading(
                      title: 'Version history',
                      subtitle:
                          'Grouped by rate-book code, ordered by version number.',
                      action: TextButton.icon(
                        onPressed: widget.live
                            ? () => _createVersion(book)
                            : null,
                        icon: const Icon(Icons.add, size: 16),
                        label: const Text('New draft'),
                      ),
                    ),
                    const SizedBox(height: 14),
                    for (final version in family.versions) ...[
                      _RateBookVersionRow(
                        versionLabel: _versionLabel(version),
                        status: _text(version, 'status'),
                        isSelected: _asInt(version['id']) == _asInt(book['id']),
                        note: version['published_at'] == null
                            ? _text(
                                version,
                                'valid_from',
                                fallback: _isDraft(version)
                                    ? 'Draft workspace'
                                    : 'Immutable workspace',
                              )
                            : 'Published ${_text(version, 'published_at')}',
                        immutable: _isImmutable(version),
                        onSelect: () => setState(() {
                          _selectedBookId = _asInt(version['id']);
                          _selectedRate = 0;
                        }),
                      ),
                      if (version != family.versions.last)
                        const Divider(
                          height: 22,
                          color: LedgerFlowDesign.border,
                        ),
                    ],
                    const SizedBox(height: 16),
                    DecoratedBox(
                      decoration: BoxDecoration(
                        color: _isDraft(book)
                            ? LedgerFlowDesign.warning.withValues(alpha: 0.09)
                            : LedgerFlowDesign.info.withValues(alpha: 0.09),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: _isDraft(book)
                              ? LedgerFlowDesign.warning.withValues(alpha: 0.28)
                              : LedgerFlowDesign.info.withValues(alpha: 0.24),
                        ),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              _isDraft(book)
                                  ? Icons.edit_note_outlined
                                  : Icons.lock_outline,
                              size: 18,
                              color: _isDraft(book)
                                  ? LedgerFlowDesign.warning
                                  : LedgerFlowDesign.info,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _isDraft(book)
                                        ? 'Editable draft'
                                        : 'Immutable version',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    _isDraft(book)
                                        ? 'Use the workspace update path to change this draft before publishing.'
                                        : 'Published and retired versions are locked. Create a new draft version from the selected record to make changes.',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: LedgerFlowDesign.muted,
                                      height: 1.4,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class CalculationTemplateWorkspacePage extends StatefulWidget {
  const CalculationTemplateWorkspacePage({
    required this.templates,
    required this.components,
    required this.rateBooks,
    required this.live,
    required this.onMutation,
    super.key,
  });

  final List<JsonMap> templates;
  final List<JsonMap> components;
  final List<JsonMap> rateBooks;
  final bool live;
  final WorkspaceMutation onMutation;

  @override
  State<CalculationTemplateWorkspacePage> createState() =>
      _CalculationTemplateWorkspacePageState();
}

class _CalculationTemplateWorkspacePageState
    extends State<CalculationTemplateWorkspacePage> {
  String? _selectedCode;
  int? _selectedId;

  List<_CalculationTemplateFamily> get _families {
    final grouped = <String, List<JsonMap>>{};
    for (final template in widget.templates) {
      final code = _text(template, 'template_code', fallback: 'UNSPECIFIED');
      grouped.putIfAbsent(code, () => []).add(template);
    }
    final families =
        grouped.entries
            .map(
              (entry) => _CalculationTemplateFamily(
                code: entry.key,
                versions: [...entry.value]
                  ..sort(
                    (left, right) => (_asInt(right['version_number']) ?? 1)
                        .compareTo(_asInt(left['version_number']) ?? 1),
                  ),
              ),
            )
            .toList(growable: false)
          ..sort(
            (left, right) =>
                left.name.toLowerCase().compareTo(right.name.toLowerCase()),
          );
    return families;
  }

  _CalculationTemplateFamily? get _family {
    final families = _families;
    if (families.isEmpty) return null;
    return families.firstWhere(
      (family) => family.code == _selectedCode,
      orElse: () => families.first,
    );
  }

  JsonMap? get _template {
    final family = _family;
    if (family == null) return null;
    return family.versions.firstWhere(
      (template) => _asInt(template['id']) == _selectedId,
      orElse: () => family.versions.first,
    );
  }

  bool _draft(JsonMap template) =>
      _text(template, 'status').toUpperCase() == 'DRAFT';

  Future<void> _openDialog(
    _CalculationTemplateDialogMode mode, {
    JsonMap? template,
  }) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (context) => _CalculationTemplateDialog(
        mode: mode,
        template: template,
        components: widget.components,
        rateBooks: widget.rateBooks,
      ),
    );
    if (payload == null) return;
    final id = template?['id'];
    final (method, path, message) = switch (mode) {
      _CalculationTemplateDialogMode.create => (
        'POST',
        '/api/v1/charge-management/calculation-templates',
        'Calculation template created.',
      ),
      _CalculationTemplateDialogMode.edit => (
        'PUT',
        '/api/v1/charge-management/calculation-templates/$id/workspace',
        'Calculation template draft updated.',
      ),
      _CalculationTemplateDialogMode.version => (
        'POST',
        '/api/v1/charge-management/calculation-templates/$id/versions',
        'Calculation template draft version created.',
      ),
    };
    await widget.onMutation(
      method: method,
      path: path,
      body: payload,
      successMessage: message,
    );
  }

  Future<void> _publish(JsonMap template) async {
    final confirmed = await _confirmAction(
      context,
      title: 'Publish calculation template?',
      message:
          'The draft becomes immutable and the previous published version in this family is retired.',
      action: 'Publish',
    );
    if (!confirmed) return;
    await widget.onMutation(
      method: 'POST',
      path:
          '/api/v1/charge-management/calculation-templates/${template['id']}/publish',
      successMessage: 'Calculation template published.',
    );
  }

  @override
  Widget build(BuildContext context) {
    final family = _family;
    final template = _template;
    if (family == null || template == null) {
      return PageCanvas(
        title: 'Calculation templates',
        subtitle:
            'Sequence component-specific rate books into a governed charge calculation.',
        trailing: FilledButton.icon(
          onPressed: widget.live
              ? () => _openDialog(_CalculationTemplateDialogMode.create)
              : null,
          icon: const Icon(Icons.add),
          label: const Text('New template'),
        ),
        children: const [
          EmptyState(message: 'No calculation templates are available.'),
        ],
      );
    }
    final families = _families;
    final familyIndex = math.max(0, families.indexOf(family));
    final steps = _rows(template, 'steps');
    return PageCanvas(
      title: _text(template, 'template_name'),
      eyebrow: 'Calculation templates / ${family.code}',
      subtitle:
          'v${_asInt(template['version_number']) ?? 1} | ${steps.length} ordered steps',
      trailing: Wrap(
        spacing: 10,
        runSpacing: 10,
        children: [
          StatusPill(_text(template, 'status')),
          FilledButton.icon(
            onPressed: widget.live
                ? () => _openDialog(_CalculationTemplateDialogMode.create)
                : null,
            icon: const Icon(Icons.add),
            label: const Text('New template'),
          ),
          OutlinedButton.icon(
            onPressed: widget.live
                ? () => _openDialog(
                    _CalculationTemplateDialogMode.version,
                    template: template,
                  )
                : null,
            icon: const Icon(Icons.copy_outlined),
            label: const Text('New draft'),
          ),
          OutlinedButton.icon(
            onPressed: widget.live && _draft(template)
                ? () => _openDialog(
                    _CalculationTemplateDialogMode.edit,
                    template: template,
                  )
                : null,
            icon: const Icon(Icons.edit_outlined),
            label: const Text('Edit draft'),
          ),
          FilledButton.tonalIcon(
            onPressed: widget.live && _draft(template)
                ? () => _publish(template)
                : null,
            icon: const Icon(Icons.publish_outlined),
            label: const Text('Publish'),
          ),
        ],
      ),
      children: [
        SurfaceCard(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: const [
              Icon(Icons.info_outline, color: LedgerFlowDesign.info, size: 19),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'A rate book prices one charge component. A calculation template orders multiple components, chooses the rate book for each step, and controls payer/payee inclusion, subtotals, conditions, and statistical output.',
                  style: TextStyle(
                    color: LedgerFlowDesign.muted,
                    fontSize: 12,
                    height: 1.45,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        _RecordPicker(
          records: families
              .map(
                (item) => <String, dynamic>{
                  'template_name': item.name,
                  'template_code': item.code,
                  'version_count': item.versions.length,
                  'published_version_number': item.publishedVersion,
                },
              )
              .toList(growable: false),
          selectedIndex: familyIndex,
          label: (item) => _text(item, 'template_name'),
          detail: (item) =>
              '${_text(item, 'template_code')} | ${item['version_count']} versions | Published ${item['published_version_number'] ?? 'none'}',
          onSelected: (index) => setState(() {
            _selectedCode = families[index].code;
            _selectedId = _asInt(families[index].versions.first['id']);
          }),
        ),
        const SizedBox(height: 14),
        SurfaceCard(
          padding: EdgeInsets.zero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.all(18),
                child: SectionHeading(
                  title: 'Calculation steps',
                  subtitle:
                      'Executed in ascending sequence; percentage steps may consume a subtotal accumulated by earlier steps.',
                ),
              ),
              if (steps.isEmpty)
                const EmptyState(message: 'This template has no steps.')
              else
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    columns: const [
                      DataColumn(label: Text('Sequence')),
                      DataColumn(label: Text('Component')),
                      DataColumn(label: Text('Role')),
                      DataColumn(label: Text('Rate book')),
                      DataColumn(label: Text('Subtotal')),
                      DataColumn(label: Text('Subtotal effect')),
                      DataColumn(label: Text('Condition')),
                      DataColumn(label: Text('Output')),
                    ],
                    rows: steps
                        .map(
                          (step) => DataRow(
                            cells: [
                              DataCell(Text(_text(step, 'step_number'))),
                              DataCell(
                                Text(
                                  _text(step, 'charge_component_code'),
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                              DataCell(Text(_text(step, 'relationship_role'))),
                              DataCell(
                                Text(
                                  _text(
                                    step,
                                    'rate_book_code',
                                    fallback: step['rate_book_id'] == null
                                        ? 'Contract default'
                                        : '#${step['rate_book_id']}',
                                  ),
                                ),
                              ),
                              DataCell(
                                Text(
                                  _text(step, 'subtotal_key', fallback: '-'),
                                ),
                              ),
                              DataCell(
                                Text(
                                  _text(step, 'subtotal_key').isEmpty
                                      ? '-'
                                      : step['accumulate_result_in_subtotal'] ==
                                            false
                                      ? 'Read only'
                                      : 'Read + add',
                                ),
                              ),
                              DataCell(
                                Text(
                                  _text(
                                    step,
                                    'precondition_key',
                                    fallback: 'Always',
                                  ),
                                ),
                              ),
                              DataCell(
                                StatusPill(
                                  step['is_statistical'] == true
                                      ? 'STATISTICAL'
                                      : 'CHARGE',
                                ),
                              ),
                            ],
                          ),
                        )
                        .toList(growable: false),
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        SurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SectionHeading(
                title: 'Version history',
                subtitle:
                    'Published and retired versions are immutable; changes start in a new draft.',
              ),
              const SizedBox(height: 12),
              for (final version in family.versions)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  selected: _asInt(version['id']) == _asInt(template['id']),
                  leading: Icon(
                    _draft(version)
                        ? Icons.edit_note_outlined
                        : Icons.lock_outline,
                    color: _draft(version)
                        ? LedgerFlowDesign.warning
                        : LedgerFlowDesign.info,
                  ),
                  title: Text(
                    'Version ${_asInt(version['version_number']) ?? 1}',
                  ),
                  subtitle: Text(_text(version, 'status')),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () =>
                      setState(() => _selectedId = _asInt(version['id'])),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _CalculationTemplateFamily {
  const _CalculationTemplateFamily({
    required this.code,
    required this.versions,
  });

  final String code;
  final List<JsonMap> versions;

  String get name => _text(versions.first, 'template_name', fallback: code);

  int? get publishedVersion {
    for (final version in versions) {
      if (_text(version, 'status').toUpperCase() == 'PUBLISHED') {
        return _asInt(version['version_number']) ?? 1;
      }
    }
    return null;
  }
}

enum _CalculationTemplateDialogMode { create, edit, version }

class _CalculationTemplateStepDraft {
  _CalculationTemplateStepDraft({
    this.stepNumber = '10',
    this.componentCode = '',
    this.relationshipRole = 'BOTH',
    this.rateBookId,
    this.subtotalKey = '',
    this.accumulateResultInSubtotal = true,
    this.preconditionKey = '',
    this.isStatistical = false,
  });

  factory _CalculationTemplateStepDraft.fromJson(JsonMap step) =>
      _CalculationTemplateStepDraft(
        stepNumber: _text(step, 'step_number', fallback: '10'),
        componentCode: _text(step, 'charge_component_code'),
        relationshipRole: _text(step, 'relationship_role', fallback: 'BOTH'),
        rateBookId: _asInt(step['rate_book_id']),
        subtotalKey: _text(step, 'subtotal_key', fallback: ''),
        accumulateResultInSubtotal:
            step['accumulate_result_in_subtotal'] != false,
        preconditionKey: _text(step, 'precondition_key', fallback: ''),
        isStatistical: step['is_statistical'] == true,
      );

  String stepNumber;
  String componentCode;
  String relationshipRole;
  int? rateBookId;
  String subtotalKey;
  bool accumulateResultInSubtotal;
  String preconditionKey;
  bool isStatistical;

  JsonMap toJson() => {
    'step_number': _asInt(stepNumber) ?? 10,
    'charge_component_code': componentCode.trim().toUpperCase(),
    'relationship_role': relationshipRole,
    'rate_book_id': rateBookId,
    'subtotal_key': subtotalKey.trim().isEmpty
        ? null
        : subtotalKey.trim().toUpperCase(),
    'accumulate_result_in_subtotal': accumulateResultInSubtotal,
    'precondition_key': preconditionKey.trim().isEmpty
        ? null
        : preconditionKey.trim(),
    'is_statistical': isStatistical,
  };
}

class _CalculationTemplateDialog extends StatefulWidget {
  const _CalculationTemplateDialog({
    required this.mode,
    required this.components,
    required this.rateBooks,
    this.template,
  });

  final _CalculationTemplateDialogMode mode;
  final List<JsonMap> components;
  final List<JsonMap> rateBooks;
  final JsonMap? template;

  @override
  State<_CalculationTemplateDialog> createState() =>
      _CalculationTemplateDialogState();
}

class _CalculationTemplateDialogState
    extends State<_CalculationTemplateDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _code;
  late final TextEditingController _name;
  late final TextEditingController _description;
  late bool _active;
  late List<_CalculationTemplateStepDraft> _steps;

  @override
  void initState() {
    super.initState();
    final template = widget.template ?? const <String, dynamic>{};
    _code = TextEditingController(text: _text(template, 'template_code'));
    _name = TextEditingController(text: _text(template, 'template_name'));
    _description = TextEditingController(text: _text(template, 'description'));
    _active = widget.template == null || template['is_active'] != false;
    _steps = _rows(
      template,
      'steps',
    ).map(_CalculationTemplateStepDraft.fromJson).toList(growable: true);
  }

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  String? _required(String? value) =>
      value == null || value.trim().isEmpty ? 'Required' : null;

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final payload = <String, dynamic>{
      'template_code': _code.text.trim().toUpperCase(),
      'template_name': _name.text.trim(),
      'description': _description.text.trim().isEmpty
          ? null
          : _description.text.trim(),
      'status': 'DRAFT',
      'is_active': _active,
      'steps': _steps.map((step) => step.toJson()).toList(growable: false),
    };
    if (widget.mode == _CalculationTemplateDialogMode.edit) {
      final lockVersion = _asInt(widget.template?['lock_version']);
      if (lockVersion != null) payload['expected_lock_version'] = lockVersion;
    }
    Navigator.pop(context, JsonMap.from(payload));
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(switch (widget.mode) {
      _CalculationTemplateDialogMode.create => 'Create calculation template',
      _CalculationTemplateDialogMode.edit => 'Edit template draft',
      _CalculationTemplateDialogMode.version => 'Create template draft',
    }),
    content: SizedBox(
      width: 1050,
      child: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Steps run in sequence. Each step selects a charge component and an optional component-specific rate book.',
                style: TextStyle(color: LedgerFlowDesign.muted, fontSize: 12),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  SizedBox(
                    width: 230,
                    child: TextFormField(
                      controller: _code,
                      readOnly:
                          widget.mode == _CalculationTemplateDialogMode.version,
                      decoration: const InputDecoration(
                        labelText: 'Template code',
                        helperText: 'Stable identifier across versions.',
                      ),
                      validator: _required,
                    ),
                  ),
                  SizedBox(
                    width: 330,
                    child: TextFormField(
                      controller: _name,
                      decoration: const InputDecoration(
                        labelText: 'Template name',
                      ),
                      validator: _required,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _description,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'Description'),
              ),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                dense: true,
                value: _active,
                onChanged: (value) => setState(() => _active = value),
                title: const Text('Template is active'),
              ),
              SectionHeading(
                title: 'Ordered steps',
                subtitle:
                    'A subtotal key provides the current percentage base. Use each step\'s switch to control whether its result is added back into that subtotal.',
                action: TextButton.icon(
                  onPressed: () => setState(
                    () => _steps.add(
                      _CalculationTemplateStepDraft(
                        stepNumber: '${(_steps.length + 1) * 10}',
                      ),
                    ),
                  ),
                  icon: const Icon(Icons.add, size: 16),
                  label: const Text('Add step'),
                ),
              ),
              const SizedBox(height: 12),
              if (_steps.isEmpty)
                const EmptyState(message: 'Add at least one step to publish.')
              else
                for (var index = 0; index < _steps.length; index++) ...[
                  _CalculationTemplateStepEditor(
                    key: ValueKey('template-step-$index'),
                    index: index,
                    step: _steps[index],
                    components: widget.components,
                    rateBooks: widget.rateBooks,
                    required: _required,
                    onChanged: () => setState(() {}),
                    onRemove: () => setState(() => _steps.removeAt(index)),
                  ),
                  if (index != _steps.length - 1) const SizedBox(height: 10),
                ],
            ],
          ),
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(onPressed: _submit, child: const Text('Save draft')),
    ],
  );
}

String? _rateBookHeaderComponent(JsonMap rateBook) {
  final header = _text(rateBook, 'charge_component_code', fallback: '');
  if (header.isNotEmpty) return header.toUpperCase();
  final entries = _rows(rateBook, 'entries');
  final codes = entries
      .map((entry) => _text(entry, 'charge_component_code').toUpperCase())
      .where((code) => code.isNotEmpty)
      .toSet();
  return codes.length == 1 ? codes.first : null;
}

class _CalculationTemplateStepEditor extends StatelessWidget {
  const _CalculationTemplateStepEditor({
    required super.key,
    required this.index,
    required this.step,
    required this.components,
    required this.rateBooks,
    required this.required,
    required this.onChanged,
    required this.onRemove,
  });

  final int index;
  final _CalculationTemplateStepDraft step;
  final List<JsonMap> components;
  final List<JsonMap> rateBooks;
  final String? Function(String?) required;
  final VoidCallback onChanged;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final books = rateBooks
        .where((book) {
          final component = _rateBookHeaderComponent(book);
          return component == null ||
              component == step.componentCode.toUpperCase();
        })
        .toList(growable: false);
    if (step.rateBookId != null &&
        !books.any((book) => _asInt(book['id']) == step.rateBookId)) {
      step.rateBookId = null;
    }
    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        border: Border.all(color: LedgerFlowDesign.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  'Step ${index + 1}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: onRemove,
                  icon: const Icon(Icons.delete_outline, size: 16),
                  label: const Text('Remove'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                SizedBox(
                  width: 110,
                  child: TextFormField(
                    initialValue: step.stepNumber,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Sequence',
                      helperText: 'Execution order.',
                      helperMaxLines: 2,
                    ),
                    validator: (value) {
                      final number = _asInt(value);
                      return number == null || number < 1
                          ? 'Positive integer'
                          : null;
                    },
                    onChanged: (value) => step.stepNumber = value,
                  ),
                ),
                SizedBox(
                  width: 330,
                  child: DropdownButtonFormField<String>(
                    key: ValueKey('template-step-component-$index'),
                    initialValue: step.componentCode.isEmpty
                        ? null
                        : step.componentCode,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Charge component',
                      helperText: 'The charge produced by this step.',
                      helperMaxLines: 2,
                    ),
                    items: _rateComponentOptions(components, step.componentCode)
                        .map(
                          (component) => DropdownMenuItem(
                            value: _text(
                              component,
                              'component_code',
                            ).toUpperCase(),
                            child: Text(
                              _rateComponentLabel(component),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(growable: false),
                    validator: required,
                    onChanged: (value) {
                      step.componentCode = value ?? '';
                      step.rateBookId = null;
                      onChanged();
                    },
                  ),
                ),
                SizedBox(
                  width: 270,
                  child: DropdownButtonFormField<String>(
                    initialValue: step.relationshipRole,
                    decoration: const InputDecoration(
                      labelText: 'Relationship role',
                      helperText:
                          'PAYER = supplier cost; PAYEE = customer price; BOTH = either contract side.',
                      helperMaxLines: 3,
                    ),
                    items: const ['BOTH', 'PAYER', 'PAYEE']
                        .map(
                          (value) => DropdownMenuItem(
                            value: value,
                            child: Text(value),
                          ),
                        )
                        .toList(growable: false),
                    onChanged: (value) =>
                        step.relationshipRole = value ?? 'BOTH',
                  ),
                ),
                SizedBox(
                  width: 330,
                  child: DropdownButtonFormField<int?>(
                    key: ValueKey('template-step-rate-book-$index'),
                    initialValue: step.rateBookId,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Rate book',
                      helperText:
                          'Only books for the selected component are listed.',
                      helperMaxLines: 2,
                    ),
                    items: [
                      const DropdownMenuItem<int?>(
                        value: null,
                        child: Text('Use contract default'),
                      ),
                      ...books.map(
                        (book) => DropdownMenuItem<int?>(
                          value: _asInt(book['id']),
                          child: Text(
                            '${_text(book, 'rate_book_name')} v${_asInt(book['version_number']) ?? 1} (${_text(book, 'status')})',
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ),
                    ],
                    onChanged: (value) => step.rateBookId = value,
                  ),
                ),
                SizedBox(
                  width: 310,
                  child: TextFormField(
                    initialValue: step.subtotalKey,
                    decoration: const InputDecoration(
                      labelText: 'Subtotal key',
                      helperText:
                          'Free-text bucket, e.g. BASE_TRANSPORT. A percentage step reads its current amount as the base.',
                      helperMaxLines: 3,
                    ),
                    onChanged: (value) {
                      step.subtotalKey = value;
                      onChanged();
                    },
                  ),
                ),
                SizedBox(
                  width: 340,
                  child: TextFormField(
                    initialValue: step.preconditionKey,
                    decoration: const InputDecoration(
                      labelText: 'Precondition context key',
                      helperText:
                          'Optional quote context key, e.g. requires_tail_lift. The step runs only when its value is true.',
                      helperMaxLines: 3,
                    ),
                    onChanged: (value) => step.preconditionKey = value,
                  ),
                ),
              ],
            ),
            SwitchListTile.adaptive(
              dense: true,
              contentPadding: EdgeInsets.zero,
              value: step.accumulateResultInSubtotal,
              onChanged: (value) {
                step.accumulateResultInSubtotal = value;
                onChanged();
              },
              title: const Text('Add result to subtotal'),
              subtitle: const Text(
                'Turn off for a commercial percentage charge that reads the subtotal but must not change the base used by later percentage steps.',
              ),
            ),
            SwitchListTile.adaptive(
              dense: true,
              contentPadding: EdgeInsets.zero,
              value: step.isStatistical,
              onChanged: (value) {
                step.isStatistical = value;
                onChanged();
              },
              title: const Text('Statistical output only'),
              subtitle: const Text(
                'Calculate and expose the line, but exclude it from commercial totals.',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class CatalogWorkspace extends StatelessWidget {
  const CatalogWorkspace({
    required this.title,
    required this.description,
    required this.records,
    required this.columns,
    super.key,
  });

  final String title;
  final String description;
  final List<JsonMap> records;
  final List<String> columns;

  @override
  Widget build(BuildContext context) {
    return PageCanvas(
      title: title,
      subtitle: description,
      trailing: OutlinedButton.icon(
        onPressed: () => _showApiGuidance(context, title),
        icon: const Icon(Icons.code),
        label: const Text('API usage'),
      ),
      children: [
        SurfaceCard(
          padding: EdgeInsets.zero,
          child: records.isEmpty
              ? const Padding(
                  padding: EdgeInsets.all(18),
                  child: EmptyState(message: 'No records are available.'),
                )
              : SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    columns: columns
                        .map(
                          (column) => DataColumn(label: Text(_label(column))),
                        )
                        .toList(),
                    rows: records.map((record) {
                      return DataRow(
                        cells: columns.map((column) {
                          final value = _text(record, column);
                          if (column == 'status' || column == 'is_active') {
                            return DataCell(
                              StatusPill(
                                column == 'is_active'
                                    ? (value == 'true' ? 'ACTIVE' : 'INACTIVE')
                                    : value,
                              ),
                            );
                          }
                          return DataCell(Text(value));
                        }).toList(),
                      );
                    }).toList(),
                  ),
                ),
        ),
      ],
    );
  }
}

class ProfileHub extends StatelessWidget {
  const ProfileHub({required this.data, super.key});

  final WorkspaceData data;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: PageCanvas(
        title: 'Calculation & allocation profiles',
        subtitle:
            'Versioned profiles keep formulas and allocation drivers reusable, reviewable, and reproducible.',
        children: [
          const SurfaceCard(
            padding: EdgeInsets.zero,
            child: TabBar(
              tabs: [
                Tab(text: 'Calculation profiles'),
                Tab(text: 'Allocation profiles'),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 560,
            child: TabBarView(
              children: [
                _ProfileTable(
                  kind: 'calculation',
                  records: data['calculationProfiles'],
                  description:
                      'Controls quantity selection, formulas, rounding, minimums, maximums, and audit snapshots.',
                ),
                _ProfileTable(
                  kind: 'allocation',
                  records: data['allocationProfiles'],
                  description:
                      'Distributes a source charge across houses or items using governed business drivers.',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class FxAndDatesWorkspace extends StatelessWidget {
  const FxAndDatesWorkspace({required this.data, super.key});

  final WorkspaceData data;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: PageCanvas(
        title: 'FX rates & business dates',
        subtitle:
            'Resolve conversion rates and the effective business date used for rate and contract applicability.',
        children: [
          const SurfaceCard(
            padding: EdgeInsets.zero,
            child: TabBar(
              tabs: [
                Tab(text: 'FX rates'),
                Tab(text: 'Business-date profiles'),
              ],
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 560,
            child: TabBarView(
              children: [
                _FxTable(records: data['fxRates']),
                _ProfileTable(
                  kind: 'business date',
                  records: data['dateProfiles'],
                  description:
                      'Defines the ordered document or logistics dates used to resolve charge applicability.',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class PageCanvas extends StatelessWidget {
  const PageCanvas({
    required this.title,
    required this.subtitle,
    required this.children,
    this.eyebrow,
    this.trailing,
    super.key,
  });

  final String title;
  final String subtitle;
  final String? eyebrow;
  final Widget? trailing;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final compact = MediaQuery.sizeOf(context).width < 760;
    return SingleChildScrollView(
      padding: compact
          ? const EdgeInsets.fromLTRB(13, 18, 13, 28)
          : const EdgeInsets.fromLTRB(26, 23, 26, 36),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1660),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (eyebrow != null) ...[
                Text(
                  eyebrow!,
                  style: const TextStyle(
                    color: LedgerFlowDesign.teal,
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.7,
                  ),
                ),
                const SizedBox(height: 6),
              ],
              LayoutBuilder(
                builder: (context, constraints) {
                  final heading = Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          fontSize: 28,
                          height: 1.15,
                          fontWeight: FontWeight.w700,
                          letterSpacing: -0.7,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        style: const TextStyle(
                          fontSize: 11,
                          color: LedgerFlowDesign.muted,
                          height: 1.45,
                        ),
                      ),
                    ],
                  );
                  if (trailing == null) return heading;
                  if (constraints.maxWidth < 760) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        heading,
                        const SizedBox(height: 16),
                        SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: trailing!,
                        ),
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Expanded(child: heading),
                      const SizedBox(width: 16),
                      trailing!,
                    ],
                  );
                },
              ),
              const SizedBox(height: 20),
              ...children,
            ],
          ),
        ),
      ),
    );
  }
}

class ResponsiveMetricGrid extends StatelessWidget {
  const ResponsiveMetricGrid({required this.children, super.key});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final columns = constraints.maxWidth >= 1080
            ? 4
            : constraints.maxWidth >= 560
            ? 2
            : 1;
        const gap = 12.0;
        final width = (constraints.maxWidth - (gap * (columns - 1))) / columns;
        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: [
            for (final child in children) SizedBox(width: width, child: child),
          ],
        );
      },
    );
  }
}

class MetricCard extends StatelessWidget {
  const MetricCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    this.detail,
    super.key,
  });

  final String label;
  final String value;
  final String? detail;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.11),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 19, color: color),
          ),
          const SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    fontSize: 11,
                    color: LedgerFlowDesign.muted,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 21,
                    height: 1.1,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -0.35,
                  ),
                ),
                if (detail != null) ...[
                  const SizedBox(height: 3),
                  Text(
                    detail!,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 11,
                      color: LedgerFlowDesign.muted,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class SectionHeading extends StatelessWidget {
  const SectionHeading({
    required this.title,
    this.subtitle,
    this.action,
    super.key,
  });

  final String title;
  final String? subtitle;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (subtitle != null) ...[
                const SizedBox(height: 3),
                Text(
                  subtitle!,
                  style: const TextStyle(
                    fontSize: 11,
                    color: LedgerFlowDesign.muted,
                  ),
                ),
              ],
            ],
          ),
        ),
        ?action,
      ],
    );
  }
}

class ResponsiveColumns extends StatelessWidget {
  const ResponsiveColumns({
    required this.left,
    required this.right,
    this.leftFlex = 2,
    this.rightFlex = 1,
    super.key,
  });

  final Widget left;
  final Widget right;
  final int leftFlex;
  final int rightFlex;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 1040) {
          return Column(children: [left, const SizedBox(height: 12), right]);
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: leftFlex, child: left),
            const SizedBox(width: 12),
            Expanded(flex: rightFlex, child: right),
          ],
        );
      },
    );
  }
}

class DetailRow extends StatelessWidget {
  const DetailRow({required this.label, required this.value, super.key});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 112,
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 12,
                color: LedgerFlowDesign.muted,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({required this.message, super.key});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.inbox_outlined,
              color: LedgerFlowDesign.muted,
              size: 32,
            ),
            const SizedBox(height: 10),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: LedgerFlowDesign.muted),
            ),
          ],
        ),
      ),
    );
  }
}

class _RecordPicker extends StatelessWidget {
  const _RecordPicker({
    required this.records,
    required this.selectedIndex,
    required this.label,
    required this.detail,
    required this.onSelected,
  });

  final List<JsonMap> records;
  final int selectedIndex;
  final String Function(JsonMap) label;
  final String Function(JsonMap) detail;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 74,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: records.length,
        separatorBuilder: (_, _) => const SizedBox(width: 10),
        itemBuilder: (context, index) {
          final selected = index == selectedIndex;
          return InkWell(
            onTap: () => onSelected(index),
            borderRadius: BorderRadius.circular(10),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              width: 220,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
              decoration: BoxDecoration(
                color: selected ? const Color(0xFFE8F7F6) : Colors.white,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(
                  color: selected
                      ? LedgerFlowDesign.teal
                      : LedgerFlowDesign.border,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label(records[index]),
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: selected
                          ? LedgerFlowDesign.tealDark
                          : LedgerFlowDesign.ink,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    detail(records[index]),
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 11,
                      color: LedgerFlowDesign.muted,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

class _LifecycleStrip extends StatelessWidget {
  const _LifecycleStrip({required this.steps, required this.activeIndex});

  final List<String> steps;
  final int activeIndex;

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      child: Row(
        children: [
          for (var index = 0; index < steps.length; index++) ...[
            Expanded(
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 15,
                    backgroundColor: index <= activeIndex
                        ? LedgerFlowDesign.teal
                        : const Color(0xFFE8ECF1),
                    foregroundColor: index <= activeIndex
                        ? Colors.white
                        : LedgerFlowDesign.muted,
                    child: index < activeIndex
                        ? const Icon(Icons.check, size: 16)
                        : Text(
                            '${index + 1}',
                            style: const TextStyle(fontSize: 11),
                          ),
                  ),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      steps[index],
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            if (index < steps.length - 1)
              Container(
                width: 24,
                height: 1,
                color: index < activeIndex
                    ? LedgerFlowDesign.teal
                    : LedgerFlowDesign.border,
              ),
          ],
        ],
      ),
    );
  }
}

class _OptionComparison extends StatelessWidget {
  const _OptionComparison({required this.options});

  final List<JsonMap> options;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: const [
          DataColumn(label: Text('Rank')),
          DataColumn(label: Text('Option')),
          DataColumn(label: Text('Payer cost')),
          DataColumn(label: Text('Customer price')),
          DataColumn(label: Text('Margin')),
          DataColumn(label: Text('Transit')),
          DataColumn(label: Text('Score')),
          DataColumn(label: Text('Policy')),
        ],
        rows: options.map((option) {
          return DataRow(
            cells: [
              DataCell(Text('#${_text(option, 'rank')}')),
              DataCell(
                Text(
                  _text(option, 'option_name'),
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    color: LedgerFlowDesign.tealDark,
                  ),
                ),
              ),
              DataCell(Text(_money(_number(option['payer_total_amount'])))),
              DataCell(Text(_money(_number(option['payee_total_amount'])))),
              DataCell(
                Text(
                  '${_money(_number(option['margin_amount']))}  ${_text(option, 'margin_percent')}%',
                ),
              ),
              DataCell(Text('${_text(option, 'transit_time_days')} days')),
              DataCell(Text(_text(option, 'score'))),
              DataCell(
                StatusPill(
                  option['policy_compliant'] == true ? 'APPROVED' : 'EXCEPTION',
                ),
              ),
            ],
          );
        }).toList(),
      ),
    );
  }
}

class _QuoteLineTable extends StatelessWidget {
  const _QuoteLineTable({required this.lines});

  final List<JsonMap> lines;

  @override
  Widget build(BuildContext context) {
    if (lines.isEmpty) {
      return const EmptyState(
        message: 'No charge-line breakdown is available.',
      );
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: const [
          DataColumn(label: Text('Component')),
          DataColumn(label: Text('Basis')),
          DataColumn(label: Text('Quantity')),
          DataColumn(label: Text('Payer')),
          DataColumn(label: Text('Payee')),
          DataColumn(label: Text('Margin')),
        ],
        rows: lines
            .map(
              (line) => DataRow(
                cells: [
                  DataCell(Text(_text(line, 'component'))),
                  DataCell(Text(_text(line, 'basis'))),
                  DataCell(Text(_text(line, 'quantity'))),
                  DataCell(Text(_money(_number(line['payer'])))),
                  DataCell(Text(_money(_number(line['payee'])))),
                  DataCell(Text(_money(_number(line['margin'])))),
                ],
              ),
            )
            .toList(),
      ),
    );
  }
}

class _ContractTile extends StatelessWidget {
  const _ContractTile({
    required this.type,
    required this.code,
    required this.party,
  });

  final String type;
  final String code;
  final String party;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      StatusPill(type == 'BUY' ? 'ACTIVE' : 'REVIEW'),
      const SizedBox(width: 10),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              code,
              style: const TextStyle(
                color: LedgerFlowDesign.info,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              party,
              style: const TextStyle(
                fontSize: 12,
                color: LedgerFlowDesign.muted,
              ),
            ),
          ],
        ),
      ),
    ],
  );
}

class _DocumentTable extends StatelessWidget {
  const _DocumentTable({required this.documents});

  final List<JsonMap> documents;

  @override
  Widget build(BuildContext context) {
    if (documents.isEmpty) {
      return const EmptyState(message: 'No charge documents are available.');
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: const [
          DataColumn(label: Text('Document')),
          DataColumn(label: Text('Source')),
          DataColumn(label: Text('Payer total')),
          DataColumn(label: Text('Payee total')),
          DataColumn(label: Text('Margin')),
          DataColumn(label: Text('Status')),
          DataColumn(label: Text('Date')),
        ],
        rows: documents
            .map(
              (document) => DataRow(
                cells: [
                  DataCell(
                    Text(
                      _text(document, 'document_number'),
                      style: const TextStyle(
                        color: LedgerFlowDesign.info,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      '${_text(document, 'source_object_type')} ${_text(document, 'source_object_id')}',
                    ),
                  ),
                  DataCell(
                    Text(
                      _money(
                        _number(document['payer_total_amount']),
                        currency: _text(document, 'currency'),
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      _money(
                        _number(document['payee_total_amount']),
                        currency: _text(document, 'currency'),
                      ),
                    ),
                  ),
                  DataCell(
                    Text(
                      _money(
                        _number(document['margin_amount']),
                        currency: _text(document, 'currency'),
                      ),
                    ),
                  ),
                  DataCell(StatusPill(_text(document, 'status'))),
                  DataCell(Text(_text(document, 'document_date'))),
                ],
              ),
            )
            .toList(),
      ),
    );
  }
}

class _QueueRow extends StatelessWidget {
  const _QueueRow({required this.document});

  final JsonMap document;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _text(document, 'document_number'),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 3),
                Text(
                  '${_text(document, 'source_object_type')} ${_text(document, 'source_object_id')}',
                  style: const TextStyle(
                    fontSize: 11,
                    color: LedgerFlowDesign.muted,
                  ),
                ),
              ],
            ),
          ),
          Text(
            _money(
              _number(document['payee_total_amount']),
              currency: _text(document, 'currency'),
            ),
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 10),
          StatusPill(_text(document, 'status')),
        ],
      ),
    );
  }
}

class _ChargeLineTable extends StatelessWidget {
  const _ChargeLineTable({
    required this.lines,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<JsonMap> lines;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    if (lines.isEmpty) {
      return const EmptyState(message: 'No charge lines are available.');
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        showCheckboxColumn: false,
        columns: const [
          DataColumn(label: Text('#')),
          DataColumn(label: Text('Component')),
          DataColumn(label: Text('Role')),
          DataColumn(label: Text('Target')),
          DataColumn(label: Text('Basis')),
          DataColumn(label: Text('Source amount')),
          DataColumn(label: Text('FX')),
          DataColumn(label: Text('Expected')),
          DataColumn(label: Text('Actual')),
          DataColumn(label: Text('Approved')),
          DataColumn(label: Text('Status')),
        ],
        rows: List.generate(lines.length, (index) {
          final line = lines[index];
          return DataRow(
            selected: index == selectedIndex,
            onSelectChanged: (_) => onSelected(index),
            cells: [
              DataCell(Text(_text(line, 'line_number'))),
              DataCell(
                Text(
                  _text(
                    line,
                    'description',
                    fallback: _text(line, 'charge_component_code'),
                  ),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              DataCell(Text(_text(line, 'relationship_role'))),
              DataCell(Text(_text(line, 'target_level'))),
              DataCell(Text(_text(line, 'basis'))),
              DataCell(
                Text(
                  '${_text(line, 'source_currency')} ${_text(line, 'source_amount')}',
                ),
              ),
              DataCell(Text(_text(line, 'exchange_rate'))),
              DataCell(Text(_text(line, 'expected_amount'))),
              DataCell(Text(_text(line, 'actual_amount', fallback: '—'))),
              DataCell(Text(_text(line, 'approved_amount', fallback: '—'))),
              DataCell(StatusPill(_text(line, 'status'))),
            ],
          );
        }),
      ),
    );
  }
}

class _ProvenancePanel extends StatelessWidget {
  const _ProvenancePanel({required this.line, this.sourceQuoteLine});

  final JsonMap line;
  final JsonMap? sourceQuoteLine;

  @override
  Widget build(BuildContext context) {
    return SurfaceCard(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final cards = [
            _ProvenanceBlock(
              title: 'Calculation',
              icon: Icons.calculate_outlined,
              rows: {
                'Mode': _text(line, 'calculation_mode'),
                'Status': _text(line, 'calculation_status'),
                'Basis': _text(line, 'basis'),
                'Profile version': _text(
                  line,
                  'calculation_profile_version_id',
                  fallback: 'Direct / none',
                ),
                'Rate': _text(line, 'rate_amount', fallback: '—'),
                'Rate result':
                    '${_text(line, 'source_currency')} ${_text(line, 'source_amount')}',
              },
            ),
            _ProvenanceBlock(
              title: 'Allocation',
              icon: Icons.call_split_outlined,
              rows: {
                'Mode': _text(line, 'allocation_mode'),
                'Status': _text(line, 'allocation_status'),
                'Target': _text(line, 'target_level'),
                'Profile / version':
                    '${_text(line, 'allocation_profile_id', fallback: '—')} / ${_text(line, 'allocation_profile_version_id', fallback: '—')}',
                'Basis': _text(line, 'allocation_basis', fallback: '—'),
                'Ratio': _text(line, 'allocation_ratio', fallback: '—'),
                'Driver value': _text(
                  line,
                  'allocation_driver_value',
                  fallback: '—',
                ),
              },
            ),
            _ProvenanceBlock(
              title: 'Date & FX',
              icon: Icons.currency_exchange_outlined,
              rows: {
                'Charge date': _text(line, 'charge_date', fallback: '—'),
                'Date basis': _text(line, 'charge_date_basis'),
                'Source amount':
                    '${_text(line, 'source_currency')} ${_text(line, 'source_amount')}',
                'FX source': _text(line, 'exchange_rate_source_code'),
                'FX rate ID': _text(line, 'fx_rate_id', fallback: '—'),
                'Type / method':
                    '${_text(line, 'exchange_rate_type', fallback: '—')} / ${_text(line, 'exchange_rate_method', fallback: '—')}',
                'FX date': _text(line, 'exchange_rate_date', fallback: '—'),
                'Rate': _text(line, 'exchange_rate'),
              },
            ),
            _ProvenanceBlock(
              title: 'Commercial source',
              icon: Icons.account_tree_outlined,
              rows: {
                'Quote option line': _text(
                  line,
                  'source_quote_option_line_id',
                  fallback: 'Direct / manual',
                ),
                'Contract / source': sourceQuoteLine == null
                    ? '—'
                    : sourceQuoteLine!['source_contract_template_route_id'] !=
                          null
                    ? '${_text(sourceQuoteLine!, 'source_contract_id', fallback: '-')} / route ${_text(sourceQuoteLine!, 'source_contract_template_route_id')}'
                    : sourceQuoteLine!['source_contract_line_id'] != null
                    ? '${_text(sourceQuoteLine!, 'source_contract_id', fallback: '-')} / line ${_text(sourceQuoteLine!, 'source_contract_line_id')}'
                    : '${_text(sourceQuoteLine!, 'source_contract_id', fallback: '-')} / header template',
                'Rate book / row': sourceQuoteLine == null
                    ? '—'
                    : '${_text(sourceQuoteLine!, 'source_rate_book_id', fallback: '—')} / ${_text(sourceQuoteLine!, 'source_rate_book_entry_id', fallback: '—')}',
                'Template / step': sourceQuoteLine == null
                    ? '—'
                    : '${_text(sourceQuoteLine!, 'source_calculation_template_id', fallback: '—')} / ${_text(sourceQuoteLine!, 'source_calculation_template_step_id', fallback: '—')}',
              },
            ),
          ];
          final cardWidth = constraints.maxWidth < 760
              ? constraints.maxWidth
              : (constraints.maxWidth - 14) / 2;
          final snapshots = <String, dynamic>{
            'Calculation configuration':
                line['calculation_config_snapshot_json'],
            'Calculation inputs': line['calculation_input_snapshot_json'],
            'Calculation audit': line['calculation_audit_json'],
            'Allocation configuration': line['allocation_config_snapshot_json'],
            'Pinned allocation': line['pinned_allocation_snapshot_json'],
            'Effective allocation': line['effective_allocation_snapshot_json'],
            'Target reference': line['target_reference_snapshot_json'],
          }..removeWhere((_, value) => value == null);
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  for (final card in cards)
                    SizedBox(width: cardWidth, child: card),
                ],
              ),
              if (snapshots.isNotEmpty) ...[
                const SizedBox(height: 18),
                const Divider(),
                const SizedBox(height: 8),
                const Text(
                  'Immutable snapshots',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                for (final snapshot in snapshots.entries)
                  _SnapshotInspector(
                    label: snapshot.key,
                    value: snapshot.value,
                  ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _ProvenanceBlock extends StatelessWidget {
  const _ProvenanceBlock({
    required this.title,
    required this.icon,
    required this.rows,
  });

  final String title;
  final IconData icon;
  final Map<String, String> rows;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          Icon(icon, size: 19, color: LedgerFlowDesign.teal),
          const SizedBox(width: 8),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        ],
      ),
      const SizedBox(height: 10),
      for (final entry in rows.entries)
        DetailRow(label: entry.key, value: entry.value),
    ],
  );
}

class _CheckRow extends StatelessWidget {
  const _CheckRow({required this.label, required this.pass, this.detail = ''});

  final String label;
  final bool pass;
  final String detail;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 7),
    child: Row(
      children: [
        Icon(
          pass ? Icons.check_circle : Icons.error,
          color: pass ? LedgerFlowDesign.success : LedgerFlowDesign.danger,
          size: 18,
        ),
        const SizedBox(width: 9),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: const TextStyle(fontSize: 12)),
              if (detail.isNotEmpty)
                Text(
                  detail,
                  style: const TextStyle(
                    fontSize: 10,
                    color: LedgerFlowDesign.muted,
                  ),
                ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _SnapshotInspector extends StatelessWidget {
  const _SnapshotInspector({required this.label, required this.value});

  final String label;
  final dynamic value;

  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 8),
    decoration: BoxDecoration(
      border: Border.all(color: LedgerFlowDesign.border),
      borderRadius: BorderRadius.circular(8),
    ),
    child: ExpansionTile(
      dense: true,
      title: Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
      childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
      expandedCrossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: double.infinity,
          child: SelectableText(
            const JsonEncoder.withIndent('  ').convert(value),
            style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
          ),
        ),
      ],
    ),
  );
}

class _DocumentStatusDialog extends StatefulWidget {
  const _DocumentStatusDialog({required this.currentStatus});

  final String currentStatus;

  @override
  State<_DocumentStatusDialog> createState() => _DocumentStatusDialogState();
}

class _DocumentStatusDialogState extends State<_DocumentStatusDialog> {
  late String _status = widget.currentStatus;

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Set document status'),
    content: SizedBox(
      width: 460,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Mutable statuses describe the operational stage before approval. DISPUTED blocks approval until the document is moved back to an eligible status.',
            style: TextStyle(color: LedgerFlowDesign.muted),
          ),
          const SizedBox(height: 18),
          DropdownButtonFormField<String>(
            initialValue: _status,
            decoration: const InputDecoration(labelText: 'Status'),
            items: const [
              DropdownMenuItem(value: 'ESTIMATED', child: Text('ESTIMATED')),
              DropdownMenuItem(value: 'ACCRUED', child: Text('ACCRUED')),
              DropdownMenuItem(value: 'ACTUAL', child: Text('ACTUAL')),
              DropdownMenuItem(value: 'DISPUTED', child: Text('DISPUTED')),
            ],
            onChanged: (value) => setState(() => _status = value ?? _status),
          ),
        ],
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: () => Navigator.pop(context, _status),
        child: const Text('Save status'),
      ),
    ],
  );
}

class _DocumentReversalDialog extends StatefulWidget {
  const _DocumentReversalDialog({required this.documentNumber});

  final String documentNumber;

  @override
  State<_DocumentReversalDialog> createState() =>
      _DocumentReversalDialogState();
}

class _DocumentReversalDialogState extends State<_DocumentReversalDialog> {
  final _formKey = GlobalKey<FormState>();
  final _reason = TextEditingController();

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text('Reverse ${widget.documentNumber}?'),
    content: SizedBox(
      width: 500,
      child: Form(
        key: _formKey,
        child: TextFormField(
          controller: _reason,
          autofocus: true,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Reversal reason',
            helperText: 'Stored permanently with the financial document',
          ),
          validator: (value) => value == null || value.trim().isEmpty
              ? 'A reversal reason is required.'
              : null,
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: () {
          if (!_formKey.currentState!.validate()) return;
          Navigator.pop(context, _reason.text.trim());
        },
        child: const Text('Reverse document'),
      ),
    ],
  );
}

class _ExportResultDialog extends StatelessWidget {
  const _ExportResultDialog({required this.export});

  final JsonMap export;

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      _text(export, 'export_number', fallback: 'Charge document export'),
    ),
    content: SizedBox(
      width: 760,
      height: 560,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 24,
            runSpacing: 8,
            children: [
              Text('Target: ${_text(export, 'target_system')}'),
              Text('Status: ${_text(export, 'status')}'),
            ],
          ),
          const SizedBox(height: 14),
          const Text(
            'The default service stores this INTERNAL_LEDGER payload. Delivery to an ERP or ledger requires an adopter-provided export adapter.',
            style: TextStyle(color: LedgerFlowDesign.muted),
          ),
          const SizedBox(height: 14),
          const Divider(),
          const SizedBox(height: 8),
          const Text('Payload', style: TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Expanded(
            child: SingleChildScrollView(
              child: SelectableText(
                const JsonEncoder.withIndent(
                  '  ',
                ).convert(export['payload_json'] ?? const {}),
                style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
              ),
            ),
          ),
        ],
      ),
    ),
    actions: [
      FilledButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Close'),
      ),
    ],
  );
}

class _InvoiceLineTable extends StatelessWidget {
  const _InvoiceLineTable({required this.lines, required this.currency});

  final List<JsonMap> lines;
  final String currency;

  @override
  Widget build(BuildContext context) {
    if (lines.isEmpty) {
      return const EmptyState(message: 'No invoice lines are available.');
    }
    final sorted = [...lines]
      ..sort(
        (a, b) => _number(
          b['variance_amount'],
        ).abs().compareTo(_number(a['variance_amount']).abs()),
      );
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: const [
          DataColumn(label: Text('Line')),
          DataColumn(label: Text('Description')),
          DataColumn(label: Text('Matched charge')),
          DataColumn(label: Text('Expected')),
          DataColumn(label: Text('Invoiced')),
          DataColumn(label: Text('Variance')),
          DataColumn(label: Text('Result')),
        ],
        rows: sorted.map((line) {
          final variance = _number(line['variance_amount']);
          return DataRow(
            color: variance.abs() > 0.001
                ? const WidgetStatePropertyAll(Color(0xFFFFF4F2))
                : null,
            cells: [
              DataCell(Text(_text(line, 'line_number'))),
              DataCell(
                Text(
                  _text(line, 'description'),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              DataCell(
                Text(
                  line['matched_charge_line_id'] == null
                      ? 'Unmatched'
                      : '#${line['matched_charge_line_id']}',
                ),
              ),
              DataCell(
                Text(
                  _money(_number(line['expected_amount']), currency: currency),
                ),
              ),
              DataCell(
                Text(
                  _money(_number(line['invoiced_amount']), currency: currency),
                ),
              ),
              DataCell(
                Text(
                  _money(variance, currency: currency),
                  style: TextStyle(
                    color: variance == 0
                        ? LedgerFlowDesign.ink
                        : LedgerFlowDesign.danger,
                    fontWeight: variance == 0
                        ? FontWeight.w400
                        : FontWeight.w700,
                  ),
                ),
              ),
              DataCell(StatusPill(_text(line, 'status'))),
            ],
          );
        }).toList(),
      ),
    );
  }
}

class _ResolutionChoice extends StatelessWidget {
  const _ResolutionChoice({
    required this.title,
    required this.detail,
    this.selected = false,
  });

  final String title;
  final String detail;
  final bool selected;

  @override
  Widget build(BuildContext context) => Container(
    width: 230,
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      color: selected ? const Color(0xFFEAF8F7) : Colors.white,
      borderRadius: BorderRadius.circular(9),
      border: Border.all(
        color: selected ? LedgerFlowDesign.teal : LedgerFlowDesign.border,
      ),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          selected ? Icons.radio_button_checked : Icons.radio_button_off,
          color: selected ? LedgerFlowDesign.teal : LedgerFlowDesign.muted,
          size: 19,
        ),
        const SizedBox(width: 9),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                detail,
                style: const TextStyle(
                  color: LedgerFlowDesign.muted,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _MatchHealth extends StatelessWidget {
  const _MatchHealth({required this.matched, required this.total});

  final int matched;
  final int total;

  @override
  Widget build(BuildContext context) {
    final percent = total == 0 ? 0 : (matched / total * 100).round();
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionHeading(title: 'Match health'),
          const SizedBox(height: 16),
          Row(
            children: [
              SizedBox(
                width: 76,
                height: 76,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    CircularProgressIndicator(
                      value: percent / 100,
                      strokeWidth: 8,
                      color: LedgerFlowDesign.teal,
                      backgroundColor: const Color(0xFFFFC78A),
                    ),
                    Text(
                      '$percent%',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$matched matched',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      '${math.max(0, total - matched)} exceptions',
                      style: const TextStyle(color: LedgerFlowDesign.warning),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _RateTable extends StatelessWidget {
  const _RateTable({
    required this.entries,
    required this.columns,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<JsonMap> entries;
  final List<_RateBookColumnDefinition> columns;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) {
      return const EmptyState(message: 'This rate book has no entries.');
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        showCheckboxColumn: false,
        columns: [
          const DataColumn(label: Text('Rate')),
          const DataColumn(label: Text('Currency')),
          ...columns.map(
            (definition) => DataColumn(
              label: Tooltip(
                message: definition.help,
                child: Text(definition.label),
              ),
            ),
          ),
          const DataColumn(label: Text('Status')),
        ],
        rows: List.generate(entries.length, (index) {
          final entry = entries[index];
          return DataRow(
            selected: index == selectedIndex,
            onSelectChanged: (_) => onSelected(index),
            cells: [
              DataCell(
                Text(
                  _text(entry, 'basis').toUpperCase().startsWith('PERCENT')
                      ? '${_text(entry, 'rate_percent')}%'
                      : _text(entry, 'rate_amount'),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              DataCell(Text(_text(entry, 'currency'))),
              ...columns.map((definition) {
                final fallback = definition.key == 'priority' ? '100' : 'Any';
                return DataCell(
                  Text(
                    definition.isCustom
                        ? _dimensionEntryValue(entry, definition.dimension!)
                        : _text(entry, definition.key, fallback: fallback),
                  ),
                );
              }),
              DataCell(
                StatusPill(entry['is_active'] == false ? 'INACTIVE' : 'ACTIVE'),
              ),
            ],
          );
        }),
      ),
    );
  }
}

class _RateBookColumnDefinition {
  const _RateBookColumnDefinition({
    required this.key,
    required this.label,
    required this.help,
    this.dimension,
  });

  final String key;
  final String label;
  final String help;
  final _PricingDimensionView? dimension;

  bool get isCustom => dimension != null;
}

enum _RateBookDialogMode { create, editDraft, newVersion }

class _RateBookFamily {
  const _RateBookFamily({required this.code, required this.versions});

  final String code;
  final List<JsonMap> versions;

  String get primaryName =>
      _text(versions.first, 'rate_book_name', fallback: 'Rate book $code');

  int? get publishedVersion {
    for (final version in versions) {
      final status = _text(version, 'status').toUpperCase();
      if (status == 'PUBLISHED' || status == 'ACTIVE') {
        return _asInt(version['version_number']);
      }
    }
    return null;
  }
}

class _RateBookVersionRow extends StatelessWidget {
  const _RateBookVersionRow({
    required this.versionLabel,
    required this.status,
    required this.note,
    required this.isSelected,
    required this.immutable,
    required this.onSelect,
  });

  final String versionLabel;
  final String status;
  final String note;
  final bool isSelected;
  final bool immutable;
  final VoidCallback onSelect;

  @override
  Widget build(BuildContext context) {
    final borderColor = isSelected
        ? LedgerFlowDesign.teal.withValues(alpha: 0.34)
        : LedgerFlowDesign.border;
    return InkWell(
      onTap: onSelect,
      borderRadius: BorderRadius.circular(12),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isSelected
              ? LedgerFlowDesign.teal.withValues(alpha: 0.07)
              : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: borderColor),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: immutable
                    ? LedgerFlowDesign.info.withValues(alpha: 0.12)
                    : LedgerFlowDesign.warning.withValues(alpha: 0.12),
                shape: BoxShape.circle,
              ),
              child: Icon(
                immutable ? Icons.lock_outline : Icons.edit_note_outlined,
                size: 16,
                color: immutable
                    ? LedgerFlowDesign.info
                    : LedgerFlowDesign.warning,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      Text(
                        versionLabel,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          color: LedgerFlowDesign.tealDark,
                        ),
                      ),
                      const SizedBox(width: 8),
                      StatusPill(status),
                    ],
                  ),
                  const SizedBox(height: 5),
                  Text(
                    note,
                    style: const TextStyle(
                      fontSize: 11,
                      color: LedgerFlowDesign.muted,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            IconButton(
              tooltip: 'Select version',
              visualDensity: VisualDensity.compact,
              onPressed: onSelect,
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
      ),
    );
  }
}

class _RateBookModeNotice extends StatelessWidget {
  const _RateBookModeNotice();

  @override
  Widget build(BuildContext context) => SurfaceCard(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: const [
        Icon(Icons.lock_outline, size: 18, color: LedgerFlowDesign.muted),
        SizedBox(width: 10),
        Expanded(
          child: Text(
            'Demo mode is read-only. Connect a bearer-authenticated API to create rate books, edit draft workspaces, create new draft versions, and publish reviewed releases.',
            style: TextStyle(
              fontSize: 12,
              color: LedgerFlowDesign.muted,
              height: 1.45,
            ),
          ),
        ),
      ],
    ),
  );
}

class _RateAttributeDefinition {
  const _RateAttributeDefinition(this.key, this.label, this.help);

  final String key;
  final String label;
  final String help;
}

class _PricingDimensionView {
  const _PricingDimensionView({
    required this.code,
    required this.name,
    required this.dataType,
    required this.description,
    required this.allowedValues,
    required this.builtInField,
    required this.caseSensitive,
    required this.isSystem,
    required this.isActive,
  });

  factory _PricingDimensionView.fromJson(JsonMap dimension) =>
      _PricingDimensionView(
        code: _text(dimension, 'dimension_code', fallback: '').toUpperCase(),
        name: _text(dimension, 'dimension_name', fallback: ''),
        dataType: _text(
          dimension,
          'data_type',
          fallback: 'STRING',
        ).toUpperCase(),
        description: _text(dimension, 'description', fallback: ''),
        allowedValues: _stringList(dimension['allowed_values']),
        builtInField:
            dimension['built_in_field']?.toString().trim().isNotEmpty == true,
        caseSensitive: dimension['case_sensitive'] == true,
        isSystem: dimension['is_system'] == true,
        isActive: dimension['is_active'] != false,
      );

  final String code;
  final String name;
  final String dataType;
  final String description;
  final List<String> allowedValues;
  final bool builtInField;
  final bool caseSensitive;
  final bool isSystem;
  final bool isActive;

  String get label => name.isEmpty ? code : '$name ($code)';
}

List<_PricingDimensionView> _pricingDimensionViews(List<JsonMap> dimensions) =>
    dimensions.map(_PricingDimensionView.fromJson).toList(growable: false);

List<_PricingDimensionView> _customDimensionOptions(List<JsonMap> dimensions) =>
    _pricingDimensionViews(dimensions)
        .where((dimension) => !dimension.builtInField && dimension.isActive)
        .toList(growable: false);

List<_PricingDimensionView> _selectedPricingDimensions(
  List<_PricingDimensionView> dimensions,
  Set<String> selectedCodes,
) {
  if (selectedCodes.isEmpty) return const [];
  final byCode = {
    for (final dimension in dimensions) dimension.code.toUpperCase(): dimension,
  };
  return [
    for (final code in selectedCodes)
      if (byCode.containsKey(code.toUpperCase())) byCode[code.toUpperCase()]!,
  ];
}

String _pricingDimensionCode(_PricingDimensionView dimension) => dimension.code;

String _pricingDimensionLabel(_PricingDimensionView dimension) =>
    dimension.label;

String _pricingDimensionTooltip(_PricingDimensionView dimension) {
  final details = [
    dimension.dataType,
    if (dimension.allowedValues.isNotEmpty)
      'Allowed: ${dimension.allowedValues.join(', ')}',
    if (dimension.description.isNotEmpty) dimension.description,
  ];
  return details.join(' / ');
}

String _dimensionEntryValue(JsonMap entry, _PricingDimensionView dimension) {
  final values = entry['dimension_values'];
  if (values is Map && values.containsKey(dimension.code)) {
    return _dimensionValueText(values[dimension.code], dimension);
  }
  if (entry.containsKey(dimension.code)) {
    return _dimensionValueText(entry[dimension.code], dimension);
  }
  return 'Any';
}

String _dimensionValueText(dynamic value, _PricingDimensionView dimension) {
  if (value == null || value.toString().trim().isEmpty) return 'Any';
  return value.toString();
}

dynamic _typedDimensionValue(String raw, _PricingDimensionView dimension) {
  final text = raw.trim();
  if (text.isEmpty) return null;
  switch (dimension.dataType) {
    case 'DECIMAL':
      return double.tryParse(text);
    case 'INTEGER':
      return int.tryParse(text);
    case 'BOOLEAN':
      return text.toLowerCase() == 'true' || text == '1';
    case 'DATE':
      return text;
    case 'STRING':
    default:
      return text;
  }
}

double _customDimensionWidth(_PricingDimensionView dimension) {
  switch (dimension.dataType) {
    case 'BOOLEAN':
      return 160;
    case 'DATE':
      return 180;
    case 'INTEGER':
      return 130;
    case 'DECIMAL':
      return 150;
    case 'STRING':
    default:
      return dimension.allowedValues.isNotEmpty ? 230 : 190;
  }
}

Widget _customDimensionField({
  required _RateEntryDraft entry,
  required _PricingDimensionView dimension,
  required VoidCallback onChanged,
  required double width,
}) {
  final key = dimension.code;
  final value = entry.dimensionValues[key] ?? '';
  Widget field;
  switch (dimension.dataType) {
    case 'BOOLEAN':
      field = DropdownButtonFormField<String>(
        initialValue: value.isEmpty ? null : value,
        isExpanded: true,
        decoration: InputDecoration(
          labelText: dimension.name.isEmpty ? dimension.code : dimension.name,
          helperText: dimension.description.isEmpty
              ? null
              : dimension.description,
        ),
        items: const [
          DropdownMenuItem(value: '', child: Text('Any / not restricted')),
          DropdownMenuItem(value: 'true', child: Text('Yes')),
          DropdownMenuItem(value: 'false', child: Text('No')),
        ],
        onChanged: (next) {
          entry.dimensionValues[key] = next ?? '';
          onChanged();
        },
      );
      break;
    case 'DATE':
      field = _DatePickerValueField(
        initialValue: value,
        label: dimension.name.isEmpty ? dimension.code : dimension.name,
        help: dimension.description.isEmpty ? null : dimension.description,
        validator: (candidate) =>
            _isoDimensionValue(candidate, required: false),
        onChanged: (next) {
          entry.dimensionValues[key] = next;
          onChanged();
        },
      );
      break;
    case 'INTEGER':
    case 'DECIMAL':
      field = TextFormField(
        initialValue: value,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(
          labelText: dimension.name.isEmpty ? dimension.code : dimension.name,
          helperText: dimension.description.isEmpty
              ? null
              : dimension.description,
        ),
        validator: (candidate) => _numericDimensionValue(candidate, dimension),
        onChanged: (next) {
          entry.dimensionValues[key] = next;
          onChanged();
        },
      );
      break;
    default:
      if (dimension.allowedValues.isNotEmpty) {
        field = DropdownButtonFormField<String>(
          initialValue: value.isEmpty ? null : value,
          isExpanded: true,
          decoration: InputDecoration(
            labelText: dimension.name.isEmpty ? dimension.code : dimension.name,
            helperText: dimension.description.isEmpty
                ? null
                : dimension.description,
          ),
          items: [
            const DropdownMenuItem(
              value: '',
              child: Text('Any / not restricted'),
            ),
            ...dimension.allowedValues.map(
              (candidate) =>
                  DropdownMenuItem(value: candidate, child: Text(candidate)),
            ),
          ],
          onChanged: (next) {
            entry.dimensionValues[key] = next ?? '';
            onChanged();
          },
        );
      } else {
        field = TextFormField(
          initialValue: value,
          decoration: InputDecoration(
            labelText: dimension.name.isEmpty ? dimension.code : dimension.name,
            helperText: dimension.description.isEmpty
                ? null
                : dimension.description,
          ),
          onChanged: (next) {
            entry.dimensionValues[key] = next;
            onChanged();
          },
        );
      }
      break;
  }
  return SizedBox(width: width, child: field);
}

String? _numericDimensionValue(String? value, _PricingDimensionView dimension) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return null;
  final parsed = dimension.dataType == 'INTEGER'
      ? int.tryParse(text)
      : double.tryParse(text);
  return parsed == null
      ? 'Enter a valid ${dimension.dataType.toLowerCase()}'
      : null;
}

String? _isoDimensionValue(String? value, {bool required = false}) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return required ? 'Date is required' : null;
  return DateTime.tryParse(text) == null ? 'Use YYYY-MM-DD' : null;
}

List<_RateBookColumnDefinition> _rateBookColumns(
  JsonMap? book,
  List<JsonMap> pricingDimensions, {
  required Set<String> builtInKeys,
  required Set<String> customCodes,
}) {
  final columns = <_RateBookColumnDefinition>[
    for (final definition in _rateAttributeDefinitions)
      if (builtInKeys.contains(definition.key))
        _RateBookColumnDefinition(
          key: definition.key,
          label: definition.label,
          help: definition.help,
        ),
  ];
  final dimensionsByCode = {
    for (final dimension in _pricingDimensionViews(pricingDimensions))
      dimension.code.toUpperCase(): dimension,
  };
  for (final code in customCodes) {
    final dimension = dimensionsByCode[code.toUpperCase()];
    if (dimension == null) continue;
    columns.add(
      _RateBookColumnDefinition(
        key: dimension.code,
        label: dimension.name.isEmpty ? dimension.code : dimension.name,
        help: _pricingDimensionTooltip(dimension),
        dimension: dimension,
      ),
    );
  }
  return columns;
}

Set<String> _rateBookDimensionCodes(JsonMap? book) {
  final configured = (book?['dimension_codes'] as List?)
      ?.map((value) => value.toString())
      .where((value) => value.isNotEmpty)
      .toSet();
  if (configured != null) {
    return configured.map((value) => value.toUpperCase()).toSet();
  }
  final inferred = <String>{};
  for (final entry in _rows(book ?? const <String, dynamic>{}, 'entries')) {
    final values = entry['dimension_values'];
    if (values is Map) {
      for (final key in values.keys) {
        final code = key.toString().trim();
        if (code.isNotEmpty) inferred.add(code.toUpperCase());
      }
    }
  }
  return inferred;
}

const _rateAttributeDefinitions = <_RateAttributeDefinition>[
  _RateAttributeDefinition(
    'origin_code',
    'Origin',
    'Matches the origin location code supplied by the caller.',
  ),
  _RateAttributeDefinition(
    'destination_code',
    'Destination',
    'Matches the destination location code supplied by the caller.',
  ),
  _RateAttributeDefinition(
    'mode',
    'Transport mode',
    'Restricts the row to AIR, OCEAN, RAIL, or ROAD requests.',
  ),
  _RateAttributeDefinition(
    'equipment_type',
    'Equipment',
    'Restricts the row to the caller-supplied equipment type.',
  ),
  _RateAttributeDefinition(
    'commodity_code',
    'Commodity',
    'Restricts the row to a commodity or goods classification.',
  ),
  _RateAttributeDefinition(
    'service_level',
    'Service level',
    'Restricts the row to the requested service level.',
  ),
  _RateAttributeDefinition(
    'scale_from',
    'Scale from',
    'Lower inclusive break for the calculation quantity.',
  ),
  _RateAttributeDefinition(
    'scale_to',
    'Scale to',
    'Upper inclusive break for the calculation quantity.',
  ),
  _RateAttributeDefinition(
    'minimum_amount',
    'Minimum charge',
    'Minimum amount applied after rate calculation.',
  ),
  _RateAttributeDefinition(
    'maximum_amount',
    'Maximum charge',
    'Maximum amount applied after rate calculation.',
  ),
  _RateAttributeDefinition(
    'validity_from',
    'Valid from',
    'First date on which the row may be selected.',
  ),
  _RateAttributeDefinition(
    'validity_to',
    'Valid to',
    'Last date on which the row may be selected.',
  ),
  _RateAttributeDefinition(
    'basis_override',
    'Calculation basis override',
    'Overrides the charge component default only for this row.',
  ),
  _RateAttributeDefinition(
    'charge_context_override',
    'Charge context override',
    'Overrides the charge component context only for this row.',
  ),
  _RateAttributeDefinition(
    'calculation_profile_id',
    'Calculation profile',
    'Overrides the component calculation profile for this row.',
  ),
  _RateAttributeDefinition(
    'allocation_profile_id',
    'Allocation profile',
    'Overrides the component allocation profile for this row.',
  ),
  _RateAttributeDefinition(
    'priority',
    'Priority',
    'Lower values win when otherwise equally specific rows match.',
  ),
];

Set<String> _rateBookAttributeKeys(JsonMap? book) {
  final configured = (book?['row_attribute_keys'] as List?)
      ?.map((value) => value.toString())
      .where((value) => value.isNotEmpty)
      .toSet();
  if (configured != null) return configured;
  final inferred = <String>{};
  for (final entry in _rows(book ?? const <String, dynamic>{}, 'entries')) {
    for (final definition in _rateAttributeDefinitions) {
      final value = entry[definition.key];
      if (value != null && value.toString().trim().isNotEmpty) {
        inferred.add(definition.key);
      }
    }
  }
  return inferred;
}

class _RateEntryDraft {
  _RateEntryDraft({
    this.original = const <String, dynamic>{},
    this.componentCode = '',
    this.basis = '',
    this.chargeContext = '',
    this.currency = 'USD',
    this.rateAmount = '',
    this.ratePercent = '',
    this.originCode = '',
    this.destinationCode = '',
    this.mode = '',
    this.equipmentType = '',
    this.commodityCode = '',
    this.serviceLevel = '',
    this.scaleFrom = '',
    this.scaleTo = '',
    this.minimumAmount = '',
    this.maximumAmount = '',
    this.validityFrom = '',
    this.validityTo = '',
    this.calculationProfileId = '',
    this.allocationProfileId = '',
    this.priority = '100',
    this.isActive = true,
    this.dimensionValues = const <String, String>{},
  });

  factory _RateEntryDraft.fromJson(JsonMap entry) => _RateEntryDraft(
    original: JsonMap.from(entry),
    componentCode: _text(entry, 'charge_component_code', fallback: ''),
    basis: entry.containsKey('basis_override')
        ? _text(entry, 'basis_override', fallback: '')
        : _text(entry, 'basis', fallback: ''),
    chargeContext: entry.containsKey('charge_context_override')
        ? _text(entry, 'charge_context_override', fallback: '')
        : _text(entry, 'charge_context', fallback: ''),
    currency: _text(entry, 'currency', fallback: 'USD'),
    rateAmount: _text(entry, 'rate_amount', fallback: ''),
    ratePercent: _text(entry, 'rate_percent', fallback: ''),
    originCode: _text(entry, 'origin_code', fallback: ''),
    destinationCode: _text(entry, 'destination_code', fallback: ''),
    mode: _text(entry, 'mode', fallback: ''),
    equipmentType: _text(entry, 'equipment_type', fallback: ''),
    commodityCode: _text(entry, 'commodity_code', fallback: ''),
    serviceLevel: _text(entry, 'service_level', fallback: ''),
    scaleFrom: _text(entry, 'scale_from', fallback: ''),
    scaleTo: _text(entry, 'scale_to', fallback: ''),
    minimumAmount: _text(entry, 'minimum_amount', fallback: ''),
    maximumAmount: _text(entry, 'maximum_amount', fallback: ''),
    validityFrom: _text(entry, 'validity_from', fallback: ''),
    validityTo: _text(entry, 'validity_to', fallback: ''),
    calculationProfileId: _text(entry, 'calculation_profile_id', fallback: ''),
    allocationProfileId: _text(entry, 'allocation_profile_id', fallback: ''),
    priority: _text(entry, 'priority', fallback: '100'),
    isActive: entry['is_active'] != false,
    dimensionValues: _stringMap(entry['dimension_values']),
  );

  final JsonMap original;
  String componentCode;
  String basis;
  String chargeContext;
  String currency;
  String rateAmount;
  String ratePercent;
  String originCode;
  String destinationCode;
  String mode;
  String equipmentType;
  String commodityCode;
  String serviceLevel;
  String scaleFrom;
  String scaleTo;
  String minimumAmount;
  String maximumAmount;
  String validityFrom;
  String validityTo;
  String calculationProfileId;
  String allocationProfileId;
  String priority;
  bool isActive;
  Map<String, String> dimensionValues;

  JsonMap toJson(
    List<JsonMap> components, {
    required String componentCode,
    required String bookCurrency,
    required Set<String> attributeKeys,
    required List<_PricingDimensionView> customDimensions,
  }) {
    final component = _rateComponent(components, componentCode);
    final effectiveBasis = basis.trim().isNotEmpty
        ? basis.trim().toUpperCase()
        : _text(
            component ?? const <String, dynamic>{},
            'calculation_basis',
            fallback: 'FLAT',
          ).toUpperCase();
    final isPercentage = effectiveBasis.startsWith('PERCENT');
    final payload = <String, dynamic>{
      'charge_component_code': componentCode.trim().toUpperCase(),
      'currency': currency.trim().isEmpty
          ? bookCurrency.trim().toUpperCase()
          : currency.trim().toUpperCase(),
      'is_active': isActive,
    };
    if (attributeKeys.contains('basis_override') && basis.trim().isNotEmpty) {
      payload['basis_override'] = basis.trim().toUpperCase();
    }
    if (attributeKeys.contains('charge_context_override') &&
        chargeContext.trim().isNotEmpty) {
      payload['charge_context_override'] = chargeContext.trim().toUpperCase();
    }
    if (attributeKeys.contains('origin_code') && originCode.trim().isNotEmpty) {
      payload['origin_code'] = originCode.trim().toUpperCase();
    }
    if (attributeKeys.contains('destination_code') &&
        destinationCode.trim().isNotEmpty) {
      payload['destination_code'] = destinationCode.trim().toUpperCase();
    }
    if (attributeKeys.contains('mode') && mode.trim().isNotEmpty) {
      payload['mode'] = mode.trim().toUpperCase();
    }
    if (attributeKeys.contains('equipment_type') &&
        equipmentType.trim().isNotEmpty) {
      payload['equipment_type'] = equipmentType.trim().toUpperCase();
    }
    if (attributeKeys.contains('commodity_code') &&
        commodityCode.trim().isNotEmpty) {
      payload['commodity_code'] = commodityCode.trim().toUpperCase();
    }
    if (attributeKeys.contains('service_level') &&
        serviceLevel.trim().isNotEmpty) {
      payload['service_level'] = serviceLevel.trim().toUpperCase();
    }
    if (attributeKeys.contains('scale_from') && scaleFrom.trim().isNotEmpty) {
      payload['scale_from'] = scaleFrom.trim();
    }
    if (attributeKeys.contains('scale_to') && scaleTo.trim().isNotEmpty) {
      payload['scale_to'] = scaleTo.trim();
    }
    if (attributeKeys.contains('minimum_amount') &&
        minimumAmount.trim().isNotEmpty) {
      payload['minimum_amount'] = minimumAmount.trim();
    }
    if (attributeKeys.contains('maximum_amount') &&
        maximumAmount.trim().isNotEmpty) {
      payload['maximum_amount'] = maximumAmount.trim();
    }
    if (attributeKeys.contains('validity_from') &&
        validityFrom.trim().isNotEmpty) {
      payload['validity_from'] = validityFrom.trim();
    }
    if (attributeKeys.contains('validity_to') && validityTo.trim().isNotEmpty) {
      payload['validity_to'] = validityTo.trim();
    }
    final calculationProfileIdValue = _asInt(calculationProfileId.trim());
    if (attributeKeys.contains('calculation_profile_id') &&
        calculationProfileIdValue != null) {
      payload['calculation_profile_id'] = calculationProfileIdValue;
    }
    final allocationProfileIdValue = _asInt(allocationProfileId.trim());
    if (attributeKeys.contains('allocation_profile_id') &&
        allocationProfileIdValue != null) {
      payload['allocation_profile_id'] = allocationProfileIdValue;
    }
    final priorityValue = _asInt(priority.trim());
    if (attributeKeys.contains('priority') && priorityValue != null) {
      payload['priority'] = priorityValue;
    }
    final customValues = <String, dynamic>{};
    for (final dimension in customDimensions) {
      final code = dimension.code;
      final raw = dimensionValues[code] ?? '';
      final typed = _typedDimensionValue(raw, dimension);
      if (typed != null) {
        customValues[code] = typed;
      }
    }
    if (customValues.isNotEmpty) {
      payload['dimension_values'] = customValues;
    }
    if (isPercentage) {
      payload.remove('rate_amount');
      payload['rate_percent'] = ratePercent.trim();
    } else {
      payload.remove('rate_percent');
      payload['rate_amount'] = rateAmount.trim();
    }
    return JsonMap.from(payload);
  }
}

class _RateBookDialog extends StatefulWidget {
  const _RateBookDialog({
    required this.mode,
    required this.components,
    required this.pricingDimensions,
    required this.calculationProfiles,
    required this.allocationProfiles,
    this.book,
  });

  final _RateBookDialogMode mode;
  final List<JsonMap> components;
  final List<JsonMap> pricingDimensions;
  final List<JsonMap> calculationProfiles;
  final List<JsonMap> allocationProfiles;
  final JsonMap? book;

  @override
  State<_RateBookDialog> createState() => _RateBookDialogState();
}

class _RateBookDialogState extends State<_RateBookDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _code;
  late final TextEditingController _name;
  late final TextEditingController _description;
  late final TextEditingController _currency;
  late final TextEditingController _validFrom;
  late final TextEditingController _validTo;
  late final TextEditingController _calculationBasis;
  late String _componentCode;
  late Set<String> _attributeKeys;
  late Set<String> _dimensionCodes;
  late bool _isActive;
  late List<_RateEntryDraft> _entries;

  bool get _codeLocked => widget.mode == _RateBookDialogMode.newVersion;

  bool get _componentLocked => widget.book != null;

  bool get _editing => widget.mode == _RateBookDialogMode.editDraft;

  String get _title => switch (widget.mode) {
    _RateBookDialogMode.create => 'Create rate book',
    _RateBookDialogMode.editDraft => 'Edit draft rate book',
    _RateBookDialogMode.newVersion => 'Create draft version',
  };

  String get _saveLabel => switch (widget.mode) {
    _RateBookDialogMode.create => 'Create rate book',
    _RateBookDialogMode.editDraft => 'Save draft',
    _RateBookDialogMode.newVersion => 'Create draft',
  };

  @override
  void initState() {
    super.initState();
    final book = widget.book;
    _code = TextEditingController(
      text: _text(
        book ?? const <String, dynamic>{},
        'rate_book_code',
        fallback: '',
      ),
    );
    _name = TextEditingController(
      text: _text(
        book ?? const <String, dynamic>{},
        'rate_book_name',
        fallback: '',
      ),
    );
    _description = TextEditingController(
      text: _text(
        book ?? const <String, dynamic>{},
        'description',
        fallback: '',
      ),
    );
    _currency = TextEditingController(
      text: _text(
        book ?? const <String, dynamic>{},
        'currency',
        fallback: 'USD',
      ),
    );
    _validFrom = TextEditingController(
      text: _text(
        book ?? const <String, dynamic>{},
        'valid_from',
        fallback: '',
      ),
    );
    _validTo = TextEditingController(
      text: _text(book ?? const <String, dynamic>{}, 'valid_to', fallback: ''),
    );
    _calculationBasis = TextEditingController(
      text: _text(
        book ?? const <String, dynamic>{},
        'calculation_basis',
        fallback: 'FLAT',
      ),
    );
    final existingEntries = _rows(book ?? const <String, dynamic>{}, 'entries');
    _componentCode = _text(
      book ?? const <String, dynamic>{},
      'charge_component_code',
      fallback: existingEntries.isEmpty
          ? ''
          : _text(existingEntries.first, 'charge_component_code', fallback: ''),
    ).toUpperCase();
    _attributeKeys = _rateBookAttributeKeys(book);
    if (book == null && _attributeKeys.isEmpty) {
      _attributeKeys = {
        'origin_code',
        'destination_code',
        'mode',
        'equipment_type',
        'service_level',
        'validity_from',
        'validity_to',
      };
    }
    _dimensionCodes = _rateBookDimensionCodes(book);
    _isActive = book == null || book['is_active'] != false;
    _entries = _rows(
      book ?? const <String, dynamic>{},
      'entries',
    ).map(_RateEntryDraft.fromJson).toList(growable: true);
  }

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    _description.dispose();
    _currency.dispose();
    _validFrom.dispose();
    _validTo.dispose();
    _calculationBasis.dispose();
    super.dispose();
  }

  void _addEntry() => setState(
    () => _entries.add(
      _RateEntryDraft(
        componentCode: _componentCode,
        currency: _currency.text.trim().toUpperCase(),
        dimensionValues: <String, String>{},
      ),
    ),
  );

  void _removeEntry(int index) {
    setState(() {
      _entries.removeAt(index);
    });
  }

  String? _required(String? value, String label) {
    if (value == null || value.trim().isEmpty) return '$label is required';
    return null;
  }

  String? _isoDate(String? value, {bool required = false}) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return required ? 'Date is required' : null;
    return DateTime.tryParse(text) == null ? 'Use YYYY-MM-DD' : null;
  }

  String? _numeric(String? value, {bool required = false}) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) return required ? 'Amount is required' : null;
    return num.tryParse(text) == null ? 'Enter a number' : null;
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final component = _rateComponent(widget.components, _componentCode);
    final calculationBasis = _text(
      component ?? const <String, dynamic>{},
      'calculation_basis',
      fallback: _calculationBasis.text,
    );
    final payload = <String, dynamic>{
      'rate_book_code': _code.text.trim().toUpperCase(),
      'rate_book_name': _name.text.trim(),
      'charge_component_code': _componentCode,
      'row_attribute_keys': _attributeKeys.toList(growable: false)..sort(),
      'dimension_codes': _dimensionCodes.toList(growable: false)..sort(),
      'description': _description.text.trim().isEmpty
          ? null
          : _description.text.trim(),
      'currency': _currency.text.trim().toUpperCase(),
      'valid_from': _validFrom.text.trim().isEmpty
          ? null
          : _validFrom.text.trim(),
      'valid_to': _validTo.text.trim().isEmpty ? null : _validTo.text.trim(),
      'calculation_basis': calculationBasis.trim().toUpperCase(),
      'status': 'DRAFT',
      'is_active': _isActive,
      'entries': _entries
          .map(
            (entry) => entry.toJson(
              widget.components,
              componentCode: _componentCode,
              bookCurrency: _currency.text,
              attributeKeys: _attributeKeys,
              customDimensions: _selectedPricingDimensions(
                _pricingDimensionViews(widget.pricingDimensions),
                _dimensionCodes,
              ),
            ),
          )
          .toList(growable: false),
    };
    final lockVersion = _asInt(widget.book?['lock_version']);
    if (_editing && lockVersion != null) {
      payload['expected_lock_version'] = lockVersion;
    }
    Navigator.pop(context, JsonMap.from(payload));
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_title),
      content: SizedBox(
        width: 1120,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  widget.mode == _RateBookDialogMode.newVersion
                      ? 'The new version keeps the selected rate-book code and starts in DRAFT status.'
                      : 'Capture the commercial header, built-in row columns, and active custom canonical dimensions in this workspace.',
                  style: const TextStyle(
                    fontSize: 12,
                    color: LedgerFlowDesign.muted,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: 18),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    SizedBox(
                      width: 210,
                      child: TextFormField(
                        controller: _code,
                        readOnly: _codeLocked,
                        decoration: const InputDecoration(
                          labelText: 'Rate-book code',
                          isDense: true,
                        ),
                        validator: (value) =>
                            _required(value, 'Rate-book code'),
                      ),
                    ),
                    SizedBox(
                      width: 260,
                      child: TextFormField(
                        controller: _name,
                        decoration: const InputDecoration(
                          labelText: 'Rate-book name',
                          isDense: true,
                        ),
                        validator: (value) =>
                            _required(value, 'Rate-book name'),
                      ),
                    ),
                    SizedBox(
                      width: 360,
                      child: DropdownButtonFormField<String>(
                        key: const ValueKey('rate-book-component'),
                        initialValue: _componentCode.isEmpty
                            ? null
                            : _componentCode,
                        isExpanded: true,
                        decoration: const InputDecoration(
                          labelText: 'Charge component',
                          helperText:
                              'Fixed for this rate-book family and inherited by every row.',
                        ),
                        items:
                            _rateComponentOptions(
                                  widget.components,
                                  _componentCode,
                                )
                                .map(
                                  (component) => DropdownMenuItem(
                                    value: _text(
                                      component,
                                      'component_code',
                                    ).toUpperCase(),
                                    child: Text(_rateComponentLabel(component)),
                                  ),
                                )
                                .toList(growable: false),
                        validator: (value) =>
                            _required(value, 'Charge component'),
                        onChanged: _componentLocked
                            ? null
                            : (value) => setState(() {
                                _componentCode = value ?? '';
                                for (final entry in _entries) {
                                  entry.componentCode = _componentCode;
                                }
                              }),
                      ),
                    ),
                    SizedBox(
                      width: 130,
                      child: DropdownButtonFormField<String>(
                        initialValue: _currency.text.toUpperCase(),
                        isExpanded: true,
                        decoration: const InputDecoration(
                          labelText: 'Currency',
                          helperText: 'Default row currency.',
                        ),
                        items:
                            referenceValuesWithCurrent(
                                  currencyValues,
                                  _currency.text,
                                )
                                .map(
                                  (value) => DropdownMenuItem(
                                    value: value,
                                    child: Text(value),
                                  ),
                                )
                                .toList(growable: false),
                        validator: (value) => _required(value, 'Currency'),
                        onChanged: (value) => setState(() {
                          _currency.text = value ?? 'USD';
                          for (final entry in _entries) {
                            entry.currency = _currency.text;
                          }
                        }),
                      ),
                    ),
                    SizedBox(
                      width: 170,
                      child: _DatePickerField(
                        controller: _validFrom,
                        label: 'Book valid from',
                        help: 'Optional effective start for all rows.',
                        validator: _isoDate,
                      ),
                    ),
                    SizedBox(
                      width: 170,
                      child: _DatePickerField(
                        controller: _validTo,
                        label: 'Book valid to',
                        help: 'Optional effective end for all rows.',
                        validator: _isoDate,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _description,
                  maxLines: 2,
                  decoration: const InputDecoration(
                    labelText: 'Description',
                    isDense: true,
                  ),
                ),
                const SizedBox(height: 12),
                SectionHeading(
                  title: 'Row columns',
                  subtitle:
                      'Choose the applicability and override columns used by every row. Rate value, currency, and active status are always present.',
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _rateAttributeDefinitions
                      .map(
                        (definition) => Tooltip(
                          message: definition.help,
                          child: FilterChip(
                            label: Text(definition.label),
                            selected: _attributeKeys.contains(definition.key),
                            onSelected: (selected) => setState(() {
                              if (selected) {
                                _attributeKeys.add(definition.key);
                              } else {
                                _attributeKeys.remove(definition.key);
                              }
                            }),
                          ),
                        ),
                      )
                      .toList(growable: false),
                ),
                const SizedBox(height: 12),
                SectionHeading(
                  title: 'Custom canonical dimensions',
                  subtitle:
                      'These active custom dimensions are written into dimension_values for each row.',
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _customDimensionOptions(widget.pricingDimensions)
                      .map(
                        (dimension) => Tooltip(
                          message: _pricingDimensionTooltip(dimension),
                          child: FilterChip(
                            label: Text(_pricingDimensionLabel(dimension)),
                            selected: _dimensionCodes.contains(
                              _pricingDimensionCode(dimension),
                            ),
                            onSelected: (selected) => setState(() {
                              final code = _pricingDimensionCode(dimension);
                              if (selected) {
                                _dimensionCodes.add(code);
                              } else {
                                _dimensionCodes.remove(code);
                              }
                            }),
                          ),
                        ),
                      )
                      .toList(growable: false),
                ),
                const SizedBox(height: 12),
                SwitchListTile.adaptive(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  value: _isActive,
                  onChanged: (value) => setState(() => _isActive = value),
                  title: const Text('Record is active'),
                ),
                const SizedBox(height: 8),
                SectionHeading(
                  title: 'Rate rows',
                  subtitle:
                      'Entries are optional for a draft, but publishing requires at least one valid rate row.',
                  action: TextButton.icon(
                    onPressed: _addEntry,
                    icon: const Icon(Icons.add, size: 16),
                    label: const Text('Add row'),
                  ),
                ),
                const SizedBox(height: 12),
                if (_entries.isEmpty)
                  const DecoratedBox(
                    decoration: BoxDecoration(
                      color: Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.all(Radius.circular(12)),
                      border: Border.fromBorderSide(
                        BorderSide(color: LedgerFlowDesign.border),
                      ),
                    ),
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Text(
                        'No draft rate rows yet.',
                        style: TextStyle(color: LedgerFlowDesign.muted),
                      ),
                    ),
                  )
                else
                  Column(
                    children: List.generate(_entries.length, (index) {
                      final entry = _entries[index];
                      return Padding(
                        padding: EdgeInsets.only(
                          bottom: index == _entries.length - 1 ? 0 : 12,
                        ),
                        child: _RateEntryEditor(
                          key: ValueKey('rate-entry-$index'),
                          index: index,
                          entry: entry,
                          components: widget.components,
                          componentCode: _componentCode,
                          bookCurrency: _currency.text,
                          attributeKeys: _attributeKeys,
                          customDimensions: _selectedPricingDimensions(
                            _pricingDimensionViews(widget.pricingDimensions),
                            _dimensionCodes,
                          ),
                          calculationProfiles: widget.calculationProfiles,
                          allocationProfiles: widget.allocationProfiles,
                          onRemove: () => _removeEntry(index),
                          required: _required,
                          isoDate: _isoDate,
                          numeric: _numeric,
                          onChanged: () => setState(() {}),
                        ),
                      );
                    }),
                  ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _submit, child: Text(_saveLabel)),
      ],
    );
  }
}

Future<DateTime?> _pickLedgerFlowDate(BuildContext context, String current) =>
    showDatePicker(
      context: context,
      initialDate: DateTime.tryParse(current) ?? DateTime.now(),
      firstDate: DateTime(1990),
      lastDate: DateTime(2100),
    );

String _formatIsoDate(DateTime value) =>
    '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

class _DatePickerField extends StatelessWidget {
  const _DatePickerField({
    required this.controller,
    required this.label,
    required this.validator,
    this.help,
  });

  final TextEditingController controller;
  final String label;
  final String? help;
  final String? Function(String?) validator;

  @override
  Widget build(BuildContext context) => TextFormField(
    controller: controller,
    readOnly: true,
    decoration: InputDecoration(
      labelText: label,
      helperText: help,
      suffixIcon: const Icon(Icons.calendar_today_outlined, size: 17),
    ),
    validator: validator,
    onTap: () async {
      final selected = await _pickLedgerFlowDate(context, controller.text);
      if (selected != null) controller.text = _formatIsoDate(selected);
    },
  );
}

class _DatePickerValueField extends StatefulWidget {
  const _DatePickerValueField({
    required this.initialValue,
    required this.label,
    required this.validator,
    required this.onChanged,
    this.help,
  });

  final String initialValue;
  final String label;
  final String? help;
  final String? Function(String?) validator;
  final ValueChanged<String> onChanged;

  @override
  State<_DatePickerValueField> createState() => _DatePickerValueFieldState();
}

class _DatePickerValueFieldState extends State<_DatePickerValueField> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialValue);
  }

  @override
  void didUpdateWidget(covariant _DatePickerValueField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialValue != oldWidget.initialValue &&
        widget.initialValue != _controller.text) {
      _controller.text = widget.initialValue;
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => TextFormField(
    controller: _controller,
    readOnly: true,
    decoration: InputDecoration(
      labelText: widget.label,
      helperText: widget.help,
      suffixIcon: const Icon(Icons.calendar_today_outlined, size: 17),
    ),
    validator: widget.validator,
    onTap: () async {
      final selected = await _pickLedgerFlowDate(context, _controller.text);
      if (selected == null) return;
      final value = _formatIsoDate(selected);
      _controller.text = value;
      widget.onChanged(value);
    },
  );
}

class _RateEntryEditor extends StatelessWidget {
  const _RateEntryEditor({
    required super.key,
    required this.index,
    required this.entry,
    required this.components,
    required this.componentCode,
    required this.bookCurrency,
    required this.attributeKeys,
    required this.customDimensions,
    required this.calculationProfiles,
    required this.allocationProfiles,
    required this.onRemove,
    required this.required,
    required this.isoDate,
    required this.numeric,
    required this.onChanged,
  });

  final int index;
  final _RateEntryDraft entry;
  final List<JsonMap> components;
  final String componentCode;
  final String bookCurrency;
  final Set<String> attributeKeys;
  final List<_PricingDimensionView> customDimensions;
  final List<JsonMap> calculationProfiles;
  final List<JsonMap> allocationProfiles;
  final VoidCallback onRemove;
  final String? Function(String? value, String label) required;
  final String? Function(String? value, {bool required}) isoDate;
  final String? Function(String? value, {bool required}) numeric;
  final VoidCallback onChanged;

  @override
  Widget build(BuildContext context) {
    final component = _rateComponent(components, componentCode);
    final inheritedBasis = _text(
      component ?? const <String, dynamic>{},
      'calculation_basis',
      fallback: 'FLAT',
    ).toUpperCase();
    final inheritedContext = _text(
      component ?? const <String, dynamic>{},
      'charge_context',
      fallback: 'TRANSPORT',
    ).toUpperCase();
    final effectiveBasis = entry.basis.trim().isEmpty
        ? inheritedBasis
        : entry.basis.trim().toUpperCase();
    final isPercentage = effectiveBasis.startsWith('PERCENT');
    bool selected(String key) => attributeKeys.contains(key);

    Widget textField({
      required String label,
      required String initialValue,
      required ValueChanged<String> onValue,
      double width = 170,
      String? help,
      String? Function(String?)? validator,
      TextInputType? keyboardType,
    }) => SizedBox(
      width: width,
      child: TextFormField(
        initialValue: initialValue,
        keyboardType: keyboardType,
        decoration: InputDecoration(labelText: label, helperText: help),
        validator: validator,
        onChanged: onValue,
      ),
    );

    Widget valueDropdown({
      required String label,
      required String value,
      required List<String> values,
      required ValueChanged<String> onValue,
      double width = 180,
      String? help,
      bool allowBlank = true,
    }) {
      final options = [...referenceValuesWithCurrent(values, value)];
      if (allowBlank && !options.contains('')) options.insert(0, '');
      return SizedBox(
        width: width,
        child: DropdownButtonFormField<String>(
          initialValue: value,
          isExpanded: true,
          decoration: InputDecoration(labelText: label, helperText: help),
          items: options
              .map(
                (option) => DropdownMenuItem(
                  value: option,
                  child: Text(
                    option.isEmpty ? 'Any / not restricted' : option,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              )
              .toList(growable: false),
          onChanged: (next) {
            if (next != null) onValue(next);
          },
        ),
      );
    }

    Widget profileDropdown({
      required String label,
      required String value,
      required List<JsonMap> profiles,
      required ValueChanged<String> onValue,
    }) {
      final ids = profiles
          .map((profile) => '${profile['id']}')
          .where((id) => id != 'null')
          .toSet();
      if (value.isNotEmpty) ids.add(value);
      return SizedBox(
        width: 280,
        child: DropdownButtonFormField<String>(
          initialValue: value,
          isExpanded: true,
          decoration: InputDecoration(
            labelText: label,
            helperText: 'Blank uses the charge component default.',
          ),
          items: [
            const DropdownMenuItem(value: '', child: Text('Inherit default')),
            ...ids.map((id) {
              final profile = profiles.cast<JsonMap?>().firstWhere(
                (item) => '${item?['id']}' == id,
                orElse: () => null,
              );
              final code = _text(
                profile ?? const <String, dynamic>{},
                'profile_code',
                fallback: 'Profile #$id',
              );
              final name = _text(
                profile ?? const <String, dynamic>{},
                'profile_name',
                fallback: '',
              );
              return DropdownMenuItem(
                value: id,
                child: Text(
                  name.isEmpty ? code : '$code - $name',
                  overflow: TextOverflow.ellipsis,
                ),
              );
            }),
          ],
          onChanged: (next) => onValue(next ?? ''),
        ),
      );
    }

    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: LedgerFlowDesign.border),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  'Row ${index + 1}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(width: 8),
                StatusPill(entry.isActive ? 'ACTIVE' : 'INACTIVE'),
                const Spacer(),
                TextButton.icon(
                  onPressed: onRemove,
                  icon: const Icon(Icons.delete_outline, size: 16),
                  label: const Text('Remove'),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${componentCode.isEmpty ? 'Select a component above' : componentCode} defaults: $inheritedBasis basis, $inheritedContext context',
              style: const TextStyle(
                color: LedgerFlowDesign.muted,
                fontSize: 11,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                if (selected('basis_override'))
                  SizedBox(
                    width: 250,
                    child: DropdownButtonFormField<String>(
                      key: ValueKey('rate-basis-$index-$inheritedBasis'),
                      initialValue: entry.basis,
                      isExpanded: true,
                      isDense: true,
                      decoration: const InputDecoration(
                        labelText: 'Calculation basis',
                        helperText: 'Blank inherits the component default.',
                      ),
                      items: [
                        DropdownMenuItem(
                          value: '',
                          child: Text('Inherit ($inheritedBasis)'),
                        ),
                        ...referenceValuesWithCurrent(
                          chargeCalculationBasisValues,
                          entry.basis,
                        ).map(
                          (value) => DropdownMenuItem(
                            value: value,
                            child: Text(value),
                          ),
                        ),
                      ],
                      onChanged: (value) {
                        if (value == null) return;
                        entry.basis = value;
                        onChanged();
                      },
                    ),
                  ),
                if (selected('charge_context_override'))
                  SizedBox(
                    width: 230,
                    child: DropdownButtonFormField<String>(
                      key: ValueKey('rate-context-$index-$inheritedContext'),
                      initialValue: entry.chargeContext,
                      isExpanded: true,
                      isDense: true,
                      decoration: const InputDecoration(
                        labelText: 'Charge context',
                        helperText: 'Blank inherits the component context.',
                      ),
                      items: [
                        DropdownMenuItem(
                          value: '',
                          child: Text('Inherit ($inheritedContext)'),
                        ),
                        ...referenceValuesWithCurrent(
                          chargeContextValues,
                          entry.chargeContext,
                        ).map(
                          (value) => DropdownMenuItem(
                            value: value,
                            child: Text(value),
                          ),
                        ),
                      ],
                      onChanged: (value) {
                        if (value == null) return;
                        entry.chargeContext = value;
                        onChanged();
                      },
                    ),
                  ),
                valueDropdown(
                  label: 'Currency',
                  value: entry.currency.isEmpty ? bookCurrency : entry.currency,
                  values: currencyValues,
                  width: 125,
                  help: 'Defaults from the rate-book header.',
                  allowBlank: false,
                  onValue: (value) => entry.currency = value,
                ),
                textField(
                  label: isPercentage ? 'Rate percent' : 'Rate amount',
                  initialValue: isPercentage
                      ? entry.ratePercent
                      : entry.rateAmount,
                  width: 155,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  validator: (value) => numeric(value, required: true),
                  onValue: (value) {
                    if (isPercentage) {
                      entry.ratePercent = value;
                    } else {
                      entry.rateAmount = value;
                    }
                  },
                ),
                if (selected('origin_code'))
                  textField(
                    label: 'Origin',
                    initialValue: entry.originCode,
                    help: 'Location code from the caller or location master.',
                    onValue: (value) => entry.originCode = value,
                  ),
                if (selected('destination_code'))
                  textField(
                    label: 'Destination',
                    initialValue: entry.destinationCode,
                    help: 'Location code from the caller or location master.',
                    onValue: (value) => entry.destinationCode = value,
                  ),
                if (selected('mode'))
                  valueDropdown(
                    label: 'Transport mode',
                    value: entry.mode,
                    values: transportModeValues,
                    help: 'Must match the quote or contract mode.',
                    onValue: (value) => entry.mode = value,
                  ),
                if (selected('equipment_type'))
                  valueDropdown(
                    label: 'Equipment',
                    value: entry.equipmentType,
                    values: equipmentTypeValues,
                    help: 'Must match the request equipment type.',
                    onValue: (value) => entry.equipmentType = value,
                  ),
                if (selected('commodity_code'))
                  textField(
                    label: 'Commodity',
                    initialValue: entry.commodityCode,
                    help: 'Caller-supplied commodity or goods code.',
                    onValue: (value) => entry.commodityCode = value,
                  ),
                if (selected('service_level'))
                  valueDropdown(
                    label: 'Service level',
                    value: entry.serviceLevel,
                    values: serviceLevelValues,
                    help: 'Must match the request service level.',
                    onValue: (value) => entry.serviceLevel = value,
                  ),
                if (selected('scale_from'))
                  textField(
                    label: 'Scale from',
                    initialValue: entry.scaleFrom,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    validator: numeric,
                    onValue: (value) => entry.scaleFrom = value,
                  ),
                if (selected('scale_to'))
                  textField(
                    label: 'Scale to',
                    initialValue: entry.scaleTo,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    validator: numeric,
                    onValue: (value) => entry.scaleTo = value,
                  ),
                if (selected('minimum_amount'))
                  textField(
                    label: 'Minimum charge',
                    initialValue: entry.minimumAmount,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    validator: numeric,
                    onValue: (value) => entry.minimumAmount = value,
                  ),
                if (selected('maximum_amount'))
                  textField(
                    label: 'Maximum charge',
                    initialValue: entry.maximumAmount,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    validator: numeric,
                    onValue: (value) => entry.maximumAmount = value,
                  ),
                if (selected('validity_from'))
                  SizedBox(
                    width: 180,
                    child: _DatePickerValueField(
                      initialValue: entry.validityFrom,
                      label: 'Valid from',
                      help: 'Optional row-level effective start.',
                      validator: isoDate,
                      onChanged: (value) => entry.validityFrom = value,
                    ),
                  ),
                if (selected('validity_to'))
                  SizedBox(
                    width: 180,
                    child: _DatePickerValueField(
                      initialValue: entry.validityTo,
                      label: 'Valid to',
                      help: 'Optional row-level effective end.',
                      validator: isoDate,
                      onChanged: (value) => entry.validityTo = value,
                    ),
                  ),
                if (selected('calculation_profile_id'))
                  profileDropdown(
                    label: 'Calculation profile',
                    value: entry.calculationProfileId,
                    profiles: calculationProfiles,
                    onValue: (value) => entry.calculationProfileId = value,
                  ),
                if (selected('allocation_profile_id'))
                  profileDropdown(
                    label: 'Allocation profile',
                    value: entry.allocationProfileId,
                    profiles: allocationProfiles,
                    onValue: (value) => entry.allocationProfileId = value,
                  ),
                if (selected('priority'))
                  textField(
                    label: 'Priority',
                    initialValue: entry.priority,
                    help: 'Lower wins after specificity.',
                    width: 130,
                    keyboardType: TextInputType.number,
                    validator: (value) => _asInt(value?.trim()) == null
                        ? 'Enter an integer'
                        : null,
                    onValue: (value) => entry.priority = value,
                  ),
                ...customDimensions.map(
                  (dimension) => _customDimensionField(
                    dimension: dimension,
                    entry: entry,
                    width: _customDimensionWidth(dimension),
                    onChanged: onChanged,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            SwitchListTile.adaptive(
              dense: true,
              contentPadding: EdgeInsets.zero,
              value: entry.isActive,
              onChanged: (value) {
                entry.isActive = value;
                onChanged();
              },
              title: const Text('Row is active'),
            ),
          ],
        ),
      ),
    );
  }
}

List<JsonMap> _rateComponentOptions(
  List<JsonMap> components,
  String selectedCode,
) {
  final selected = selectedCode.trim().toUpperCase();
  final byCode = <String, JsonMap>{};
  for (final component in components) {
    final code = _text(component, 'component_code').trim().toUpperCase();
    if (code.isEmpty) continue;
    if (component['is_active'] != false || code == selected) {
      byCode[code] = component;
    }
  }
  if (selected.isNotEmpty && !byCode.containsKey(selected)) {
    byCode[selected] = <String, dynamic>{
      'component_code': selected,
      'component_name': 'Unavailable component',
      'is_active': false,
    };
  }
  final options = byCode.values.toList(growable: false);
  options.sort(
    (left, right) => _rateComponentLabel(
      left,
    ).toLowerCase().compareTo(_rateComponentLabel(right).toLowerCase()),
  );
  return options;
}

JsonMap? _rateComponent(List<JsonMap> components, String componentCode) {
  final selected = componentCode.trim().toUpperCase();
  if (selected.isEmpty) return null;
  return components.cast<JsonMap?>().firstWhere(
    (component) =>
        _text(
          component ?? const <String, dynamic>{},
          'component_code',
        ).toUpperCase() ==
        selected,
    orElse: () => null,
  );
}

String _rateComponentLabel(JsonMap component) {
  final code = _text(component, 'component_code');
  final name = _text(component, 'component_name', fallback: code);
  final inactive = component['is_active'] == false ? ' - inactive' : '';
  return '$name ($code)$inactive';
}

class _ProfileTable extends StatelessWidget {
  const _ProfileTable({
    required this.kind,
    required this.records,
    required this.description,
  });

  final String kind;
  final List<JsonMap> records;
  final String description;

  @override
  Widget build(BuildContext context) => SurfaceCard(
    padding: EdgeInsets.zero,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(18),
          child: SectionHeading(
            title: '${kind[0].toUpperCase()}${kind.substring(1)} profiles',
            subtitle: description,
          ),
        ),
        if (records.isEmpty)
          const EmptyState(message: 'No profiles are available.')
        else
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: const [
                DataColumn(label: Text('Code')),
                DataColumn(label: Text('Name')),
                DataColumn(label: Text('Published version')),
                DataColumn(label: Text('Description / driver')),
                DataColumn(label: Text('Status')),
              ],
              rows: records.map((record) {
                final version = _rows(record, 'versions').firstOrNull;
                final detail = _text(
                  record,
                  'description',
                  fallback: version == null
                      ? 'Versioned profile'
                      : '${_text(version, 'source_level')} -> ${_text(version, 'final_posting_level')} by ${_text(version, 'source_to_house_driver')}',
                );
                return DataRow(
                  cells: [
                    DataCell(
                      Text(
                        _text(record, 'profile_code'),
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          color: LedgerFlowDesign.info,
                        ),
                      ),
                    ),
                    DataCell(Text(_text(record, 'profile_name'))),
                    DataCell(
                      Text(
                        'v${_text(record, 'published_version_number', fallback: '-')}',
                      ),
                    ),
                    DataCell(
                      SizedBox(
                        width: 330,
                        child: Text(
                          detail,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ),
                    DataCell(
                      StatusPill(
                        record['published_version_number'] == null
                            ? 'DRAFT'
                            : 'PUBLISHED',
                      ),
                    ),
                  ],
                );
              }).toList(),
            ),
          ),
      ],
    ),
  );
}

class _FxTable extends StatelessWidget {
  const _FxTable({required this.records});

  final List<JsonMap> records;

  @override
  Widget build(BuildContext context) => SurfaceCard(
    padding: EdgeInsets.zero,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Padding(
          padding: EdgeInsets.all(18),
          child: SectionHeading(
            title: 'FX rates',
            subtitle:
                'Date-effective direct or inverse conversions with source provenance',
          ),
        ),
        if (records.isEmpty)
          const EmptyState(message: 'No FX rates are available.')
        else
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: const [
                DataColumn(label: Text('Source')),
                DataColumn(label: Text('Pair')),
                DataColumn(label: Text('Rate date')),
                DataColumn(label: Text('Rate')),
                DataColumn(label: Text('Type')),
                DataColumn(label: Text('Method')),
                DataColumn(label: Text('Status')),
              ],
              rows: records
                  .map(
                    (record) => DataRow(
                      cells: [
                        DataCell(
                          Text(
                            _text(record, 'source_code'),
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                        ),
                        DataCell(
                          Text(
                            '${_text(record, 'source_currency')} / ${_text(record, 'target_currency')}',
                          ),
                        ),
                        DataCell(Text(_text(record, 'rate_date'))),
                        DataCell(Text(_text(record, 'rate'))),
                        DataCell(Text(_text(record, 'rate_type'))),
                        DataCell(Text(_text(record, 'conversion_method'))),
                        DataCell(
                          StatusPill(
                            record['is_active'] == false
                                ? 'INACTIVE'
                                : 'ACTIVE',
                          ),
                        ),
                      ],
                    ),
                  )
                  .toList(),
            ),
          ),
      ],
    ),
  );
}

class _TrendPainter extends CustomPainter {
  static const _volume = [2.1, 2.5, 2.2, 3.2, 2.85, 3.4];
  static const _margin = [15.0, 18.0, 16.0, 18.5, 16.0, 18.6];
  static const _labels = [
    "Dec '25",
    "Jan '26",
    "Feb '26",
    "Mar '26",
    "Apr '26",
    "May '26",
  ];

  @override
  void paint(Canvas canvas, Size size) {
    const padding = EdgeInsets.fromLTRB(36, 12, 14, 28);
    final area = Rect.fromLTWH(
      padding.left,
      padding.top,
      size.width - padding.horizontal,
      size.height - padding.vertical,
    );
    final grid = Paint()
      ..color = LedgerFlowDesign.border.withValues(alpha: 0.75)
      ..strokeWidth = 1;
    for (var i = 0; i <= 4; i++) {
      final y = area.bottom - area.height * i / 4;
      canvas.drawLine(Offset(area.left, y), Offset(area.right, y), grid);
    }
    Offset volumePoint(int index) => Offset(
      area.left + area.width * index / (_volume.length - 1),
      area.bottom - area.height * _volume[index] / 4,
    );
    Offset marginPoint(int index) => Offset(
      area.left + area.width * index / (_margin.length - 1),
      area.bottom - area.height * _margin[index] / 30,
    );
    final volumePath = Path()..moveTo(volumePoint(0).dx, volumePoint(0).dy);
    final marginPath = Path()..moveTo(marginPoint(0).dx, marginPoint(0).dy);
    for (var i = 1; i < _volume.length; i++) {
      volumePath.lineTo(volumePoint(i).dx, volumePoint(i).dy);
      marginPath.lineTo(marginPoint(i).dx, marginPoint(i).dy);
    }
    final fillPath = Path.from(volumePath)
      ..lineTo(area.right, area.bottom)
      ..lineTo(area.left, area.bottom)
      ..close();
    canvas.drawPath(
      fillPath,
      Paint()
        ..shader = const LinearGradient(
          colors: [Color(0x3345B8B3), Color(0x0045B8B3)],
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        ).createShader(area),
    );
    canvas.drawPath(
      volumePath,
      Paint()
        ..color = LedgerFlowDesign.teal
        ..strokeWidth = 2.4
        ..style = PaintingStyle.stroke,
    );
    canvas.drawPath(
      marginPath,
      Paint()
        ..color = const Color(0xFF2E90FA)
        ..strokeWidth = 2
        ..style = PaintingStyle.stroke,
    );
    for (var i = 0; i < _labels.length; i++) {
      canvas.drawCircle(
        volumePoint(i),
        4.2,
        Paint()..color = LedgerFlowDesign.teal,
      );
      canvas.drawCircle(
        marginPoint(i),
        3.7,
        Paint()..color = const Color(0xFF2E90FA),
      );
      final painter = TextPainter(
        text: TextSpan(
          text: _labels[i],
          style: const TextStyle(fontSize: 10, color: LedgerFlowDesign.muted),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      painter.paint(
        canvas,
        Offset(volumePoint(i).dx - painter.width / 2, area.bottom + 10),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _TrendPainter oldDelegate) => false;
}

void _showApiGuidance(BuildContext context, String module) {
  showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text('$module API'),
      content: const Text(
        'Connect the UI with a bearer token to read live records. Create, update, publish, and lifecycle endpoints are documented in the repository API examples and interactive Swagger documentation.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Close'),
        ),
      ],
    ),
  );
}

bool _terminal(String status) {
  final normalized = status.toUpperCase();
  return normalized == 'AWARDED' ||
      normalized == 'WITHDRAWN' ||
      normalized == 'EXPIRED';
}

List<JsonMap> _rows(JsonMap record, String key) {
  final value = record[key];
  if (value is! List) return const [];
  return value
      .whereType<Map<String, dynamic>>()
      .map(JsonMap.from)
      .toList(growable: false);
}

Map<String, String> _stringMap(dynamic value) {
  if (value is! Map) return const {};
  return {
    for (final entry in value.entries)
      entry.key.toString().trim().toUpperCase(): entry.value?.toString() ?? '',
  };
}

List<String> _stringList(dynamic value) {
  if (value is! List) return const [];
  return value
      .map((item) => item.toString().trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

String _text(JsonMap record, String key, {String fallback = '-'}) {
  final value = record[key];
  if (value == null || value.toString().trim().isEmpty) return fallback;
  return value.toString();
}

double _number(dynamic value) => double.tryParse(value?.toString() ?? '') ?? 0;

int? _asInt(dynamic value) => switch (value) {
  int number => number,
  String text => int.tryParse(text),
  _ => null,
};

List<JsonMap> _sortRateBooks(List<JsonMap> books) {
  final sorted = List<JsonMap>.from(books);
  sorted.sort((left, right) {
    final versionOrder = (_asInt(right['version_number']) ?? 1).compareTo(
      _asInt(left['version_number']) ?? 1,
    );
    if (versionOrder != 0) return versionOrder;
    return (_asInt(right['id']) ?? 0).compareTo(_asInt(left['id']) ?? 0);
  });
  return List.unmodifiable(sorted);
}

String _money(double value, {String currency = 'USD'}) {
  final sign = value < 0 ? '-' : '';
  final absolute = value.abs();
  final parts = absolute.toStringAsFixed(2).split('.');
  final whole = parts.first;
  final grouped = StringBuffer();
  for (var index = 0; index < whole.length; index++) {
    if (index > 0 && (whole.length - index) % 3 == 0) grouped.write(',');
    grouped.write(whole[index]);
  }
  return '$sign$currency $grouped.${parts.last}';
}

String _label(String key) => key
    .split('_')
    .map(
      (word) =>
          word.isEmpty ? word : '${word[0].toUpperCase()}${word.substring(1)}',
    )
    .join(' ');

String? _localProcessingBlocker(List<JsonMap> lines) {
  for (final line in lines) {
    final lineReference = _text(
      line,
      'line_number',
      fallback: _text(line, 'id'),
    );
    for (final field in const ['calculation_status', 'allocation_status']) {
      final stateValue = _text(line, field).toUpperCase();
      final label = field.startsWith('calculation')
          ? 'calculation'
          : 'allocation';
      if ({'PENDING', 'PENDING_CONTEXT'}.contains(stateValue)) {
        return 'Line $lineReference still has pending $label.';
      }
      if (stateValue == 'FAILED') {
        return 'Line $lineReference has failed $label.';
      }
    }
    for (final entry in const {
      'calculation_audit_json': 'calculation',
      'effective_allocation_snapshot_json': 'allocation',
      'pinned_allocation_snapshot_json': 'allocation',
    }.entries) {
      final snapshot = line[entry.key];
      if (snapshot is! Map) continue;
      final stateValue = _snapshotProcessingState(snapshot);
      if (stateValue == null) continue;
      if ({'PENDING', 'PENDING_CONTEXT'}.contains(stateValue)) {
        return 'Line $lineReference still has pending ${entry.value}.';
      }
      return 'Line $lineReference has failed ${entry.value}.';
    }
  }
  return null;
}

String? _snapshotProcessingState(Map<dynamic, dynamic> snapshot) {
  for (final key in const [
    'status',
    'state',
    'calculation_status',
    'allocation_status',
  ]) {
    final stateValue = snapshot[key]?.toString().trim().toUpperCase();
    if ({'PENDING', 'PENDING_CONTEXT', 'FAILED'}.contains(stateValue)) {
      return stateValue;
    }
  }
  return null;
}

Future<bool> _confirmAction(
  BuildContext context, {
  required String title,
  required String message,
  required String action,
  bool destructive = false,
}) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          style: destructive
              ? FilledButton.styleFrom(backgroundColor: LedgerFlowDesign.danger)
              : null,
          onPressed: () => Navigator.pop(context, true),
          child: Text(action),
        ),
      ],
    ),
  );
  return confirmed ?? false;
}
