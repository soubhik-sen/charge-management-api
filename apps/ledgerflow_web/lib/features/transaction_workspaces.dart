import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/design.dart';
import '../core/reference_values.dart';
import '../data/workspace_data.dart';
import 'transaction_record_list.dart';
import 'workspace_pages.dart';

class ContractManagementWorkspace extends StatefulWidget {
  const ContractManagementWorkspace({
    required this.contracts,
    required this.components,
    required this.rateBooks,
    required this.calculationTemplates,
    required this.calculationProfiles,
    required this.allocationProfiles,
    required this.live,
    required this.client,
    required this.onReload,
    super.key,
  });

  final List<JsonMap> contracts;
  final List<JsonMap> components;
  final List<JsonMap> rateBooks;
  final List<JsonMap> calculationTemplates;
  final List<JsonMap> calculationProfiles;
  final List<JsonMap> allocationProfiles;
  final bool live;
  final LedgerFlowApiClient? client;
  final Future<void> Function() onReload;

  @override
  State<ContractManagementWorkspace> createState() =>
      _ContractManagementWorkspaceState();
}

class _ContractManagementWorkspaceState
    extends State<ContractManagementWorkspace> {
  int _selectedIndex = 0;
  bool _busy = false;

  @override
  void didUpdateWidget(covariant ContractManagementWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selectedIndex >= widget.contracts.length) {
      _selectedIndex = widget.contracts.isEmpty
          ? 0
          : widget.contracts.length - 1;
    }
  }

  JsonMap? get _selectedContract => widget.contracts.isEmpty
      ? null
      : widget.contracts[_selectedIndex.clamp(0, widget.contracts.length - 1)];

  Future<void> _editContract([JsonMap? contract]) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      barrierDismissible: false,
      builder: (_) => ContractEditorDialog(
        contract: contract,
        components: widget.components,
        rateBooks: widget.rateBooks,
        calculationTemplates: widget.calculationTemplates,
        calculationProfiles: widget.calculationProfiles,
        allocationProfiles: widget.allocationProfiles,
      ),
    );
    if (payload == null) return;
    final editing = contract != null;
    final result = await _request(
      editing ? 'PUT' : 'POST',
      editing
          ? '/api/v1/charge-management/contracts/${contract['id']}/workspace'
          : '/api/v1/charge-management/contracts',
      body: payload,
      success: editing ? 'Contract updated.' : 'Contract created.',
    );
    if (result != null && !editing && mounted) {
      final created = result['contract'] is JsonMap
          ? result['contract'] as JsonMap
          : result;
      final id = _asInt(created['id']);
      final index = widget.contracts.indexWhere(
        (row) => _asInt(row['id']) == id,
      );
      if (index >= 0) setState(() => _selectedIndex = index);
    }
  }

  Future<void> _release(JsonMap contract) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Release contract?'),
        content: const Text(
          'Release makes this contract eligible for quote matching. Every referenced rate book and calculation template must already be published.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Release'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    await _request(
      'POST',
      '/api/v1/charge-management/contracts/${contract['id']}/release',
      success: 'Contract released.',
    );
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
      await widget.onReload();
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(success)));
      }
      return response;
    } catch (error) {
      if (mounted) _showError(context, error);
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final contract = _selectedContract;
    final contractStatus = contract == null
        ? null
        : _text(contract, 'status', fallback: 'DRAFT').toUpperCase();
    final actions = Wrap(
      spacing: 10,
      runSpacing: 8,
      children: [
        OutlinedButton.icon(
          onPressed:
              widget.live &&
                  !_busy &&
                  contract != null &&
                  contractStatus == 'DRAFT'
              ? () => _editContract(contract)
              : null,
          icon: const Icon(Icons.edit_outlined),
          label: const Text('Edit'),
        ),
        FilledButton.icon(
          onPressed: widget.live && !_busy ? () => _editContract() : null,
          icon: const Icon(Icons.add),
          label: const Text('New contract'),
        ),
      ],
    );
    if (contract == null) {
      return PageCanvas(
        title: 'Contracts',
        subtitle:
            'Bind published pricing to caller party IDs and applicability rules.',
        trailing: actions,
        children: const [
          SurfaceCard(
            child: EmptyState(
              message: 'No contracts exist. Create a draft contract to begin.',
            ),
          ),
        ],
      );
    }
    final lines = _rows(contract, 'lines');
    final templateRoutes = _rows(contract, 'template_routes');
    final status = _text(contract, 'status', fallback: 'DRAFT');
    return PageCanvas(
      title: _text(contract, 'contract_name'),
      eyebrow: 'Contracts / ${_text(contract, 'contract_number')}',
      subtitle:
          '${_text(contract, 'contract_role')} pricing contract · ${_partySummary(contract)}',
      trailing: actions,
      children: [
        _HorizontalRecordPicker(
          records: widget.contracts,
          selectedIndex: _selectedIndex,
          label: (row) => _text(row, 'contract_number'),
          detail: (row) =>
              '${_text(row, 'contract_role')} · ${_text(row, 'status')}',
          onSelected: (index) => setState(() => _selectedIndex = index),
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
                const Padding(
                  padding: EdgeInsets.all(18),
                  child: SectionHeading(
                    title: 'Pricing execution',
                    subtitle:
                        'A header template runs once. Optional routes choose another template for specific conditions; direct component lines are retained for legacy pricing.',
                  ),
                ),
                if (templateRoutes.isNotEmpty)
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const [
                        DataColumn(label: Text('Route')),
                        DataColumn(label: Text('Template')),
                        DataColumn(label: Text('Applicability')),
                        DataColumn(label: Text('Priority')),
                      ],
                      rows: templateRoutes
                          .map(
                            (route) => DataRow(
                              cells: [
                                DataCell(Text(_text(route, 'route_number'))),
                                DataCell(
                                  Text(
                                    _lookupName(
                                      widget.calculationTemplates,
                                      route['calculation_template_id'],
                                      'template_name',
                                    ),
                                  ),
                                ),
                                DataCell(Text(_lineApplicability(route))),
                                DataCell(
                                  Text(
                                    _text(route, 'priority', fallback: '100'),
                                  ),
                                ),
                              ],
                            ),
                          )
                          .toList(growable: false),
                    ),
                  )
                else if (contract['default_calculation_template_id'] != null)
                  const Padding(
                    padding: EdgeInsets.fromLTRB(18, 0, 18, 18),
                    child: Text(
                      'The default calculation template applies to every matching request; no routing rows are required.',
                      style: TextStyle(color: LedgerFlowDesign.muted),
                    ),
                  ),
                const Divider(height: 1),
                const Padding(
                  padding: EdgeInsets.all(18),
                  child: SectionHeading(
                    title: 'Legacy direct component lines',
                    subtitle:
                        'Use only for direct component pricing that does not run a calculation template.',
                  ),
                ),
                if (lines.isEmpty)
                  const EmptyState(
                    message: 'No direct component lines configured.',
                  )
                else
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      showCheckboxColumn: false,
                      columns: const [
                        DataColumn(label: Text('Line')),
                        DataColumn(label: Text('Component')),
                        DataColumn(label: Text('Rate book')),
                        DataColumn(label: Text('Template')),
                        DataColumn(label: Text('Applicability')),
                        DataColumn(label: Text('Priority')),
                      ],
                      rows: lines
                          .map((line) {
                            return DataRow(
                              cells: [
                                DataCell(Text(_text(line, 'line_number'))),
                                DataCell(
                                  Text(_text(line, 'charge_component_code')),
                                ),
                                DataCell(
                                  Text(
                                    _lookupName(
                                      widget.rateBooks,
                                      line['rate_book_id'],
                                      'rate_book_name',
                                    ),
                                  ),
                                ),
                                DataCell(
                                  Text(
                                    _lookupName(
                                      widget.calculationTemplates,
                                      line['calculation_template_id'],
                                      'template_name',
                                    ),
                                  ),
                                ),
                                DataCell(Text(_lineApplicability(line))),
                                DataCell(
                                  Text(
                                    _text(line, 'priority', fallback: '100'),
                                  ),
                                ),
                              ],
                            );
                          })
                          .toList(growable: false),
                    ),
                  ),
              ],
            ),
          ),
          right: Column(
            children: [
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SectionHeading(
                      title: 'Contract status',
                      action: StatusPill(status),
                    ),
                    const SizedBox(height: 12),
                    DetailRow(
                      label: 'Bindings',
                      value: _partySummary(contract),
                    ),
                    DetailRow(
                      label: 'Currency',
                      value: _text(contract, 'currency'),
                    ),
                    DetailRow(
                      label: 'Selection priority',
                      value: _text(
                        contract,
                        'selection_priority',
                        fallback: '100',
                      ),
                    ),
                    DetailRow(
                      label: 'Effective',
                      value:
                          '${_text(contract, 'valid_from', fallback: 'Open')} → ${_text(contract, 'valid_to', fallback: 'Open')}',
                    ),
                    DetailRow(
                      label: 'Default book',
                      value: _lookupName(
                        widget.rateBooks,
                        contract['default_rate_book_id'],
                        'rate_book_name',
                      ),
                    ),
                    DetailRow(
                      label: 'Default template',
                      value: _lookupName(
                        widget.calculationTemplates,
                        contract['default_calculation_template_id'],
                        'template_name',
                      ),
                    ),
                    if (status == 'DRAFT') ...[
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: widget.live && !_busy
                              ? () => _release(contract)
                              : null,
                          icon: const Icon(Icons.verified_outlined),
                          label: const Text('Release contract'),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
              const SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SectionHeading(title: 'Matching rule'),
                    SizedBox(height: 10),
                    Text(
                      'The caller must send the same company, customer, vendor, forwarder, or carrier ID stored on this contract. Party-reference text is retained for audit but does not select the contract.',
                      style: TextStyle(
                        color: LedgerFlowDesign.muted,
                        height: 1.45,
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

class ContractEditorDialog extends StatefulWidget {
  const ContractEditorDialog({
    required this.components,
    required this.rateBooks,
    required this.calculationTemplates,
    required this.calculationProfiles,
    required this.allocationProfiles,
    this.contract,
    super.key,
  });

  final JsonMap? contract;
  final List<JsonMap> components;
  final List<JsonMap> rateBooks;
  final List<JsonMap> calculationTemplates;
  final List<JsonMap> calculationProfiles;
  final List<JsonMap> allocationProfiles;

  @override
  State<ContractEditorDialog> createState() => _ContractEditorDialogState();
}

class _ContractEditorDialogState extends State<ContractEditorDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _number;
  late final TextEditingController _name;
  late final TextEditingController _description;
  late final TextEditingController _companyId;
  late final TextEditingController _customerId;
  late final TextEditingController _vendorId;
  late final TextEditingController _forwarderId;
  late final TextEditingController _carrierId;
  late final TextEditingController _payerRef;
  late final TextEditingController _payeeRef;
  late String _role;
  late String _currency;
  late String _validFrom;
  late String _validTo;
  late int _selectionPriority;
  int? _defaultRateBookId;
  int? _defaultTemplateId;
  late List<_ContractTemplateRouteDraft> _templateRoutes;
  late List<_ContractLineDraft> _lines;

  bool get _editing => widget.contract != null;

  @override
  void initState() {
    super.initState();
    final row = widget.contract ?? const <String, dynamic>{};
    _number = TextEditingController(text: _text(row, 'contract_number'));
    _name = TextEditingController(text: _text(row, 'contract_name'));
    _description = TextEditingController(text: _text(row, 'description'));
    _payerRef = TextEditingController(text: _text(row, 'payer_party_ref'));
    _payeeRef = TextEditingController(text: _text(row, 'payee_party_ref'));
    _role = _text(row, 'contract_role', fallback: 'PAYEE');
    _currency = _text(row, 'currency', fallback: 'EUR');
    _companyId = TextEditingController(text: _text(row, 'company_id'));
    _customerId = TextEditingController(text: _text(row, 'customer_id'));
    _vendorId = TextEditingController(text: _text(row, 'vendor_id'));
    _forwarderId = TextEditingController(text: _text(row, 'forwarder_id'));
    _carrierId = TextEditingController(text: _text(row, 'carrier_id'));
    _validFrom = _text(row, 'valid_from');
    _validTo = _text(row, 'valid_to');
    _selectionPriority = _asInt(row['selection_priority']) ?? 100;
    _defaultRateBookId = _asInt(row['default_rate_book_id']);
    _defaultTemplateId = _asInt(row['default_calculation_template_id']);
    _templateRoutes = _rows(
      row,
      'template_routes',
    ).map(_ContractTemplateRouteDraft.fromJson).toList();
    _lines = _rows(row, 'lines').map(_ContractLineDraft.fromJson).toList();
  }

  @override
  void dispose() {
    _number.dispose();
    _name.dispose();
    _description.dispose();
    _companyId.dispose();
    _customerId.dispose();
    _vendorId.dispose();
    _forwarderId.dispose();
    _carrierId.dispose();
    _payerRef.dispose();
    _payeeRef.dispose();
    super.dispose();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final payload = <String, dynamic>{
      'contract_number': _number.text.trim().toUpperCase(),
      'contract_name': _name.text.trim(),
      'contract_role': _role,
      'description': _nullIfEmpty(_description.text),
      'payer_party_ref': _nullIfEmpty(_payerRef.text),
      'payee_party_ref': _nullIfEmpty(_payeeRef.text),
      'party_role_ref': _role,
      'company_id': _optionalInt(_companyId.text),
      'customer_id': _optionalInt(_customerId.text),
      'vendor_id': _optionalInt(_vendorId.text),
      'forwarder_id': _optionalInt(_forwarderId.text),
      'carrier_id': _optionalInt(_carrierId.text),
      'currency': _currency,
      'valid_from': _nullIfEmpty(_validFrom),
      'valid_to': _nullIfEmpty(_validTo),
      'selection_priority': _selectionPriority,
      'default_rate_book_id': _defaultRateBookId,
      'default_calculation_template_id': _defaultTemplateId,
      'template_routes': _templateRoutes
          .map((route) => route.toJson())
          .toList(growable: false),
      'lines': _lines.map((line) => line.toJson()).toList(growable: false),
    };
    Navigator.pop(context, JsonMap.from(payload));
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_editing ? 'Edit contract' : 'Create contract'),
      content: SizedBox(
        width: 1120,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Contract identity',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                _FormGrid(
                  children: [
                    TextFormField(
                      controller: _number,
                      decoration: const InputDecoration(
                        labelText: 'Contract number',
                        helperText: 'Stable external or commercial identifier',
                      ),
                      validator: (value) => _required(value, 'Contract number'),
                    ),
                    TextFormField(
                      controller: _name,
                      decoration: const InputDecoration(
                        labelText: 'Contract name',
                      ),
                      validator: (value) => _required(value, 'Contract name'),
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: _role,
                      decoration: const InputDecoration(
                        labelText: 'Contract role',
                        helperText:
                            'PAYER is provider cost; PAYEE is customer price',
                      ),
                      items: const ['PAYER', 'PAYEE']
                          .map(
                            (value) => DropdownMenuItem(
                              value: value,
                              child: Text(value),
                            ),
                          )
                          .toList(),
                      onChanged: (value) =>
                          setState(() => _role = value ?? _role),
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: _currency,
                      decoration: const InputDecoration(labelText: 'Currency'),
                      items:
                          referenceValuesWithCurrent(currencyValues, _currency)
                              .map(
                                (value) => DropdownMenuItem(
                                  value: value,
                                  child: Text(value),
                                ),
                              )
                              .toList(),
                      onChanged: (value) =>
                          setState(() => _currency = value ?? _currency),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                TextFormField(
                  controller: _description,
                  decoration: const InputDecoration(labelText: 'Description'),
                ),
                const SizedBox(height: 22),
                const Text(
                  'Caller party binding',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Enter the caller IDs that may match this contract. Multiple bindings can be populated at the same time.',
                  style: TextStyle(color: LedgerFlowDesign.muted),
                ),
                const SizedBox(height: 12),
                _FormGrid(
                  children: [
                    TextFormField(
                      controller: _companyId,
                      decoration: const InputDecoration(
                        labelText: 'Company ID',
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) =>
                          _optionalIntValidator(value, label: 'Company ID'),
                    ),
                    TextFormField(
                      controller: _customerId,
                      decoration: const InputDecoration(
                        labelText: 'Customer ID',
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) =>
                          _optionalIntValidator(value, label: 'Customer ID'),
                    ),
                    TextFormField(
                      controller: _vendorId,
                      decoration: const InputDecoration(labelText: 'Vendor ID'),
                      keyboardType: TextInputType.number,
                      validator: (value) =>
                          _optionalIntValidator(value, label: 'Vendor ID'),
                    ),
                    TextFormField(
                      controller: _forwarderId,
                      decoration: const InputDecoration(
                        labelText: 'Forwarder ID',
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) =>
                          _optionalIntValidator(value, label: 'Forwarder ID'),
                    ),
                    TextFormField(
                      controller: _carrierId,
                      decoration: const InputDecoration(
                        labelText: 'Carrier ID',
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) =>
                          _optionalIntValidator(value, label: 'Carrier ID'),
                    ),
                    TextFormField(
                      controller: _payerRef,
                      decoration: const InputDecoration(
                        labelText: 'Payer reference',
                      ),
                    ),
                    TextFormField(
                      controller: _payeeRef,
                      decoration: const InputDecoration(
                        labelText: 'Payee reference',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                const Text(
                  'Defaults and validity',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                _FormGrid(
                  children: [
                    _DateInput(
                      label: 'Valid from',
                      value: _validFrom,
                      onChanged: (value) => setState(() => _validFrom = value),
                    ),
                    _DateInput(
                      label: 'Valid to',
                      value: _validTo,
                      onChanged: (value) => setState(() => _validTo = value),
                    ),
                    TextFormField(
                      initialValue: '$_selectionPriority',
                      decoration: const InputDecoration(
                        labelText: 'Contract selection priority',
                        helperText:
                            'Lower number wins when multiple contracts match',
                      ),
                      keyboardType: TextInputType.number,
                      validator: (value) =>
                          int.tryParse((value ?? '').trim()) == null
                          ? 'Enter a numeric priority'
                          : null,
                      onChanged: (value) => _selectionPriority =
                          int.tryParse(value) ?? _selectionPriority,
                    ),
                    _NullableIdDropdown(
                      label: 'Default rate book',
                      value: _defaultRateBookId,
                      records: widget.rateBooks.where(_isPublished).toList(),
                      nameField: 'rate_book_name',
                      onChanged: (value) =>
                          setState(() => _defaultRateBookId = value),
                    ),
                    _NullableIdDropdown(
                      label: 'Default calculation template',
                      value: _defaultTemplateId,
                      records: widget.calculationTemplates
                          .where(_isPublished)
                          .toList(),
                      nameField: 'template_name',
                      helperText:
                          'Runs once for every matching request; no contract rows are required',
                      onChanged: (value) =>
                          setState(() => _defaultTemplateId = value),
                    ),
                  ],
                ),
                const SizedBox(height: 24),
                Row(
                  children: [
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Conditional template routes',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          SizedBox(height: 3),
                          Text(
                            'Optional. Use only when conditions must select a different template than the header default.',
                            style: TextStyle(color: LedgerFlowDesign.muted),
                          ),
                        ],
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => setState(() {
                        _templateRoutes.add(
                          _ContractTemplateRouteDraft(
                            routeNumber: (_templateRoutes.length + 1) * 10,
                          ),
                        );
                      }),
                      icon: const Icon(Icons.alt_route),
                      label: const Text('Add route'),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                ...List.generate(_templateRoutes.length, (index) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _ContractTemplateRouteEditor(
                      index: index,
                      route: _templateRoutes[index],
                      calculationTemplates: widget.calculationTemplates,
                      onChanged: () => setState(() {}),
                      onRemove: () =>
                          setState(() => _templateRoutes.removeAt(index)),
                    ),
                  );
                }),
                const SizedBox(height: 18),
                Row(
                  children: [
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Legacy direct component pricing',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          SizedBox(height: 3),
                          Text(
                            'Optional compatibility path. Do not add these when the contract executes a calculation template.',
                            style: TextStyle(color: LedgerFlowDesign.muted),
                          ),
                        ],
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => setState(() {
                        _lines.add(
                          _ContractLineDraft(
                            lineNumber: (_lines.length + 1) * 10,
                          ),
                        );
                      }),
                      icon: const Icon(Icons.add),
                      label: const Text('Add direct line'),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                ...List.generate(_lines.length, (index) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: _ContractLineEditor(
                      index: index,
                      line: _lines[index],
                      components: widget.components,
                      rateBooks: widget.rateBooks,
                      calculationProfiles: widget.calculationProfiles,
                      allocationProfiles: widget.allocationProfiles,
                      onChanged: () => setState(() {}),
                      onRemove: () => setState(() => _lines.removeAt(index)),
                    ),
                  );
                }),
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
        FilledButton(
          onPressed: _submit,
          child: Text(_editing ? 'Save contract' : 'Create contract'),
        ),
      ],
    );
  }
}

class _ContractTemplateRouteDraft {
  _ContractTemplateRouteDraft({required this.routeNumber});

  factory _ContractTemplateRouteDraft.fromJson(JsonMap row) {
    return _ContractTemplateRouteDraft(
        routeNumber: _asInt(row['route_number']) ?? 10,
      )
      ..templateId = _asInt(row['calculation_template_id'])
      ..originCode = _text(row, 'origin_code')
      ..destinationCode = _text(row, 'destination_code')
      ..mode = _text(row, 'mode')
      ..equipmentType = _text(row, 'equipment_type')
      ..commodityCode = _text(row, 'commodity_code')
      ..serviceLevel = _text(row, 'service_level')
      ..chargeContext = _text(row, 'charge_context')
      ..priority = _asInt(row['priority']) ?? 100
      ..validFrom = _text(row, 'valid_from')
      ..validTo = _text(row, 'valid_to')
      ..isActive = row['is_active'] != false;
  }

  int routeNumber;
  int? templateId;
  String originCode = '';
  String destinationCode = '';
  String mode = '';
  String equipmentType = '';
  String commodityCode = '';
  String serviceLevel = '';
  String chargeContext = '';
  int priority = 100;
  String validFrom = '';
  String validTo = '';
  bool isActive = true;

  JsonMap toJson() => {
    'route_number': routeNumber,
    'calculation_template_id': templateId,
    'origin_code': _nullIfEmpty(originCode),
    'destination_code': _nullIfEmpty(destinationCode),
    'mode': _nullIfEmpty(mode),
    'equipment_type': _nullIfEmpty(equipmentType),
    'commodity_code': _nullIfEmpty(commodityCode),
    'service_level': _nullIfEmpty(serviceLevel),
    'charge_context': _nullIfEmpty(chargeContext),
    'priority': priority,
    'valid_from': _nullIfEmpty(validFrom),
    'valid_to': _nullIfEmpty(validTo),
    'is_active': isActive,
  };
}

class _ContractTemplateRouteEditor extends StatelessWidget {
  const _ContractTemplateRouteEditor({
    required this.index,
    required this.route,
    required this.calculationTemplates,
    required this.onChanged,
    required this.onRemove,
  });

  final int index;
  final _ContractTemplateRouteDraft route;
  final List<JsonMap> calculationTemplates;
  final VoidCallback onChanged;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final templates = calculationTemplates.where(_isPublished).toList();
    return Material(
      color: const Color(0xFFF8FAFC),
      shape: RoundedRectangleBorder(
        side: const BorderSide(color: LedgerFlowDesign.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Template route ${index + 1}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                IconButton(
                  onPressed: onRemove,
                  tooltip: 'Remove route',
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
            _FormGrid(
              children: [
                DropdownButtonFormField<int>(
                  isExpanded: true,
                  initialValue: route.templateId,
                  decoration: const InputDecoration(
                    labelText: 'Calculation template',
                    helperText: 'Published template selected by this rule',
                  ),
                  items: templates
                      .map(
                        (row) => DropdownMenuItem<int>(
                          value: _asInt(row['id']),
                          child: Text(
                            _recordLabel(row, 'template_name', 'template_code'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      )
                      .toList(),
                  validator: (value) =>
                      value == null ? 'Calculation template is required' : null,
                  onChanged: (value) {
                    route.templateId = value;
                    onChanged();
                  },
                ),
                TextFormField(
                  initialValue: '${route.routeNumber}',
                  decoration: const InputDecoration(labelText: 'Route number'),
                  keyboardType: TextInputType.number,
                  onChanged: (value) => route.routeNumber =
                      int.tryParse(value) ?? route.routeNumber,
                ),
                TextFormField(
                  initialValue: route.originCode,
                  decoration: const InputDecoration(labelText: 'Origin code'),
                  onChanged: (value) =>
                      route.originCode = value.trim().toUpperCase(),
                ),
                TextFormField(
                  initialValue: route.destinationCode,
                  decoration: const InputDecoration(
                    labelText: 'Destination code',
                  ),
                  onChanged: (value) =>
                      route.destinationCode = value.trim().toUpperCase(),
                ),
                _OptionalStringDropdown(
                  label: 'Mode',
                  value: route.mode,
                  values: transportModeValues,
                  onChanged: (value) => route.mode = value,
                ),
                _OptionalStringDropdown(
                  label: 'Equipment',
                  value: route.equipmentType,
                  values: equipmentTypeValues,
                  onChanged: (value) => route.equipmentType = value,
                ),
                _OptionalStringDropdown(
                  label: 'Service level',
                  value: route.serviceLevel,
                  values: serviceLevelValues,
                  onChanged: (value) => route.serviceLevel = value,
                ),
                _OptionalStringDropdown(
                  label: 'Charge context',
                  value: route.chargeContext,
                  values: chargeContextValues,
                  onChanged: (value) => route.chargeContext = value,
                ),
                TextFormField(
                  initialValue: route.commodityCode,
                  decoration: const InputDecoration(
                    labelText: 'Commodity code',
                  ),
                  onChanged: (value) =>
                      route.commodityCode = value.trim().toUpperCase(),
                ),
                TextFormField(
                  initialValue: '${route.priority}',
                  decoration: const InputDecoration(
                    labelText: 'Route priority',
                    helperText:
                        'Lower number wins; equal best matches are rejected',
                  ),
                  keyboardType: TextInputType.number,
                  onChanged: (value) =>
                      route.priority = int.tryParse(value) ?? route.priority,
                ),
                _DateInput(
                  label: 'Valid from',
                  value: route.validFrom,
                  onChanged: (value) => route.validFrom = value,
                ),
                _DateInput(
                  label: 'Valid to',
                  value: route.validTo,
                  onChanged: (value) => route.validTo = value,
                ),
              ],
            ),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text('Route is active'),
              value: route.isActive,
              onChanged: (value) {
                route.isActive = value;
                onChanged();
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _ContractLineDraft {
  _ContractLineDraft({required this.lineNumber});

  factory _ContractLineDraft.fromJson(JsonMap row) {
    return _ContractLineDraft(lineNumber: _asInt(row['line_number']) ?? 10)
      ..componentCode = _text(row, 'charge_component_code')
      ..rateBookId = _asInt(row['rate_book_id'])
      ..templateId = _asInt(row['calculation_template_id'])
      ..calculationProfileId = _asInt(row['calculation_profile_id'])
      ..allocationProfileId = _asInt(row['allocation_profile_id'])
      ..originCode = _text(row, 'origin_code')
      ..destinationCode = _text(row, 'destination_code')
      ..mode = _text(row, 'mode')
      ..equipmentType = _text(row, 'equipment_type')
      ..commodityCode = _text(row, 'commodity_code')
      ..serviceLevel = _text(row, 'service_level')
      ..chargeContext = _text(row, 'charge_context')
      ..priority = _asInt(row['priority']) ?? 100
      ..validFrom = _text(row, 'valid_from')
      ..validTo = _text(row, 'valid_to')
      ..isActive = row['is_active'] != false;
  }

  int lineNumber;
  String componentCode = '';
  int? rateBookId;
  int? templateId;
  int? calculationProfileId;
  int? allocationProfileId;
  String originCode = '';
  String destinationCode = '';
  String mode = '';
  String equipmentType = '';
  String commodityCode = '';
  String serviceLevel = '';
  String chargeContext = '';
  int priority = 100;
  String validFrom = '';
  String validTo = '';
  bool isActive = true;

  JsonMap toJson() => {
    'line_number': lineNumber,
    'charge_component_code': componentCode,
    'rate_book_id': rateBookId,
    'calculation_template_id': templateId,
    'calculation_profile_id': calculationProfileId,
    'allocation_profile_id': allocationProfileId,
    'origin_code': _nullIfEmpty(originCode),
    'destination_code': _nullIfEmpty(destinationCode),
    'mode': _nullIfEmpty(mode),
    'equipment_type': _nullIfEmpty(equipmentType),
    'commodity_code': _nullIfEmpty(commodityCode),
    'service_level': _nullIfEmpty(serviceLevel),
    'charge_context': _nullIfEmpty(chargeContext),
    'priority': priority,
    'valid_from': _nullIfEmpty(validFrom),
    'valid_to': _nullIfEmpty(validTo),
    'is_active': isActive,
  };
}

class _ContractLineEditor extends StatelessWidget {
  const _ContractLineEditor({
    required this.index,
    required this.line,
    required this.components,
    required this.rateBooks,
    required this.calculationProfiles,
    required this.allocationProfiles,
    required this.onChanged,
    required this.onRemove,
  });

  final int index;
  final _ContractLineDraft line;
  final List<JsonMap> components;
  final List<JsonMap> rateBooks;
  final List<JsonMap> calculationProfiles;
  final List<JsonMap> allocationProfiles;
  final VoidCallback onChanged;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    final books = rateBooks
        .where((book) {
          return _isPublished(book) &&
              (line.componentCode.isEmpty ||
                  _text(book, 'charge_component_code') == line.componentCode);
        })
        .toList(growable: false);
    if (line.rateBookId != null &&
        !books.any((book) => _asInt(book['id']) == line.rateBookId)) {
      line.rateBookId = null;
    }
    return Material(
      color: const Color(0xFFF8FAFC),
      shape: RoundedRectangleBorder(
        side: const BorderSide(color: LedgerFlowDesign.border),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Line ${index + 1}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                IconButton(
                  onPressed: onRemove,
                  tooltip: 'Remove line',
                  icon: const Icon(Icons.delete_outline),
                ),
              ],
            ),
            _FormGrid(
              children: [
                DropdownButtonFormField<String>(
                  isExpanded: true,
                  initialValue: line.componentCode.isEmpty
                      ? null
                      : line.componentCode,
                  decoration: const InputDecoration(
                    labelText: 'Charge component',
                  ),
                  items: components
                      .where((row) => row['is_active'] != false)
                      .map(
                        (row) => DropdownMenuItem(
                          value: _text(row, 'component_code'),
                          child: Text(
                            _recordLabel(
                              row,
                              'component_name',
                              'component_code',
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      )
                      .toList(),
                  validator: (value) => _required(value, 'Charge component'),
                  onChanged: (value) {
                    line.componentCode = value ?? '';
                    line.rateBookId = null;
                    onChanged();
                  },
                ),
                _NullableIdDropdown(
                  label: 'Rate book',
                  value: line.rateBookId,
                  records: books,
                  nameField: 'rate_book_name',
                  helperText: 'Published books for this component only',
                  onChanged: (value) {
                    line.rateBookId = value;
                    onChanged();
                  },
                ),
                TextFormField(
                  initialValue: '${line.lineNumber}',
                  decoration: const InputDecoration(labelText: 'Line number'),
                  keyboardType: TextInputType.number,
                  onChanged: (value) =>
                      line.lineNumber = int.tryParse(value) ?? line.lineNumber,
                ),
                TextFormField(
                  initialValue: line.originCode,
                  decoration: const InputDecoration(labelText: 'Origin code'),
                  onChanged: (value) =>
                      line.originCode = value.trim().toUpperCase(),
                ),
                TextFormField(
                  initialValue: line.destinationCode,
                  decoration: const InputDecoration(
                    labelText: 'Destination code',
                  ),
                  onChanged: (value) =>
                      line.destinationCode = value.trim().toUpperCase(),
                ),
                _OptionalStringDropdown(
                  label: 'Mode',
                  value: line.mode,
                  values: transportModeValues,
                  onChanged: (value) => line.mode = value,
                ),
                _OptionalStringDropdown(
                  label: 'Equipment',
                  value: line.equipmentType,
                  values: equipmentTypeValues,
                  onChanged: (value) => line.equipmentType = value,
                ),
                _OptionalStringDropdown(
                  label: 'Service level',
                  value: line.serviceLevel,
                  values: serviceLevelValues,
                  onChanged: (value) => line.serviceLevel = value,
                ),
                _OptionalStringDropdown(
                  label: 'Charge context',
                  value: line.chargeContext,
                  values: chargeContextValues,
                  onChanged: (value) => line.chargeContext = value,
                ),
                TextFormField(
                  initialValue: line.commodityCode,
                  decoration: const InputDecoration(
                    labelText: 'Commodity code',
                  ),
                  onChanged: (value) =>
                      line.commodityCode = value.trim().toUpperCase(),
                ),
                TextFormField(
                  initialValue: '${line.priority}',
                  decoration: const InputDecoration(labelText: 'Priority'),
                  keyboardType: TextInputType.number,
                  onChanged: (value) =>
                      line.priority = int.tryParse(value) ?? line.priority,
                ),
                _NullableIdDropdown(
                  label: 'Calculation profile',
                  value: line.calculationProfileId,
                  records: calculationProfiles
                      .where(_hasPublishedVersion)
                      .toList(),
                  nameField: 'profile_name',
                  onChanged: (value) => line.calculationProfileId = value,
                ),
                _NullableIdDropdown(
                  label: 'Allocation profile',
                  value: line.allocationProfileId,
                  records: allocationProfiles
                      .where(_hasPublishedVersion)
                      .toList(),
                  nameField: 'profile_name',
                  onChanged: (value) => line.allocationProfileId = value,
                ),
                _DateInput(
                  label: 'Valid from',
                  value: line.validFrom,
                  onChanged: (value) => line.validFrom = value,
                ),
                _DateInput(
                  label: 'Valid to',
                  value: line.validTo,
                  onChanged: (value) => line.validTo = value,
                ),
              ],
            ),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text('Line is active'),
              value: line.isActive,
              onChanged: (value) {
                line.isActive = value;
                onChanged();
              },
            ),
          ],
        ),
      ),
    );
  }
}

class TransactionQuoteWorkspace extends StatefulWidget {
  const TransactionQuoteWorkspace({
    required this.quotes,
    required this.contracts,
    required this.live,
    required this.client,
    required this.onReload,
    super.key,
  });

  final List<JsonMap> quotes;
  final List<JsonMap> contracts;
  final bool live;
  final LedgerFlowApiClient? client;
  final Future<void> Function() onReload;

  @override
  State<TransactionQuoteWorkspace> createState() =>
      _TransactionQuoteWorkspaceState();
}

class _TransactionQuoteWorkspaceState extends State<TransactionQuoteWorkspace> {
  int _selectedIndex = 0;
  int _selectedOption = 0;
  bool _busy = false;
  JsonMap? _workspace;
  List<JsonMap> _determinedContracts = const [];
  int? _preferredQuoteId;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadWorkspace());
  }

  @override
  void didUpdateWidget(covariant TransactionQuoteWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    final oldSelectedId = oldWidget.quotes.isEmpty
        ? null
        : _asInt(
            oldWidget.quotes[_selectedIndex.clamp(
              0,
              oldWidget.quotes.length - 1,
            )]['id'],
          );
    if (_preferredQuoteId != null) {
      final index = widget.quotes.indexWhere(
        (quote) => _asInt(quote['id']) == _preferredQuoteId,
      );
      if (index >= 0) {
        _selectedIndex = index;
        _preferredQuoteId = null;
      }
    }
    if (_selectedIndex >= widget.quotes.length) {
      _selectedIndex = widget.quotes.isEmpty ? 0 : widget.quotes.length - 1;
    }
    if (oldSelectedId != _selectedQuoteId || oldWidget.live != widget.live) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _loadWorkspace());
    }
  }

  int? get _selectedQuoteId => widget.quotes.isEmpty
      ? null
      : _asInt(
          widget.quotes[_selectedIndex.clamp(
            0,
            widget.quotes.length - 1,
          )]['id'],
        );

  JsonMap? get _listQuote => widget.quotes.isEmpty
      ? null
      : widget.quotes[_selectedIndex.clamp(0, widget.quotes.length - 1)];

  JsonMap? get _quote {
    final nested = _workspace?['quote_request'];
    return nested is Map<String, dynamic> ? JsonMap.from(nested) : _listQuote;
  }

  List<JsonMap> get _options => _rows(_workspace ?? const {}, 'options');
  List<JsonMap> get _commitments =>
      _rows(_workspace ?? const {}, 'commitments');
  List<JsonMap> get _documents =>
      _rows(_workspace ?? const {}, 'charge_documents');

  Future<void> _loadWorkspace() async {
    final id = _selectedQuoteId;
    final client = widget.client;
    if (!widget.live || id == null || client == null) {
      if (mounted) {
        setState(() {
          _workspace = _listQuote;
          _determinedContracts = const [];
        });
      }
      return;
    }
    setState(() {
      _busy = true;
      _determinedContracts = const [];
    });
    try {
      final response = await client.requestJson(
        'GET',
        '/api/v1/charge-management/quote-requests/$id/workspace',
      );
      if (!mounted) return;
      setState(() {
        _workspace = response;
        _selectedOption = _options.isEmpty
            ? 0
            : _selectedOption.clamp(0, _options.length - 1);
      });
    } catch (error) {
      if (mounted) _showError(context, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _editQuote([JsonMap? quote]) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      barrierDismissible: false,
      builder: (_) => QuoteRequestEditorDialog(quote: quote),
    );
    if (payload == null) return;
    final editing = quote != null;
    final result = await _request(
      editing ? 'PUT' : 'POST',
      editing
          ? '/api/v1/charge-management/quote-requests/${quote['id']}/workspace'
          : '/api/v1/charge-management/quote-requests',
      body: payload,
      success: editing ? 'Quote request updated.' : 'Quote request created.',
      reloadWorkspace: false,
    );
    if (result == null) return;
    final created = result['quote_request'] is Map<String, dynamic>
        ? JsonMap.from(result['quote_request'] as Map<String, dynamic>)
        : result;
    _preferredQuoteId = _asInt(created['id']);
    await widget.onReload();
    await _loadWorkspace();
  }

  Future<void> _deleteQuote(JsonMap quote) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(
          'Delete ${_text(quote, 'request_number', fallback: 'quote #${quote['id']}')}?',
        ),
        content: const Text(
          'This permanently deletes the quote request together with its provider offers, rated options, and charge lines. Awarded quotes are retained as audit provenance.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: LedgerFlowDesign.danger,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete quote'),
          ),
        ],
      ),
    );
    if (confirmed != true || widget.client == null) return;
    setState(() => _busy = true);
    try {
      await widget.client!.requestJson(
        'DELETE',
        '/api/v1/charge-management/quote-requests/${quote['id']}',
      );
      if (!mounted) return;
      setState(() {
        _selectedIndex = _selectedIndex > 0 ? _selectedIndex - 1 : 0;
        _selectedOption = 0;
        _preferredQuoteId = null;
        _workspace = null;
        _determinedContracts = const [];
      });
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Quote request deleted.')));
      await widget.onReload();
    } catch (error) {
      if (mounted) _showError(context, error);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<JsonMap?> _request(
    String method,
    String path, {
    JsonMap? body,
    required String success,
    bool reloadWorkspace = true,
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
      if (reloadWorkspace) {
        await widget.onReload();
        await _loadWorkspace();
      }
      return response;
    } catch (error) {
      if (mounted) _showError(context, error);
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submitQuote(JsonMap quote) async {
    await _request(
      'PUT',
      '/api/v1/charge-management/quote-requests/${quote['id']}/workspace',
      body: {'status': 'REQUESTED'},
      success: 'Quote request submitted.',
    );
  }

  Future<void> _determineContracts(JsonMap quote) async {
    final response = await _request(
      'POST',
      '/api/v1/charge-management/quote-requests/${quote['id']}/determine-contracts',
      success: 'Contract determination completed.',
      reloadWorkspace: false,
    );
    if (response == null || !mounted) return;
    setState(() {
      _determinedContracts = [
        ..._rows(response, 'payer_contracts'),
        ..._rows(response, 'payee_contracts'),
      ];
    });
  }

  Future<void> _rate(JsonMap quote) async {
    final response = await _request(
      'POST',
      '/api/v1/charge-management/quote-requests/${quote['id']}/rate',
      success: 'Quote rated and charge lines generated.',
      reloadWorkspace: false,
    );
    if (response == null) return;
    await widget.onReload();
    await _loadWorkspace();
  }

  Future<void> _rank(JsonMap quote) async {
    await _request(
      'POST',
      '/api/v1/charge-management/quote-requests/${quote['id']}/rank',
      success: 'Quote options ranked.',
    );
  }

  Future<void> _award(JsonMap quote, JsonMap option) async {
    await _request(
      'POST',
      '/api/v1/charge-management/quote-requests/${quote['id']}/award',
      body: {'quote_option_id': option['id']},
      success: 'Quote awarded and charge document created.',
    );
  }

  @override
  Widget build(BuildContext context) {
    final quote = _quote;
    final createButton = FilledButton.icon(
      onPressed: widget.live && !_busy ? () => _editQuote() : null,
      icon: const Icon(Icons.add),
      label: const Text('New request'),
    );
    if (quote == null) {
      return PageCanvas(
        title: 'Quotes',
        subtitle:
            'Submit caller shipment context, match contracts, and inspect generated charge lines.',
        trailing: createButton,
        children: const [
          SurfaceCard(
            child: EmptyState(
              message:
                  'No quote requests exist. Create or import a test request.',
            ),
          ),
        ],
      );
    }
    final status = _text(quote, 'status', fallback: 'DRAFT');
    final canDelete =
        status.toUpperCase() != 'AWARDED' &&
        _commitments.isEmpty &&
        _documents.isEmpty;
    final options = _options;
    final option = options.isEmpty
        ? null
        : options[_selectedOption.clamp(0, options.length - 1)];
    final lines = option == null ? const <JsonMap>[] : _rows(option, 'lines');
    final matchedContracts = _realMatchedContracts(options);
    return PageCanvas(
      title:
          '${_text(quote, 'origin_code', fallback: 'Any origin')} → ${_text(quote, 'destination_code', fallback: 'Any destination')}',
      eyebrow:
          'Quotes / ${_text(quote, 'request_number', fallback: '#${quote['id']}')}',
      subtitle:
          '${_text(quote, 'mode', fallback: 'Any mode')} · ${_partySummary(quote)} · ${_text(quote, 'requested_service_date', fallback: 'No service date')}',
      trailing: Wrap(
        spacing: 10,
        runSpacing: 8,
        children: [
          OutlinedButton.icon(
            onPressed: widget.live && !_busy && status == 'DRAFT'
                ? () => _editQuote(quote)
                : null,
            icon: const Icon(Icons.edit_outlined),
            label: const Text('Edit request'),
          ),
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: LedgerFlowDesign.danger,
            ),
            onPressed: widget.live && !_busy && canDelete
                ? () => _deleteQuote(quote)
                : null,
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete'),
          ),
          createButton,
        ],
      ),
      children: [
        TransactionRecordList(
          records: widget.quotes,
          selectedIndex: _selectedIndex,
          searchHint: 'Search request, lane, mode, or party',
          emptyMessage: 'No quote requests are available.',
          searchText: (row) => [
            _text(row, 'request_number'),
            _text(row, 'origin_code'),
            _text(row, 'destination_code'),
            _text(row, 'mode'),
            _text(row, 'status'),
            _partySummary(row),
          ].join(' '),
          status: (row) => _text(row, 'status'),
          columns: [
            TransactionListColumn(
              label: 'Request',
              flex: 2,
              value: (row) =>
                  _text(row, 'request_number', fallback: '#${row['id']}'),
            ),
            TransactionListColumn(
              label: 'Lane',
              flex: 2,
              value: (row) =>
                  '${_text(row, 'origin_code', fallback: 'Any')} -> ${_text(row, 'destination_code', fallback: 'Any')}',
            ),
            TransactionListColumn(
              label: 'Mode',
              value: (row) => _text(row, 'mode', fallback: 'Any'),
            ),
            TransactionListColumn(
              label: 'Service date',
              value: (row) =>
                  _text(row, 'requested_service_date', fallback: 'Not set'),
            ),
            TransactionListColumn(
              label: 'Status',
              value: (row) => _text(row, 'status'),
              isStatus: true,
            ),
          ],
          onSelected: (index) {
            setState(() {
              _selectedIndex = index;
              _selectedOption = 0;
              _workspace = null;
              _determinedContracts = const [];
            });
            _loadWorkspace();
          },
        ),
        const SizedBox(height: 16),
        _QuoteLifecycleActions(
          status: status,
          busy: _busy,
          hasOptions: options.isNotEmpty,
          onSubmit: () => _submitQuote(quote),
          onDetermine: () => _determineContracts(quote),
          onRate: () => _rate(quote),
          onRank: () => _rank(quote),
          onAward: option == null ? null : () => _award(quote, option),
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
                            'Real options returned by the quote workspace endpoint',
                      ),
                    ),
                    if (_busy && _workspace == null)
                      const Padding(
                        padding: EdgeInsets.all(28),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (options.isEmpty)
                      const EmptyState(
                        message:
                            'No charge options yet. Submit the request, verify matched contracts, then rate it.',
                      )
                    else
                      _OptionPicker(
                        options: options,
                        selectedIndex: _selectedOption,
                        onSelected: (index) =>
                            setState(() => _selectedOption = index),
                      ),
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
                        title: 'Charge lines',
                        subtitle: option == null
                            ? 'Rate the request to generate charges'
                            : 'Calculation result with exact source provenance',
                      ),
                    ),
                    _RatedChargeLineTable(lines: lines),
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
                    SectionHeading(
                      title: 'Request details',
                      action: StatusPill(status),
                    ),
                    const SizedBox(height: 10),
                    DetailRow(label: 'Bindings', value: _partySummary(quote)),
                    DetailRow(
                      label: 'Equipment',
                      value: _text(quote, 'equipment_type', fallback: 'Any'),
                    ),
                    DetailRow(
                      label: 'Service',
                      value: _text(quote, 'service_level', fallback: 'Any'),
                    ),
                    DetailRow(
                      label: 'Weight',
                      value: _text(
                        quote,
                        'gross_weight',
                        fallback: 'Not supplied',
                      ),
                    ),
                    DetailRow(
                      label: 'Containers',
                      value: _text(
                        quote,
                        'container_count',
                        fallback: 'Not supplied',
                      ),
                    ),
                    DetailRow(
                      label: 'Dates',
                      value:
                          '${_rows(quote, 'date_values').length} typed values',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              SurfaceCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeading(
                      title: 'Matched contracts',
                      subtitle:
                          'Backend determination, never demo placeholders',
                    ),
                    const SizedBox(height: 10),
                    if (matchedContracts.isEmpty)
                      const Text(
                        'Run Determine contracts or Rate to see the selected commercial configuration.',
                        style: TextStyle(color: LedgerFlowDesign.muted),
                      )
                    else
                      ...matchedContracts.map(_MatchedContractCard.new),
                  ],
                ),
              ),
              if (_documents.isNotEmpty) ...[
                const SizedBox(height: 16),
                SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeading(title: 'Awarded documents'),
                      const SizedBox(height: 10),
                      ..._documents.map(
                        (document) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.description_outlined),
                          title: Text(_text(document, 'document_number')),
                          subtitle: Text(_text(document, 'status')),
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

  List<JsonMap> _realMatchedContracts(List<JsonMap> options) {
    if (_determinedContracts.isNotEmpty) return _determinedContracts;
    final ids = <int>{};
    for (final option in options) {
      for (final key in ['payer_contract_id', 'payee_contract_id']) {
        final id = _asInt(option[key]);
        if (id != null) ids.add(id);
      }
    }
    return widget.contracts
        .where((contract) => ids.contains(_asInt(contract['id'])))
        .toList(growable: false);
  }
}

class QuoteRequestEditorDialog extends StatefulWidget {
  const QuoteRequestEditorDialog({this.quote, super.key});

  final JsonMap? quote;

  @override
  State<QuoteRequestEditorDialog> createState() =>
      _QuoteRequestEditorDialogState();
}

class _QuoteRequestEditorDialogState extends State<QuoteRequestEditorDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _requestNumber;
  late final TextEditingController _sourceType;
  late final TextEditingController _sourceId;
  late final TextEditingController _companyId;
  late final TextEditingController _customerId;
  late final TextEditingController _vendorId;
  late final TextEditingController _forwarderId;
  late final TextEditingController _carrierId;
  late final TextEditingController _payerRef;
  late final TextEditingController _payeeRef;
  late final TextEditingController _origin;
  late final TextEditingController _destination;
  late final TextEditingController _commodity;
  late final TextEditingController _quantity;
  late final TextEditingController _grossWeight;
  late final TextEditingController _chargeableWeight;
  late final TextEditingController _volume;
  late final TextEditingController _containers;
  late final TextEditingController _packages;
  late final TextEditingController _contextJson;
  late final TextEditingController _calculationInputsJson;
  late final TextEditingController _componentInputsJson;
  late String _mode;
  late String _equipment;
  late String _serviceLevel;
  late String _currency;
  late String _chargeContext;
  late String _serviceDate;
  late List<_DateValueDraft> _dateValues;
  String? _importError;

  @override
  void initState() {
    super.initState();
    final row = widget.quote ?? const <String, dynamic>{};
    _requestNumber = TextEditingController(text: _text(row, 'request_number'));
    _sourceType = TextEditingController(
      text: _text(row, 'source_object_type', fallback: 'MANUAL'),
    );
    _sourceId = TextEditingController(text: _text(row, 'source_object_id'));
    _companyId = TextEditingController(text: _text(row, 'company_id'));
    _customerId = TextEditingController(text: _text(row, 'customer_id'));
    _vendorId = TextEditingController(text: _text(row, 'vendor_id'));
    _forwarderId = TextEditingController(text: _text(row, 'forwarder_id'));
    _carrierId = TextEditingController(text: _text(row, 'carrier_id'));
    _payerRef = TextEditingController(text: _text(row, 'payer_party_ref'));
    _payeeRef = TextEditingController(text: _text(row, 'payee_party_ref'));
    _origin = TextEditingController(text: _text(row, 'origin_code'));
    _destination = TextEditingController(text: _text(row, 'destination_code'));
    _commodity = TextEditingController(text: _text(row, 'commodity_code'));
    _quantity = TextEditingController(
      text: _text(row, 'quantity', fallback: '1'),
    );
    _grossWeight = TextEditingController(text: _text(row, 'gross_weight'));
    _chargeableWeight = TextEditingController(
      text: _text(row, 'chargeable_weight'),
    );
    _volume = TextEditingController(text: _text(row, 'gross_volume_cbm'));
    _containers = TextEditingController(text: _text(row, 'container_count'));
    _packages = TextEditingController(text: _text(row, 'package_count'));
    _contextJson = TextEditingController(
      text: _prettyJson(row['context'] ?? const <String, dynamic>{}),
    );
    _calculationInputsJson = TextEditingController(
      text: _prettyJson(row['calculation_inputs'] ?? const <String, dynamic>{}),
    );
    _componentInputsJson = TextEditingController(
      text: _prettyJson(
        row['component_calculation_inputs'] ?? const <String, dynamic>{},
      ),
    );
    _mode = _text(row, 'mode', fallback: 'ROAD');
    _equipment = _text(row, 'equipment_type');
    _serviceLevel = _text(row, 'service_level');
    _currency = _text(row, 'currency', fallback: 'EUR');
    _chargeContext = _text(row, 'charge_context', fallback: 'ROAD');
    _serviceDate = _text(row, 'requested_service_date');
    _dateValues = _rows(
      row,
      'date_values',
    ).map(_DateValueDraft.fromJson).toList();
  }

  @override
  void dispose() {
    for (final controller in [
      _requestNumber,
      _sourceType,
      _sourceId,
      _companyId,
      _customerId,
      _vendorId,
      _forwarderId,
      _carrierId,
      _payerRef,
      _payeeRef,
      _origin,
      _destination,
      _commodity,
      _quantity,
      _grossWeight,
      _chargeableWeight,
      _volume,
      _containers,
      _packages,
      _contextJson,
      _calculationInputsJson,
      _componentInputsJson,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _importRequest() async {
    final selection = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['json'],
      withData: true,
    );
    if (selection == null || selection.files.single.bytes == null) return;
    try {
      final decoded = jsonDecode(utf8.decode(selection.files.single.bytes!));
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('The file must contain one JSON object.');
      }
      _applyImported(JsonMap.from(decoded));
      setState(() => _importError = null);
    } catch (error) {
      setState(() => _importError = 'Could not import JSON: $error');
    }
  }

  void _applyImported(JsonMap row) {
    _requestNumber.text = _text(row, 'request_number');
    _sourceType.text = _text(row, 'source_object_type', fallback: 'MANUAL');
    _sourceId.text = _text(row, 'source_object_id');
    _companyId.text = _text(row, 'company_id');
    _customerId.text = _text(row, 'customer_id');
    _vendorId.text = _text(row, 'vendor_id');
    _forwarderId.text = _text(row, 'forwarder_id');
    _carrierId.text = _text(row, 'carrier_id');
    _origin.text = _text(row, 'origin_code');
    _destination.text = _text(row, 'destination_code');
    _commodity.text = _text(row, 'commodity_code');
    _quantity.text = _text(row, 'quantity', fallback: '1');
    _grossWeight.text = _text(row, 'gross_weight');
    _chargeableWeight.text = _text(row, 'chargeable_weight');
    _volume.text = _text(row, 'gross_volume_cbm');
    _containers.text = _text(row, 'container_count');
    _packages.text = _text(row, 'package_count');
    _contextJson.text = _prettyJson(
      row['context'] ?? const <String, dynamic>{},
    );
    _calculationInputsJson.text = _prettyJson(
      row['calculation_inputs'] ?? const <String, dynamic>{},
    );
    _componentInputsJson.text = _prettyJson(
      row['component_calculation_inputs'] ?? const <String, dynamic>{},
    );
    _mode = _text(row, 'mode', fallback: 'ROAD');
    _equipment = _text(row, 'equipment_type');
    _serviceLevel = _text(row, 'service_level');
    _currency = _text(row, 'currency', fallback: 'EUR');
    _chargeContext = _text(row, 'charge_context', fallback: 'ROAD');
    _serviceDate = _text(row, 'requested_service_date');
    _dateValues = _rows(
      row,
      'date_values',
    ).map(_DateValueDraft.fromJson).toList();
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    try {
      final contextJson = _decodeObject(_contextJson.text, 'Context');
      final calculationInputs = _decodeObject(
        _calculationInputsJson.text,
        'Calculation inputs',
      );
      final componentInputs = _decodeObject(
        _componentInputsJson.text,
        'Component inputs',
      );
      final payload = <String, dynamic>{
        'request_number': _nullIfEmpty(_requestNumber.text),
        'source_object_type': _sourceType.text.trim().toUpperCase(),
        'source_object_id': _nullIfEmpty(_sourceId.text),
        'company_id': _optionalInt(_companyId.text),
        'customer_id': _optionalInt(_customerId.text),
        'vendor_id': _optionalInt(_vendorId.text),
        'forwarder_id': _optionalInt(_forwarderId.text),
        'carrier_id': _optionalInt(_carrierId.text),
        'origin_code': _nullIfEmpty(_origin.text.toUpperCase()),
        'destination_code': _nullIfEmpty(_destination.text.toUpperCase()),
        'mode': _nullIfEmpty(_mode),
        'equipment_type': _nullIfEmpty(_equipment),
        'commodity_code': _nullIfEmpty(_commodity.text.toUpperCase()),
        'service_level': _nullIfEmpty(_serviceLevel),
        'currency': _currency,
        'quantity': _decimalOrDefault(_quantity.text, '1'),
        'gross_weight': _decimalOrNull(_grossWeight.text),
        'chargeable_weight': _decimalOrNull(_chargeableWeight.text),
        'gross_volume_cbm': _decimalOrNull(_volume.text),
        'container_count': _decimalOrNull(_containers.text),
        'package_count': _decimalOrNull(_packages.text),
        'requested_service_date': _nullIfEmpty(_serviceDate),
        'charge_context': _nullIfEmpty(_chargeContext),
        'context': contextJson,
        'calculation_inputs': calculationInputs,
        'component_calculation_inputs': componentInputs,
        'date_values': _dateValues.map((value) => value.toJson()).toList(),
      };
      Navigator.pop(context, JsonMap.from(payload));
    } catch (error) {
      setState(() => _importError = error.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Row(
        children: [
          Expanded(
            child: Text(
              widget.quote == null ? 'New quote request' : 'Edit quote request',
            ),
          ),
          OutlinedButton.icon(
            onPressed: _importRequest,
            icon: const Icon(Icons.upload_file_outlined),
            label: const Text('Upload JSON'),
          ),
        ],
      ),
      content: SizedBox(
        width: 1120,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_importError != null) ...[
                  Text(
                    _importError!,
                    style: const TextStyle(color: LedgerFlowDesign.danger),
                  ),
                  const SizedBox(height: 12),
                ],
                const Text(
                  'Caller reference and party',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                const Text(
                  'The quote request can bind to any combination of caller IDs. Importing JSON keeps all populated IDs.',
                  style: TextStyle(color: LedgerFlowDesign.muted),
                ),
                const SizedBox(height: 12),
                _PartyBindingFields(
                  companyController: _companyId,
                  customerController: _customerId,
                  vendorController: _vendorId,
                  forwarderController: _forwarderId,
                  carrierController: _carrierId,
                ),
                const SizedBox(height: 12),
                _FormGrid(
                  children: [
                    TextFormField(
                      controller: _requestNumber,
                      decoration: const InputDecoration(
                        labelText: 'Request number',
                        helperText:
                            'Optional; LedgerFlow generates one when blank',
                      ),
                    ),
                    TextFormField(
                      controller: _sourceType,
                      decoration: const InputDecoration(
                        labelText: 'Source object type',
                        helperText:
                            'Caller-owned object type, not a profile code',
                      ),
                      validator: (value) =>
                          _required(value, 'Source object type'),
                    ),
                    TextFormField(
                      controller: _sourceId,
                      decoration: const InputDecoration(
                        labelText: 'Source object ID',
                      ),
                    ),
                    TextFormField(
                      controller: _payerRef,
                      decoration: const InputDecoration(
                        labelText: 'Payer reference',
                      ),
                    ),
                    TextFormField(
                      controller: _payeeRef,
                      decoration: const InputDecoration(
                        labelText: 'Payee reference',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                const Text(
                  'Applicability',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                _FormGrid(
                  children: [
                    TextFormField(
                      controller: _origin,
                      decoration: const InputDecoration(
                        labelText: 'Origin code',
                      ),
                    ),
                    TextFormField(
                      controller: _destination,
                      decoration: const InputDecoration(
                        labelText: 'Destination code',
                      ),
                    ),
                    _OptionalStringDropdown(
                      label: 'Mode',
                      value: _mode,
                      values: transportModeValues,
                      allowEmpty: false,
                      onChanged: (value) => setState(() => _mode = value),
                    ),
                    _OptionalStringDropdown(
                      label: 'Equipment',
                      value: _equipment,
                      values: equipmentTypeValues,
                      onChanged: (value) => setState(() => _equipment = value),
                    ),
                    _OptionalStringDropdown(
                      label: 'Service level',
                      value: _serviceLevel,
                      values: serviceLevelValues,
                      onChanged: (value) =>
                          setState(() => _serviceLevel = value),
                    ),
                    TextFormField(
                      controller: _commodity,
                      decoration: const InputDecoration(
                        labelText: 'Commodity code',
                      ),
                    ),
                    _OptionalStringDropdown(
                      label: 'Charge context',
                      value: _chargeContext,
                      values: chargeContextValues,
                      allowEmpty: false,
                      onChanged: (value) =>
                          setState(() => _chargeContext = value),
                    ),
                    DropdownButtonFormField<String>(
                      initialValue: _currency,
                      decoration: const InputDecoration(
                        labelText: 'Result currency',
                      ),
                      items:
                          referenceValuesWithCurrent(currencyValues, _currency)
                              .map(
                                (value) => DropdownMenuItem(
                                  value: value,
                                  child: Text(value),
                                ),
                              )
                              .toList(),
                      onChanged: (value) =>
                          setState(() => _currency = value ?? _currency),
                    ),
                    _DateInput(
                      label: 'Requested service date',
                      value: _serviceDate,
                      onChanged: (value) =>
                          setState(() => _serviceDate = value),
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                const Text(
                  'Calculation quantities',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 12),
                _FormGrid(
                  children: [
                    _DecimalInput(controller: _quantity, label: 'Quantity'),
                    _DecimalInput(
                      controller: _grossWeight,
                      label: 'Gross weight',
                    ),
                    _DecimalInput(
                      controller: _chargeableWeight,
                      label: 'Chargeable weight',
                    ),
                    _DecimalInput(controller: _volume, label: 'Volume CBM'),
                    _DecimalInput(
                      controller: _containers,
                      label: 'Container count',
                    ),
                    _DecimalInput(
                      controller: _packages,
                      label: 'Package count',
                    ),
                  ],
                ),
                const SizedBox(height: 22),
                Row(
                  children: [
                    const Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Typed operational dates',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          Text(
                            'Business-date profiles evaluate these identifiers in configured priority order.',
                            style: TextStyle(color: LedgerFlowDesign.muted),
                          ),
                        ],
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () =>
                          setState(() => _dateValues.add(_DateValueDraft())),
                      icon: const Icon(Icons.add),
                      label: const Text('Add date'),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                ...List.generate(_dateValues.length, (index) {
                  final value = _dateValues[index];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String>(
                            isExpanded: true,
                            initialValue: value.dateType.isEmpty
                                ? null
                                : value.dateType,
                            decoration: const InputDecoration(
                              labelText: 'Date identifier',
                            ),
                            items: businessDateTypeValues
                                .map(
                                  (item) => DropdownMenuItem(
                                    value: item,
                                    child: Text(
                                      item,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                )
                                .toList(),
                            validator: (selected) =>
                                _required(selected, 'Date identifier'),
                            onChanged: (selected) =>
                                value.dateType = selected ?? '',
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _DateInput(
                            label: 'Date value',
                            value: value.dateValue,
                            requiredValue: true,
                            onChanged: (selected) => value.dateValue = selected,
                          ),
                        ),
                        IconButton(
                          tooltip: 'Remove date',
                          onPressed: () =>
                              setState(() => _dateValues.removeAt(index)),
                          icon: const Icon(Icons.delete_outline),
                        ),
                      ],
                    ),
                  );
                }),
                const SizedBox(height: 16),
                Material(
                  type: MaterialType.transparency,
                  child: ExpansionTile(
                    tilePadding: EdgeInsets.zero,
                    title: const Text('Advanced calculation inputs'),
                    subtitle: const Text(
                      'Use factor codes such as DISTANCE_KM, STOP_COUNT, PALLET_COUNT, or component-specific overrides.',
                    ),
                    children: [
                      TextFormField(
                        controller: _calculationInputsJson,
                        minLines: 3,
                        maxLines: 8,
                        decoration: const InputDecoration(
                          labelText: 'Global calculation inputs (JSON)',
                          helperText: 'Example: {"DISTANCE_KM": 480}',
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextFormField(
                        controller: _componentInputsJson,
                        minLines: 3,
                        maxLines: 8,
                        decoration: const InputDecoration(
                          labelText: 'Component calculation inputs (JSON)',
                          helperText:
                              'Example: {"ROAD_TOLL": {"DISTANCE_KM": 480}}',
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextFormField(
                        controller: _contextJson,
                        minLines: 3,
                        maxLines: 8,
                        decoration: const InputDecoration(
                          labelText: 'Matching and precondition context (JSON)',
                          helperText:
                              'Percentage bases, duration, and template precondition flags',
                        ),
                      ),
                    ],
                  ),
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
        FilledButton(
          onPressed: _submit,
          child: Text(widget.quote == null ? 'Create request' : 'Save request'),
        ),
      ],
    );
  }
}

class _DateValueDraft {
  _DateValueDraft({this.dateType = '', this.dateValue = ''});

  factory _DateValueDraft.fromJson(JsonMap row) => _DateValueDraft(
    dateType: _text(row, 'date_type'),
    dateValue: _text(row, 'date_value'),
  );

  String dateType;
  String dateValue;

  JsonMap toJson() => {'date_type': dateType, 'date_value': dateValue};
}

class _QuoteLifecycleActions extends StatelessWidget {
  const _QuoteLifecycleActions({
    required this.status,
    required this.busy,
    required this.hasOptions,
    required this.onSubmit,
    required this.onDetermine,
    required this.onRate,
    required this.onRank,
    required this.onAward,
  });

  final String status;
  final bool busy;
  final bool hasOptions;
  final VoidCallback onSubmit;
  final VoidCallback onDetermine;
  final VoidCallback onRate;
  final VoidCallback onRank;
  final VoidCallback? onAward;

  @override
  Widget build(BuildContext context) {
    final normalized = status.toUpperCase();
    final isAwarded = normalized == 'AWARDED';
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SectionHeading(
            title: 'Rating lifecycle',
            subtitle:
                'Each action calls the corresponding public API endpoint.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              FilledButton.icon(
                onPressed: !busy && normalized == 'DRAFT' ? onSubmit : null,
                icon: const Icon(Icons.send_outlined),
                label: const Text('Submit request'),
              ),
              OutlinedButton.icon(
                onPressed:
                    !busy &&
                        {'REQUESTED', 'RATED', 'RANKED'}.contains(normalized)
                    ? onDetermine
                    : null,
                icon: const Icon(Icons.manage_search_outlined),
                label: const Text('Determine contracts'),
              ),
              FilledButton.tonalIcon(
                onPressed:
                    !busy &&
                        {'REQUESTED', 'RATED', 'RANKED'}.contains(normalized)
                    ? onRate
                    : null,
                icon: const Icon(Icons.calculate_outlined),
                label: const Text('Rate charges'),
              ),
              OutlinedButton.icon(
                onPressed: !busy && hasOptions && !isAwarded ? onRank : null,
                icon: const Icon(Icons.leaderboard_outlined),
                label: const Text('Rank options'),
              ),
              FilledButton.icon(
                onPressed: !busy && onAward != null && normalized != 'AWARDED'
                    ? onAward
                    : null,
                icon: const Icon(Icons.workspace_premium_outlined),
                label: const Text('Award selected'),
              ),
              if (busy)
                const Padding(
                  padding: EdgeInsets.all(8),
                  child: SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _OptionPicker extends StatelessWidget {
  const _OptionPicker({
    required this.options,
    required this.selectedIndex,
    required this.onSelected,
  });

  final List<JsonMap> options;
  final int selectedIndex;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
      child: Row(
        children: List.generate(options.length, (index) {
          final option = options[index];
          final selected = index == selectedIndex;
          return Padding(
            padding: const EdgeInsets.only(right: 10),
            child: InkWell(
              onTap: () => onSelected(index),
              borderRadius: BorderRadius.circular(12),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                width: 230,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: selected
                      ? LedgerFlowDesign.teal.withValues(alpha: 0.08)
                      : Colors.white,
                  border: Border.all(
                    color: selected
                        ? LedgerFlowDesign.teal
                        : LedgerFlowDesign.border,
                  ),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _text(
                        option,
                        'option_name',
                        fallback: 'Option ${index + 1}',
                      ),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '${_text(option, 'payee_total_amount', fallback: '0')} total',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Margin ${_text(option, 'margin_amount', fallback: '0')} · Rank ${_text(option, 'rank', fallback: '—')}',
                      style: const TextStyle(
                        fontSize: 12,
                        color: LedgerFlowDesign.muted,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _RatedChargeLineTable extends StatelessWidget {
  const _RatedChargeLineTable({required this.lines});

  final List<JsonMap> lines;

  @override
  Widget build(BuildContext context) {
    if (lines.isEmpty) {
      return const EmptyState(message: 'No calculated charge lines available.');
    }
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        columns: const [
          DataColumn(label: Text('Role / output')),
          DataColumn(label: Text('Component')),
          DataColumn(label: Text('Basis')),
          DataColumn(label: Text('Quantity')),
          DataColumn(label: Text('Amount')),
          DataColumn(label: Text('Contract / source')),
          DataColumn(label: Text('Rate source')),
          DataColumn(label: Text('Template step')),
        ],
        rows: lines
            .map((line) {
              final contractId = _text(
                line,
                'source_contract_id',
                fallback: '-',
              );
              final routeId = _asInt(line['source_contract_template_route_id']);
              final contractLineId = _asInt(line['source_contract_line_id']);
              final contractSource = routeId != null
                  ? '$contractId / route $routeId'
                  : contractLineId != null
                  ? '$contractId / line $contractLineId'
                  : '$contractId / header template';
              return DataRow(
                cells: [
                  DataCell(
                    Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      children: [
                        StatusPill(_text(line, 'relationship_role')),
                        if (line['is_statistical'] == true)
                          const StatusPill('STATISTICAL'),
                      ],
                    ),
                  ),
                  DataCell(Text(_text(line, 'charge_component_code'))),
                  DataCell(Text(_text(line, 'basis'))),
                  DataCell(Text(_text(line, 'quantity', fallback: '1'))),
                  DataCell(
                    Text(
                      '${_text(line, 'currency')} ${_text(line, 'amount')}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                  DataCell(Text(contractSource)),
                  DataCell(
                    Text(
                      'Book ${_text(line, 'source_rate_book_id', fallback: '—')} · row ${_text(line, 'source_rate_book_entry_id', fallback: '—')}',
                    ),
                  ),
                  DataCell(
                    Text(
                      '${_text(line, 'source_calculation_template_id', fallback: '—')} / ${_text(line, 'source_calculation_template_step_id', fallback: '—')}',
                    ),
                  ),
                ],
              );
            })
            .toList(growable: false),
      ),
    );
  }
}

class _MatchedContractCard extends StatelessWidget {
  const _MatchedContractCard(this.contract);

  final JsonMap contract;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        border: Border.all(color: LedgerFlowDesign.border),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  _text(contract, 'contract_number'),
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ),
              StatusPill(_text(contract, 'contract_role')),
            ],
          ),
          const SizedBox(height: 5),
          Text(
            '${_partySummary(contract)} · ${_rows(contract, 'lines').length} lines',
            style: const TextStyle(color: LedgerFlowDesign.muted, fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _HorizontalRecordPicker extends StatelessWidget {
  const _HorizontalRecordPicker({
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
      height: 70,
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
              duration: const Duration(milliseconds: 150),
              width: 220,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: selected
                    ? LedgerFlowDesign.teal.withValues(alpha: 0.09)
                    : Colors.white,
                border: Border.all(
                  color: selected
                      ? LedgerFlowDesign.teal
                      : LedgerFlowDesign.border,
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    label(records[index]),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    detail(records[index]),
                    maxLines: 1,
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

class _FormGrid extends StatelessWidget {
  const _FormGrid({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth < 760
            ? constraints.maxWidth
            : (constraints.maxWidth - 12) / 2;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: children
              .map((child) => SizedBox(width: width, child: child))
              .toList(),
        );
      },
    );
  }
}

class _NullableIdDropdown extends StatelessWidget {
  const _NullableIdDropdown({
    required this.label,
    required this.value,
    required this.records,
    required this.nameField,
    required this.onChanged,
    this.helperText,
  });

  final String label;
  final int? value;
  final List<JsonMap> records;
  final String nameField;
  final String? helperText;
  final ValueChanged<int?> onChanged;

  @override
  Widget build(BuildContext context) {
    final options = records
        .where((row) => _asInt(row['id']) != null)
        .toList(growable: false);
    final safeValue = options.any((row) => _asInt(row['id']) == value)
        ? value
        : null;
    return DropdownButtonFormField<int?>(
      initialValue: safeValue,
      isExpanded: true,
      decoration: InputDecoration(labelText: label, helperText: helperText),
      items: [
        const DropdownMenuItem<int?>(
          value: null,
          child: Text('Inherit / none'),
        ),
        ...options.map(
          (row) => DropdownMenuItem<int?>(
            value: _asInt(row['id']),
            child: Text(
              _recordLabel(row, nameField, _codeFieldForName(nameField)),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
      ],
      onChanged: onChanged,
    );
  }
}

class _OptionalStringDropdown extends StatelessWidget {
  const _OptionalStringDropdown({
    required this.label,
    required this.value,
    required this.values,
    required this.onChanged,
    this.allowEmpty = true,
  });

  final String label;
  final String value;
  final List<String> values;
  final ValueChanged<String> onChanged;
  final bool allowEmpty;

  @override
  Widget build(BuildContext context) {
    final options = referenceValuesWithCurrent(values, value);
    final safeValue = value.isEmpty ? (allowEmpty ? '' : options.first) : value;
    return DropdownButtonFormField<String>(
      initialValue: safeValue,
      isExpanded: true,
      decoration: InputDecoration(labelText: label),
      items: [
        if (allowEmpty)
          const DropdownMenuItem(value: '', child: Text('Any / inherit')),
        ...options.map(
          (item) => DropdownMenuItem(value: item, child: Text(item)),
        ),
      ],
      onChanged: (selected) => onChanged(selected ?? ''),
    );
  }
}

class _DateInput extends StatefulWidget {
  const _DateInput({
    required this.label,
    required this.value,
    required this.onChanged,
    this.requiredValue = false,
  });

  final String label;
  final String value;
  final ValueChanged<String> onChanged;
  final bool requiredValue;

  @override
  State<_DateInput> createState() => _DateInputState();
}

class _DateInputState extends State<_DateInput> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.value);
  }

  @override
  void didUpdateWidget(covariant _DateInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.value != _controller.text) _controller.text = widget.value;
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _pick() async {
    final current = DateTime.tryParse(_controller.text);
    final selected = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (selected == null) return;
    final value = selected.toIso8601String().substring(0, 10);
    _controller.text = value;
    widget.onChanged(value);
  }

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: _controller,
      readOnly: true,
      decoration: InputDecoration(
        labelText: widget.label,
        suffixIcon: IconButton(
          tooltip: 'Choose date',
          onPressed: _pick,
          icon: const Icon(Icons.calendar_today_outlined),
        ),
      ),
      validator: widget.requiredValue
          ? (value) => _required(value, widget.label)
          : null,
      onTap: _pick,
    );
  }
}

class _DecimalInput extends StatelessWidget {
  const _DecimalInput({required this.controller, required this.label});

  final TextEditingController controller;
  final String label;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      decoration: InputDecoration(labelText: label),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      validator: (value) {
        if ((value ?? '').trim().isEmpty) return null;
        return num.tryParse(value!.trim()) == null ? 'Enter a number' : null;
      },
    );
  }
}

const businessDateTypeValues = <String>[
  'DOCUMENT_DATE',
  'MANUAL_LINE_DATE',
  'SHIPPED_ON_BOARD_DATE',
  'SHIPMENT_ACTUAL_DEPARTURE_DATE',
  'SHIPMENT_PLANNED_DEPARTURE_DATE',
  'SHIPMENT_ARRIVAL_DATE',
  'HOUSE_BILL_ISSUE_DATE',
  'ACTUAL_FLIGHT_DEPARTURE_DATE',
  'AWB_EXECUTION_DATE',
  'ESTIMATED_FLIGHT_DEPARTURE_DATE',
  'ROAD_ACTUAL_PICKUP_DATE',
  'ROAD_PLANNED_PICKUP_DATE',
  'ROAD_ACTUAL_DELIVERY_DATE',
  'ROAD_PLANNED_DELIVERY_DATE',
  'CMR_ISSUE_DATE',
];

List<JsonMap> _rows(JsonMap row, String key) {
  final value = row[key];
  if (value is! List) return const [];
  return value
      .whereType<Map<String, dynamic>>()
      .map(JsonMap.from)
      .toList(growable: false);
}

String _text(JsonMap row, String key, {String fallback = ''}) {
  final value = row[key];
  if (value == null || value.toString().trim().isEmpty) return fallback;
  return value.toString();
}

int? _asInt(dynamic value) => switch (value) {
  int number => number,
  num number => number.toInt(),
  String text => int.tryParse(text),
  _ => null,
};

String? _nullIfEmpty(String value) {
  final trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

String? _required(String? value, String label) =>
    (value ?? '').trim().isEmpty ? '$label is required' : null;

String? _decimalOrNull(String value) {
  final trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

String _decimalOrDefault(String value, String fallback) =>
    value.trim().isEmpty ? fallback : value.trim();

JsonMap _decodeObject(String source, String label) {
  if (source.trim().isEmpty) return {};
  final value = jsonDecode(source);
  if (value is! Map<String, dynamic>) {
    throw FormatException('$label must be a JSON object.');
  }
  return JsonMap.from(value);
}

String _prettyJson(dynamic value) {
  if (value is! Map) return '{}';
  return const JsonEncoder.withIndent('  ').convert(value);
}

bool _isPublished(JsonMap row) =>
    _text(row, 'status').toUpperCase() == 'PUBLISHED' &&
    row['is_active'] != false;

bool _hasPublishedVersion(JsonMap row) =>
    row['published_version_id'] != null ||
    _rows(row, 'versions').any(_isPublished);

String _lookupName(List<JsonMap> records, dynamic id, String nameField) {
  final normalized = _asInt(id);
  if (normalized == null) return 'Inherit / none';
  final row = records.cast<JsonMap?>().firstWhere(
    (record) => _asInt(record?['id']) == normalized,
    orElse: () => null,
  );
  return row == null
      ? '#$normalized'
      : _recordLabel(row, nameField, _codeFieldForName(nameField));
}

String _recordLabel(JsonMap row, String nameField, String codeField) {
  final name = _text(row, nameField, fallback: '#${row['id']}');
  final code = _text(row, codeField);
  return code.isEmpty ? name : '$code · $name';
}

String _codeFieldForName(String nameField) => switch (nameField) {
  'rate_book_name' => 'rate_book_code',
  'template_name' => 'template_code',
  'profile_name' => 'profile_code',
  _ => 'id',
};

int? _optionalInt(String value) {
  final trimmed = value.trim();
  if (trimmed.isEmpty) return null;
  final parsed = int.tryParse(trimmed);
  if (parsed == null) {
    throw FormatException('Expected an integer value.');
  }
  return parsed;
}

String? _optionalIntValidator(String? value, {required String label}) {
  final trimmed = value?.trim() ?? '';
  if (trimmed.isEmpty) return null;
  return int.tryParse(trimmed) == null ? 'Enter a numeric $label' : null;
}

List<String> _partyBindings(JsonMap row) {
  final bindings = <String>[];
  for (final entry in const [
    ('Company', 'company_id'),
    ('Customer', 'customer_id'),
    ('Vendor', 'vendor_id'),
    ('Forwarder', 'forwarder_id'),
    ('Carrier', 'carrier_id'),
  ]) {
    final value = _text(row, entry.$2);
    if (value.isNotEmpty) bindings.add('${entry.$1} $value');
  }
  return bindings;
}

String _partySummary(JsonMap row) {
  final bindings = _partyBindings(row);
  return bindings.isEmpty ? 'No party restriction' : bindings.join(' · ');
}

String _lineApplicability(JsonMap row) {
  final values = [
    _text(row, 'origin_code'),
    _text(row, 'destination_code'),
    _text(row, 'mode'),
    _text(row, 'equipment_type'),
    _text(row, 'service_level'),
  ].where((value) => value.isNotEmpty).toList();
  return values.isEmpty ? 'Any' : values.join(' · ');
}

void _showError(BuildContext context, Object error) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      backgroundColor: LedgerFlowDesign.danger,
      content: Text(error.toString()),
    ),
  );
}

class _PartyBindingFields extends StatelessWidget {
  const _PartyBindingFields({
    required this.companyController,
    required this.customerController,
    required this.vendorController,
    required this.forwarderController,
    required this.carrierController,
  });

  final TextEditingController companyController;
  final TextEditingController customerController;
  final TextEditingController vendorController;
  final TextEditingController forwarderController;
  final TextEditingController carrierController;

  @override
  Widget build(BuildContext context) {
    return _FormGrid(
      children: [
        TextFormField(
          controller: companyController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Company ID'),
          validator: (value) =>
              _optionalIntValidator(value, label: 'Company ID'),
        ),
        TextFormField(
          controller: customerController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Customer ID'),
          validator: (value) =>
              _optionalIntValidator(value, label: 'Customer ID'),
        ),
        TextFormField(
          controller: vendorController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Vendor ID'),
          validator: (value) =>
              _optionalIntValidator(value, label: 'Vendor ID'),
        ),
        TextFormField(
          controller: forwarderController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Forwarder ID'),
          validator: (value) =>
              _optionalIntValidator(value, label: 'Forwarder ID'),
        ),
        TextFormField(
          controller: carrierController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Carrier ID'),
          validator: (value) =>
              _optionalIntValidator(value, label: 'Carrier ID'),
        ),
      ],
    );
  }
}
