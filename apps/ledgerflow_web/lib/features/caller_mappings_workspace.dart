import 'dart:convert';

import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/design.dart';
import '../data/workspace_data.dart';
import 'workspace_pages.dart'
    show
        DetailRow,
        EmptyState,
        PageCanvas,
        ResponsiveColumns,
        SectionHeading,
        WorkspaceMutation;

enum _CallerMappingsView { dimensions, profiles }

class CallerMappingsWorkspace extends StatefulWidget {
  const CallerMappingsWorkspace({
    required this.pricingDimensions,
    required this.callerMappingProfiles,
    required this.live,
    required this.onMutation,
    this.client,
    super.key,
  });

  final List<JsonMap> pricingDimensions;
  final List<JsonMap> callerMappingProfiles;
  final bool live;
  final WorkspaceMutation onMutation;
  final LedgerFlowApiClient? client;

  @override
  State<CallerMappingsWorkspace> createState() =>
      _CallerMappingsWorkspaceState();
}

class _CallerMappingsWorkspaceState extends State<CallerMappingsWorkspace> {
  _CallerMappingsView _view = _CallerMappingsView.dimensions;

  @override
  Widget build(BuildContext context) {
    final hasDimensions = _view == _CallerMappingsView.dimensions;
    return PageCanvas(
      title: 'Caller mappings',
      subtitle:
          'Normalize each caller schema into shared pricing dimensions. Mapping profiles are selected by incoming quote requests, not assigned to contracts.',
      trailing: SegmentedButton<_CallerMappingsView>(
        segments: const [
          ButtonSegment(
            value: _CallerMappingsView.dimensions,
            label: Text('Dimensions'),
            icon: Icon(Icons.category_outlined),
          ),
          ButtonSegment(
            value: _CallerMappingsView.profiles,
            label: Text('Profiles'),
            icon: Icon(Icons.alt_route_outlined),
          ),
        ],
        selected: {_view},
        onSelectionChanged: (selection) =>
            setState(() => _view = selection.single),
      ),
      children: [
        if (!widget.live) const _LiveModeNotice(),
        if (!widget.live) const SizedBox(height: 16),
        SurfaceCard(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(
                Icons.lock_outline,
                size: 18,
                color: LedgerFlowDesign.teal,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  hasDimensions
                      ? 'System dimensions are locked. Custom canonical dimensions can be created, edited, or deactivated and then selected in rate-book rows.'
                      : 'Mapping profiles resolve raw caller attributes before contract matching. The caller sends caller_mapping_profile_code with its quote request; contracts use only the normalized result.',
                  style: const TextStyle(
                    fontSize: 12,
                    color: LedgerFlowDesign.muted,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (hasDimensions)
          _PricingDimensionWorkspace(
            pricingDimensions: widget.pricingDimensions,
            live: widget.live,
            onMutation: widget.onMutation,
          )
        else
          _CallerMappingProfileWorkspace(
            pricingDimensions: widget.pricingDimensions,
            callerMappingProfiles: widget.callerMappingProfiles,
            live: widget.live,
            onMutation: widget.onMutation,
            client: widget.client,
          ),
      ],
    );
  }
}

class _PricingDimensionWorkspace extends StatefulWidget {
  const _PricingDimensionWorkspace({
    required this.pricingDimensions,
    required this.live,
    required this.onMutation,
  });

  final List<JsonMap> pricingDimensions;
  final bool live;
  final WorkspaceMutation onMutation;

  @override
  State<_PricingDimensionWorkspace> createState() =>
      _PricingDimensionWorkspaceState();
}

class _PricingDimensionWorkspaceState
    extends State<_PricingDimensionWorkspace> {
  final _search = TextEditingController();
  int? _selectedId;

  @override
  void initState() {
    super.initState();
    _selectedId = _id(widget.pricingDimensions.firstOrNull);
    _search.addListener(_refresh);
  }

  @override
  void didUpdateWidget(covariant _PricingDimensionWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selectedId != null &&
        !widget.pricingDimensions.any(
          (dimension) => _id(dimension) == _selectedId,
        )) {
      _selectedId = _id(widget.pricingDimensions.firstOrNull);
    }
  }

  @override
  void dispose() {
    _search
      ..removeListener(_refresh)
      ..dispose();
    super.dispose();
  }

  void _refresh() => setState(() {});

  List<JsonMap> get _filtered {
    final query = _search.text.trim().toLowerCase();
    if (query.isEmpty) return widget.pricingDimensions;
    return widget.pricingDimensions
        .where(
          (dimension) => [
            _text(dimension, 'dimension_code'),
            _text(dimension, 'dimension_name'),
            _text(dimension, 'data_type'),
            _text(dimension, 'description'),
          ].any((value) => value.toLowerCase().contains(query)),
        )
        .toList(growable: false);
  }

  JsonMap? get _selected =>
      widget.pricingDimensions.cast<JsonMap?>().firstWhere(
        (dimension) => _id(dimension) == _selectedId,
        orElse: () => widget.pricingDimensions.firstOrNull,
      );

  @override
  Widget build(BuildContext context) {
    final selected = _selected;
    return ResponsiveColumns(
      leftFlex: 4,
      rightFlex: 3,
      left: SurfaceCard(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Expanded(
                    child: SectionHeading(
                      title: 'Pricing dimensions',
                      subtitle:
                          'Locked system dimensions stay visible for reference. Custom dimensions are editable and can be selected by rate books or caller mappings.',
                    ),
                  ),
                  FilledButton.icon(
                    onPressed: widget.live ? _createDimension : null,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('New dimension'),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: TextField(
                controller: _search,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  labelText: 'Search dimensions',
                ),
              ),
            ),
            const Divider(height: 1),
            if (_filtered.isEmpty)
              const EmptyState(
                message: 'No pricing dimensions match the search.',
              )
            else
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  showCheckboxColumn: false,
                  columns: const [
                    DataColumn(label: Text('Code')),
                    DataColumn(label: Text('Name')),
                    DataColumn(label: Text('Type')),
                    DataColumn(label: Text('Scope')),
                    DataColumn(label: Text('Status')),
                  ],
                  rows: _filtered
                      .map(
                        (dimension) => DataRow(
                          selected: _id(dimension) == _selectedId,
                          onSelectChanged: (_) =>
                              setState(() => _selectedId = _id(dimension)),
                          cells: [
                            DataCell(
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  if (_isSystemDimension(dimension)) ...[
                                    const Icon(
                                      Icons.lock_outline,
                                      size: 15,
                                      color: LedgerFlowDesign.muted,
                                    ),
                                    const SizedBox(width: 6),
                                  ],
                                  Text(
                                    _text(dimension, 'dimension_code'),
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                      color: LedgerFlowDesign.info,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            DataCell(Text(_text(dimension, 'dimension_name'))),
                            DataCell(Text(_text(dimension, 'data_type'))),
                            DataCell(
                              Wrap(
                                spacing: 6,
                                children: [
                                  if (_isBuiltInField(dimension))
                                    const StatusPill('BUILT-IN')
                                  else
                                    const StatusPill('CUSTOM'),
                                  if (_isSystemDimension(dimension))
                                    const StatusPill('SYSTEM'),
                                ],
                              ),
                            ),
                            DataCell(
                              StatusPill(
                                dimension['is_active'] == false
                                    ? 'INACTIVE'
                                    : 'ACTIVE',
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
      right: selected == null
          ? const SurfaceCard(
              child: EmptyState(
                message: 'Select a pricing dimension to inspect.',
              ),
            )
          : _DimensionInspector(
              dimension: selected,
              live: widget.live,
              onEdit: _isBuiltInField(selected) || _isSystemDimension(selected)
                  ? null
                  : () => _editDimension(selected),
              onDeactivate:
                  widget.live &&
                      !(_isBuiltInField(selected) ||
                          _isSystemDimension(selected)) &&
                      selected['is_active'] != false
                  ? () => _deactivateDimension(selected)
                  : null,
            ),
    );
  }

  Future<void> _createDimension() async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _PricingDimensionDialog(),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'POST',
      path: '/api/v1/charge-management/pricing-dimensions',
      body: payload,
      successMessage: 'Pricing dimension created.',
    );
  }

  Future<void> _editDimension(JsonMap dimension) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _PricingDimensionDialog(dimension: dimension),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'PUT',
      path: '/api/v1/charge-management/pricing-dimensions/${dimension['id']}',
      body: payload,
      successMessage: 'Pricing dimension updated.',
    );
  }

  Future<void> _deactivateDimension(JsonMap dimension) async {
    final confirmed = await _confirm(
      context,
      title: 'Deactivate dimension?',
      message:
          '${_text(dimension, 'dimension_code')} will stay in historical payloads but cannot be selected for new work.',
      action: 'Deactivate',
    );
    if (!confirmed) return;
    await widget.onMutation(
      method: 'DELETE',
      path: '/api/v1/charge-management/pricing-dimensions/${dimension['id']}',
      successMessage: 'Pricing dimension deactivated.',
    );
  }
}

class _DimensionInspector extends StatelessWidget {
  const _DimensionInspector({
    required this.dimension,
    required this.live,
    required this.onEdit,
    required this.onDeactivate,
  });

  final JsonMap dimension;
  final bool live;
  final VoidCallback? onEdit;
  final VoidCallback? onDeactivate;

  @override
  Widget build(BuildContext context) {
    final allowedValues = _stringList(dimension['allowed_values']);
    final locked = _isBuiltInField(dimension) || _isSystemDimension(dimension);
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _text(dimension, 'dimension_name'),
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _text(dimension, 'dimension_code'),
                      style: const TextStyle(color: LedgerFlowDesign.muted),
                    ),
                  ],
                ),
              ),
              if (locked)
                const StatusPill('LOCKED')
              else
                StatusPill(
                  dimension['is_active'] == false ? 'INACTIVE' : 'ACTIVE',
                ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              if (_isBuiltInField(dimension)) const StatusPill('BUILT-IN'),
              if (_isSystemDimension(dimension)) const StatusPill('SYSTEM'),
              StatusPill(_text(dimension, 'data_type')),
            ],
          ),
          const SizedBox(height: 14),
          DetailRow(
            label: 'Description',
            value: _text(dimension, 'description'),
          ),
          DetailRow(
            label: 'Case sensitive',
            value: dimension['case_sensitive'] == true ? 'Yes' : 'No',
          ),
          DetailRow(
            label: 'Allowed values',
            value: allowedValues.isEmpty ? 'Any' : allowedValues.join(', '),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_outlined, size: 17),
                  label: const Text('Edit'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onDeactivate,
                  icon: const Icon(Icons.block_outlined, size: 17),
                  label: const Text('Deactivate'),
                ),
              ),
            ],
          ),
          if (locked) ...[
            const SizedBox(height: 12),
            const Text(
              'Locked system dimensions are referenced by API contracts and cannot be edited from the UI.',
              style: TextStyle(fontSize: 12, color: LedgerFlowDesign.muted),
            ),
          ],
        ],
      ),
    );
  }
}

class _CallerMappingProfileWorkspace extends StatefulWidget {
  const _CallerMappingProfileWorkspace({
    required this.pricingDimensions,
    required this.callerMappingProfiles,
    required this.live,
    required this.onMutation,
    required this.client,
  });

  final List<JsonMap> pricingDimensions;
  final List<JsonMap> callerMappingProfiles;
  final bool live;
  final WorkspaceMutation onMutation;
  final LedgerFlowApiClient? client;

  @override
  State<_CallerMappingProfileWorkspace> createState() =>
      _CallerMappingProfileWorkspaceState();
}

class _CallerMappingProfileWorkspaceState
    extends State<_CallerMappingProfileWorkspace> {
  final _search = TextEditingController();
  int? _selectedId;

  @override
  void initState() {
    super.initState();
    _selectedId = _id(widget.callerMappingProfiles.firstOrNull);
    _search.addListener(_refresh);
  }

  @override
  void didUpdateWidget(covariant _CallerMappingProfileWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selectedId != null &&
        !widget.callerMappingProfiles.any(
          (profile) => _id(profile) == _selectedId,
        )) {
      _selectedId = _id(widget.callerMappingProfiles.firstOrNull);
    }
  }

  @override
  void dispose() {
    _search
      ..removeListener(_refresh)
      ..dispose();
    super.dispose();
  }

  void _refresh() => setState(() {});

  List<JsonMap> get _filtered {
    final query = _search.text.trim().toLowerCase();
    if (query.isEmpty) return widget.callerMappingProfiles;
    return widget.callerMappingProfiles
        .where(
          (profile) => [
            _text(profile, 'profile_code'),
            _text(profile, 'profile_name'),
            _text(profile, 'caller_system_code'),
            _text(profile, 'schema_version'),
            _text(profile, 'description'),
          ].any((value) => value.toLowerCase().contains(query)),
        )
        .toList(growable: false);
  }

  JsonMap? get _selected =>
      widget.callerMappingProfiles.cast<JsonMap?>().firstWhere(
        (profile) => _id(profile) == _selectedId,
        orElse: () => widget.callerMappingProfiles.firstOrNull,
      );

  @override
  Widget build(BuildContext context) {
    final selected = _selected;
    return ResponsiveColumns(
      leftFlex: 4,
      rightFlex: 3,
      left: SurfaceCard(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Expanded(
                    child: SectionHeading(
                      title: 'Caller mapping profiles',
                      subtitle:
                          'Profiles map caller-specific fields to canonical pricing dimensions. A profile can be deactivated without deleting its audit trail.',
                    ),
                  ),
                  FilledButton.icon(
                    onPressed: widget.live ? _createProfile : null,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('New profile'),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: TextField(
                controller: _search,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  labelText: 'Search profiles',
                ),
              ),
            ),
            const Divider(height: 1),
            if (_filtered.isEmpty)
              const EmptyState(
                message: 'No caller mapping profiles match the search.',
              )
            else
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  showCheckboxColumn: false,
                  columns: const [
                    DataColumn(label: Text('Code')),
                    DataColumn(label: Text('Caller system')),
                    DataColumn(label: Text('Schema')),
                    DataColumn(label: Text('Canonical dimensions')),
                    DataColumn(label: Text('Status')),
                  ],
                  rows: _filtered
                      .map(
                        (profile) => DataRow(
                          selected: _id(profile) == _selectedId,
                          onSelectChanged: (_) =>
                              setState(() => _selectedId = _id(profile)),
                          cells: [
                            DataCell(
                              Text(
                                _text(profile, 'profile_code'),
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  color: LedgerFlowDesign.info,
                                ),
                              ),
                            ),
                            DataCell(
                              Text(_text(profile, 'caller_system_code')),
                            ),
                            DataCell(Text(_text(profile, 'schema_version'))),
                            DataCell(
                              SizedBox(
                                width: 260,
                                child: Text(
                                  _canonicalCodes(profile).join(', '),
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ),
                            DataCell(
                              StatusPill(
                                profile['is_active'] == false
                                    ? 'INACTIVE'
                                    : 'ACTIVE',
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
      right: selected == null
          ? const SurfaceCard(
              child: EmptyState(
                message: 'Select a caller mapping profile to inspect.',
              ),
            )
          : _CallerMappingProfileInspector(
              profile: selected,
              pricingDimensions: widget.pricingDimensions,
              live: widget.live,
              onEdit: widget.live ? () => _editProfile(selected) : null,
              onDeactivate: widget.live && selected['is_active'] != false
                  ? () => _deactivateProfile(selected)
                  : null,
              onPreview: widget.live && widget.client != null
                  ? () => _previewProfile(selected)
                  : null,
            ),
    );
  }

  Future<void> _createProfile() async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _CallerMappingProfileDialog(
        pricingDimensions: widget.pricingDimensions,
      ),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'POST',
      path: '/api/v1/charge-management/caller-mapping-profiles',
      body: payload,
      successMessage: 'Caller mapping profile created.',
    );
  }

  Future<void> _editProfile(JsonMap profile) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _CallerMappingProfileDialog(
        pricingDimensions: widget.pricingDimensions,
        profile: profile,
      ),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'PUT',
      path:
          '/api/v1/charge-management/caller-mapping-profiles/${profile['id']}',
      body: payload,
      successMessage: 'Caller mapping profile updated.',
    );
  }

  Future<void> _deactivateProfile(JsonMap profile) async {
    final confirmed = await _confirm(
      context,
      title: 'Deactivate profile?',
      message:
          '${_text(profile, 'profile_code')} will remain in audit history but cannot be used for new caller requests.',
      action: 'Deactivate',
    );
    if (!confirmed) return;
    await widget.onMutation(
      method: 'DELETE',
      path:
          '/api/v1/charge-management/caller-mapping-profiles/${profile['id']}',
      successMessage: 'Caller mapping profile deactivated.',
    );
  }

  Future<void> _previewProfile(JsonMap profile) async {
    final callerAttributes = await showDialog<JsonMap>(
      context: context,
      builder: (_) => const _CallerMappingPreviewDialog(),
    );
    if (callerAttributes == null || widget.client == null) return;
    try {
      final response = await widget.client!.requestJson(
        'POST',
        '/api/v1/charge-management/caller-mapping-profiles/${profile['id']}/preview',
        body: {'caller_attributes': callerAttributes},
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Normalized preview'),
          content: SizedBox(
            width: 680,
            child: SingleChildScrollView(
              child: SelectableText(
                const JsonEncoder.withIndent('  ').convert(response),
                style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Mapping preview failed: $error')));
    }
  }
}

class _CallerMappingPreviewDialog extends StatefulWidget {
  const _CallerMappingPreviewDialog();

  @override
  State<_CallerMappingPreviewDialog> createState() =>
      _CallerMappingPreviewDialogState();
}

class _CallerMappingPreviewDialogState
    extends State<_CallerMappingPreviewDialog> {
  final _formKey = GlobalKey<FormState>();
  final _json = TextEditingController(text: '{\n  "shipment": {}\n}');

  @override
  void dispose() {
    _json.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Preview caller mapping'),
    content: SizedBox(
      width: 680,
      child: Form(
        key: _formKey,
        child: TextFormField(
          controller: _json,
          minLines: 12,
          maxLines: 20,
          style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
          decoration: const InputDecoration(
            labelText: 'Caller attributes JSON',
            helperText:
                'Enter the raw caller_attributes object, not the complete quote request.',
            alignLabelWithHint: true,
          ),
          validator: (value) {
            try {
              final decoded = jsonDecode(value?.trim() ?? '');
              return decoded is Map<String, dynamic>
                  ? null
                  : 'Enter a JSON object';
            } on FormatException {
              return 'Enter valid JSON';
            }
          },
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
          Navigator.pop(
            context,
            JsonMap.from(jsonDecode(_json.text.trim()) as Map<String, dynamic>),
          );
        },
        child: const Text('Run preview'),
      ),
    ],
  );
}

class _CallerMappingProfileInspector extends StatelessWidget {
  const _CallerMappingProfileInspector({
    required this.profile,
    required this.pricingDimensions,
    required this.live,
    required this.onEdit,
    required this.onDeactivate,
    required this.onPreview,
  });

  final JsonMap profile;
  final List<JsonMap> pricingDimensions;
  final bool live;
  final VoidCallback? onEdit;
  final VoidCallback? onDeactivate;
  final VoidCallback? onPreview;

  @override
  Widget build(BuildContext context) {
    final mappings = _rows(profile, 'mappings');
    final codes = _canonicalCodes(profile);
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _text(profile, 'profile_name'),
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_text(profile, 'profile_code')} / ${_text(profile, 'caller_system_code')} / ${_text(profile, 'schema_version')}',
                      style: const TextStyle(color: LedgerFlowDesign.muted),
                    ),
                  ],
                ),
              ),
              StatusPill(profile['is_active'] == false ? 'INACTIVE' : 'ACTIVE'),
            ],
          ),
          const SizedBox(height: 14),
          DetailRow(label: 'Description', value: _text(profile, 'description')),
          DetailRow(
            label: 'Caller system',
            value: _text(profile, 'caller_system_code'),
          ),
          DetailRow(
            label: 'Schema version',
            value: _text(profile, 'schema_version'),
          ),
          const SizedBox(height: 14),
          Text(
            'Canonical dimensions',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: codes.isEmpty
                ? const [StatusPill('NONE')]
                : codes
                      .map(
                        (code) => StatusPill(
                          _dimensionLabel(
                            _pricingDimensionByCode(pricingDimensions, code) ??
                                {'dimension_code': code},
                          ),
                        ),
                      )
                      .toList(growable: false),
          ),
          const SizedBox(height: 16),
          Text(
            'Mappings',
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          if (mappings.isEmpty)
            const Text(
              'No mappings are defined.',
              style: TextStyle(color: LedgerFlowDesign.muted),
            )
          else
            ...mappings.map(
              (mapping) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: const Color(0xFFF8FAFC),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: LedgerFlowDesign.border),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _text(mapping, 'source_attribute'),
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 12,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _dimensionLabel(
                            _pricingDimensionByCode(
                                  pricingDimensions,
                                  _text(mapping, 'dimension_code'),
                                ) ??
                                {
                                  'dimension_code': _text(
                                    mapping,
                                    'dimension_code',
                                  ),
                                },
                          ),
                          style: const TextStyle(
                            fontSize: 12,
                            color: LedgerFlowDesign.info,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _text(mapping, 'required') == 'true'
                              ? 'Required'
                              : 'Optional',
                          style: const TextStyle(
                            fontSize: 11,
                            color: LedgerFlowDesign.muted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_outlined, size: 17),
                  label: const Text('Edit'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onPreview,
                  icon: const Icon(Icons.search_outlined, size: 17),
                  label: const Text('Preview'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: onDeactivate,
                  icon: const Icon(Icons.block_outlined, size: 17),
                  label: const Text('Deactivate'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PricingDimensionDialog extends StatefulWidget {
  const _PricingDimensionDialog({this.dimension});

  final JsonMap? dimension;

  @override
  State<_PricingDimensionDialog> createState() =>
      _PricingDimensionDialogState();
}

class _PricingDimensionDialogState extends State<_PricingDimensionDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _code;
  late final TextEditingController _name;
  late final TextEditingController _description;
  late final TextEditingController _allowedValues;
  late String _dataType;
  late bool _builtInField;
  late bool _caseSensitive;
  late bool _isSystem;
  late bool _isActive;

  bool get _locked =>
      widget.dimension?['is_system'] == true ||
      _isBuiltInField(widget.dimension ?? const <String, dynamic>{});

  @override
  void initState() {
    super.initState();
    final value = widget.dimension ?? const <String, dynamic>{};
    _code = TextEditingController(
      text: _text(value, 'dimension_code', fallback: ''),
    );
    _name = TextEditingController(
      text: _text(value, 'dimension_name', fallback: ''),
    );
    _description = TextEditingController(
      text: _text(value, 'description', fallback: ''),
    );
    _allowedValues = TextEditingController(
      text: _stringList(value['allowed_values']).join(', '),
    );
    _dataType = _text(value, 'data_type', fallback: 'STRING').toUpperCase();
    _builtInField = _isBuiltInField(value);
    _caseSensitive = value['case_sensitive'] == true;
    _isSystem = value['is_system'] == true;
    _isActive = value['is_active'] != false;
  }

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    _description.dispose();
    _allowedValues.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      widget.dimension == null ? 'Create dimension' : 'Edit dimension',
    ),
    content: SizedBox(
      width: 720,
      child: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  SizedBox(
                    width: 220,
                    child: TextFormField(
                      controller: _code,
                      readOnly: widget.dimension != null,
                      decoration: const InputDecoration(
                        labelText: 'Dimension code',
                      ),
                      validator: (value) => _required(value, 'Dimension code'),
                    ),
                  ),
                  SizedBox(
                    width: 240,
                    child: TextFormField(
                      controller: _name,
                      decoration: const InputDecoration(
                        labelText: 'Dimension name',
                      ),
                      validator: (value) => _required(value, 'Dimension name'),
                    ),
                  ),
                  SizedBox(
                    width: 170,
                    child: DropdownButtonFormField<String>(
                      initialValue: _dataType,
                      decoration: const InputDecoration(labelText: 'Data type'),
                      items: const [
                        DropdownMenuItem(
                          value: 'STRING',
                          child: Text('STRING'),
                        ),
                        DropdownMenuItem(
                          value: 'DECIMAL',
                          child: Text('DECIMAL'),
                        ),
                        DropdownMenuItem(
                          value: 'INTEGER',
                          child: Text('INTEGER'),
                        ),
                        DropdownMenuItem(
                          value: 'BOOLEAN',
                          child: Text('BOOLEAN'),
                        ),
                        DropdownMenuItem(value: 'DATE', child: Text('DATE')),
                      ],
                      onChanged: _locked
                          ? null
                          : (value) =>
                                setState(() => _dataType = value ?? 'STRING'),
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
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  SizedBox(
                    width: 280,
                    child: TextFormField(
                      controller: _allowedValues,
                      enabled: !_locked && _dataType == 'STRING',
                      decoration: const InputDecoration(
                        labelText: 'Allowed values',
                        helperText:
                            'Comma-separated values for string dimensions.',
                      ),
                    ),
                  ),
                  SizedBox(
                    width: 160,
                    child: CheckboxListTile(
                      value: _caseSensitive,
                      onChanged: _locked
                          ? null
                          : (value) =>
                                setState(() => _caseSensitive = value ?? false),
                      title: const Text('Case sensitive'),
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                  ),
                  SizedBox(
                    width: 160,
                    child: CheckboxListTile(
                      value: _builtInField,
                      onChanged: null,
                      title: const Text('Built-in field'),
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                  ),
                  SizedBox(
                    width: 120,
                    child: CheckboxListTile(
                      value: _isSystem,
                      onChanged: null,
                      title: const Text('System'),
                      contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                value: _isActive,
                onChanged: _locked
                    ? null
                    : (value) => setState(() => _isActive = value),
                title: const Text('Record is active'),
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
        onPressed: _locked ? null : _submit,
        child: const Text('Save dimension'),
      ),
    ],
  );

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final allowedValues = _dataType == 'STRING'
        ? _stringListFromText(_allowedValues.text)
        : const <String>[];
    Navigator.pop(
      context,
      JsonMap.from({
        'dimension_code': _code.text.trim().toUpperCase(),
        'dimension_name': _name.text.trim(),
        'description': _description.text.trim().isEmpty
            ? null
            : _description.text.trim(),
        'data_type': _dataType,
        'allowed_values': allowedValues,
        'case_sensitive': _caseSensitive,
        'is_active': _isActive,
      }),
    );
  }
}

class _CallerMappingProfileDialog extends StatefulWidget {
  const _CallerMappingProfileDialog({
    required this.pricingDimensions,
    this.profile,
  });

  final List<JsonMap> pricingDimensions;
  final JsonMap? profile;

  @override
  State<_CallerMappingProfileDialog> createState() =>
      _CallerMappingProfileDialogState();
}

class _CallerMappingProfileDialogState
    extends State<_CallerMappingProfileDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _code;
  late final TextEditingController _name;
  late final TextEditingController _callerSystemCode;
  late final TextEditingController _schemaVersion;
  late final TextEditingController _description;
  late bool _isActive;
  late final List<_MappingDraft> _mappings;

  @override
  void initState() {
    super.initState();
    final value = widget.profile ?? const <String, dynamic>{};
    _code = TextEditingController(
      text: _text(value, 'profile_code', fallback: ''),
    );
    _name = TextEditingController(
      text: _text(value, 'profile_name', fallback: ''),
    );
    _callerSystemCode = TextEditingController(
      text: _text(value, 'caller_system_code', fallback: 'COCKPIT'),
    );
    _schemaVersion = TextEditingController(
      text: _text(value, 'schema_version', fallback: '1.0'),
    );
    _description = TextEditingController(
      text: _text(value, 'description', fallback: ''),
    );
    _isActive = value['is_active'] != false;
    final mappings = _rows(value, 'mappings');
    _mappings =
        (mappings.isEmpty ? <JsonMap>[const <String, dynamic>{}] : mappings)
            .map((mapping) => _MappingDraft.fromJson(mapping))
            .toList(growable: true);
  }

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    _callerSystemCode.dispose();
    _schemaVersion.dispose();
    _description.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final canonicalCodes = _canonicalCodesFromDrafts(_mappings);
    return AlertDialog(
      title: Text(
        widget.profile == null
            ? 'Create mapping profile'
            : 'Edit mapping profile',
      ),
      content: SizedBox(
        width: 900,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    SizedBox(
                      width: 220,
                      child: TextFormField(
                        controller: _code,
                        decoration: const InputDecoration(
                          labelText: 'Profile code',
                        ),
                        validator: (value) => _required(value, 'Profile code'),
                      ),
                    ),
                    SizedBox(
                      width: 220,
                      child: TextFormField(
                        controller: _name,
                        decoration: const InputDecoration(
                          labelText: 'Profile name',
                        ),
                        validator: (value) => _required(value, 'Profile name'),
                      ),
                    ),
                    SizedBox(
                      width: 190,
                      child: TextFormField(
                        controller: _callerSystemCode,
                        decoration: const InputDecoration(
                          labelText: 'Caller system code',
                        ),
                        validator: (value) =>
                            _required(value, 'Caller system code'),
                      ),
                    ),
                    SizedBox(
                      width: 160,
                      child: TextFormField(
                        controller: _schemaVersion,
                        decoration: const InputDecoration(
                          labelText: 'Schema version',
                        ),
                        validator: (value) =>
                            _required(value, 'Schema version'),
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
                const SizedBox(height: 12),
                SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  value: _isActive,
                  onChanged: (value) => setState(() => _isActive = value),
                  title: const Text('Record is active'),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Expanded(
                      child: SectionHeading(
                        title: 'Mappings',
                        subtitle:
                            'Each mapping resolves a caller source attribute to a canonical dimension code.',
                      ),
                    ),
                    TextButton.icon(
                      onPressed: () =>
                          setState(() => _mappings.add(_MappingDraft.empty())),
                      icon: const Icon(Icons.add, size: 16),
                      label: const Text('Add mapping'),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                if (_mappings.isEmpty)
                  const EmptyState(message: 'Add at least one mapping.')
                else
                  ...List.generate(_mappings.length, (index) {
                    final mapping = _mappings[index];
                    return Padding(
                      padding: EdgeInsets.only(
                        bottom: index == _mappings.length - 1 ? 0 : 12,
                      ),
                      child: _MappingEditorCard(
                        key: ValueKey('mapping-$index'),
                        mapping: mapping,
                        pricingDimensions: widget.pricingDimensions,
                        onRemove: _mappings.length == 1
                            ? null
                            : () => setState(() => _mappings.removeAt(index)),
                      ),
                    );
                  }),
                const SizedBox(height: 14),
                Text(
                  'Canonical dimensions',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: canonicalCodes.isEmpty
                      ? const [StatusPill('NONE')]
                      : canonicalCodes
                            .map(
                              (code) => StatusPill(
                                _dimensionLabel(
                                  _pricingDimensionByCode(
                                        widget.pricingDimensions,
                                        code,
                                      ) ??
                                      {'dimension_code': code},
                                ),
                              ),
                            )
                            .toList(growable: false),
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
        FilledButton(onPressed: _submit, child: const Text('Save profile')),
      ],
    );
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final mappings = _mappings
        .map((mapping) => mapping.toJson())
        .where(
          (mapping) =>
              mapping['source_attribute'] != null &&
              mapping['source_attribute'].toString().trim().isNotEmpty &&
              mapping['dimension_code'] != null &&
              mapping['dimension_code'].toString().trim().isNotEmpty,
        )
        .toList(growable: false);
    Navigator.pop(
      context,
      JsonMap.from({
        'profile_code': _code.text.trim().toUpperCase(),
        'profile_name': _name.text.trim(),
        'caller_system_code': _callerSystemCode.text.trim().toUpperCase(),
        'schema_version': _schemaVersion.text.trim(),
        'description': _description.text.trim().isEmpty
            ? null
            : _description.text.trim(),
        'mappings': mappings,
        'is_active': _isActive,
      }),
    );
  }
}

class _MappingEditorCard extends StatelessWidget {
  const _MappingEditorCard({
    super.key,
    required this.mapping,
    required this.pricingDimensions,
    required this.onRemove,
  });

  final _MappingDraft mapping;
  final List<JsonMap> pricingDimensions;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: LedgerFlowDesign.border),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text(
                  'Mapping',
                  style: TextStyle(fontWeight: FontWeight.w700),
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: onRemove,
                  icon: const Icon(Icons.delete_outline, size: 16),
                  label: const Text('Remove'),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                SizedBox(
                  width: 250,
                  child: TextFormField(
                    initialValue: mapping.sourceAttribute,
                    decoration: const InputDecoration(
                      labelText: 'Source attribute',
                    ),
                    validator: (value) => _required(value, 'Source attribute'),
                    onChanged: (value) => mapping.sourceAttribute = value,
                  ),
                ),
                SizedBox(
                  width: 250,
                  child: DropdownButtonFormField<String>(
                    initialValue: mapping.dimensionCode.isEmpty
                        ? null
                        : mapping.dimensionCode,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Canonical dimension',
                    ),
                    items: [
                      const DropdownMenuItem<String>(
                        value: '',
                        child: Text('Select dimension'),
                      ),
                      ...pricingDimensions.map(
                        (dimension) => DropdownMenuItem<String>(
                          value: _text(dimension, 'dimension_code'),
                          child: Text(_dimensionLabel(dimension)),
                        ),
                      ),
                    ],
                    onChanged: (value) => mapping.dimensionCode = value ?? '',
                    validator: (value) => _required(
                      value == '' ? null : value,
                      'Canonical dimension',
                    ),
                  ),
                ),
                SizedBox(
                  width: 110,
                  child: SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    value: mapping.required,
                    onChanged: (value) => mapping.required = value,
                    title: const Text('Required'),
                  ),
                ),
                SizedBox(
                  width: 180,
                  child: TextFormField(
                    initialValue: mapping.defaultValue,
                    decoration: const InputDecoration(
                      labelText: 'Default value',
                    ),
                    onChanged: (value) => mapping.defaultValue = value,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            TextFormField(
              initialValue: mapping.valueMapJson,
              minLines: 2,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Value map JSON',
                helperText: 'Example: {"ROAD_FTL":"ROAD"}',
              ),
              validator: (value) {
                if (value == null || value.trim().isEmpty) return null;
                try {
                  final parsed = jsonDecode(value.trim());
                  if (parsed is! Map<String, dynamic>) {
                    return 'Enter a JSON object';
                  }
                } on FormatException {
                  return 'Enter valid JSON';
                }
                return null;
              },
              onChanged: (value) => mapping.valueMapJson = value,
            ),
          ],
        ),
      ),
    );
  }
}

class _MappingDraft {
  _MappingDraft({
    this.sourceAttribute = '',
    this.dimensionCode = '',
    this.required = false,
    this.defaultValue = '',
    this.valueMapJson = '',
  });

  factory _MappingDraft.empty() => _MappingDraft();

  factory _MappingDraft.fromJson(JsonMap mapping) => _MappingDraft(
    sourceAttribute: _text(mapping, 'source_attribute', fallback: ''),
    dimensionCode: _text(mapping, 'dimension_code', fallback: ''),
    required: mapping['required'] == true,
    defaultValue: mapping['default_value']?.toString() ?? '',
    valueMapJson: _mapToJsonText(mapping['value_map']),
  );

  String sourceAttribute;
  String dimensionCode;
  bool required;
  String defaultValue;
  String valueMapJson;

  JsonMap toJson() {
    final result = <String, dynamic>{
      'source_attribute': sourceAttribute.trim(),
      'dimension_code': dimensionCode.trim(),
      'required': required,
      'default_value': defaultValue.trim().isEmpty ? null : defaultValue.trim(),
      'value_map': _parsedValueMap,
    };
    return JsonMap.from(result);
  }

  Map<String, dynamic> get _parsedValueMap {
    final text = valueMapJson.trim();
    if (text.isEmpty) return <String, dynamic>{};
    final parsed = jsonDecode(text);
    if (parsed is Map<String, dynamic>) return parsed;
    return <String, dynamic>{};
  }
}

List<String> _canonicalCodesFromDrafts(List<_MappingDraft> mappings) {
  final codes = <String>{};
  for (final mapping in mappings) {
    final code = mapping.dimensionCode.trim();
    if (code.isNotEmpty) codes.add(code);
  }
  return codes.toList(growable: false);
}

List<String> _canonicalCodes(JsonMap profile) {
  final configured = _stringList(profile['canonical_dimension_codes']);
  if (configured.isNotEmpty) return configured;
  return _rows(profile, 'mappings')
      .map((mapping) => _text(mapping, 'dimension_code', fallback: '').trim())
      .where((code) => code.isNotEmpty)
      .toSet()
      .toList(growable: false);
}

JsonMap? _pricingDimensionByCode(List<JsonMap> pricingDimensions, String code) {
  final selected = code.trim().toLowerCase();
  return pricingDimensions.cast<JsonMap?>().firstWhere(
    (dimension) =>
        _text(
          dimension ?? const <String, dynamic>{},
          'dimension_code',
        ).trim().toLowerCase() ==
        selected,
    orElse: () => null,
  );
}

String _dimensionLabel(JsonMap dimension) {
  final code = _text(dimension, 'dimension_code');
  final name = _text(dimension, 'dimension_name', fallback: code);
  final locked = _isSystemDimension(dimension) || _isBuiltInField(dimension)
      ? ' [locked]'
      : '';
  return '$name ($code)$locked';
}

bool _isBuiltInField(JsonMap dimension) =>
    dimension['built_in_field']?.toString().trim().isNotEmpty == true;

bool _isSystemDimension(JsonMap dimension) => dimension['is_system'] == true;

String _mapToJsonText(dynamic value) {
  if (value is Map<String, dynamic> && value.isNotEmpty) {
    return const JsonEncoder.withIndent('  ').convert(value);
  }
  return '';
}

List<String> _stringList(dynamic value) {
  if (value is! List) return const [];
  return value
      .map((item) => item.toString())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

List<String> _stringListFromText(String text) {
  return text
      .split(',')
      .map((item) => item.trim())
      .where((item) => item.isNotEmpty)
      .toList(growable: false);
}

String? _required(String? value, String label) =>
    value == null || value.trim().isEmpty ? '$label is required' : null;

int? _id(JsonMap? record) => switch (record?['id']) {
  int number => number,
  String text => int.tryParse(text),
  _ => null,
};

String _text(JsonMap record, String key, {String fallback = '-'}) {
  final value = record[key];
  if (value == null || value.toString().trim().isEmpty) return fallback;
  return value.toString();
}

List<JsonMap> _rows(JsonMap record, String key) {
  final value = record[key];
  if (value is! List) return const [];
  return value
      .whereType<Map<String, dynamic>>()
      .map(JsonMap.from)
      .toList(growable: false);
}

Future<bool> _confirm(
  BuildContext context, {
  required String title,
  required String message,
  required String action,
}) async {
  final result = await showDialog<bool>(
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
          onPressed: () => Navigator.pop(context, true),
          child: Text(action),
        ),
      ],
    ),
  );
  return result == true;
}

class _LiveModeNotice extends StatelessWidget {
  const _LiveModeNotice();

  @override
  Widget build(BuildContext context) => const SurfaceCard(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(Icons.lock_outline, size: 18, color: LedgerFlowDesign.muted),
        SizedBox(width: 10),
        Expanded(
          child: Text(
            'Demo mode is read-only. Connect an authenticated API to create, edit, preview, or deactivate dimensions and mapping profiles.',
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
