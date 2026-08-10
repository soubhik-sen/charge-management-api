import 'dart:convert';

import 'package:flutter/material.dart';

import '../core/design.dart';
import '../core/reference_values.dart';
import '../data/workspace_data.dart';
import 'workspace_pages.dart' hide WorkspaceMutation;

typedef WorkspaceMutation =
    Future<bool> Function({
      required String method,
      required String path,
      JsonMap? body,
      required String successMessage,
    });

typedef AssignmentLoader = Future<List<JsonMap>> Function(int profileId);

class ComponentManagementWorkspace extends StatefulWidget {
  const ComponentManagementWorkspace({
    required this.records,
    required this.calculationProfiles,
    required this.allocationProfiles,
    required this.businessDateProfiles,
    required this.live,
    required this.onMutation,
    super.key,
  });

  final List<JsonMap> records;
  final List<JsonMap> calculationProfiles;
  final List<JsonMap> allocationProfiles;
  final List<JsonMap> businessDateProfiles;
  final bool live;
  final WorkspaceMutation onMutation;

  @override
  State<ComponentManagementWorkspace> createState() =>
      _ComponentManagementWorkspaceState();
}

class _ComponentManagementWorkspaceState
    extends State<ComponentManagementWorkspace> {
  final _search = TextEditingController();
  int? _selectedId;

  @override
  void initState() {
    super.initState();
    _search.addListener(_refresh);
  }

  @override
  void didUpdateWidget(covariant ComponentManagementWorkspace oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selectedId != null &&
        !widget.records.any((record) => _id(record) == _selectedId)) {
      _selectedId = null;
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
    if (query.isEmpty) return widget.records;
    return widget.records
        .where(
          (record) => [
            _value(record, 'component_code'),
            _value(record, 'component_name'),
            _value(record, 'category'),
            _value(record, 'charge_context'),
          ].any((value) => value.toLowerCase().contains(query)),
        )
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    return PageCanvas(
      title: 'Charge components',
      subtitle:
          'Define reusable charge identities and connect them to governed calculation, allocation, and business-date behavior.',
      trailing: FilledButton.icon(
        onPressed: widget.live ? () => _editComponent() : null,
        icon: const Icon(Icons.add),
        label: const Text('New component'),
      ),
      children: [
        if (!widget.live) const _LiveWriteNotice(),
        if (!widget.live) const SizedBox(height: 16),
        _ModulePrimer(
          title: 'What a component controls',
          text:
              'A component is the canonical identity of a charge, such as ocean freight or documentation. Its defaults make rating consistent; rate rows and document lines may then reference it without redefining behavior.',
          points: const [
            'Party role and calculation basis define the commercial default.',
            'Calculation and allocation profiles attach reusable versioned rules.',
            'Business-date policy determines which date drives rates and FX.',
          ],
        ),
        const SizedBox(height: 16),
        SurfaceCard(
          padding: EdgeInsets.zero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.all(16),
                child: TextField(
                  controller: _search,
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.search),
                    labelText: 'Search code, name, category, or context',
                  ),
                ),
              ),
              const Divider(height: 1),
              if (_filtered.isEmpty)
                const EmptyState(message: 'No components match the search.')
              else
                LayoutBuilder(
                  builder: (context, constraints) {
                    final compact = constraints.maxWidth < 850;
                    return Column(
                      children: [
                        _ComponentTableHeader(compact: compact),
                        for (final record in _filtered)
                          _ExpandableComponentRow(
                            component: record,
                            compact: compact,
                            expanded: _id(record) == _selectedId,
                            onTap: () {
                              final id = _id(record);
                              setState(
                                () =>
                                    _selectedId = _selectedId == id ? null : id,
                              );
                            },
                            details: _componentExpandedDetails(record),
                          ),
                      ],
                    );
                  },
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _componentExpandedDetails(JsonMap component) {
    final active = component['is_active'] != false;
    return ColoredBox(
      color: const Color(0xFFF4F8F7),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 18, 20, 20),
        child: Wrap(
          spacing: 38,
          runSpacing: 18,
          crossAxisAlignment: WrapCrossAlignment.start,
          children: [
            SizedBox(
              width: 260,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _InlineDetailHeading('Classification'),
                  DetailRow(
                    label: 'Category',
                    value: _value(component, 'category'),
                  ),
                  DetailRow(
                    label: 'Context',
                    value: _value(component, 'charge_context'),
                  ),
                  DetailRow(
                    label: 'Party role',
                    value: _value(component, 'default_party_role'),
                  ),
                  DetailRow(
                    label: 'Tax class',
                    value: component['is_tax'] == true ? 'TAX' : 'STANDARD',
                  ),
                ],
              ),
            ),
            SizedBox(
              width: 360,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _InlineDetailHeading('Default profile usage'),
                  DetailRow(
                    label: 'Calculation',
                    value: _profileName(
                      widget.calculationProfiles,
                      component['default_calculation_profile_id'],
                    ),
                  ),
                  DetailRow(
                    label: 'Allocation',
                    value: _profileName(
                      widget.allocationProfiles,
                      component['allocation_profile_id'],
                    ),
                  ),
                  DetailRow(
                    label: 'Business date',
                    value: _profileName(
                      widget.businessDateProfiles,
                      component['business_date_profile_id'],
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(
              width: 260,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _InlineDetailHeading('Rating defaults'),
                  DetailRow(
                    label: 'Calc. basis',
                    value: _value(component, 'calculation_basis'),
                  ),
                  DetailRow(
                    label: 'Date basis',
                    value: _value(component, 'charge_date_basis'),
                  ),
                  DetailRow(
                    label: 'Date policy',
                    value: _value(component, 'business_date_policy_mode'),
                  ),
                ],
              ),
            ),
            SizedBox(
              width: 190,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  FilledButton.icon(
                    onPressed: widget.live
                        ? () => _editComponent(component)
                        : null,
                    icon: const Icon(Icons.edit_outlined),
                    label: const Text('Edit defaults'),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: widget.live && active
                        ? () => _deactivate(component)
                        : null,
                    icon: const Icon(Icons.block_outlined),
                    label: const Text('Deactivate'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _editComponent([JsonMap? component]) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _ComponentDialog(
        component: component,
        calculationProfiles: widget.calculationProfiles,
        allocationProfiles: widget.allocationProfiles,
        businessDateProfiles: widget.businessDateProfiles,
      ),
    );
    if (payload == null || !mounted) return;
    final creating = component == null;
    await widget.onMutation(
      method: creating ? 'POST' : 'PUT',
      path: creating
          ? '/api/v1/charge-management/components'
          : '/api/v1/charge-management/components/${component['id']}',
      body: payload,
      successMessage: creating ? 'Component created.' : 'Component updated.',
    );
  }

  Future<void> _deactivate(JsonMap component) async {
    final confirmed = await _confirm(
      context,
      title: 'Deactivate component?',
      message:
          '${_value(component, 'component_code')} remains available in historical audit data but cannot be selected for new work.',
      action: 'Deactivate',
    );
    if (!confirmed) return;
    await widget.onMutation(
      method: 'DELETE',
      path: '/api/v1/charge-management/components/${component['id']}',
      successMessage: 'Component deactivated.',
    );
  }
}

class _ComponentTableHeader extends StatelessWidget {
  const _ComponentTableHeader({required this.compact});

  final bool compact;

  @override
  Widget build(BuildContext context) => ColoredBox(
    color: const Color(0xFFF7F9FB),
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          const _ComponentTableCell('Code', flex: 5, header: true),
          const _ComponentTableCell('Name', flex: 4, header: true),
          if (!compact) ...const [
            _ComponentTableCell('Category', flex: 3, header: true),
            _ComponentTableCell('Context', flex: 3, header: true),
            _ComponentTableCell('Role', flex: 2, header: true),
            _ComponentTableCell('Basis', flex: 3, header: true),
          ],
          const SizedBox(width: 88, child: Text('Status')),
          const SizedBox(width: 32),
        ],
      ),
    ),
  );
}

class _ExpandableComponentRow extends StatelessWidget {
  const _ExpandableComponentRow({
    required this.component,
    required this.compact,
    required this.expanded,
    required this.onTap,
    required this.details,
  });

  final JsonMap component;
  final bool compact;
  final bool expanded;
  final VoidCallback onTap;
  final Widget details;

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Material(
        color: expanded ? const Color(0xFFEAF4F2) : Colors.transparent,
        child: InkWell(
          key: ValueKey('component-row-${component['id']}'),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              children: [
                _ComponentTableCell(
                  _value(component, 'component_code'),
                  flex: 5,
                  emphasis: true,
                ),
                _ComponentTableCell(
                  _value(component, 'component_name'),
                  flex: 4,
                ),
                if (!compact) ...[
                  _ComponentTableCell(_value(component, 'category'), flex: 3),
                  _ComponentTableCell(
                    _value(component, 'charge_context'),
                    flex: 3,
                  ),
                  _ComponentTableCell(
                    _value(component, 'default_party_role'),
                    flex: 2,
                  ),
                  _ComponentTableCell(
                    _value(component, 'calculation_basis'),
                    flex: 3,
                  ),
                ],
                SizedBox(
                  width: 88,
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: StatusPill(
                      component['is_active'] == false ? 'INACTIVE' : 'ACTIVE',
                    ),
                  ),
                ),
                SizedBox(
                  width: 32,
                  child: Icon(
                    expanded ? Icons.expand_less : Icons.expand_more,
                    color: LedgerFlowDesign.muted,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
      AnimatedSize(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        alignment: Alignment.topCenter,
        child: expanded ? details : const SizedBox.shrink(),
      ),
      const Divider(height: 1),
    ],
  );
}

class _ComponentTableCell extends StatelessWidget {
  const _ComponentTableCell(
    this.value, {
    required this.flex,
    this.header = false,
    this.emphasis = false,
  });

  final String value;
  final int flex;
  final bool header;
  final bool emphasis;

  @override
  Widget build(BuildContext context) => Expanded(
    flex: flex,
    child: Padding(
      padding: const EdgeInsets.only(right: 12),
      child: Text(
        value,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(
          color: emphasis ? LedgerFlowDesign.info : null,
          fontSize: header ? 12 : 13,
          fontWeight: header || emphasis ? FontWeight.w700 : FontWeight.w500,
        ),
      ),
    ),
  );
}

class _InlineDetailHeading extends StatelessWidget {
  const _InlineDetailHeading(this.value);

  final String value;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: Text(
      value,
      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
    ),
  );
}

enum ProfileKind { calculation, allocation, businessDate }

extension on ProfileKind {
  String get singular => switch (this) {
    ProfileKind.calculation => 'calculation profile',
    ProfileKind.allocation => 'allocation profile',
    ProfileKind.businessDate => 'business-date profile',
  };

  String get title => switch (this) {
    ProfileKind.calculation => 'Calculation profiles',
    ProfileKind.allocation => 'Allocation profiles',
    ProfileKind.businessDate => 'Business-date profiles',
  };

  String get resource => switch (this) {
    ProfileKind.calculation => 'calculation-profiles',
    ProfileKind.allocation => 'allocation-profiles',
    ProfileKind.businessDate => 'business-date-profiles',
  };

  String get versionResource => switch (this) {
    ProfileKind.calculation => 'calculation-profile-versions',
    ProfileKind.allocation => 'allocation-profile-versions',
    ProfileKind.businessDate => 'business-date-profile-versions',
  };
}

class ProfileManagementHub extends StatefulWidget {
  const ProfileManagementHub({
    required this.data,
    required this.live,
    required this.onMutation,
    super.key,
  });

  final WorkspaceData data;
  final bool live;
  final WorkspaceMutation onMutation;

  @override
  State<ProfileManagementHub> createState() => _ProfileManagementHubState();
}

class _ProfileManagementHubState extends State<ProfileManagementHub> {
  ProfileKind _kind = ProfileKind.calculation;

  @override
  Widget build(BuildContext context) {
    final records = _kind == ProfileKind.calculation
        ? widget.data['calculationProfiles']
        : widget.data['allocationProfiles'];
    return PageCanvas(
      title: 'Calculation & allocation profiles',
      subtitle:
          'Build versioned rules once, publish reviewed definitions, and attach them to components and rate rows.',
      trailing: SegmentedButton<ProfileKind>(
        segments: const [
          ButtonSegment(
            value: ProfileKind.calculation,
            label: Text('Calculation'),
            icon: Icon(Icons.calculate_outlined),
          ),
          ButtonSegment(
            value: ProfileKind.allocation,
            label: Text('Allocation'),
            icon: Icon(Icons.call_split_outlined),
          ),
        ],
        selected: {_kind},
        onSelectionChanged: (selection) =>
            setState(() => _kind = selection.single),
      ),
      children: [
        if (!widget.live) const _LiveWriteNotice(),
        if (!widget.live) const SizedBox(height: 16),
        _ModulePrimer(
          title: _kind == ProfileKind.calculation
              ? 'How calculation profiles are used'
              : 'How allocation profiles are used',
          text: _kind == ProfileKind.calculation
              ? 'A calculation profile resolves measurable factors and applies a flat or rate-times-product formula. Published versions are immutable, preserving the exact rule used by historical charges.'
              : 'An allocation profile distributes a source charge from shipment, container, or house level to its final posting level. Drivers define how value is apportioned at each hierarchy boundary.',
          points: _kind == ProfileKind.calculation
              ? const [
                  'Create a profile with an initial draft version.',
                  'Add ordered factor resolvers, then publish the reviewed draft.',
                  'Select the profile as a component or rate-row default.',
                ]
              : const [
                  'Choose source and final posting levels.',
                  'Set the driver used for each hierarchy transition.',
                  'Publish before assigning the profile as a reusable default.',
                ],
        ),
        const SizedBox(height: 16),
        _ProfileManager(
          key: ValueKey(_kind),
          kind: _kind,
          records: records,
          components: widget.data['components'],
          rateBooks: widget.data['rateBooks'],
          live: widget.live,
          onMutation: widget.onMutation,
        ),
      ],
    );
  }
}

class FxDateManagementHub extends StatefulWidget {
  const FxDateManagementHub({
    required this.data,
    required this.live,
    required this.onMutation,
    required this.loadAssignments,
    super.key,
  });

  final WorkspaceData data;
  final bool live;
  final WorkspaceMutation onMutation;
  final AssignmentLoader? loadAssignments;

  @override
  State<FxDateManagementHub> createState() => _FxDateManagementHubState();
}

class _FxDateManagementHubState extends State<FxDateManagementHub> {
  bool _showDates = true;

  @override
  Widget build(BuildContext context) => PageCanvas(
    title: 'FX rates & business dates',
    subtitle:
        'Govern the conversion rate and the ordered business-date fallback used during charge calculation.',
    trailing: SegmentedButton<bool>(
      segments: const [
        ButtonSegment(
          value: true,
          label: Text('Business dates'),
          icon: Icon(Icons.event_repeat_outlined),
        ),
        ButtonSegment(
          value: false,
          label: Text('FX rates'),
          icon: Icon(Icons.currency_exchange_outlined),
        ),
      ],
      selected: {_showDates},
      onSelectionChanged: (selection) =>
          setState(() => _showDates = selection.single),
    ),
    children: [
      if (_showDates) ...[
        if (!widget.live) const _LiveWriteNotice(),
        if (!widget.live) const SizedBox(height: 16),
        const _ModulePrimer(
          title: 'How business-date profiles are used',
          text:
              'A business-date profile is an ordered fallback chain. At runtime LedgerFlow tries each date key until one resolves, then records the selected key and value in calculation provenance.',
          points: [
            'Publish a profile version after reviewing its ordered steps.',
            'Assign it globally or to a company, customer, vendor, forwarder, or carrier.',
            'A component may inherit the assignment or explicitly override it.',
          ],
        ),
        const SizedBox(height: 16),
        _ProfileManager(
          kind: ProfileKind.businessDate,
          records: widget.data['dateProfiles'],
          components: widget.data['components'],
          rateBooks: widget.data['rateBooks'],
          live: widget.live,
          onMutation: widget.onMutation,
          loadAssignments: widget.loadAssignments,
        ),
      ] else ...[
        if (!widget.live) const _LiveWriteNotice(),
        if (!widget.live) const SizedBox(height: 16),
        const _ModulePrimer(
          title: 'How FX rates are used',
          text:
              'FX resolution uses the business date, currency pair, source priority, and permitted fallback strategy. LedgerFlow records whether conversion was direct or inverse for auditability.',
          points: [
            'Rates are directional and date-effective.',
            'Source metadata and conversion method remain visible in provenance.',
            'Use the API for rate-source and bulk rate maintenance.',
          ],
        ),
        const SizedBox(height: 16),
        _FxRateManager(
          records: widget.data['fxRates'],
          live: widget.live,
          onMutation: widget.onMutation,
        ),
      ],
    ],
  );
}

class _ProfileManager extends StatefulWidget {
  const _ProfileManager({
    required this.kind,
    required this.records,
    required this.components,
    required this.rateBooks,
    required this.live,
    required this.onMutation,
    this.loadAssignments,
    super.key,
  });

  final ProfileKind kind;
  final List<JsonMap> records;
  final List<JsonMap> components;
  final List<JsonMap> rateBooks;
  final bool live;
  final WorkspaceMutation onMutation;
  final AssignmentLoader? loadAssignments;

  @override
  State<_ProfileManager> createState() => _ProfileManagerState();
}

class _ProfileManagerState extends State<_ProfileManager> {
  final _search = TextEditingController();
  int? _selectedId;
  List<JsonMap> _assignments = const [];
  bool _loadingAssignments = false;

  @override
  void initState() {
    super.initState();
    _selectedId = _id(widget.records.firstOrNull);
    _search.addListener(_refresh);
    _queueAssignmentLoad();
  }

  @override
  void didUpdateWidget(covariant _ProfileManager oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selectedId != null &&
        !widget.records.any((record) => _id(record) == _selectedId)) {
      _selectedId = _id(widget.records.firstOrNull);
    }
    if (widget.kind == ProfileKind.businessDate &&
        (oldWidget.records != widget.records ||
            oldWidget.loadAssignments != widget.loadAssignments)) {
      _queueAssignmentLoad();
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
    if (query.isEmpty) return widget.records;
    return widget.records
        .where(
          (record) => [
            _value(record, 'profile_code'),
            _value(record, 'profile_name'),
            _value(record, 'description'),
          ].any((value) => value.toLowerCase().contains(query)),
        )
        .toList(growable: false);
  }

  JsonMap? get _selected => widget.records.cast<JsonMap?>().firstWhere(
    (record) => _id(record) == _selectedId,
    orElse: () => widget.records.firstOrNull,
  );

  @override
  Widget build(BuildContext context) {
    final selected = _selected;
    return ResponsiveColumns(
      leftFlex: 4,
      rightFlex: 5,
      left: SurfaceCard(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          widget.kind.title,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      FilledButton.icon(
                        onPressed: widget.live ? _createProfile : null,
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('New'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _search,
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search),
                      labelText: 'Search profiles',
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            if (_filtered.isEmpty)
              const EmptyState(message: 'No profiles match the search.')
            else
              ..._filtered.map((profile) {
                final id = _id(profile);
                final published = profile['published_version_number'];
                return InkWell(
                  onTap: () {
                    setState(() => _selectedId = id);
                    _queueAssignmentLoad();
                  },
                  child: Container(
                    color: id == _selectedId
                        ? const Color(0xFFE8F7F6)
                        : Colors.transparent,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 14,
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                _value(profile, 'profile_code'),
                                style: const TextStyle(
                                  color: LedgerFlowDesign.info,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                _value(profile, 'profile_name'),
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 12),
                              ),
                            ],
                          ),
                        ),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            StatusPill(
                              published == null ? 'DRAFT' : 'PUBLISHED',
                            ),
                            const SizedBox(height: 4),
                            Text(
                              published == null ? 'No release' : 'v$published',
                              style: const TextStyle(
                                fontSize: 11,
                                color: LedgerFlowDesign.muted,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
      right: selected == null
          ? const SurfaceCard(
              child: EmptyState(message: 'Select a profile to inspect.'),
            )
          : _profileInspector(selected),
    );
  }

  Widget _profileInspector(JsonMap profile) {
    final versions = _maps(profile['versions'])
      ..sort(
        (left, right) => (_idValue(right['version_number']) ?? 0).compareTo(
          _idValue(left['version_number']) ?? 0,
        ),
      );
    final profileId = _id(profile);
    final referenceKey = switch (widget.kind) {
      ProfileKind.calculation => 'default_calculation_profile_id',
      ProfileKind.allocation => 'allocation_profile_id',
      ProfileKind.businessDate => 'business_date_profile_id',
    };
    final componentUses = widget.components
        .where((record) => _idValue(record[referenceKey]) == profileId)
        .length;
    final rateReferenceKey = widget.kind == ProfileKind.calculation
        ? 'calculation_profile_id'
        : referenceKey;
    final rateUses = _countReferences(
      widget.rateBooks,
      rateReferenceKey,
      profileId,
    );
    return Column(
      children: [
        SurfaceCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionHeading(
                title: _value(profile, 'profile_name'),
                subtitle: _value(profile, 'profile_code'),
                action: OutlinedButton.icon(
                  onPressed: widget.live ? () => _editHeader(profile) : null,
                  icon: const Icon(Icons.edit_outlined, size: 17),
                  label: const Text('Edit'),
                ),
              ),
              const SizedBox(height: 12),
              Text(
                _value(
                  profile,
                  'description',
                  fallback: 'Reusable ${widget.kind.singular}.',
                ),
                style: const TextStyle(color: LedgerFlowDesign.muted),
              ),
              const SizedBox(height: 14),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  StatusPill(
                    profile['published_version_number'] == null
                        ? 'DRAFT'
                        : 'PUBLISHED',
                  ),
                  _UsageChip(
                    icon: Icons.account_tree_outlined,
                    label: '$componentUses component references',
                  ),
                  if (rateUses > 0)
                    _UsageChip(
                      icon: Icons.menu_book_outlined,
                      label: '$rateUses rate references',
                    ),
                ],
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
                padding: const EdgeInsets.all(16),
                child: SectionHeading(
                  title: 'Version history',
                  subtitle:
                      'Published versions are immutable; create a new draft for changes.',
                  action: FilledButton.icon(
                    onPressed: widget.live
                        ? () => _createVersion(profile, versions.firstOrNull)
                        : null,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('New draft'),
                  ),
                ),
              ),
              if (versions.isEmpty)
                const EmptyState(message: 'No versions are available.')
              else
                ...versions.map(
                  (version) => _VersionPanel(
                    kind: widget.kind,
                    version: version,
                    live: widget.live,
                    onEdit: () => _editVersion(version),
                    onPublish: () => _publishVersion(profile, version),
                  ),
                ),
            ],
          ),
        ),
        if (widget.kind == ProfileKind.businessDate) ...[
          const SizedBox(height: 16),
          _assignmentPanel(profile),
        ],
      ],
    );
  }

  Widget _assignmentPanel(JsonMap profile) => SurfaceCard(
    padding: EdgeInsets.zero,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: SectionHeading(
            title: 'Assignment scopes',
            subtitle:
                'Lower priority numbers win when multiple active assignments match.',
            action: FilledButton.icon(
              onPressed:
                  widget.live && profile['published_version_number'] != null
                  ? () => _editAssignment(profile)
                  : null,
              icon: const Icon(Icons.add, size: 18),
              label: const Text('Assign'),
            ),
          ),
        ),
        if (_loadingAssignments)
          const Padding(
            padding: EdgeInsets.all(24),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (_assignments.isEmpty)
          const EmptyState(
            message:
                'No scoped assignments. Components can still explicitly reference this profile.',
          )
        else
          ..._assignments.map(
            (assignment) => ListTile(
              leading: const Icon(
                Icons.filter_alt_outlined,
                color: LedgerFlowDesign.teal,
              ),
              title: Text(
                '${_value(assignment, 'scope_type')}: ${_value(assignment, 'scope_id', fallback: 'all')}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              subtitle: Text(
                '${_value(assignment, 'shipment_scope')} - priority ${_value(assignment, 'priority')}',
              ),
              trailing: PopupMenuButton<String>(
                onSelected: (action) {
                  if (action == 'edit') {
                    _editAssignment(profile, assignment);
                  } else {
                    _removeAssignment(assignment);
                  }
                },
                itemBuilder: (_) => [
                  PopupMenuItem(
                    value: 'edit',
                    enabled: widget.live,
                    child: const Text('Edit assignment'),
                  ),
                  PopupMenuItem(
                    value: 'remove',
                    enabled: widget.live && assignment['is_active'] != false,
                    child: const Text('Remove'),
                  ),
                ],
              ),
            ),
          ),
      ],
    ),
  );

  void _queueAssignmentLoad() {
    if (widget.kind != ProfileKind.businessDate) return;
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadAssignments());
  }

  Future<void> _loadAssignments() async {
    final profile = _selected;
    final id = _id(profile);
    if (!mounted || id == null) return;
    if (widget.loadAssignments == null) {
      setState(() {
        _assignments = _maps(profile?['assignments']);
        _loadingAssignments = false;
      });
      return;
    }
    setState(() => _loadingAssignments = true);
    try {
      final records = await widget.loadAssignments!(id);
      if (mounted && id == _selectedId) setState(() => _assignments = records);
    } finally {
      if (mounted) setState(() => _loadingAssignments = false);
    }
  }

  Future<void> _createProfile() async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _ProfileCreateDialog(kind: widget.kind),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'POST',
      path: '/api/v1/charge-management/${widget.kind.resource}',
      body: payload,
      successMessage: '${_sentence(widget.kind.singular)} created.',
    );
  }

  Future<void> _editHeader(JsonMap profile) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _ProfileHeaderDialog(kind: widget.kind, profile: profile),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'PUT',
      path:
          '/api/v1/charge-management/${widget.kind.resource}/${profile['id']}',
      body: payload,
      successMessage: '${_sentence(widget.kind.singular)} updated.',
    );
  }

  Future<void> _createVersion(JsonMap profile, JsonMap? source) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _VersionDialog(kind: widget.kind, version: source),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'POST',
      path:
          '/api/v1/charge-management/${widget.kind.resource}/${profile['id']}/versions',
      body: payload,
      successMessage: 'Draft version created.',
    );
  }

  Future<void> _editVersion(JsonMap version) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _VersionDialog(kind: widget.kind, version: version),
    );
    if (payload == null) return;
    await widget.onMutation(
      method: 'PUT',
      path:
          '/api/v1/charge-management/${widget.kind.versionResource}/${version['id']}',
      body: payload,
      successMessage: 'Draft version updated.',
    );
  }

  Future<void> _publishVersion(JsonMap profile, JsonMap version) async {
    final confirmed = await _confirm(
      context,
      title: 'Publish version ${version['version_number']}?',
      message:
          'This makes the version available for calculation and retires the previously published version. Published content cannot be edited.',
      action: 'Publish',
    );
    if (!confirmed) return;
    await widget.onMutation(
      method: 'POST',
      path:
          '/api/v1/charge-management/${widget.kind.versionResource}/${version['id']}/publish',
      successMessage: '${_sentence(widget.kind.singular)} published.',
    );
  }

  Future<void> _editAssignment(JsonMap profile, [JsonMap? assignment]) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _AssignmentDialog(assignment: assignment),
    );
    if (payload == null) return;
    final creating = assignment == null;
    final changed = await widget.onMutation(
      method: creating ? 'POST' : 'PUT',
      path: creating
          ? '/api/v1/charge-management/business-date-profiles/${profile['id']}/assignments'
          : '/api/v1/charge-management/business-date-profile-assignments/${assignment['id']}',
      body: payload,
      successMessage: creating
          ? 'Business-date assignment created.'
          : 'Business-date assignment updated.',
    );
    if (changed) await _loadAssignments();
  }

  Future<void> _removeAssignment(JsonMap assignment) async {
    final confirmed = await _confirm(
      context,
      title: 'Remove assignment?',
      message:
          'The scope will stop selecting this business-date profile for new resolutions.',
      action: 'Remove',
    );
    if (!confirmed) return;
    final changed = await widget.onMutation(
      method: 'DELETE',
      path:
          '/api/v1/charge-management/business-date-profile-assignments/${assignment['id']}',
      successMessage: 'Business-date assignment removed.',
    );
    if (changed) await _loadAssignments();
  }
}

class _ComponentDialog extends StatefulWidget {
  const _ComponentDialog({
    required this.component,
    required this.calculationProfiles,
    required this.allocationProfiles,
    required this.businessDateProfiles,
  });

  final JsonMap? component;
  final List<JsonMap> calculationProfiles;
  final List<JsonMap> allocationProfiles;
  final List<JsonMap> businessDateProfiles;

  @override
  State<_ComponentDialog> createState() => _ComponentDialogState();
}

class _ComponentDialogState extends State<_ComponentDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _code;
  late final TextEditingController _name;
  late String _category;
  late String _context;
  late String _basis;
  late String _role;
  late String _dateBasis;
  late String _datePolicy;
  late bool _isTax;
  late bool _active;
  int? _calculationProfileId;
  int? _allocationProfileId;
  int? _allocationVersionId;
  int? _dateProfileId;

  @override
  void initState() {
    super.initState();
    final value = widget.component ?? const <String, dynamic>{};
    _code = TextEditingController(
      text: _value(value, 'component_code', fallback: ''),
    );
    _name = TextEditingController(
      text: _value(value, 'component_name', fallback: ''),
    );
    _category = _value(value, 'category', fallback: 'ACCESSORIAL');
    _context = _value(value, 'charge_context', fallback: 'TRANSPORT');
    _basis = _value(value, 'calculation_basis', fallback: 'FLAT');
    _role = _value(value, 'default_party_role', fallback: 'BOTH');
    _dateBasis = _value(value, 'charge_date_basis', fallback: 'DOCUMENT_DATE');
    _datePolicy = _value(
      value,
      'business_date_policy_mode',
      fallback: 'LEGACY_BASIS',
    );
    _isTax = value['is_tax'] == true;
    _active = value['is_active'] != false;
    _calculationProfileId = _validProfileId(
      widget.calculationProfiles,
      value['default_calculation_profile_id'],
    );
    _allocationProfileId = _validProfileId(
      widget.allocationProfiles,
      value['allocation_profile_id'],
    );
    _allocationVersionId = _idValue(value['allocation_profile_version_id']);
    _dateProfileId = _validProfileId(
      widget.businessDateProfiles,
      value['business_date_profile_id'],
    );
  }

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      widget.component == null ? 'Create component' : 'Edit component',
    ),
    content: SizedBox(
      width: 760,
      child: Form(
        key: _formKey,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 650),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _DialogSection(
                  title: 'Identity',
                  text:
                      'Codes and categories identify the charge. Context locates it in the operational lifecycle; DESTINATION means the import or arrival side.',
                ),
                _TwoFields(
                  left: _requiredField(_code, 'Component code'),
                  right: _requiredField(_name, 'Component name'),
                ),
                const SizedBox(height: 12),
                _TwoFields(
                  left: _dropdown(
                    label: 'Category',
                    value: _category,
                    values: referenceValuesWithCurrent(
                      chargeCategoryValues,
                      _category,
                    ),
                    onChanged: (value) => setState(() => _category = value!),
                  ),
                  right: _dropdown(
                    label: 'Charge context',
                    value: _context,
                    values: referenceValuesWithCurrent(
                      chargeContextValues,
                      _context,
                    ),
                    onChanged: (value) => setState(() => _context = value!),
                  ),
                ),
                const SizedBox(height: 18),
                const _DialogSection(
                  title: 'Commercial defaults',
                  text:
                      'These defaults may be overridden by a selected rate row.',
                ),
                _TwoFields(
                  left: _dropdown(
                    label: 'Default party role',
                    value: _role,
                    values: const ['PAYER', 'PAYEE', 'BOTH'],
                    onChanged: (value) => setState(() => _role = value!),
                  ),
                  right: _dropdown(
                    label: 'Calculation basis',
                    value: _basis,
                    values: referenceValuesWithCurrent(
                      chargeCalculationBasisValues,
                      _basis,
                    ),
                    onChanged: (value) => setState(() => _basis = value!),
                  ),
                ),
                const SizedBox(height: 12),
                _ProfileDropdown(
                  label: 'Calculation profile',
                  value: _calculationProfileId,
                  records: widget.calculationProfiles,
                  onChanged: (value) =>
                      setState(() => _calculationProfileId = value),
                ),
                const SizedBox(height: 12),
                _ProfileDropdown(
                  label: 'Allocation profile',
                  value: _allocationProfileId,
                  records: widget.allocationProfiles,
                  onChanged: (value) => setState(() {
                    _allocationProfileId = value;
                    _allocationVersionId = null;
                  }),
                ),
                const SizedBox(height: 18),
                const _DialogSection(
                  title: 'Business date',
                  text:
                      'Use legacy basis directly, inherit a scoped assignment, or pin an explicit profile.',
                ),
                _TwoFields(
                  left: _dropdown(
                    label: 'Date policy',
                    value: _datePolicy,
                    values: const [
                      'LEGACY_BASIS',
                      'INHERIT_PROFILE',
                      'PROFILE_OVERRIDE',
                    ],
                    onChanged: (value) => setState(() => _datePolicy = value!),
                  ),
                  right: _dropdown(
                    label: 'Legacy date basis',
                    value: _dateBasis,
                    values: const [
                      'DOCUMENT_DATE',
                      'SHIPMENT_DEPARTURE_DATE',
                      'SHIPMENT_ARRIVAL_DATE',
                      'HOUSE_BILL_ISSUE_DATE',
                      'MANUAL',
                    ],
                    onChanged: (value) => setState(() => _dateBasis = value!),
                  ),
                ),
                const SizedBox(height: 12),
                _ProfileDropdown(
                  label: 'Business-date profile',
                  value: _dateProfileId,
                  records: widget.businessDateProfiles,
                  enabled: _datePolicy == 'PROFILE_OVERRIDE',
                  requiredSelection: true,
                  onChanged: (value) => setState(() => _dateProfileId = value),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 28,
                  children: [
                    SizedBox(
                      width: 350,
                      child: SwitchListTile.adaptive(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Tax classification'),
                        subtitle: const Text(
                          'Classifies the component for reporting; calculation still comes from its rate or profile.',
                        ),
                        value: _isTax,
                        onChanged: (value) => setState(() => _isTax = value),
                      ),
                    ),
                    SizedBox(
                      width: 220,
                      child: SwitchListTile.adaptive(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Active'),
                        value: _active,
                        onChanged: (value) => setState(() => _active = value),
                      ),
                    ),
                  ],
                ),
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
      FilledButton(onPressed: _save, child: const Text('Save component')),
    ],
  );

  void _save() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.pop<JsonMap>(context, {
      'component_code': _code.text.trim(),
      'component_name': _name.text.trim(),
      'category': _category,
      'default_party_role': _role,
      'charge_context': _context,
      'calculation_basis': _basis,
      'charge_date_basis': _dateBasis,
      'business_date_policy_mode': _datePolicy,
      'business_date_profile_id': _datePolicy == 'PROFILE_OVERRIDE'
          ? _dateProfileId
          : null,
      'allocation_profile_id': _allocationProfileId,
      'allocation_profile_version_id': _allocationVersionId,
      'default_calculation_profile_id': _calculationProfileId,
      'is_tax': _isTax,
      'is_active': _active,
    });
  }
}

class _ProfileCreateDialog extends StatefulWidget {
  const _ProfileCreateDialog({required this.kind});

  final ProfileKind kind;

  @override
  State<_ProfileCreateDialog> createState() => _ProfileCreateDialogState();
}

class _ProfileCreateDialogState extends State<_ProfileCreateDialog> {
  final _formKey = GlobalKey<FormState>();
  final _versionKey = GlobalKey<_VersionEditorState>();
  final _code = TextEditingController();
  final _name = TextEditingController();
  final _description = TextEditingController();
  bool _active = true;
  String? _error;

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text('Create ${widget.kind.singular}'),
    content: SizedBox(
      width: 820,
      child: Form(
        key: _formKey,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 680),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _DialogSection(
                  title: 'Profile identity',
                  text: 'The profile groups an ordered history of versions.',
                ),
                _TwoFields(
                  left: _requiredField(_code, 'Profile code'),
                  right: _requiredField(_name, 'Profile name'),
                ),
                if (widget.kind != ProfileKind.allocation) ...[
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _description,
                    maxLines: 2,
                    decoration: const InputDecoration(labelText: 'Description'),
                  ),
                ],
                if (widget.kind == ProfileKind.calculation)
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Active'),
                    value: _active,
                    onChanged: (value) => setState(() => _active = value),
                  ),
                const Divider(height: 32),
                const _DialogSection(
                  title: 'Initial draft version',
                  text: 'Save the profile first, then publish after review.',
                ),
                _VersionEditor(key: _versionKey, kind: widget.kind),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _error!,
                    style: const TextStyle(color: LedgerFlowDesign.danger),
                  ),
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
      FilledButton(onPressed: _save, child: const Text('Create profile')),
    ],
  );

  void _save() {
    if (!_formKey.currentState!.validate()) return;
    try {
      final payload = <String, dynamic>{
        'profile_code': _code.text.trim(),
        'profile_name': _name.text.trim(),
        if (widget.kind != ProfileKind.allocation)
          'description': _nullable(_description.text),
        if (widget.kind == ProfileKind.calculation) 'is_active': _active,
        'initial_version': _versionKey.currentState!.payload(),
      };
      Navigator.pop<JsonMap>(context, payload);
    } on FormatException catch (error) {
      setState(() => _error = error.message);
    }
  }
}

class _ProfileHeaderDialog extends StatefulWidget {
  const _ProfileHeaderDialog({required this.kind, required this.profile});

  final ProfileKind kind;
  final JsonMap profile;

  @override
  State<_ProfileHeaderDialog> createState() => _ProfileHeaderDialogState();
}

class _ProfileHeaderDialogState extends State<_ProfileHeaderDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _code;
  late final TextEditingController _name;
  late final TextEditingController _description;
  late bool _active;

  @override
  void initState() {
    super.initState();
    _code = TextEditingController(
      text: _value(widget.profile, 'profile_code', fallback: ''),
    );
    _name = TextEditingController(
      text: _value(widget.profile, 'profile_name', fallback: ''),
    );
    _description = TextEditingController(
      text: _value(widget.profile, 'description', fallback: ''),
    );
    _active = widget.profile['is_active'] != false;
  }

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text('Edit ${widget.kind.singular}'),
    content: SizedBox(
      width: 620,
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _TwoFields(
              left: _requiredField(_code, 'Profile code'),
              right: _requiredField(_name, 'Profile name'),
            ),
            if (widget.kind != ProfileKind.allocation) ...[
              const SizedBox(height: 12),
              TextFormField(
                controller: _description,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'Description'),
              ),
            ],
            if (widget.kind == ProfileKind.calculation)
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Active'),
                value: _active,
                onChanged: (value) => setState(() => _active = value),
              ),
          ],
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
          Navigator.pop<JsonMap>(context, {
            'profile_code': _code.text.trim(),
            'profile_name': _name.text.trim(),
            if (widget.kind != ProfileKind.allocation)
              'description': _nullable(_description.text),
            if (widget.kind == ProfileKind.calculation) 'is_active': _active,
          });
        },
        child: const Text('Save changes'),
      ),
    ],
  );
}

class _VersionDialog extends StatefulWidget {
  const _VersionDialog({required this.kind, this.version});

  final ProfileKind kind;
  final JsonMap? version;

  @override
  State<_VersionDialog> createState() => _VersionDialogState();
}

class _VersionDialogState extends State<_VersionDialog> {
  final _formKey = GlobalKey<FormState>();
  final _editorKey = GlobalKey<_VersionEditorState>();
  String? _error;

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      widget.version?['status'] == 'DRAFT'
          ? 'Edit draft version'
          : 'Create draft version',
    ),
    content: SizedBox(
      width: 820,
      child: Form(
        key: _formKey,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 680),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _VersionEditor(
                  key: _editorKey,
                  kind: widget.kind,
                  initial: widget.version,
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _error!,
                    style: const TextStyle(color: LedgerFlowDesign.danger),
                  ),
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
      FilledButton(
        onPressed: () {
          if (!_formKey.currentState!.validate()) return;
          try {
            final payload = _editorKey.currentState!.payload();
            if (widget.version?['status'] == 'DRAFT') {
              final lockVersion = _idValue(widget.version?['lock_version']);
              if (lockVersion != null) {
                payload['expected_lock_version'] = lockVersion;
              }
            }
            Navigator.pop<JsonMap>(context, payload);
          } on FormatException catch (error) {
            setState(() => _error = error.message);
          }
        },
        child: const Text('Save draft'),
      ),
    ],
  );
}

class _VersionEditor extends StatefulWidget {
  const _VersionEditor({required this.kind, this.initial, super.key});

  final ProfileKind kind;
  final JsonMap? initial;

  @override
  State<_VersionEditor> createState() => _VersionEditorState();
}

class _VersionEditorState extends State<_VersionEditor> {
  late String _applicationLevel;
  late String _method;
  late final TextEditingController _effectiveFrom;
  late final TextEditingController _effectiveTo;
  late final TextEditingController _rateUom;
  late List<_FactorDraft> _factors;

  late String _sourceLevel;
  late String _postingLevel;
  late final TextEditingController _sourceDriver;
  late final TextEditingController _itemDriver;
  late final TextEditingController _quantityUom;
  late String _missingDriverPolicy;
  late final TextEditingController _settings;
  late final TextEditingController _notes;

  late List<_DateStepDraft> _steps;

  @override
  void initState() {
    super.initState();
    final initial = widget.initial ?? const <String, dynamic>{};
    _applicationLevel = _value(
      initial,
      'application_level',
      fallback: 'SHIPMENT',
    );
    _method = _value(
      initial,
      'calculation_method',
      fallback: 'RATE_TIMES_PRODUCT',
    );
    _effectiveFrom = TextEditingController(
      text: _value(initial, 'effective_from', fallback: ''),
    );
    _effectiveTo = TextEditingController(
      text: _value(initial, 'effective_to', fallback: ''),
    );
    _rateUom = TextEditingController(
      text: _value(initial, 'rate_uom', fallback: ''),
    );
    _factors = _maps(initial['factors']).map(_FactorDraft.fromJson).toList();
    if (_factors.isEmpty && widget.kind == ProfileKind.calculation) {
      _factors = [_FactorDraft.empty(1)];
    }

    _sourceLevel = _value(initial, 'source_level', fallback: 'SHIPMENT');
    _postingLevel = _value(
      initial,
      'final_posting_level',
      fallback: 'PO_SCHEDULE_LINE',
    );
    _sourceDriver = TextEditingController(
      text: _value(initial, 'source_to_house_driver', fallback: ''),
    );
    _itemDriver = TextEditingController(
      text: _value(initial, 'house_to_item_driver', fallback: ''),
    );
    _quantityUom = TextEditingController(
      text: _value(initial, 'default_quantity_uom', fallback: ''),
    );
    _missingDriverPolicy = _value(
      initial,
      'missing_driver_policy',
      fallback: 'BLOCK',
    );
    _settings = TextEditingController(
      text: const JsonEncoder.withIndent(
        '  ',
      ).convert(initial['settings_json'] ?? <String, dynamic>{}),
    );
    _notes = TextEditingController(
      text: _value(initial, 'notes', fallback: ''),
    );

    _steps = _maps(initial['steps']).map(_DateStepDraft.fromJson).toList();
    if (_steps.isEmpty && widget.kind == ProfileKind.businessDate) {
      _steps = [_DateStepDraft.empty(1)];
    }
  }

  @override
  void dispose() {
    _effectiveFrom.dispose();
    _effectiveTo.dispose();
    _rateUom.dispose();
    for (final factor in _factors) {
      factor.dispose();
    }
    _sourceDriver.dispose();
    _itemDriver.dispose();
    _quantityUom.dispose();
    _settings.dispose();
    _notes.dispose();
    for (final step in _steps) {
      step.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => switch (widget.kind) {
    ProfileKind.calculation => _calculationFields(),
    ProfileKind.allocation => _allocationFields(),
    ProfileKind.businessDate => _businessDateFields(),
  };

  Widget _calculationFields() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _TwoFields(
        left: _dropdown(
          label: 'Application level',
          value: _applicationLevel,
          values: const ['SHIPMENT', 'CONTAINER', 'HOUSE', 'PO_SCHEDULE_LINE'],
          onChanged: (value) => setState(() => _applicationLevel = value!),
        ),
        right: _dropdown(
          label: 'Calculation method',
          value: _method,
          values: const ['FLAT_AMOUNT', 'RATE_TIMES_PRODUCT'],
          onChanged: (value) => setState(() => _method = value!),
        ),
      ),
      const SizedBox(height: 12),
      _TwoFields(
        left: TextFormField(
          controller: _effectiveFrom,
          decoration: const InputDecoration(
            labelText: 'Effective from',
            hintText: 'YYYY-MM-DD',
          ),
          validator: _optionalIsoDate,
        ),
        right: TextFormField(
          controller: _effectiveTo,
          decoration: const InputDecoration(
            labelText: 'Effective to',
            hintText: 'YYYY-MM-DD',
          ),
          validator: _optionalIsoDate,
        ),
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _rateUom,
        decoration: const InputDecoration(
          labelText: 'Rate UOM',
          helperText: 'For example USD/CONTAINER or USD/KG',
        ),
      ),
      const SizedBox(height: 20),
      SectionHeading(
        title: 'Factor resolvers',
        subtitle: 'Ordered inputs multiplied by the selected rate.',
        action: OutlinedButton.icon(
          onPressed: () => setState(
            () => _factors.add(_FactorDraft.empty(_factors.length + 1)),
          ),
          icon: const Icon(Icons.add, size: 17),
          label: const Text('Add factor'),
        ),
      ),
      const SizedBox(height: 10),
      ...List.generate(_factors.length, (index) {
        final factor = _factors[index];
        return Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: LedgerFlowDesign.canvas,
            border: Border.all(color: LedgerFlowDesign.border),
            borderRadius: BorderRadius.circular(9),
          ),
          child: Column(
            children: [
              Row(
                children: [
                  Text(
                    'Factor ${index + 1}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const Spacer(),
                  IconButton(
                    tooltip: 'Remove factor',
                    onPressed: _factors.length == 1
                        ? null
                        : () => setState(
                            () => _factors.removeAt(index).dispose(),
                          ),
                    icon: const Icon(Icons.delete_outline, size: 19),
                  ),
                ],
              ),
              _TwoFields(
                left: _requiredField(factor.code, 'Factor code'),
                right: _requiredField(factor.label, 'Factor label'),
              ),
              const SizedBox(height: 10),
              _TwoFields(
                left: DropdownButtonFormField<String>(
                  initialValue: factor.resolver,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Resolver'),
                  items: _factorResolvers
                      .map(
                        (value) =>
                            DropdownMenuItem(value: value, child: Text(value)),
                      )
                      .toList(),
                  onChanged: (value) =>
                      setState(() => factor.resolver = value!),
                ),
                right: TextFormField(
                  controller: factor.uom,
                  decoration: const InputDecoration(labelText: 'UOM'),
                ),
              ),
              const SizedBox(height: 10),
              TextFormField(
                controller: factor.defaultValue,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(
                  labelText: 'Default value',
                  helperText:
                      'Optional fallback used when the resolver provides no value.',
                ),
                validator: (value) {
                  final text = value?.trim() ?? '';
                  return text.isEmpty || double.tryParse(text) != null
                      ? null
                      : 'Enter a number';
                },
              ),
              Material(
                color: Colors.transparent,
                child: SwitchListTile.adaptive(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Required input'),
                  value: factor.required,
                  onChanged: (value) => setState(() => factor.required = value),
                ),
              ),
            ],
          ),
        );
      }),
    ],
  );

  Widget _allocationFields() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _TwoFields(
        left: _dropdown(
          label: 'Source level',
          value: _sourceLevel,
          values: const ['SHIPMENT', 'CONTAINER', 'HOUSE'],
          onChanged: (value) => setState(() => _sourceLevel = value!),
        ),
        right: _dropdown(
          label: 'Final posting level',
          value: _postingLevel,
          values: const ['HOUSE', 'PO_SCHEDULE_LINE'],
          onChanged: (value) => setState(() => _postingLevel = value!),
        ),
      ),
      const SizedBox(height: 12),
      _TwoFields(
        left: TextFormField(
          controller: _sourceDriver,
          decoration: const InputDecoration(
            labelText: 'Source-to-house driver',
            hintText: 'WEIGHT, VOLUME, QUANTITY...',
          ),
          validator: (value) =>
              _sourceLevel != 'HOUSE' && (value == null || value.trim().isEmpty)
              ? 'Required for $_sourceLevel allocation'
              : null,
        ),
        right: TextFormField(
          controller: _itemDriver,
          decoration: const InputDecoration(
            labelText: 'House-to-item driver',
            hintText: 'VALUE, QUANTITY, WEIGHT...',
          ),
          validator: (value) =>
              _postingLevel == 'PO_SCHEDULE_LINE' &&
                  (value == null || value.trim().isEmpty)
              ? 'Required for item-level posting'
              : null,
        ),
      ),
      const SizedBox(height: 12),
      _TwoFields(
        left: TextFormField(
          controller: _effectiveFrom,
          decoration: const InputDecoration(
            labelText: 'Effective from',
            hintText: 'YYYY-MM-DD',
          ),
          validator: _optionalIsoDate,
        ),
        right: TextFormField(
          controller: _effectiveTo,
          decoration: const InputDecoration(
            labelText: 'Effective to',
            hintText: 'YYYY-MM-DD',
          ),
          validator: _optionalIsoDate,
        ),
      ),
      const SizedBox(height: 12),
      _TwoFields(
        left: TextFormField(
          controller: _quantityUom,
          decoration: const InputDecoration(labelText: 'Default quantity UOM'),
        ),
        right: _dropdown(
          label: 'Missing driver policy',
          value: _missingDriverPolicy,
          values: const ['BLOCK', 'EQUAL'],
          onChanged: (value) => setState(() => _missingDriverPolicy = value!),
        ),
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _settings,
        minLines: 3,
        maxLines: 7,
        style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
        decoration: const InputDecoration(
          labelText: 'Advanced settings JSON',
          helperText:
              'Portable adapter-specific driver settings; use {} when none.',
        ),
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _notes,
        maxLines: 2,
        decoration: const InputDecoration(labelText: 'Version notes'),
      ),
    ],
  );

  Widget _businessDateFields() => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      _TwoFields(
        left: TextFormField(
          controller: _effectiveFrom,
          decoration: const InputDecoration(
            labelText: 'Effective from',
            hintText: 'YYYY-MM-DD',
          ),
          validator: _optionalIsoDate,
        ),
        right: TextFormField(
          controller: _effectiveTo,
          decoration: const InputDecoration(
            labelText: 'Effective to',
            hintText: 'YYYY-MM-DD',
          ),
          validator: _optionalIsoDate,
        ),
      ),
      const SizedBox(height: 18),
      SectionHeading(
        title: 'Ordered date fallback',
        subtitle: 'The first available date wins.',
        action: OutlinedButton.icon(
          onPressed: () => setState(
            () => _steps.add(_DateStepDraft.empty(_steps.length + 1)),
          ),
          icon: const Icon(Icons.add, size: 17),
          label: const Text('Add step'),
        ),
      ),
      const SizedBox(height: 10),
      ...List.generate(_steps.length, (index) {
        final step = _steps[index];
        final dateKeyField = DropdownButtonFormField<String>(
          initialValue: _businessDateKeys.contains(step.dateKey.text)
              ? step.dateKey.text
              : _businessDateKeys.first,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Date key'),
          items: _businessDateKeys
              .map(
                (value) => DropdownMenuItem(value: value, child: Text(value)),
              )
              .toList(),
          onChanged: (value) => step.dateKey.text = value!,
        );
        final notesField = TextFormField(
          controller: step.notes,
          decoration: const InputDecoration(labelText: 'Notes'),
        );
        final removeButton = IconButton(
          tooltip: 'Remove step',
          onPressed: _steps.length == 1
              ? null
              : () => setState(() => _steps.removeAt(index).dispose()),
          icon: const Icon(Icons.delete_outline),
        );
        return Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: LedgerFlowDesign.canvas,
            border: Border.all(color: LedgerFlowDesign.border),
            borderRadius: BorderRadius.circular(9),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final sequence = CircleAvatar(
                radius: 15,
                backgroundColor: LedgerFlowDesign.teal,
                foregroundColor: Colors.white,
                child: Text(
                  '${index + 1}',
                  style: const TextStyle(fontSize: 11),
                ),
              );
              if (constraints.maxWidth < 520) {
                return Column(
                  children: [
                    Row(
                      children: [
                        sequence,
                        const SizedBox(width: 10),
                        Expanded(child: dateKeyField),
                        removeButton,
                      ],
                    ),
                    const SizedBox(height: 10),
                    notesField,
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  sequence,
                  const SizedBox(width: 12),
                  Expanded(child: dateKeyField),
                  const SizedBox(width: 10),
                  Expanded(child: notesField),
                  removeButton,
                ],
              );
            },
          ),
        );
      }),
      const SizedBox(height: 4),
      TextFormField(
        controller: _notes,
        maxLines: 2,
        decoration: const InputDecoration(labelText: 'Version notes'),
      ),
    ],
  );

  JsonMap payload() => switch (widget.kind) {
    ProfileKind.calculation => {
      'effective_from': _nullable(_effectiveFrom.text),
      'effective_to': _nullable(_effectiveTo.text),
      'application_level': _applicationLevel,
      'calculation_method': _method,
      'rate_uom': _nullable(_rateUom.text),
      'missing_factor_policy': 'BLOCK',
      'factors': List.generate(
        _factors.length,
        (index) => _factors[index].payload(index + 1),
      ),
    },
    ProfileKind.allocation => {
      'effective_from': _nullable(_effectiveFrom.text),
      'effective_to': _nullable(_effectiveTo.text),
      'source_level': _sourceLevel,
      'source_to_house_driver': _nullable(_sourceDriver.text),
      'house_to_item_driver': _nullable(_itemDriver.text),
      'final_posting_level': _postingLevel,
      'default_quantity_uom': _nullable(_quantityUom.text),
      'missing_driver_policy': _missingDriverPolicy,
      'settings_json': _jsonObject(_settings.text),
      'notes': _nullable(_notes.text),
    },
    ProfileKind.businessDate => {
      'effective_from': _nullable(_effectiveFrom.text),
      'effective_to': _nullable(_effectiveTo.text),
      'steps': List.generate(
        _steps.length,
        (index) => _steps[index].payload(index + 1),
      ),
      'notes': _nullable(_notes.text),
    },
  };
}

class _AssignmentDialog extends StatefulWidget {
  const _AssignmentDialog({this.assignment});

  final JsonMap? assignment;

  @override
  State<_AssignmentDialog> createState() => _AssignmentDialogState();
}

class _AssignmentDialogState extends State<_AssignmentDialog> {
  final _formKey = GlobalKey<FormState>();
  late String _scopeType;
  late String _shipmentScope;
  late final TextEditingController _scopeId;
  late final TextEditingController _priority;
  late bool _active;

  @override
  void initState() {
    super.initState();
    final value = widget.assignment ?? const <String, dynamic>{};
    _scopeType = _value(value, 'scope_type', fallback: 'GLOBAL');
    _shipmentScope = _value(value, 'shipment_scope', fallback: 'OCEAN_HOUSE');
    _scopeId = TextEditingController(
      text: _value(value, 'scope_id', fallback: ''),
    );
    _priority = TextEditingController(
      text: _value(value, 'priority', fallback: '100'),
    );
    _active = value['is_active'] != false;
  }

  @override
  void dispose() {
    _scopeId.dispose();
    _priority.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text(
      widget.assignment == null
          ? 'Assign business-date profile'
          : 'Edit assignment',
    ),
    content: SizedBox(
      width: 620,
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _TwoFields(
              left: _dropdown(
                label: 'Scope type',
                value: _scopeType,
                values: const [
                  'GLOBAL',
                  'COMPANY',
                  'CUSTOMER',
                  'VENDOR',
                  'FORWARDER',
                  'CARRIER',
                ],
                onChanged: (value) => setState(() => _scopeType = value!),
              ),
              right: TextFormField(
                controller: _scopeId,
                enabled: _scopeType != 'GLOBAL',
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Scope ID',
                  helperText: _scopeType == 'GLOBAL'
                      ? 'Not used for a global assignment'
                      : 'Host-system numeric identifier',
                ),
                validator: (value) =>
                    _scopeType != 'GLOBAL' &&
                        int.tryParse(value?.trim() ?? '') == null
                    ? 'A numeric scope ID is required'
                    : null,
              ),
            ),
            const SizedBox(height: 12),
            _TwoFields(
              left: _dropdown(
                label: 'Shipment scope',
                value: _shipmentScope,
                values: const ['OCEAN_HOUSE', 'AIR_HOUSE', 'ROAD_SHIPMENT'],
                onChanged: (value) => setState(() => _shipmentScope = value!),
              ),
              right: TextFormField(
                controller: _priority,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Priority'),
                validator: (value) => int.tryParse(value?.trim() ?? '') == null
                    ? 'Enter a whole number'
                    : null,
              ),
            ),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text('Active assignment'),
              value: _active,
              onChanged: (value) => setState(() => _active = value),
            ),
          ],
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
          final scopeId = _scopeType == 'GLOBAL'
              ? null
              : int.tryParse(_scopeId.text.trim());
          final priority = int.tryParse(_priority.text.trim());
          Navigator.pop<JsonMap>(context, {
            'scope_type': _scopeType,
            'scope_id': scopeId,
            'shipment_scope': _shipmentScope,
            'business_purpose': 'EXCHANGE_RATE_DATE',
            'priority': priority!,
            'is_active': _active,
          });
        },
        child: const Text('Save assignment'),
      ),
    ],
  );
}

class _VersionPanel extends StatelessWidget {
  const _VersionPanel({
    required this.kind,
    required this.version,
    required this.live,
    required this.onEdit,
    required this.onPublish,
  });

  final ProfileKind kind;
  final JsonMap version;
  final bool live;
  final VoidCallback onEdit;
  final VoidCallback onPublish;

  @override
  Widget build(BuildContext context) {
    final draft = version['status'] == 'DRAFT';
    return Container(
      decoration: const BoxDecoration(
        border: Border(top: BorderSide(color: LedgerFlowDesign.border)),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 10,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                'Version ${_value(version, 'version_number')}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              StatusPill(_value(version, 'status')),
              if (draft)
                TextButton.icon(
                  onPressed: live ? onEdit : null,
                  icon: const Icon(Icons.edit_outlined, size: 17),
                  label: const Text('Edit draft'),
                ),
              if (draft)
                FilledButton.icon(
                  onPressed: live ? onPublish : null,
                  icon: const Icon(Icons.publish_outlined, size: 17),
                  label: const Text('Publish'),
                ),
            ],
          ),
          const SizedBox(height: 11),
          Wrap(
            spacing: 22,
            runSpacing: 8,
            children: _versionFacts(
              kind,
              version,
            ).map((fact) => _Fact(label: fact.$1, value: fact.$2)).toList(),
          ),
          if (kind == ProfileKind.calculation) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 7,
              runSpacing: 7,
              children: _maps(version['factors'])
                  .map(
                    (factor) => Chip(
                      label: Text(
                        '${_value(factor, 'factor_code')} - ${_value(factor, 'resolver')}',
                        style: const TextStyle(fontSize: 11),
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
          if (kind == ProfileKind.businessDate) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 7,
              runSpacing: 7,
              children: _maps(version['steps'])
                  .map(
                    (step) => Chip(
                      avatar: CircleAvatar(
                        child: Text(_value(step, 'step_number')),
                      ),
                      label: Text(_value(step, 'date_key')),
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _FxRateManager extends StatefulWidget {
  const _FxRateManager({
    required this.records,
    required this.live,
    required this.onMutation,
  });

  final List<JsonMap> records;
  final bool live;
  final WorkspaceMutation onMutation;

  @override
  State<_FxRateManager> createState() => _FxRateManagerState();
}

class _FxRateManagerState extends State<_FxRateManager> {
  final _search = TextEditingController();
  int? _selectedId;

  @override
  void initState() {
    super.initState();
    _selectedId = _id(widget.records.firstOrNull);
    _search.addListener(_refresh);
  }

  @override
  void didUpdateWidget(covariant _FxRateManager oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_selectedId != null &&
        !widget.records.any((record) => _id(record) == _selectedId)) {
      _selectedId = _id(widget.records.firstOrNull);
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
    if (query.isEmpty) return widget.records;
    return widget.records
        .where((record) {
          final pair =
              '${_value(record, 'source_currency')} ${_value(record, 'target_currency')}';
          return [
            _value(record, 'source_code'),
            _value(record, 'source_name'),
            pair,
            _value(record, 'rate_date'),
            _value(record, 'rate_type'),
            _value(record, 'conversion_method'),
          ].any((value) => value.toLowerCase().contains(query));
        })
        .toList(growable: false);
  }

  JsonMap? get _selected => widget.records.cast<JsonMap?>().firstWhere(
    (record) => _id(record) == _selectedId,
    orElse: () => widget.records.firstOrNull,
  );

  List<_FxSourceOption> get _sources {
    final byId = <int, _FxSourceOption>{};
    for (final record in widget.records) {
      final sourceId = _idValue(record['source_id']);
      if (sourceId == null || byId.containsKey(sourceId)) continue;
      byId[sourceId] = _FxSourceOption(
        id: sourceId,
        code: _value(record, 'source_code', fallback: 'SOURCE_$sourceId'),
        name: _value(record, 'source_name', fallback: 'FX Source #$sourceId'),
      );
    }
    final values = byId.values.toList()
      ..sort((left, right) {
        final codeCompare = left.code.compareTo(right.code);
        return codeCompare == 0 ? left.id.compareTo(right.id) : codeCompare;
      });
    return values;
  }

  @override
  Widget build(BuildContext context) {
    final selected = _selected;
    final sources = _sources;
    return ResponsiveColumns(
      leftFlex: 5,
      rightFlex: 3,
      left: SurfaceCard(
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'FX rate register',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              sources.isEmpty
                                  ? 'Loaded rates do not expose any reusable source catalogue yet. Use the API to maintain sources, then create rates against the numeric source ID.'
                                  : 'Select a maintained rate to inspect or update the live register.',
                              style: const TextStyle(
                                fontSize: 12,
                                color: LedgerFlowDesign.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      FilledButton.icon(
                        onPressed: widget.live ? () => _editRate() : null,
                        icon: const Icon(Icons.add, size: 18),
                        label: const Text('New rate'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _search,
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search),
                      labelText: 'Search source, pair, date, or method',
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            if (_filtered.isEmpty)
              EmptyState(
                message: widget.records.isEmpty
                    ? 'No FX rates are available.'
                    : 'No FX rates match the search.',
              )
            else
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  showCheckboxColumn: false,
                  columns: const [
                    DataColumn(label: Text('Source')),
                    DataColumn(label: Text('Pair')),
                    DataColumn(label: Text('Rate date')),
                    DataColumn(label: Text('Rate')),
                    DataColumn(label: Text('Type')),
                    DataColumn(label: Text('Method')),
                    DataColumn(label: Text('Status')),
                  ],
                  rows: _filtered.map((record) {
                    final id = _id(record);
                    final active = record['is_active'] != false;
                    return DataRow(
                      selected: id == _selectedId,
                      onSelectChanged: (_) => setState(() => _selectedId = id),
                      cells: [
                        DataCell(Text(_value(record, 'source_code'))),
                        DataCell(
                          Text(
                            '${_value(record, 'source_currency')} / ${_value(record, 'target_currency')}',
                          ),
                        ),
                        DataCell(Text(_value(record, 'rate_date'))),
                        DataCell(Text(_value(record, 'rate'))),
                        DataCell(Text(_value(record, 'rate_type'))),
                        DataCell(Text(_value(record, 'conversion_method'))),
                        DataCell(StatusPill(active ? 'ACTIVE' : 'INACTIVE')),
                      ],
                    );
                  }).toList(),
                ),
              ),
          ],
        ),
      ),
      right: selected == null
          ? SurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const EmptyState(
                    message: 'Select a rate to inspect, edit, or deactivate.',
                  ),
                  if (sources.isEmpty) ...[
                    const SizedBox(height: 12),
                    const _DialogSection(
                      title: 'Source catalogue',
                      text:
                          'FX sources are maintained through the API. When no rates are loaded yet, enter the numeric source ID provided by the source-maintenance endpoint.',
                    ),
                  ],
                ],
              ),
            )
          : _fxInspector(selected, sources),
    );
  }

  Widget _fxInspector(JsonMap rate, List<_FxSourceOption> sources) {
    final active = rate['is_active'] != false;
    return SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SectionHeading(
            title:
                '${_value(rate, 'source_currency')} -> ${_value(rate, 'target_currency')}',
            subtitle:
                '${_value(rate, 'source_code')} on ${_value(rate, 'rate_date')}',
            action: PopupMenuButton<String>(
              tooltip: 'FX rate actions',
              onSelected: (action) {
                if (action == 'edit') _editRate(rate);
                if (action == 'deactivate') _deactivate(rate);
              },
              itemBuilder: (_) => [
                PopupMenuItem(
                  value: 'edit',
                  enabled: widget.live,
                  child: const Text('Edit rate'),
                ),
                PopupMenuItem(
                  value: 'deactivate',
                  enabled: widget.live && active,
                  child: const Text('Deactivate'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          StatusPill(active ? 'ACTIVE' : 'INACTIVE'),
          const SizedBox(height: 14),
          DetailRow(label: 'Source code', value: _value(rate, 'source_code')),
          DetailRow(label: 'Source name', value: _value(rate, 'source_name')),
          DetailRow(label: 'Source ID', value: _value(rate, 'source_id')),
          DetailRow(
            label: 'Currency pair',
            value:
                '${_value(rate, 'source_currency')} / ${_value(rate, 'target_currency')}',
          ),
          DetailRow(label: 'Rate date', value: _value(rate, 'rate_date')),
          DetailRow(label: 'Rate', value: _value(rate, 'rate')),
          DetailRow(label: 'Rate type', value: _value(rate, 'rate_type')),
          DetailRow(
            label: 'Conversion method',
            value: _value(rate, 'conversion_method'),
          ),
          const SizedBox(height: 12),
          if (sources.isEmpty)
            const _DialogSection(
              title: 'Source maintenance',
              text:
                  'This workspace edits live rates only. Add or rename FX sources through the API, then refresh this screen to reuse those source codes here.',
            ),
          const SizedBox(height: 4),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: widget.live ? () => _editRate(rate) : null,
              icon: const Icon(Icons.edit_outlined),
              label: const Text('Edit rate'),
            ),
          ),
          if (active) ...[
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: TextButton.icon(
                onPressed: widget.live ? () => _deactivate(rate) : null,
                icon: const Icon(Icons.block_outlined),
                label: const Text('Deactivate'),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _editRate([JsonMap? rate]) async {
    final payload = await showDialog<JsonMap>(
      context: context,
      builder: (_) => _FxRateDialog(initial: rate, sourceOptions: _sources),
    );
    if (payload == null || !mounted) return;
    final creating = rate == null;
    await widget.onMutation(
      method: creating ? 'POST' : 'PUT',
      path: creating
          ? '/api/v1/charge-management/fx-rates'
          : '/api/v1/charge-management/fx-rates/${rate['id']}',
      body: payload,
      successMessage: creating ? 'FX rate created.' : 'FX rate updated.',
    );
  }

  Future<void> _deactivate(JsonMap rate) async {
    final confirmed = await _confirm(
      context,
      title: 'Deactivate FX rate?',
      message:
          '${_value(rate, 'source_code')} ${_value(rate, 'source_currency')}/${_value(rate, 'target_currency')} on ${_value(rate, 'rate_date')} will remain available for audit but no longer resolve for active use.',
      action: 'Deactivate',
    );
    if (!confirmed) return;
    await widget.onMutation(
      method: 'DELETE',
      path: '/api/v1/charge-management/fx-rates/${rate['id']}',
      successMessage: 'FX rate deactivated.',
    );
  }
}

class _FxSourceOption {
  const _FxSourceOption({
    required this.id,
    required this.code,
    required this.name,
  });

  final int id;
  final String code;
  final String name;

  String get label => '$code (#$id)';
}

class _FxRateDialog extends StatefulWidget {
  const _FxRateDialog({required this.sourceOptions, this.initial});

  final List<_FxSourceOption> sourceOptions;
  final JsonMap? initial;

  @override
  State<_FxRateDialog> createState() => _FxRateDialogState();
}

class _FxRateDialogState extends State<_FxRateDialog> {
  final _formKey = GlobalKey<FormState>();
  late int? _selectedSourceId;
  late final TextEditingController _manualSourceId;
  late final TextEditingController _sourceCurrency;
  late final TextEditingController _targetCurrency;
  late final TextEditingController _rateDate;
  late final TextEditingController _rate;
  late final TextEditingController _conversionMethod;
  late String _rateType;

  bool get _hasSourceOptions => widget.sourceOptions.isNotEmpty;

  @override
  void initState() {
    super.initState();
    final initial = widget.initial ?? const <String, dynamic>{};
    final initialSourceId = _idValue(initial['source_id']);
    _selectedSourceId =
        widget.sourceOptions.any((option) => option.id == initialSourceId)
        ? initialSourceId
        : widget.sourceOptions.firstOrNull?.id;
    _manualSourceId = TextEditingController(
      text: initialSourceId?.toString() ?? '',
    );
    _sourceCurrency = TextEditingController(
      text: _value(initial, 'source_currency', fallback: ''),
    );
    _targetCurrency = TextEditingController(
      text: _value(initial, 'target_currency', fallback: ''),
    );
    _rateDate = TextEditingController(
      text: _value(initial, 'rate_date', fallback: ''),
    );
    _rate = TextEditingController(text: _value(initial, 'rate', fallback: ''));
    _conversionMethod = TextEditingController(
      text: _value(initial, 'conversion_method', fallback: 'DIRECT'),
    );
    _rateType = _value(initial, 'rate_type', fallback: 'MID');
  }

  @override
  void dispose() {
    _manualSourceId.dispose();
    _sourceCurrency.dispose();
    _targetCurrency.dispose();
    _rateDate.dispose();
    _rate.dispose();
    _conversionMethod.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final editing = widget.initial != null;
    return AlertDialog(
      title: Text(editing ? 'Edit FX rate' : 'Create FX rate'),
      content: SizedBox(
        width: 560,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _DialogSection(
                  title: 'Maintained conversion rate',
                  text:
                      'Store a directional rate with an effective date, source, and method so charge calculation can reproduce the exact conversion used.',
                ),
                if (_hasSourceOptions) ...[
                  DropdownButtonFormField<int>(
                    initialValue: _selectedSourceId,
                    isExpanded: true,
                    decoration: const InputDecoration(
                      labelText: 'Source',
                      helperText:
                          'Loaded rate sources. Manage the catalogue via API.',
                    ),
                    items: widget.sourceOptions
                        .map(
                          (option) => DropdownMenuItem<int>(
                            value: option.id,
                            child: Text(
                              option.label,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        )
                        .toList(),
                    validator: (value) =>
                        value == null ? 'Source is required' : null,
                    onChanged: (value) =>
                        setState(() => _selectedSourceId = value),
                  ),
                ] else ...[
                  const _DialogSection(
                    title: 'Source reference',
                    text:
                        'FX rate sources are maintained via API. Enter the numeric source ID that this rate should reference.',
                  ),
                  TextFormField(
                    controller: _manualSourceId,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Source ID'),
                    validator: _sourceIdValidator,
                  ),
                ],
                const SizedBox(height: 12),
                _TwoFields(
                  left: TextFormField(
                    controller: _sourceCurrency,
                    textCapitalization: TextCapitalization.characters,
                    decoration: const InputDecoration(
                      labelText: 'Source currency',
                      hintText: 'EUR',
                    ),
                    validator: (value) =>
                        _currencyCodeValidator(value, label: 'Source currency'),
                  ),
                  right: TextFormField(
                    controller: _targetCurrency,
                    textCapitalization: TextCapitalization.characters,
                    decoration: const InputDecoration(
                      labelText: 'Target currency',
                      hintText: 'USD',
                    ),
                    validator: (value) {
                      final code = _currencyCodeValidator(
                        value,
                        label: 'Target currency',
                      );
                      if (code != null) return code;
                      final source = _sourceCurrency.text.trim().toUpperCase();
                      final target = value?.trim().toUpperCase() ?? '';
                      return source == target ? 'Currencies must differ' : null;
                    },
                  ),
                ),
                const SizedBox(height: 12),
                _TwoFields(
                  left: TextFormField(
                    controller: _rateDate,
                    decoration: const InputDecoration(
                      labelText: 'Rate date',
                      hintText: 'YYYY-MM-DD',
                    ),
                    validator: _requiredIsoDate,
                  ),
                  right: TextFormField(
                    controller: _rate,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(labelText: 'Rate'),
                    validator: _positiveRateValidator,
                  ),
                ),
                const SizedBox(height: 12),
                _TwoFields(
                  left: DropdownButtonFormField<String>(
                    initialValue:
                        const [
                          'MID',
                          'BUY',
                          'SELL',
                          'CUSTOM',
                        ].contains(_rateType)
                        ? _rateType
                        : 'MID',
                    decoration: const InputDecoration(labelText: 'Rate type'),
                    items: const ['MID', 'BUY', 'SELL', 'CUSTOM']
                        .map(
                          (value) => DropdownMenuItem(
                            value: value,
                            child: Text(value),
                          ),
                        )
                        .toList(),
                    onChanged: (value) =>
                        setState(() => _rateType = value ?? 'MID'),
                  ),
                  right: TextFormField(
                    controller: _conversionMethod,
                    textCapitalization: TextCapitalization.characters,
                    decoration: const InputDecoration(
                      labelText: 'Conversion method',
                      helperText: 'Examples: DIRECT, PUBLISHED, TREASURY',
                    ),
                    validator: (value) {
                      final text = value?.trim() ?? '';
                      return text.isEmpty
                          ? 'Conversion method is required'
                          : null;
                    },
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
          onPressed: _save,
          child: Text(editing ? 'Save rate' : 'Create rate'),
        ),
      ],
    );
  }

  void _save() {
    if (!_formKey.currentState!.validate()) return;
    final payload = <String, dynamic>{
      'source_id': _hasSourceOptions
          ? _selectedSourceId
          : int.parse(_manualSourceId.text.trim()),
      'source_currency': _sourceCurrency.text.trim().toUpperCase(),
      'target_currency': _targetCurrency.text.trim().toUpperCase(),
      'rate_date': _rateDate.text.trim(),
      'rate': _rate.text.trim(),
      'rate_type': _rateType,
      'conversion_method': _conversionMethod.text.trim().toUpperCase(),
      'is_active': widget.initial?['is_active'] != false,
      'metadata_json': widget.initial?['metadata_json'] ?? <String, dynamic>{},
    };
    Navigator.pop(context, payload);
  }
}

class _ModulePrimer extends StatelessWidget {
  const _ModulePrimer({
    required this.title,
    required this.text,
    required this.points,
  });

  final String title;
  final String text;
  final List<String> points;

  @override
  Widget build(BuildContext context) => SurfaceCard(
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: const Color(0xFFE8F7F6),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(
            Icons.lightbulb_outline,
            color: LedgerFlowDesign.teal,
          ),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 5),
              Text(
                text,
                style: const TextStyle(
                  color: LedgerFlowDesign.muted,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 10),
              LayoutBuilder(
                builder: (context, constraints) {
                  if (constraints.maxWidth < 700) {
                    return Column(
                      children: [
                        for (final point in points)
                          Padding(
                            padding: const EdgeInsets.only(bottom: 7),
                            child: _PrimerPoint(text: point),
                          ),
                      ],
                    );
                  }
                  return Wrap(
                    spacing: 16,
                    runSpacing: 7,
                    children: points
                        .map(
                          (point) => SizedBox(
                            width: 310,
                            child: _PrimerPoint(text: point),
                          ),
                        )
                        .toList(),
                  );
                },
              ),
            ],
          ),
        ),
      ],
    ),
  );
}

class _PrimerPoint extends StatelessWidget {
  const _PrimerPoint({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      const Padding(
        padding: EdgeInsets.only(top: 1),
        child: Icon(
          Icons.check_circle_outline,
          size: 16,
          color: LedgerFlowDesign.success,
        ),
      ),
      const SizedBox(width: 6),
      Expanded(child: Text(text, style: const TextStyle(fontSize: 12))),
    ],
  );
}

class _LiveWriteNotice extends StatelessWidget {
  const _LiveWriteNotice();

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
    decoration: BoxDecoration(
      color: const Color(0xFFFFF7E8),
      border: Border.all(color: const Color(0xFFF2CC8F)),
      borderRadius: BorderRadius.circular(10),
    ),
    child: const Row(
      children: [
        Icon(Icons.lock_outline, color: LedgerFlowDesign.warning, size: 20),
        SizedBox(width: 10),
        Expanded(
          child: Text(
            'Demo mode is read-only. Connect a bearer-authenticated API to create, edit, publish, and assign records.',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ),
      ],
    ),
  );
}

class _DialogSection extends StatelessWidget {
  const _DialogSection({required this.title, required this.text});

  final String title;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
        const SizedBox(height: 3),
        Text(
          text,
          style: const TextStyle(fontSize: 12, color: LedgerFlowDesign.muted),
        ),
      ],
    ),
  );
}

class _TwoFields extends StatelessWidget {
  const _TwoFields({required this.left, required this.right});

  final Widget left;
  final Widget right;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      if (constraints.maxWidth < 560) {
        return Column(children: [left, const SizedBox(height: 12), right]);
      }
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: left),
          const SizedBox(width: 12),
          Expanded(child: right),
        ],
      );
    },
  );
}

class _ProfileDropdown extends StatelessWidget {
  const _ProfileDropdown({
    required this.label,
    required this.value,
    required this.records,
    required this.onChanged,
    this.enabled = true,
    this.requiredSelection = false,
  });

  final String label;
  final int? value;
  final List<JsonMap> records;
  final ValueChanged<int?> onChanged;
  final bool enabled;
  final bool requiredSelection;

  @override
  Widget build(BuildContext context) => DropdownButtonFormField<int?>(
    initialValue: value,
    decoration: InputDecoration(labelText: label),
    items: [
      DropdownMenuItem<int?>(
        value: null,
        child: Text(
          enabled && requiredSelection
              ? 'Select a published profile'
              : 'Inherit / none',
        ),
      ),
      ...records
          .where((record) => record['published_version_number'] != null)
          .map(
            (record) => DropdownMenuItem<int?>(
              value: _id(record),
              child: Text(
                '${_value(record, 'profile_code')} - ${_value(record, 'profile_name')}',
              ),
            ),
          ),
    ],
    validator: (value) => enabled && requiredSelection && value == null
        ? '$label is required for this policy'
        : null,
    onChanged: enabled ? onChanged : null,
  );
}

class _UsageChip extends StatelessWidget {
  const _UsageChip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    decoration: BoxDecoration(
      color: LedgerFlowDesign.canvas,
      border: Border.all(color: LedgerFlowDesign.border),
      borderRadius: BorderRadius.circular(999),
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 15, color: LedgerFlowDesign.muted),
        const SizedBox(width: 6),
        Text(label, style: const TextStyle(fontSize: 11)),
      ],
    ),
  );
}

class _Fact extends StatelessWidget {
  const _Fact({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        label,
        style: const TextStyle(fontSize: 10, color: LedgerFlowDesign.muted),
      ),
      const SizedBox(height: 2),
      Text(
        value,
        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
      ),
    ],
  );
}

class _FactorDraft {
  _FactorDraft({
    required this.code,
    required this.label,
    required this.uom,
    required this.resolver,
    required this.required,
    required this.defaultValue,
  });

  factory _FactorDraft.empty(int sequence) => _FactorDraft(
    code: TextEditingController(text: 'FACTOR_$sequence'),
    label: TextEditingController(text: 'Factor $sequence'),
    uom: TextEditingController(),
    resolver: 'MANUAL',
    required: true,
    defaultValue: TextEditingController(),
  );

  factory _FactorDraft.fromJson(JsonMap value) => _FactorDraft(
    code: TextEditingController(
      text: _value(value, 'factor_code', fallback: ''),
    ),
    label: TextEditingController(
      text: _value(value, 'factor_label', fallback: ''),
    ),
    uom: TextEditingController(text: _value(value, 'uom', fallback: '')),
    resolver: _value(value, 'resolver', fallback: 'MANUAL'),
    required: value['is_required'] != false,
    defaultValue: TextEditingController(
      text: _value(value, 'default_value', fallback: ''),
    ),
  );

  final TextEditingController code;
  final TextEditingController label;
  final TextEditingController uom;
  String resolver;
  bool required;
  final TextEditingController defaultValue;

  JsonMap payload(int sequence) => {
    'sequence': sequence,
    'factor_code': code.text.trim(),
    'factor_label': label.text.trim(),
    'resolver': resolver,
    'uom': _nullable(uom.text),
    'is_required': required,
    'default_value': _nullable(defaultValue.text),
  };

  void dispose() {
    code.dispose();
    label.dispose();
    uom.dispose();
    defaultValue.dispose();
  }
}

class _DateStepDraft {
  _DateStepDraft({required this.dateKey, required this.notes});

  factory _DateStepDraft.empty(int sequence) => _DateStepDraft(
    dateKey: TextEditingController(
      text: sequence == 1 ? 'DOCUMENT_DATE' : 'SHIPMENT_PLANNED_DEPARTURE_DATE',
    ),
    notes: TextEditingController(),
  );

  factory _DateStepDraft.fromJson(JsonMap value) => _DateStepDraft(
    dateKey: TextEditingController(
      text: _value(value, 'date_key', fallback: ''),
    ),
    notes: TextEditingController(text: _value(value, 'notes', fallback: '')),
  );

  final TextEditingController dateKey;
  final TextEditingController notes;

  JsonMap payload(int step) => {
    'step_number': step,
    'date_key': dateKey.text.trim(),
    'notes': _nullable(notes.text),
  };

  void dispose() {
    dateKey.dispose();
    notes.dispose();
  }
}

const _factorResolvers = [
  'MANUAL',
  'TARGET_COUNT',
  'CONTAINER_COUNT',
  'HOUSE_COUNT',
  'PO_SCHEDULE_LINE_COUNT',
  'QUANTITY',
  'WEIGHT',
  'VOLUME',
  'CHARGEABLE_WEIGHT',
  'DURATION_HOURS',
  'DURATION_DAYS',
  'FIXED_VALUE',
];

const _businessDateKeys = [
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
];

Widget _requiredField(TextEditingController controller, String label) =>
    TextFormField(
      controller: controller,
      decoration: InputDecoration(labelText: label),
      validator: (value) =>
          value == null || value.trim().isEmpty ? '$label is required' : null,
    );

Widget _dropdown({
  required String label,
  required String value,
  required List<String> values,
  required ValueChanged<String?> onChanged,
}) => DropdownButtonFormField<String>(
  initialValue: values.contains(value) ? value : values.first,
  isExpanded: true,
  decoration: InputDecoration(labelText: label),
  items: values
      .map((item) => DropdownMenuItem(value: item, child: Text(item)))
      .toList(),
  onChanged: onChanged,
);

List<(String, String)> _versionFacts(
  ProfileKind kind,
  JsonMap version,
) => switch (kind) {
  ProfileKind.calculation => [
    ('Level', _value(version, 'application_level')),
    ('Method', _value(version, 'calculation_method')),
    ('Rate UOM', _value(version, 'rate_uom', fallback: 'Not fixed')),
    (
      'Effective',
      '${_value(version, 'effective_from', fallback: 'Any')} to ${_value(version, 'effective_to', fallback: 'open')}',
    ),
  ],
  ProfileKind.allocation => [
    (
      'Flow',
      '${_value(version, 'source_level')} -> ${_value(version, 'final_posting_level')}',
    ),
    (
      'To house',
      _value(version, 'source_to_house_driver', fallback: 'Not required'),
    ),
    (
      'To item',
      _value(version, 'house_to_item_driver', fallback: 'Not required'),
    ),
    (
      'Quantity UOM',
      _value(version, 'default_quantity_uom', fallback: 'Inherit'),
    ),
  ],
  ProfileKind.businessDate => [
    ('Steps', '${_maps(version['steps']).length}'),
    ('Notes', _value(version, 'notes', fallback: 'No version notes')),
  ],
};

Future<bool> _confirm(
  BuildContext context, {
  required String title,
  required String message,
  required String action,
}) async =>
    await showDialog<bool>(
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
    ) ??
    false;

String? _optionalIsoDate(String? value) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return null;
  return RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(text)
      ? null
      : 'Use YYYY-MM-DD';
}

String? _requiredIsoDate(String? value) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return 'Rate date is required';
  return _optionalIsoDate(text);
}

String? _currencyCodeValidator(String? value, {required String label}) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return '$label is required';
  return RegExp(r'^[A-Za-z]{3}$').hasMatch(text)
      ? null
      : '$label must be a 3-letter code';
}

String? _positiveRateValidator(String? value) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return 'Rate is required';
  final parsed = double.tryParse(text);
  if (parsed == null) return 'Enter a valid rate';
  return parsed > 0 ? null : 'Enter a positive rate';
}

String? _sourceIdValidator(String? value) {
  final text = value?.trim() ?? '';
  if (text.isEmpty) return 'Source ID is required';
  final parsed = int.tryParse(text);
  if (parsed == null || parsed <= 0) return 'Enter a positive source ID';
  return null;
}

Map<String, dynamic> _jsonObject(String source) {
  try {
    final value = jsonDecode(source.trim().isEmpty ? '{}' : source);
    if (value is Map<String, dynamic>) return value;
  } on FormatException {
    // The message below is intentionally stable for form feedback and tests.
  }
  throw const FormatException('Advanced settings must be a valid JSON object.');
}

String _profileName(List<JsonMap> records, dynamic id) {
  final target = _idValue(id);
  if (target == null) return 'Inherit / none';
  final match = records.cast<JsonMap?>().firstWhere(
    (record) => _id(record) == target,
    orElse: () => null,
  );
  return match == null
      ? 'Profile #$target'
      : '${_value(match, 'profile_code')} - ${_value(match, 'profile_name')}';
}

int? _validProfileId(List<JsonMap> records, dynamic value) {
  final id = _idValue(value);
  return records.any(
        (record) =>
            _id(record) == id && record['published_version_number'] != null,
      )
      ? id
      : null;
}

int _countReferences(List<JsonMap> records, String key, int? id) {
  if (id == null) return 0;
  var count = 0;
  void visit(dynamic value) {
    if (value is Map) {
      if (_idValue(value[key]) == id) count++;
      for (final child in value.values) {
        visit(child);
      }
    } else if (value is List) {
      for (final child in value) {
        visit(child);
      }
    }
  }

  visit(records);
  return count;
}

List<JsonMap> _maps(dynamic value) {
  if (value is! List) return [];
  return value.whereType<Map<String, dynamic>>().map(JsonMap.from).toList();
}

int? _id(JsonMap? value) => _idValue(value?['id']);

int? _idValue(dynamic value) => value is int ? value : int.tryParse('$value');

String _value(JsonMap? record, String key, {String fallback = '-'}) {
  final value = record?[key];
  if (value == null || value.toString().trim().isEmpty) return fallback;
  return value.toString();
}

String? _nullable(String value) => value.trim().isEmpty ? null : value.trim();

String _sentence(String value) =>
    '${value[0].toUpperCase()}${value.substring(1)}';
