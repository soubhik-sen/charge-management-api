import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../core/design.dart';
import '../data/workspace_data.dart';
import 'management_workspaces.dart';
import 'workspace_pages.dart';

class LedgerFlowShell extends StatefulWidget {
  const LedgerFlowShell({super.key});

  @override
  State<LedgerFlowShell> createState() => _LedgerFlowShellState();
}

class _LedgerFlowShellState extends State<LedgerFlowShell> {
  static const _destinations = <_Destination>[
    _Destination('Overview', Icons.home_outlined),
    _Destination('Quotes', Icons.request_quote_outlined),
    _Destination('Charge documents', Icons.folder_copy_outlined),
    _Destination('Invoices', Icons.receipt_long_outlined),
    _Destination('Rate books', Icons.menu_book_outlined),
    _Destination('Components', Icons.account_tree_outlined),
    _Destination('Profiles', Icons.tune_outlined),
    _Destination('FX & dates', Icons.currency_exchange_outlined),
  ];

  final _scaffoldKey = GlobalKey<ScaffoldState>();
  WorkspaceData _data = WorkspaceData.demo();
  int _selectedIndex = 0;
  bool _loading = false;
  bool _live = false;
  String _apiUrl = LedgerFlowApiClient.defaultBaseUrl;
  String? _lastError;
  LedgerFlowApiClient? _client;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final compact = width < 900;
    return Scaffold(
      key: _scaffoldKey,
      drawer: compact
          ? Drawer(
              backgroundColor: LedgerFlowDesign.navy,
              child: SafeArea(child: _navigation(closeAfterSelection: true)),
            )
          : null,
      body: Row(
        children: [
          if (!compact) SizedBox(width: 238, child: _navigation()),
          Expanded(
            child: Column(
              children: [
                _TopBar(
                  compact: compact,
                  live: _live,
                  loading: _loading,
                  apiUrl: _apiUrl,
                  onMenu: () => _scaffoldKey.currentState?.openDrawer(),
                  onConnect: _showConnectionDialog,
                  onRefresh: _live ? _reload : null,
                ),
                if (_lastError != null)
                  MaterialBanner(
                    content: Text(_lastError!),
                    leading: const Icon(
                      Icons.error_outline,
                      color: LedgerFlowDesign.danger,
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => setState(() => _lastError = null),
                        child: const Text('Dismiss'),
                      ),
                    ],
                  ),
                Expanded(
                  child: Stack(
                    children: [
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 240),
                        child: KeyedSubtree(
                          key: ValueKey(
                            'page-$_selectedIndex-${_live ? 'live' : 'demo'}',
                          ),
                          child: _page(),
                        ),
                      ),
                      if (_loading)
                        const Positioned.fill(
                          child: ColoredBox(
                            color: Color(0x99FFFFFF),
                            child: Center(child: CircularProgressIndicator()),
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _navigation({bool closeAfterSelection = false}) {
    return ColoredBox(
      color: LedgerFlowDesign.navy,
      child: Column(
        children: [
          const _Brand(),
          const SizedBox(height: 10),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              itemCount: _destinations.length,
              separatorBuilder: (_, _) => const SizedBox(height: 4),
              itemBuilder: (context, index) {
                final item = _destinations[index];
                final selected = index == _selectedIndex;
                return Material(
                  color: selected ? LedgerFlowDesign.teal : Colors.transparent,
                  borderRadius: BorderRadius.circular(8),
                  child: ListTile(
                    dense: true,
                    minLeadingWidth: 22,
                    selected: selected,
                    selectedColor: Colors.white,
                    textColor: const Color(0xFFDCE7F4),
                    iconColor: const Color(0xFFDCE7F4),
                    leading: Icon(item.icon, size: 21),
                    title: Text(
                      item.label,
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                    onTap: () {
                      setState(() => _selectedIndex = index);
                      if (closeAfterSelection) Navigator.of(context).pop();
                    },
                  ),
                );
              },
            ),
          ),
          Container(
            margin: const EdgeInsets.all(12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.07),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
            ),
            child: Row(
              children: [
                Icon(
                  _live ? Icons.cloud_done_outlined : Icons.science_outlined,
                  size: 20,
                  color: _live
                      ? const Color(0xFF54D6C7)
                      : const Color(0xFFFFCC80),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _live ? 'Live API' : 'Demo workspace',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        _live
                            ? Uri.parse(_apiUrl).host
                            : 'No credentials required',
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: Color(0xFFAFC2D9),
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _page() => switch (_selectedIndex) {
    0 => OperationsDashboard(data: _data, onOpen: _selectPage),
    1 => QuoteWorkspace(quotes: _data['quotes']),
    2 => ChargeDocumentWorkspace(documents: _data['documents']),
    3 => InvoiceWorkspace(invoices: _data['invoices']),
    4 => RateBookWorkspace(
      rateBooks: _data['rateBooks'],
      live: _live,
      onMutation: _mutate,
    ),
    5 => ComponentManagementWorkspace(
      records: _data['components'],
      calculationProfiles: _data['calculationProfiles'],
      allocationProfiles: _data['allocationProfiles'],
      businessDateProfiles: _data['dateProfiles'],
      live: _live,
      onMutation: _mutate,
    ),
    6 => ProfileManagementHub(data: _data, live: _live, onMutation: _mutate),
    _ => FxDateManagementHub(
      data: _data,
      live: _live,
      onMutation: _mutate,
      loadAssignments: _live ? _loadAssignments : null,
    ),
  };

  void _selectPage(int index) => setState(() => _selectedIndex = index);

  Future<void> _showConnectionDialog() async {
    final urlController = TextEditingController(text: _apiUrl);
    final tokenController = TextEditingController();
    final result = await showDialog<_ConnectionInput>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Connect LedgerFlow API'),
        content: SizedBox(
          width: 540,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Use an access token from your identity provider. The token stays in memory and is never stored by the browser app.',
                style: TextStyle(color: LedgerFlowDesign.muted),
              ),
              const SizedBox(height: 18),
              TextField(
                controller: urlController,
                decoration: const InputDecoration(labelText: 'API base URL'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: tokenController,
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'Bearer token',
                  helperText:
                      'Held only in memory until this page is refreshed',
                ),
              ),
            ],
          ),
        ),
        actions: [
          if (_live)
            TextButton(
              onPressed: () =>
                  Navigator.pop(context, const _ConnectionInput.demo()),
              child: const Text('Use demo data'),
            ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(
              context,
              _ConnectionInput(
                urlController.text.trim(),
                tokenController.text.trim(),
              ),
            ),
            child: const Text('Connect'),
          ),
        ],
      ),
    );
    urlController.dispose();
    tokenController.dispose();
    if (result == null) return;
    if (result.demoMode) {
      setState(() {
        _data = WorkspaceData.demo();
        _live = false;
        _lastError = null;
        _client = null;
      });
      return;
    }
    if (result.url.isEmpty || result.token.isEmpty) {
      setState(() => _lastError = 'API URL and bearer token are required.');
      return;
    }
    await _connect(result.url, result.token);
  }

  Future<void> _connect(String url, String token) async {
    setState(() {
      _loading = true;
      _lastError = null;
    });
    try {
      final client = LedgerFlowApiClient(baseUrl: url, token: token);
      final data = await client.loadWorkspace();
      if (!mounted) return;
      setState(() {
        _data = data;
        _apiUrl = url;
        _live = true;
        _client = client;
      });
      _token = token;
    } catch (error) {
      if (!mounted) return;
      setState(() => _lastError = 'Could not connect to LedgerFlow: $error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String? _token;

  Future<void> _reload() async {
    final token = _token;
    if (token == null) return;
    await _connect(_apiUrl, token);
  }

  Future<bool> _mutate({
    required String method,
    required String path,
    JsonMap? body,
    required String successMessage,
  }) async {
    final client = _client;
    if (client == null) return false;
    setState(() {
      _loading = true;
      _lastError = null;
    });
    try {
      try {
        await client.requestJson(method, path, body: body);
      } catch (error) {
        if (mounted) {
          setState(() => _lastError = 'The change could not be saved: $error');
        }
        return false;
      }
      try {
        final data = await client.loadWorkspace();
        if (mounted) setState(() => _data = data);
      } catch (error) {
        if (mounted) {
          setState(
            () => _lastError =
                '$successMessage Refresh failed; use the refresh action: $error',
          );
        }
      }
      if (!mounted) return true;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(successMessage)));
      return true;
    } catch (error) {
      // Defensive fallback for unexpected client failures.
      if (mounted) setState(() => _lastError = 'Request failed: $error');
      return false;
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<List<JsonMap>> _loadAssignments(int profileId) async {
    final client = _client;
    if (client == null) return const [];
    try {
      return await client.loadBusinessDateAssignments(profileId);
    } catch (error) {
      if (mounted) {
        setState(() => _lastError = 'Assignments could not be loaded: $error');
      }
      return const [];
    }
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.compact,
    required this.live,
    required this.loading,
    required this.apiUrl,
    required this.onMenu,
    required this.onConnect,
    required this.onRefresh,
  });

  final bool compact;
  final bool live;
  final bool loading;
  final String apiUrl;
  final VoidCallback onMenu;
  final VoidCallback onConnect;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 66,
      padding: EdgeInsets.symmetric(horizontal: compact ? 12 : 24),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: LedgerFlowDesign.border)),
      ),
      child: Row(
        children: [
          if (compact)
            IconButton(onPressed: onMenu, icon: const Icon(Icons.menu))
          else
            const Text(
              'Charge management',
              style: TextStyle(fontSize: 14, color: LedgerFlowDesign.muted),
            ),
          const Spacer(),
          if (live && !compact)
            Padding(
              padding: const EdgeInsets.only(right: 12),
              child: Text(
                Uri.parse(apiUrl).host,
                style: const TextStyle(
                  fontSize: 12,
                  color: LedgerFlowDesign.muted,
                ),
              ),
            ),
          if (onRefresh != null)
            IconButton(
              tooltip: 'Refresh API data',
              onPressed: loading ? null : onRefresh,
              icon: const Icon(Icons.refresh),
            ),
          OutlinedButton.icon(
            onPressed: loading ? null : onConnect,
            icon: Icon(live ? Icons.cloud_done_outlined : Icons.link),
            label: Text(live ? 'API connected' : 'Connect API'),
          ),
          const SizedBox(width: 12),
          const CircleAvatar(
            radius: 18,
            backgroundColor: LedgerFlowDesign.teal,
            foregroundColor: Colors.white,
            child: Text(
              'LF',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}

class _Brand extends StatelessWidget {
  const _Brand();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.fromLTRB(20, 24, 16, 18),
      child: Row(
        children: [
          DecoratedBox(
            decoration: BoxDecoration(
              color: LedgerFlowDesign.teal,
              borderRadius: BorderRadius.all(Radius.circular(9)),
            ),
            child: Padding(
              padding: EdgeInsets.all(8),
              child: Icon(Icons.waterfall_chart, color: Colors.white, size: 22),
            ),
          ),
          SizedBox(width: 11),
          Text(
            'LedgerFlow',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _Destination {
  const _Destination(this.label, this.icon);

  final String label;
  final IconData icon;
}

class _ConnectionInput {
  const _ConnectionInput(this.url, this.token) : demoMode = false;
  const _ConnectionInput.demo() : url = '', token = '', demoMode = true;

  final String url;
  final String token;
  final bool demoMode;
}
