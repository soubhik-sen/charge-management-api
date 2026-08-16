import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/design.dart';
import '../data/workspace_data.dart';

class TransactionListColumn {
  const TransactionListColumn({
    required this.label,
    required this.value,
    this.flex = 1,
    this.isStatus = false,
    this.alignEnd = false,
  });

  final String label;
  final String Function(JsonMap record) value;
  final int flex;
  final bool isStatus;
  final bool alignEnd;
}

class TransactionRecordList extends StatefulWidget {
  const TransactionRecordList({
    required this.records,
    required this.selectedIndex,
    required this.searchText,
    required this.status,
    required this.columns,
    required this.onSelected,
    required this.searchHint,
    required this.emptyMessage,
    this.pageSize = 10,
    super.key,
  });

  final List<JsonMap> records;
  final int selectedIndex;
  final String Function(JsonMap record) searchText;
  final String Function(JsonMap record) status;
  final List<TransactionListColumn> columns;
  final ValueChanged<int> onSelected;
  final String searchHint;
  final String emptyMessage;
  final int pageSize;

  @override
  State<TransactionRecordList> createState() => _TransactionRecordListState();
}

class _TransactionRecordListState extends State<TransactionRecordList> {
  final _searchController = TextEditingController();
  String _query = '';
  String _status = '';
  int _page = 0;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final statuses =
        widget.records
            .map(widget.status)
            .map((value) => value.trim().toUpperCase())
            .where((value) => value.isNotEmpty)
            .toSet()
            .toList()
          ..sort();
    final effectiveStatus = statuses.contains(_status) ? _status : '';
    final filtered = <_IndexedTransactionRecord>[
      for (var index = 0; index < widget.records.length; index++)
        if (_matches(widget.records[index], effectiveStatus))
          _IndexedTransactionRecord(index, widget.records[index]),
    ];
    final pageCount = math.max(1, (filtered.length / widget.pageSize).ceil());
    final page = _page.clamp(0, pageCount - 1);
    final start = page * widget.pageSize;
    final end = math.min(start + widget.pageSize, filtered.length);
    final visible = filtered.sublist(start, end);

    return SurfaceCard(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(14),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final search = TextField(
                  key: const ValueKey('transaction-list-search'),
                  controller: _searchController,
                  onChanged: (value) => setState(() {
                    _query = value.trim().toLowerCase();
                    _page = 0;
                  }),
                  decoration: InputDecoration(
                    labelText: widget.searchHint,
                    prefixIcon: const Icon(Icons.search, size: 19),
                    suffixIcon: _query.isEmpty
                        ? null
                        : IconButton(
                            tooltip: 'Clear search',
                            onPressed: () {
                              _searchController.clear();
                              setState(() {
                                _query = '';
                                _page = 0;
                              });
                            },
                            icon: const Icon(Icons.close, size: 18),
                          ),
                  ),
                );
                final statusFilter = DropdownButtonFormField<String>(
                  key: const ValueKey('transaction-list-status'),
                  initialValue: effectiveStatus,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Status'),
                  items: [
                    const DropdownMenuItem(
                      value: '',
                      child: Text('All statuses'),
                    ),
                    ...statuses.map(
                      (value) => DropdownMenuItem(
                        value: value,
                        child: Text(value.replaceAll('_', ' ')),
                      ),
                    ),
                  ],
                  onChanged: (value) => setState(() {
                    _status = value ?? '';
                    _page = 0;
                  }),
                );
                if (constraints.maxWidth < 680) {
                  return Column(
                    children: [
                      search,
                      const SizedBox(height: 10),
                      statusFilter,
                    ],
                  );
                }
                return Row(
                  children: [
                    Expanded(child: search),
                    const SizedBox(width: 12),
                    SizedBox(width: 190, child: statusFilter),
                  ],
                );
              },
            ),
          ),
          const Divider(height: 1),
          LayoutBuilder(
            builder: (context, constraints) => constraints.maxWidth < 760
                ? _CompactTransactionRows(
                    records: visible,
                    columns: widget.columns,
                    selectedIndex: widget.selectedIndex,
                    onSelected: widget.onSelected,
                  )
                : _DesktopTransactionRows(
                    records: visible,
                    columns: widget.columns,
                    selectedIndex: widget.selectedIndex,
                    onSelected: widget.onSelected,
                  ),
          ),
          if (visible.isEmpty)
            Padding(
              padding: const EdgeInsets.all(28),
              child: Center(
                child: Text(
                  _query.isEmpty && effectiveStatus.isEmpty
                      ? widget.emptyMessage
                      : 'No records match the current filters.',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: LedgerFlowDesign.muted),
                ),
              ),
            ),
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    filtered.isEmpty
                        ? '0 of ${widget.records.length} records'
                        : '${start + 1}-$end of ${filtered.length} records',
                    style: const TextStyle(
                      color: LedgerFlowDesign.muted,
                      fontSize: 11,
                    ),
                  ),
                ),
                IconButton(
                  tooltip: 'Previous page',
                  onPressed: page > 0
                      ? () => setState(() => _page = page - 1)
                      : null,
                  icon: const Icon(Icons.chevron_left),
                ),
                Text(
                  'Page ${page + 1} of $pageCount',
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                IconButton(
                  tooltip: 'Next page',
                  onPressed: page + 1 < pageCount
                      ? () => setState(() => _page = page + 1)
                      : null,
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  bool _matches(JsonMap record, String statusFilter) {
    final status = widget.status(record).trim().toUpperCase();
    if (statusFilter.isNotEmpty && status != statusFilter) return false;
    return _query.isEmpty ||
        widget.searchText(record).toLowerCase().contains(_query);
  }
}

class _DesktopTransactionRows extends StatelessWidget {
  const _DesktopTransactionRows({
    required this.records,
    required this.columns,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<_IndexedTransactionRecord> records;
  final List<TransactionListColumn> columns;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    if (records.isEmpty) return const SizedBox.shrink();
    return Column(
      children: [
        Container(
          color: const Color(0xFFF6F8FA),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          child: Row(
            children: [
              for (final column in columns)
                Expanded(
                  flex: column.flex,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 6),
                    child: Align(
                      alignment: column.alignEnd
                          ? Alignment.centerRight
                          : Alignment.centerLeft,
                      child: Text(
                        column.label,
                        style: const TextStyle(
                          color: LedgerFlowDesign.muted,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        for (final entry in records)
          _DesktopTransactionRow(
            entry: entry,
            columns: columns,
            selected: entry.index == selectedIndex,
            onSelected: onSelected,
          ),
      ],
    );
  }
}

class _DesktopTransactionRow extends StatelessWidget {
  const _DesktopTransactionRow({
    required this.entry,
    required this.columns,
    required this.selected,
    required this.onSelected,
  });

  final _IndexedTransactionRecord entry;
  final List<TransactionListColumn> columns;
  final bool selected;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      key: ValueKey('transaction-row-${entry.index}'),
      onTap: () => onSelected(entry.index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 140),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: selected
              ? LedgerFlowDesign.teal.withValues(alpha: 0.08)
              : Colors.white,
          border: const Border(
            bottom: BorderSide(color: LedgerFlowDesign.border),
          ),
        ),
        child: Row(
          children: [
            for (final column in columns)
              Expanded(
                flex: column.flex,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  child: Align(
                    alignment: column.alignEnd
                        ? Alignment.centerRight
                        : Alignment.centerLeft,
                    child: column.isStatus
                        ? StatusPill(column.value(entry.record))
                        : Text(
                            column.value(entry.record),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: column == columns.first
                                  ? FontWeight.w700
                                  : FontWeight.w500,
                              color: selected && column == columns.first
                                  ? LedgerFlowDesign.tealDark
                                  : LedgerFlowDesign.ink,
                            ),
                          ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _CompactTransactionRows extends StatelessWidget {
  const _CompactTransactionRows({
    required this.records,
    required this.columns,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<_IndexedTransactionRecord> records;
  final List<TransactionListColumn> columns;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    if (records.isEmpty) return const SizedBox.shrink();
    final valueColumns = columns.where((column) => !column.isStatus).toList();
    final statusColumn = columns.where((column) => column.isStatus).firstOrNull;
    return Column(
      children: [
        for (final entry in records)
          InkWell(
            key: ValueKey('transaction-row-${entry.index}'),
            onTap: () => onSelected(entry.index),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
              decoration: BoxDecoration(
                color: entry.index == selectedIndex
                    ? LedgerFlowDesign.teal.withValues(alpha: 0.08)
                    : Colors.white,
                border: const Border(
                  bottom: BorderSide(color: LedgerFlowDesign.border),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          valueColumns.first.value(entry.record),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        if (valueColumns.length > 1) ...[
                          const SizedBox(height: 3),
                          Text(
                            valueColumns
                                .skip(1)
                                .take(2)
                                .map((column) => column.value(entry.record))
                                .join('  |  '),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              color: LedgerFlowDesign.muted,
                              fontSize: 11,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (statusColumn != null) ...[
                    const SizedBox(width: 10),
                    StatusPill(statusColumn.value(entry.record)),
                  ],
                ],
              ),
            ),
          ),
      ],
    );
  }
}

class _IndexedTransactionRecord {
  const _IndexedTransactionRecord(this.index, this.record);

  final int index;
  final JsonMap record;
}
