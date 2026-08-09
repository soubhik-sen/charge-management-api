import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/design.dart';
import '../data/workspace_data.dart';

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
        Wrap(
          spacing: 14,
          runSpacing: 14,
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
                    onPressed: () => onOpen(2),
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
                    onPressed: () => onOpen(2),
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
  const ChargeDocumentWorkspace({required this.documents, super.key});

  final List<JsonMap> documents;

  @override
  State<ChargeDocumentWorkspace> createState() =>
      _ChargeDocumentWorkspaceState();
}

class _ChargeDocumentWorkspaceState extends State<ChargeDocumentWorkspace> {
  int _selected = 0;
  int _selectedLine = 0;

  @override
  Widget build(BuildContext context) {
    if (widget.documents.isEmpty) {
      return const PageCanvas(
        title: 'Charge documents',
        subtitle:
            'Inspect calculated charges, provenance, approvals, and export readiness.',
        children: [EmptyState(message: 'No charge documents are available.')],
      );
    }
    final index = math.min(_selected, widget.documents.length - 1);
    final document = widget.documents[index];
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
    return PageCanvas(
      title: _text(
        document,
        'document_number',
        fallback: 'Charge document #${document['id']}',
      ),
      eyebrow: 'Charge documents',
      subtitle:
          '${_text(document, 'source_object_type')} ${_text(document, 'source_object_id')}  |  Document date ${_text(document, 'document_date')}',
      trailing: StatusPill(_text(document, 'status')),
      children: [
        _RecordPicker(
          records: widget.documents,
          selectedIndex: index,
          label: (item) =>
              _text(item, 'document_number', fallback: '#${item['id']}'),
          detail: (item) =>
              '${_text(item, 'source_object_type')} ${_text(item, 'source_object_id')}',
          onSelected: (value) => setState(() {
            _selected = value;
            _selectedLine = 0;
          }),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 14,
          runSpacing: 14,
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
                _ProvenancePanel(line: selectedLine),
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
                      label: 'Quote request',
                      value: _text(
                        document,
                        'quote_request_id',
                        fallback: 'Not linked',
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
                    const SectionHeading(title: 'Approval checks'),
                    const SizedBox(height: 12),
                    _CheckRow(
                      label: 'All lines calculated',
                      pass: lines.isNotEmpty,
                    ),
                    _CheckRow(
                      label: 'FX rates resolved',
                      pass: lines.every(
                        (line) => _text(line, 'exchange_rate').isNotEmpty,
                      ),
                    ),
                    const _CheckRow(
                      label: 'Required references present',
                      pass: true,
                    ),
                    _CheckRow(
                      label: 'Document is not reversed',
                      pass: _text(document, 'status') != 'REVERSED',
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

class InvoiceWorkspace extends StatefulWidget {
  const InvoiceWorkspace({required this.invoices, super.key});

  final List<JsonMap> invoices;

  @override
  State<InvoiceWorkspace> createState() => _InvoiceWorkspaceState();
}

class _InvoiceWorkspaceState extends State<InvoiceWorkspace> {
  int _selected = 0;

  @override
  Widget build(BuildContext context) {
    if (widget.invoices.isEmpty) {
      return const PageCanvas(
        title: 'Invoice reconciliation',
        subtitle:
            'Match invoices to expected charge lines and resolve variances.',
        children: [EmptyState(message: 'No invoices are available.')],
      );
    }
    final index = math.min(_selected, widget.invoices.length - 1);
    final invoice = widget.invoices[index];
    final lines = _rows(invoice, 'lines');
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
    return PageCanvas(
      title: _text(
        invoice,
        'invoice_number',
        fallback: 'Invoice #${invoice['id']}',
      ),
      eyebrow: 'Invoices',
      subtitle:
          '${_text(invoice, 'invoice_type')}  |  ${_text(invoice, 'invoice_date')}  |  $currency',
      trailing: StatusPill(_text(invoice, 'status')),
      children: [
        _RecordPicker(
          records: widget.invoices,
          selectedIndex: index,
          label: (item) =>
              _text(item, 'invoice_number', fallback: '#${item['id']}'),
          detail: (item) =>
              _text(item, 'charge_document_number', fallback: 'Unlinked'),
          onSelected: (value) => setState(() => _selected = value),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 14,
          runSpacing: 14,
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
                    _InvoiceLineTable(lines: lines),
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

class RateBookWorkspace extends StatefulWidget {
  const RateBookWorkspace({required this.rateBooks, super.key});

  final List<JsonMap> rateBooks;

  @override
  State<RateBookWorkspace> createState() => _RateBookWorkspaceState();
}

class _RateBookWorkspaceState extends State<RateBookWorkspace> {
  int _selectedBook = 0;
  int _selectedRate = 0;

  @override
  Widget build(BuildContext context) {
    if (widget.rateBooks.isEmpty) {
      return const PageCanvas(
        title: 'Rate books',
        subtitle:
            'Maintain versioned, date-effective rate tables and applicability.',
        children: [EmptyState(message: 'No rate books are available.')],
      );
    }
    final bookIndex = math.min(_selectedBook, widget.rateBooks.length - 1);
    final book = widget.rateBooks[bookIndex];
    final entries = _rows(book, 'entries');
    final rateIndex = entries.isEmpty
        ? 0
        : math.min(_selectedRate, entries.length - 1);
    final selectedRate = entries.isEmpty ? null : entries[rateIndex];
    return PageCanvas(
      title: _text(
        book,
        'rate_book_name',
        fallback: 'Rate book #${book['id']}',
      ),
      eyebrow: 'Rate books / ${_text(book, 'rate_book_code')}',
      subtitle:
          '${_text(book, 'currency')}  |  Valid ${_text(book, 'valid_from')} to ${_text(book, 'valid_to')}',
      trailing: StatusPill(_text(book, 'status')),
      children: [
        _RecordPicker(
          records: widget.rateBooks,
          selectedIndex: bookIndex,
          label: (item) => _text(item, 'rate_book_name'),
          detail: (item) => _text(item, 'rate_book_code'),
          onSelected: (value) => setState(() {
            _selectedBook = value;
            _selectedRate = 0;
          }),
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 14,
          runSpacing: 14,
          children: [
            MetricCard(
              label: 'Entries',
              value: '${entries.length}',
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
              label: 'Valid from',
              value: _text(book, 'valid_from'),
              icon: Icons.calendar_today_outlined,
              color: LedgerFlowDesign.success,
            ),
            MetricCard(
              label: 'Valid to',
              value: _text(book, 'valid_to'),
              icon: Icons.event_busy_outlined,
              color: LedgerFlowDesign.warning,
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
                                '${_text(selectedRate, 'currency')} ${_text(selectedRate, 'rate_amount')}',
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
                        ],
                      ),
              ),
              const SizedBox(height: 16),
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeading(title: 'Version history'),
                    const SizedBox(height: 14),
                    const _VersionRow(
                      version: 'v4',
                      status: 'PUBLISHED',
                      date: 'Current',
                    ),
                    const _VersionRow(
                      version: 'v3',
                      status: 'ARCHIVED',
                      date: 'Previous',
                    ),
                    const _VersionRow(
                      version: 'v2',
                      status: 'ARCHIVED',
                      date: 'Initial',
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
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(24, 26, 24, 40),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1380),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (eyebrow != null) ...[
                Text(
                  eyebrow!,
                  style: const TextStyle(
                    color: LedgerFlowDesign.teal,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 8),
              ],
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(
                            fontSize: 30,
                            height: 1.1,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 7),
                        Text(
                          subtitle,
                          style: const TextStyle(
                            color: LedgerFlowDesign.muted,
                            height: 1.45,
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (trailing != null) ...[
                    const SizedBox(width: 16),
                    trailing!,
                  ],
                ],
              ),
              const SizedBox(height: 24),
              ...children,
            ],
          ),
        ),
      ),
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
    return SizedBox(
      width: 258,
      child: SurfaceCard(
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.11),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      fontSize: 13,
                      color: LedgerFlowDesign.muted,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    value,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (detail != null)
                    Text(
                      detail!,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 11,
                        color: LedgerFlowDesign.muted,
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
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
                    fontSize: 12,
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
        if (constraints.maxWidth < 920) {
          return Column(children: [left, const SizedBox(height: 16), right]);
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: leftFlex, child: left),
            const SizedBox(width: 16),
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
              DataCell(StatusPill(_text(line, 'status'))),
            ],
          );
        }),
      ),
    );
  }
}

class _ProvenancePanel extends StatelessWidget {
  const _ProvenancePanel({required this.line});

  final JsonMap line;

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
                'Basis': _text(line, 'basis'),
                'Rate result':
                    '${_text(line, 'source_currency')} ${_text(line, 'source_amount')}',
              },
            ),
            _ProvenanceBlock(
              title: 'Allocation',
              icon: Icons.call_split_outlined,
              rows: {
                'Mode': _text(line, 'allocation_mode'),
                'Target': _text(line, 'target_level'),
                'Profile': _text(
                  line,
                  'allocation_profile_version_id',
                  fallback: 'Inherited',
                ),
              },
            ),
            _ProvenanceBlock(
              title: 'Date & FX',
              icon: Icons.currency_exchange_outlined,
              rows: {
                'Date basis': _text(line, 'charge_date_basis'),
                'FX source': _text(line, 'exchange_rate_source_code'),
                'Rate': _text(line, 'exchange_rate'),
              },
            ),
          ];
          if (constraints.maxWidth < 700) {
            return Column(
              children: [
                for (final card in cards) ...[card, const SizedBox(height: 14)],
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var index = 0; index < cards.length; index++) ...[
                Expanded(child: cards[index]),
                if (index < cards.length - 1) const VerticalDivider(width: 28),
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
  const _CheckRow({required this.label, required this.pass});

  final String label;
  final bool pass;

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
        Expanded(child: Text(label, style: const TextStyle(fontSize: 12))),
      ],
    ),
  );
}

class _InvoiceLineTable extends StatelessWidget {
  const _InvoiceLineTable({required this.lines});

  final List<JsonMap> lines;

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
              DataCell(Text('#${_text(line, 'matched_charge_line_id')}')),
              DataCell(Text(_money(_number(line['expected_amount'])))),
              DataCell(Text(_money(_number(line['invoiced_amount'])))),
              DataCell(
                Text(
                  _money(variance),
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
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<JsonMap> entries;
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
        columns: const [
          DataColumn(label: Text('Component')),
          DataColumn(label: Text('Origin')),
          DataColumn(label: Text('Destination')),
          DataColumn(label: Text('Equipment')),
          DataColumn(label: Text('Basis')),
          DataColumn(label: Text('Rate')),
          DataColumn(label: Text('Valid from')),
          DataColumn(label: Text('Valid to')),
        ],
        rows: List.generate(entries.length, (index) {
          final entry = entries[index];
          return DataRow(
            selected: index == selectedIndex,
            onSelectChanged: (_) => onSelected(index),
            cells: [
              DataCell(
                Text(
                  _text(entry, 'charge_component_code'),
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
              ),
              DataCell(Text(_text(entry, 'origin_code'))),
              DataCell(Text(_text(entry, 'destination_code'))),
              DataCell(Text(_text(entry, 'equipment_type'))),
              DataCell(Text(_text(entry, 'basis'))),
              DataCell(
                Text(
                  '${_text(entry, 'currency')} ${_text(entry, 'rate_amount')}',
                ),
              ),
              DataCell(Text(_text(entry, 'validity_from'))),
              DataCell(Text(_text(entry, 'validity_to'))),
            ],
          );
        }),
      ),
    );
  }
}

class _VersionRow extends StatelessWidget {
  const _VersionRow({
    required this.version,
    required this.status,
    required this.date,
  });

  final String version;
  final String status;
  final String date;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 7),
    child: Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: const BoxDecoration(
            color: LedgerFlowDesign.teal,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 10),
        SizedBox(
          width: 28,
          child: Text(
            version,
            style: const TextStyle(
              fontWeight: FontWeight.w700,
              color: LedgerFlowDesign.tealDark,
            ),
          ),
        ),
        StatusPill(status),
        const Spacer(),
        Text(
          date,
          style: const TextStyle(fontSize: 11, color: LedgerFlowDesign.muted),
        ),
      ],
    ),
  );
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

String _text(JsonMap record, String key, {String fallback = '-'}) {
  final value = record[key];
  if (value == null || value.toString().trim().isEmpty) return fallback;
  return value.toString();
}

double _number(dynamic value) => double.tryParse(value?.toString() ?? '') ?? 0;

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
