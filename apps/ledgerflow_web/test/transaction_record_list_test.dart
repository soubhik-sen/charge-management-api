import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ledgerflow_web/core/design.dart';
import 'package:ledgerflow_web/data/workspace_data.dart';
import 'package:ledgerflow_web/features/transaction_record_list.dart';

void main() {
  testWidgets('filters rows by free-text search', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: _buildList(records: _records, pageSize: 2, onSelected: (_) {}),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const ValueKey('transaction-list-search')),
      'gamma',
    );
    await tester.pumpAndSettle();

    expect(find.text('REC-003'), findsOneWidget);
    expect(find.text('Gamma freight'), findsOneWidget);
    expect(find.text('REC-001'), findsNothing);
    expect(find.text('REC-002'), findsNothing);
  });

  testWidgets('filters rows by status', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: _buildList(records: _records, pageSize: 2, onSelected: (_) {}),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('All statuses'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('OPEN').last);
    await tester.pumpAndSettle();

    expect(find.text('REC-001'), findsOneWidget);
    expect(find.text('REC-003'), findsOneWidget);
    expect(find.text('REC-002'), findsNothing);
    expect(find.text('REC-004'), findsNothing);
  });

  testWidgets('paginates records with the configured page size', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: _buildList(
            records: _pagedRecords,
            pageSize: 2,
            onSelected: (_) {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('1-2 of 5 records'), findsOneWidget);
    expect(find.text('REC-001'), findsOneWidget);
    expect(find.text('REC-002'), findsOneWidget);
    expect(find.text('REC-003'), findsNothing);

    await tester.tap(find.byTooltip('Next page'));
    await tester.pumpAndSettle();

    expect(find.text('3-4 of 5 records'), findsOneWidget);
    expect(find.text('REC-003'), findsOneWidget);
    expect(find.text('REC-004'), findsOneWidget);
    expect(find.text('REC-001'), findsNothing);

    await tester.tap(find.byTooltip('Next page'));
    await tester.pumpAndSettle();

    expect(find.text('5-5 of 5 records'), findsOneWidget);
    expect(find.text('REC-005'), findsOneWidget);
    expect(find.text('REC-004'), findsNothing);
  });

  testWidgets('returns the original record index when a row is tapped', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final selected = <int>[];
    await tester.pumpWidget(
      MaterialApp(
        theme: LedgerFlowDesign.theme,
        home: Scaffold(
          body: _buildList(
            records: _pagedRecords,
            pageSize: 2,
            onSelected: selected.add,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Next page'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('transaction-row-3')));
    await tester.pumpAndSettle();

    expect(selected, equals([3]));
  });
}

Widget _buildList({
  required List<JsonMap> records,
  required int pageSize,
  required ValueChanged<int> onSelected,
}) {
  return TransactionRecordList(
    records: records,
    selectedIndex: -1,
    searchHint: 'Search records',
    emptyMessage: 'No records available.',
    searchText: (record) =>
        '${record['record_number']} ${record['record_name']} ${record['status']}',
    status: (record) => record['status'] as String,
    columns: [
      TransactionListColumn(
        label: 'Record',
        flex: 2,
        value: (record) => record['record_number'] as String,
      ),
      TransactionListColumn(
        label: 'Name',
        flex: 2,
        value: (record) => record['record_name'] as String,
      ),
      TransactionListColumn(
        label: 'Status',
        value: (record) => record['status'] as String,
        isStatus: true,
      ),
    ],
    onSelected: onSelected,
    pageSize: pageSize,
  );
}

final List<JsonMap> _records = [
  {
    'record_number': 'REC-001',
    'record_name': 'Alpha freight',
    'status': 'OPEN',
  },
  {
    'record_number': 'REC-002',
    'record_name': 'Beta freight',
    'status': 'CLOSED',
  },
  {
    'record_number': 'REC-003',
    'record_name': 'Gamma freight',
    'status': 'OPEN',
  },
  {
    'record_number': 'REC-004',
    'record_name': 'Delta freight',
    'status': 'CLOSED',
  },
];

final List<JsonMap> _pagedRecords = [
  {
    'record_number': 'REC-001',
    'record_name': 'Alpha freight',
    'status': 'OPEN',
  },
  {
    'record_number': 'REC-002',
    'record_name': 'Beta freight',
    'status': 'CLOSED',
  },
  {
    'record_number': 'REC-003',
    'record_name': 'Gamma freight',
    'status': 'OPEN',
  },
  {
    'record_number': 'REC-004',
    'record_name': 'Delta freight',
    'status': 'CLOSED',
  },
  {'record_number': 'REC-005', 'record_name': 'Echo freight', 'status': 'OPEN'},
];
