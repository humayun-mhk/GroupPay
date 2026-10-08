import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'dart:async';

import '../core/auth/session_controller.dart';
import '../core/theme/app_theme.dart';
import '../core/utils/money_format.dart';
import '../core/widgets/ui.dart';
import 'data/group_pay_repository.dart';
import 'data/settlement_action_policy.dart';

GroupPayRepository _repo(WidgetRef ref) => GroupPayRepository(ref.watch(apiClientProvider).dio);

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.location, required this.child});
  final String location;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final index = location.startsWith('/groups') || location.startsWith('/expenses') ? 1 : location == '/friends' || location == '/requests' ? 2 : location == '/search' ? 3 : location == '/profile' ? 4 : 0;
    return Scaffold(
      body: SafeArea(child: child),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => context.go(['/home', '/groups', '/friends', '/search', '/profile'][i]),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.groups_outlined), selectedIcon: Icon(Icons.groups), label: 'Groups'),
          NavigationDestination(icon: Icon(Icons.people_outline), selectedIcon: Icon(Icons.people), label: 'Friends'),
          NavigationDestination(icon: Icon(Icons.search), label: 'Find'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});
  @override
  Widget build(BuildContext context) => const Scaffold(body: Center(child: CircularProgressIndicator()));
}

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;

  @override
  void dispose() { _email.dispose(); _password.dispose(); super.dispose(); }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(sessionProvider.notifier).login(_email.text.trim(), _password.text);
      if (mounted) context.go('/home');
    } catch (error) {
      if (mounted) _message(context, apiError(error));
    } finally { if (mounted) setState(() => _busy = false); }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const _BrandMark(), const SizedBox(height: 34),
            Text('Welcome back', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700, color: AppTheme.ink)),
            const SizedBox(height: 8), const Text('Sign in to keep shared plans in sync.'), const SizedBox(height: 28),
            Form(key: _form, child: Column(children: [
              TextFormField(controller: _email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline)), validator: _emailValidator),
              const SizedBox(height: 14), TextFormField(controller: _password, obscureText: true, decoration: const InputDecoration(labelText: 'Password', prefixIcon: Icon(Icons.lock_outline)), validator: (v) => (v == null || v.isEmpty) ? 'Enter your password' : null),
              const SizedBox(height: 22), FilledButton(onPressed: _busy ? null : _submit, child: _busy ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2)) : const Text('Sign in')),
            ])),
            const SizedBox(height: 18), Center(child: TextButton(onPressed: () => context.go('/register'), child: const Text('New to GroupPay? Create an account'))),
          ]),
        ))),
      );
}

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});
  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController(), _email = TextEditingController(), _phone = TextEditingController(), _password = TextEditingController();
  bool _busy = false;
  @override
  void dispose() { _name.dispose(); _email.dispose(); _phone.dispose(); _password.dispose(); super.dispose(); }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await ref.read(sessionProvider.notifier).register(_name.text.trim(), _email.text.trim(), _phone.text, _password.text);
      if (mounted) context.go('/home');
    } catch (error) { if (mounted) _message(context, apiError(error)); }
    finally { if (mounted) setState(() => _busy = false); }
  }

  @override
  Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Create account')), body: Center(child: SingleChildScrollView(padding: const EdgeInsets.all(24), child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 440), child: Form(key: _form, child: Column(children: [
    const _BrandMark(), const SizedBox(height: 24), TextFormField(controller: _name, textCapitalization: TextCapitalization.words, decoration: const InputDecoration(labelText: 'Full name', prefixIcon: Icon(Icons.person_outline)), validator: (v) => (v == null || v.trim().length < 2) ? 'Enter your name' : null),
    const SizedBox(height: 12), TextFormField(controller: _email, keyboardType: TextInputType.emailAddress, decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.mail_outline)), validator: _emailValidator),
    const SizedBox(height: 12), TextFormField(controller: _phone, keyboardType: TextInputType.phone, decoration: const InputDecoration(labelText: 'Phone number (optional)', prefixIcon: Icon(Icons.phone_outlined))),
    const SizedBox(height: 12), TextFormField(controller: _password, obscureText: true, decoration: const InputDecoration(labelText: 'Password (8+ characters)', prefixIcon: Icon(Icons.lock_outline)), validator: (v) => (v == null || v.length < 8) ? 'Use at least 8 characters' : null),
    const SizedBox(height: 20), FilledButton(onPressed: _busy ? null : _submit, child: _busy ? const CircularProgressIndicator() : const Text('Create account')),
    TextButton(onPressed: () => context.go('/login'), child: const Text('Already have an account? Sign in')),
  ]))))));
}

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionProvider);
    final repo = _repo(ref);
    return Scaffold(appBar: AppBar(title: const _BrandMark(), actions: [IconButton(tooltip: 'Payment requests', onPressed: () => context.go('/payment-requests'), icon: const Icon(Icons.receipt_long_outlined)), IconButton(tooltip: 'Notifications', onPressed: () => context.go('/notifications'), icon: const Icon(Icons.notifications_none)), IconButton(tooltip: 'Profile', onPressed: () => context.go('/profile'), icon: const Icon(Icons.person_outline))]), body: RefreshIndicator(onRefresh: () async { await Future.wait([repo.groups(), repo.friends(), repo.incomingPayments(), repo.notifications()]); }, child: ListView(padding: const EdgeInsets.fromLTRB(20, 12, 20, 28), children: [
      Text('Assalamu alaikum, ${_firstName(session.user?['full_name'])}', style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700, color: AppTheme.ink)),
      const SizedBox(height: 5), const Text('Make shared plans feel simple.'), const SizedBox(height: 22),
      FutureBuilder<List<dynamic>>(future: Future.wait([repo.groups(), repo.friends(), repo.incomingPayments(), repo.notifications()]), builder: (context, snapshot) {
        if (snapshot.hasError) return _RetryCard(message: apiError(snapshot.error!), onRetry: () => ref.invalidate(apiClientProvider));
        if (!snapshot.hasData) return const Padding(padding: EdgeInsets.all(28), child: Center(child: CircularProgressIndicator()));
        final groups = snapshot.data![0] as List<Map<String, dynamic>>; final friends = snapshot.data![1] as List<Map<String, dynamic>>; final requests = snapshot.data![2] as List<Map<String, dynamic>>; final notifications = snapshot.data![3] as List<Map<String, dynamic>>;
        return Column(children: [Row(children: [Expanded(child: _StatCard(label: 'Groups', value: '${groups.length}', icon: Icons.groups_outlined)), const SizedBox(width: 12), Expanded(child: _StatCard(label: 'Friends', value: '${friends.length}', icon: Icons.people_outline)), const SizedBox(width: 12), Expanded(child: _StatCard(label: 'Requests', value: '${requests.where((r) => r['status'] == 'PENDING' || r['status'] == 'PAYMENT_CLAIMED').length}', icon: Icons.payments_outlined))]), const SizedBox(height: 12), ...groups.take(4).map((group) => FutureBuilder<Map<String, dynamic>>(future: repo.groupSummary(group['id']), builder: (context, summary) { if (!summary.hasData) return const SizedBox.shrink(); final data = summary.data!; return AppCard(child: Row(children: [Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('You owe', style: Theme.of(context).textTheme.labelMedium), Text(MoneyFormat.format(data['amount_user_owes']), style: Theme.of(context).textTheme.titleMedium)])), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('You are owed', style: Theme.of(context).textTheme.labelMedium), Text(MoneyFormat.format(data['amount_owed_to_user']), style: Theme.of(context).textTheme.titleMedium)]))])); })), if (notifications.isNotEmpty) ...[const SizedBox(height: 12), _SectionHeading(title: 'Recent activity', action: 'See all', onTap: () => context.go('/notifications')), ...notifications.take(3).map((item) => ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.bolt), title: Text(item['title'].toString()), subtitle: Text(item['message'].toString(), maxLines: 1, overflow: TextOverflow.ellipsis)))]]);
      }),
      const SizedBox(height: 26), _SectionHeading(title: 'Your groups', action: 'See all', onTap: () => context.go('/groups')),
      const SizedBox(height: 12), FutureBuilder<List<Map<String, dynamic>>>(future: repo.groups(), builder: (context, snapshot) {
        if (snapshot.hasError) return _RetryCard(message: apiError(snapshot.error!), onRetry: () => context.go('/groups'));
        if (!snapshot.hasData) return const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator()));
        final groups = snapshot.data!;
        if (groups.isEmpty) return const AppCard(child: EmptyState(title: 'Start your first group', message: 'Create a group for a trip, flat, or shared plan.', icon: Icons.group_add_outlined));
        return Column(children: groups.take(4).map((g) => Padding(padding: const EdgeInsets.only(bottom: 10), child: _GroupTile(group: g))).toList());
      }),
      const SizedBox(height: 16), FilledButton.icon(onPressed: () => context.go('/groups/create'), icon: const Icon(Icons.add), label: const Text('Create a group')),
    ])));
  }
}

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(sessionProvider).user ?? {};
    return Scaffold(appBar: AppBar(title: const Text('Profile')), body: ListView(padding: const EdgeInsets.all(20), children: [
      AppCard(child: Column(children: [CircleAvatar(radius: 38, backgroundColor: const Color(0xFFE1F1EC), child: Text(_initials(user['full_name']), style: const TextStyle(fontSize: 24, color: AppTheme.green, fontWeight: FontWeight.bold))), const SizedBox(height: 14), Text(user['full_name']?.toString() ?? 'GroupPay member', style: Theme.of(context).textTheme.titleLarge), const SizedBox(height: 5), Text(user['email']?.toString() ?? '', style: const TextStyle(color: Colors.black54))])),
      const SizedBox(height: 14), if (user['phone_number'] != null) AppCard(child: ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.phone_outlined), title: const Text('Phone'), subtitle: Text(user['phone_number'].toString()))),
      const SizedBox(height: 20), OutlinedButton.icon(onPressed: () async { await ref.read(sessionProvider.notifier).logout(); if (context.mounted) context.go('/login'); }, icon: const Icon(Icons.logout), label: const Text('Sign out')),
    ]));
  }
}

class UserSearchScreen extends ConsumerStatefulWidget {
  const UserSearchScreen({super.key});
  @override
  ConsumerState<UserSearchScreen> createState() => _UserSearchScreenState();
}

class _UserSearchScreenState extends ConsumerState<UserSearchScreen> {
  final _query = TextEditingController();
  Timer? _debounce;
  List<Map<String, dynamic>> _results = [];
  bool _busy = false, _searched = false;
  @override
  void dispose() { _debounce?.cancel(); _query.dispose(); super.dispose(); }
  Future<void> _search() async {
    if (_query.text.trim().isEmpty) return;
    setState(() { _busy = true; _searched = true; });
    try { _results = await _repo(ref).search(_query.text.trim()); }
    catch (error) { if (mounted) _message(context, apiError(error)); }
    finally { if (mounted) setState(() => _busy = false); }
  }
  @override
  Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Find people')), body: ListView(padding: const EdgeInsets.all(20), children: [
    const Text('Search by name, email, or phone number.'), const SizedBox(height: 14), Row(children: [Expanded(child: TextField(controller: _query, textInputAction: TextInputAction.search, onChanged: (_) { _debounce?.cancel(); _debounce = Timer(const Duration(milliseconds: 350), _search); }, onSubmitted: (_) => _search(), decoration: const InputDecoration(hintText: 'Search people', prefixIcon: Icon(Icons.search)))), const SizedBox(width: 8), IconButton.filled(onPressed: _busy ? null : _search, icon: const Icon(Icons.arrow_forward))]),
    const SizedBox(height: 16), if (_busy) const Center(child: CircularProgressIndicator()), if (!_busy && _searched && _results.isEmpty) const EmptyState(title: 'No people found', message: 'Try another name, email, or number.'),
    ..._results.map((user) => _PersonTile(user: user, action: IconButton(tooltip: 'Add friend', icon: const Icon(Icons.person_add_alt_1), onPressed: () async { try { await _repo(ref).sendFriendRequest(user['id']); if (context.mounted) _message(context, 'Friend request sent'); } catch (e) { if (context.mounted) _message(context, apiError(e)); } }))),
  ]));
}

class FriendsScreen extends ConsumerWidget {
  const FriendsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final repo = _repo(ref);
    return Scaffold(appBar: AppBar(title: const Text('Friends'), actions: [IconButton(tooltip: 'Friend requests', onPressed: () => context.go('/requests'), icon: const Icon(Icons.mark_email_unread_outlined)), IconButton(tooltip: 'Find people', onPressed: () => context.go('/search'), icon: const Icon(Icons.person_add_alt_1))]), body: FutureBuilder<List<Map<String, dynamic>>>(future: repo.friends(), builder: (context, snapshot) {
      if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      if (snapshot.data!.isEmpty) return const EmptyState(title: 'Your circle starts here', message: 'Find people and send a friend request.', icon: Icons.people_outline);
      return ListView(padding: const EdgeInsets.all(20), children: snapshot.data!.map((item) => _PersonTile(user: Map<String, dynamic>.from(item['user']))).toList());
    }));
  }
}

class FriendRequestsScreen extends ConsumerWidget {
  const FriendRequestsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final repo = _repo(ref);
    return Scaffold(appBar: AppBar(title: const Text('Friend requests')), body: FutureBuilder<List<Map<String, dynamic>>>(future: repo.incoming(), builder: (context, snapshot) {
      if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      if (snapshot.data!.isEmpty) return const EmptyState(title: 'All caught up', message: 'New friend requests will show up here.', icon: Icons.mark_email_read_outlined);
      return ListView(padding: const EdgeInsets.all(20), children: snapshot.data!.map((request) {
        final user = Map<String, dynamic>.from(request['requester']);
        return _PersonTile(user: user, subtitle: 'Wants to connect', action: Wrap(spacing: 2, children: [IconButton(tooltip: 'Accept', color: AppTheme.green, icon: const Icon(Icons.check_circle_outline), onPressed: () async { await repo.respondFriendRequest(request['id'], true); ref.invalidate(apiClientProvider); if (context.mounted) (context as Element).markNeedsBuild(); }), IconButton(tooltip: 'Decline', icon: const Icon(Icons.close), onPressed: () async { await repo.respondFriendRequest(request['id'], false); if (context.mounted) _message(context, 'Request declined'); })]));
      }).toList());
    }));
  }
}

class GroupsScreen extends ConsumerWidget {
  const GroupsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final repo = _repo(ref);
    return Scaffold(appBar: AppBar(title: const Text('Groups'), actions: [IconButton(tooltip: 'Create group', onPressed: () => context.go('/groups/create'), icon: const Icon(Icons.add))]), body: FutureBuilder<List<Map<String, dynamic>>>(future: repo.groups(), builder: (context, snapshot) {
      if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      if (snapshot.data!.isEmpty) return const EmptyState(title: 'No groups yet', message: 'Bring a shared plan together by creating a group.', icon: Icons.groups_outlined);
      return ListView(padding: const EdgeInsets.all(20), children: snapshot.data!.map((g) => Padding(padding: const EdgeInsets.only(bottom: 10), child: _GroupTile(group: g))).toList());
    }));
  }
}

class CreateGroupScreen extends ConsumerStatefulWidget {
  const CreateGroupScreen({super.key});
  @override
  ConsumerState<CreateGroupScreen> createState() => _CreateGroupScreenState();
}

class _CreateGroupScreenState extends ConsumerState<CreateGroupScreen> {
  final _form = GlobalKey<FormState>(), _name = TextEditingController(), _description = TextEditingController();
  bool _busy = false;
  @override
  void dispose() { _name.dispose(); _description.dispose(); super.dispose(); }
  Future<void> _create() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _busy = true);
    try { await _repo(ref).createGroup(_name.text.trim(), _description.text.trim()); if (mounted) context.go('/groups'); }
    catch (e) { if (mounted) _message(context, apiError(e)); }
    finally { if (mounted) setState(() => _busy = false); }
  }
  @override
  Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Create a group')), body: ListView(padding: const EdgeInsets.all(20), children: [
    const AppCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Icon(Icons.groups_2_outlined, size: 32, color: AppTheme.green), SizedBox(height: 10), Text('Bring everyone together', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)), SizedBox(height: 4), Text('You’ll be an admin and can invite accepted friends.') ])),
    const SizedBox(height: 18), Form(key: _form, child: Column(children: [TextFormField(controller: _name, maxLength: 100, decoration: const InputDecoration(labelText: 'Group name', hintText: 'e.g. Hunza trip'), validator: (v) => (v == null || v.trim().length < 2) ? 'Enter at least 2 characters' : null), const SizedBox(height: 12), TextFormField(controller: _description, maxLines: 3, maxLength: 1000, decoration: const InputDecoration(labelText: 'Description (optional)', alignLabelWithHint: true)), const SizedBox(height: 10), FilledButton(onPressed: _busy ? null : _create, child: _busy ? const CircularProgressIndicator() : const Text('Create group'))])),
  ]));
}

class GroupDetailsScreen extends ConsumerWidget {
  const GroupDetailsScreen({super.key, required this.groupId});
  final int groupId;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final repo = _repo(ref);
    return Scaffold(appBar: AppBar(title: const Text('Group details')), body: FutureBuilder<Map<String, dynamic>>(future: repo.group(groupId), builder: (context, snapshot) {
      if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => context.go('/groups'));
      if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
      final group = snapshot.data!, members = (group['members'] as List).map((m) => Map<String, dynamic>.from(m)).toList();
      final admin = group['current_user_role'] == 'ADMIN';
      return DefaultTabController(length: 4, child: Column(children: [
        Padding(padding: const EdgeInsets.fromLTRB(20, 4, 20, 12), child: AppCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [const CircleAvatar(backgroundColor: Color(0xFFE1F1EC), child: Icon(Icons.groups, color: AppTheme.green)), const SizedBox(width: 12), Expanded(child: Text(group['name'], style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)))]), if ((group['description'] ?? '').toString().isNotEmpty) ...[const SizedBox(height: 9), Text(group['description'])], const SizedBox(height: 7), Text('${group['current_user_role']} · ${members.length} members', style: const TextStyle(color: Colors.black54))]))),
        const TabBar(isScrollable: true, tabs: [Tab(text: 'Overview'), Tab(text: 'Expenses'), Tab(text: 'Balances'), Tab(text: 'Members')]),
        Expanded(child: TabBarView(children: [
          _GroupOverviewTab(groupId: groupId),
          _GroupExpenseTab(groupId: groupId),
          _GroupBalancesTab(groupId: groupId),
          _GroupMembersTab(groupId: groupId, members: members, canManage: admin),
        ])),
      ]));
    }));
  }
}

class _GroupOverviewTab extends ConsumerWidget {
  const _GroupOverviewTab({required this.groupId});
  final int groupId;
  @override
  Widget build(BuildContext context, WidgetRef ref) => FutureBuilder<Map<String, dynamic>>(future: _repo(ref).groupSummary(groupId), builder: (context, snapshot) {
    if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
    if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
    final data = snapshot.data!;
    final recent = (data['recent_expenses'] as List).map((e) => Map<String, dynamic>.from(e)).toList();
    return ListView(padding: const EdgeInsets.all(20), children: [
      Row(children: [Expanded(child: _StatCard(label: 'Group spending', value: MoneyFormat.format(data['total_group_spending']), icon: Icons.payments_outlined)), const SizedBox(width: 12), Expanded(child: _StatCard(label: 'Your balance', value: MoneyFormat.format(data['current_balance']), icon: Icons.account_balance_wallet_outlined))]),
      const SizedBox(height: 14), AppCard(child: Row(children: [Expanded(child: _MoneyMetric(label: 'You paid', value: data['current_user_total_paid'])), Expanded(child: _MoneyMetric(label: 'Your share', value: data['current_user_total_share']))])),
      const SizedBox(height: 22), _SectionHeading(title: 'Recent expenses', action: 'All', onTap: () => context.go('/groups/$groupId/expenses')),
      if (recent.isEmpty) const AppCard(child: EmptyState(title: 'No expenses yet', message: 'Add the first shared expense to start the group balance.', icon: Icons.receipt_long_outlined))
      else ...recent.map((expense) => _ExpenseTile(expense: expense)),
      const SizedBox(height: 10), FilledButton.icon(onPressed: () => context.go('/groups/$groupId/expenses/add'), icon: const Icon(Icons.add), label: const Text('Add expense')),
    ]);
  });
}

class _GroupExpenseTab extends ConsumerWidget {
  const _GroupExpenseTab({required this.groupId});
  final int groupId;
  @override
  Widget build(BuildContext context, WidgetRef ref) => FutureBuilder<Map<String, dynamic>>(future: _repo(ref).expensePage(groupId), builder: (context, snapshot) {
    if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
    if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
    final items = (snapshot.data!['items'] as List).map((e) => Map<String, dynamic>.from(e)).toList();
    return Column(children: [Padding(padding: const EdgeInsets.fromLTRB(20, 8, 20, 0), child: Align(alignment: Alignment.centerRight, child: FilledButton.tonalIcon(onPressed: () => context.go('/groups/$groupId/expenses/add'), icon: const Icon(Icons.add), label: const Text('Add expense')))), Expanded(child: items.isEmpty ? const EmptyState(title: 'No expenses yet', message: 'Expenses you add will appear here.', icon: Icons.receipt_long_outlined) : ListView(padding: const EdgeInsets.all(20), children: items.map((item) => _ExpenseTile(expense: item)).toList()))]);
  });
}

class _GroupBalancesTab extends ConsumerWidget {
  const _GroupBalancesTab({required this.groupId});
  final int groupId;
  @override
  Widget build(BuildContext context, WidgetRef ref) => FutureBuilder<List<dynamic>>(future: Future.wait([_repo(ref).balances(groupId), _repo(ref).settlements(groupId), _repo(ref).settlementHistory(groupId)]), builder: (context, snapshot) {
    if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
    if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
    final balances = snapshot.data![0] as List<Map<String, dynamic>>;
    final settlements = snapshot.data![1] as List<Map<String, dynamic>>;
    final history = snapshot.data![2] as List<Map<String, dynamic>>;
    final currentId = ref.watch(sessionProvider).user?['id'];
    return ListView(padding: const EdgeInsets.all(20), children: [
      _SectionHeading(title: 'Member balances', action: 'History', onTap: () => context.go('/groups/$groupId/settlement-history')),
      if (balances.every((line) => _isZeroMoney(line['net_balance']))) const AppCard(child: EmptyState(title: 'All settled', message: 'There are no outstanding group balances.', icon: Icons.check_circle_outline)),
      ...balances.where((line) => !_isZeroMoney(line['net_balance'])).map((line) { final user = Map<String, dynamic>.from(line['user']); final amount = line['net_balance']; final owed = amount.toString().startsWith('-'); return _PersonTile(user: user, subtitle: owed ? 'Owes ${MoneyFormat.format(line['amount_owed'])}' : 'Is owed ${MoneyFormat.format(line['amount_owed_to_user'])}'); }),
      const SizedBox(height: 20), const _SectionHeading(title: 'Suggested settlements'),
      if (settlements.isEmpty) const AppCard(child: EmptyState(title: 'No transfers needed', message: 'The group has no unsettled transfers to suggest.', icon: Icons.check_circle_outline)),
      ...settlements.map((item) { final from = Map<String, dynamic>.from(item['from_user']); final to = Map<String, dynamic>.from(item['to_user']); final open = history.where((r) => r['payer']['id'] == from['id'] && r['requester']['id'] == to['id'] && (r['status'] == 'PENDING' || r['status'] == 'PAYMENT_CLAIMED')).toList(); final relevant = open.isEmpty ? null : open.first; final status = relevant?['status']; return AppCard(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Row(children: [Expanded(child: Text(currentId == from['id'] ? 'You owe ${to['full_name']}' : from['full_name'], style: const TextStyle(fontWeight: FontWeight.w600))), const Icon(Icons.arrow_forward, size: 18), Expanded(child: Text(currentId == to['id'] ? 'you' : to['full_name'], textAlign: TextAlign.end, style: const TextStyle(fontWeight: FontWeight.w600)))]), const SizedBox(height: 8), Row(children: [Expanded(child: Text(MoneyFormat.format(item['amount']), style: const TextStyle(color: AppTheme.green, fontWeight: FontWeight.bold))), if (status != null) Text(status == 'PAYMENT_CLAIMED' ? 'Awaiting confirmation' : 'Requested', style: const TextStyle(color: Colors.black54)), if (status == null && currentId == to['id']) TextButton.icon(onPressed: () => _showRequestPayment(context, ref, groupId, from['id'] as int, from['full_name'].toString(), item['amount'].toString()), icon: const Icon(Icons.send_outlined), label: const Text('Request payment')), if (relevant != null) IconButton(tooltip: 'Settlement details', onPressed: () => context.go('/settlements/${relevant['id']}'), icon: const Icon(Icons.chevron_right))]) ])); }),
    ]);
  });
}

Future<void> _showRequestPayment(BuildContext context, WidgetRef ref, int groupId, int payerId, String payerName, String suggestedAmount) async {
  final amount = TextEditingController(text: suggestedAmount);
  final note = TextEditingController();
  final create = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(title: const Text('Request payment'), content: Column(mainAxisSize: MainAxisSize.min, children: [Text('Request a manual transfer from $payerName.'), const SizedBox(height: 12), TextField(controller: amount, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Amount (PKR)')), TextField(controller: note, maxLength: 240, decoration: const InputDecoration(labelText: 'Reason (optional)'))]), actions: [TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Send request'))]));
  if (create == true) { try { await _repo(ref).requestPayment(groupId, payerId, amount.text.trim(), note: note.text.trim().isEmpty ? null : note.text.trim()); ref.invalidate(apiClientProvider); if (context.mounted) _message(context, 'Payment request sent'); } catch (error) { if (context.mounted) _message(context, apiError(error)); } }
  amount.dispose(); note.dispose();
}

class _GroupMembersTab extends ConsumerWidget {
  const _GroupMembersTab({required this.groupId, required this.members, required this.canManage});
  final int groupId; final List<Map<String, dynamic>> members; final bool canManage;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final currentId = ref.watch(sessionProvider).user?['id'];
    final repo = _repo(ref);
    return ListView(padding: const EdgeInsets.all(20), children: [
      if (canManage) Align(alignment: Alignment.centerRight, child: FilledButton.tonalIcon(onPressed: () => context.go('/groups/$groupId/add-members'), icon: const Icon(Icons.person_add_alt_1), label: const Text('Add members'))),
      ...members.map((member) {
        final user = Map<String, dynamic>.from(member['user']);
        final role = member['role'].toString();
        final canAct = canManage && user['id'] != currentId;
        return _PersonTile(user: user, subtitle: role, action: canAct ? Wrap(spacing: 0, children: [
          IconButton(tooltip: role == 'ADMIN' ? 'Make member' : 'Make admin', icon: Icon(role == 'ADMIN' ? Icons.admin_panel_settings : Icons.shield_outlined), onPressed: () async {
            try { await repo.updateMemberRole(groupId, user['id'], role == 'ADMIN' ? 'MEMBER' : 'ADMIN'); ref.invalidate(apiClientProvider); }
            catch (e) { if (context.mounted) _message(context, apiError(e)); }
          }),
          IconButton(tooltip: 'Remove member', icon: const Icon(Icons.person_remove_outlined), onPressed: () async {
            final yes = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(title: const Text('Remove member?'), content: Text('Remove ${user['full_name']} from this group? Their previous expenses will remain in the balance history.'), actions: [TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Remove'))]));
            if (yes == true) { try { await repo.removeMember(groupId, user['id']); ref.invalidate(apiClientProvider); } catch (e) { if (context.mounted) _message(context, apiError(e)); } }
          }),
        ]) : null);
      }),
    ]);
  }
}

class GroupBalancesScreen extends ConsumerWidget {
  const GroupBalancesScreen({super.key, required this.groupId});
  final int groupId;
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(appBar: AppBar(title: const Text('Group balances')), body: _GroupBalancesTab(groupId: groupId));
}

class PaymentRequestsScreen extends StatelessWidget {
  const PaymentRequestsScreen({super.key});
  @override
  Widget build(BuildContext context) => DefaultTabController(length: 2, child: Scaffold(appBar: AppBar(title: const Text('Payment requests'), bottom: const TabBar(tabs: [Tab(text: 'Incoming'), Tab(text: 'Outgoing')])), body: const TabBarView(children: [_PaymentRequestList(incoming: true), _PaymentRequestList(incoming: false)])));
}

class _PaymentRequestList extends ConsumerWidget {
  const _PaymentRequestList({required this.incoming});
  final bool incoming;
  @override
  Widget build(BuildContext context, WidgetRef ref) => FutureBuilder<List<Map<String, dynamic>>>(future: incoming ? _repo(ref).incomingPayments() : _repo(ref).outgoingPayments(), builder: (context, snapshot) {
    if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
    if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
    final items = snapshot.data!;
    if (items.isEmpty) return EmptyState(title: incoming ? 'No incoming requests' : 'No outgoing requests', message: 'Manual payment requests will appear here.', icon: Icons.payments_outlined);
    return ListView(padding: const EdgeInsets.all(16), children: items.map((item) { final person = Map<String, dynamic>.from(incoming ? item['requester'] : item['payer']); return AppCard(child: ListTile(contentPadding: EdgeInsets.zero, title: Text('${incoming ? person['full_name'] : 'You'} · ${MoneyFormat.format(item['amount'])}'), subtitle: Text('${item['group_name']} · ${item['status']}\n${item['note'] ?? 'Manual transfer'}'), isThreeLine: true, trailing: const Icon(Icons.chevron_right), onTap: () => context.go('/settlements/${item['id']}'))); }).toList());
  });
}

class SettlementDetailScreen extends ConsumerWidget {
  const SettlementDetailScreen({super.key, required this.id});
  final int id;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: const Text('Settlement details')),
        body: FutureBuilder<Map<String, dynamic>>(
          future: _repo(ref).settlement(id),
          builder: (context, snapshot) {
            if (snapshot.hasError) {
              return _ErrorState(
                error: snapshot.error!,
                onRetry: () => ref.invalidate(apiClientProvider),
              );
            }
            if (!snapshot.hasData) {
              return const Center(child: CircularProgressIndicator());
            }
            final item = snapshot.data!;
            final currentId = ref.watch(sessionProvider).user?['id'];
            final isPayer = item['payer']['id'] == currentId;
            final status = item['status'].toString();

            Future<void> run(String action) async {
              try {
                await _repo(ref).transitionSettlement(id, action);
                ref.invalidate(apiClientProvider);
                if (context.mounted) {
                  final message = switch (action) {
                    'confirm' => 'Payment confirmed and balance updated',
                    'reject' => 'Payment claim rejected; balance remains outstanding',
                    'claim-paid' => 'Marked as paid; waiting for receiver confirmation',
                    _ => 'Request cancelled',
                  };
                  _message(context, message);
                }
              } catch (error) {
                if (context.mounted) _message(context, apiError(error));
              }
            }

            final events = (item['events'] as List)
                .map((row) => Map<String, dynamic>.from(row))
                .toList();
            return ListView(
              padding: const EdgeInsets.all(20),
              children: [
                AppCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        MoneyFormat.format(item['amount']),
                        style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: AppTheme.green,
                            ),
                      ),
                      const SizedBox(height: 8),
                      Text(item['group_name'],
                          style: Theme.of(context).textTheme.titleMedium),
                      Text(
                        '${item['requester']['full_name']} requested from ${item['payer']['full_name']}',
                      ),
                      const SizedBox(height: 12),
                      Chip(label: Text(status.replaceAll('_', ' '))),
                      Text(item['note'] ?? 'No reason provided'),
                      const SizedBox(height: 8),
                      const Text(
                        'This is a manual payment. Transfer outside GroupPay; this app does not move money.',
                        style: TextStyle(color: Colors.black54),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                if (SettlementActionPolicy.canClaimPaid(status, isPayer))
                  FilledButton.icon(
                    onPressed: () => run('claim-paid'),
                    icon: const Icon(Icons.check),
                    label: const Text('I have paid'),
                  ),
                if (SettlementActionPolicy.canConfirmOrReject(status, isPayer))
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => _confirmSettlementDialog(
                            context,
                            () => run('reject'),
                          ),
                          child: const Text('Reject claim'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton(
                          onPressed: () => _confirmSettlementDialog(
                            context,
                            () => run('confirm'),
                          ),
                          child: const Text('Confirm payment'),
                        ),
                      ),
                    ],
                  ),
                if (SettlementActionPolicy.canCancel(status, isPayer))
                  OutlinedButton(
                    onPressed: () => _confirmSettlementDialog(
                      context,
                      () => run('cancel'),
                    ),
                    child: const Text('Cancel request'),
                  ),
                const SizedBox(height: 20),
                Text('History', style: Theme.of(context).textTheme.titleLarge),
                ...events.map(
                  (event) => ListTile(
                    leading: const Icon(Icons.history),
                    title: Text(event['action'].toString().replaceAll('_', ' ')),
                    subtitle: Text(event['note']?.toString() ?? 'Status updated'),
                  ),
                ),
              ],
            );
          },
        ),
      );
}

Future<void> _confirmSettlementDialog(BuildContext context, Future<void> Function() action) async {
  final proceed = await showDialog<bool>(context: context, builder: (dialogContext) => AlertDialog(title: const Text('Confirm this action?'), content: const Text('Settlement actions are recorded in the group history.'), actions: [TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text('Go back')), FilledButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text('Continue'))]));
  if (proceed == true) await action();
}

class SettlementHistoryScreen extends ConsumerWidget {
  const SettlementHistoryScreen({super.key, required this.groupId});
  final int groupId;
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(appBar: AppBar(title: const Text('Settlement history')), body: FutureBuilder<List<Map<String, dynamic>>>(future: _repo(ref).settlementHistory(groupId), builder: (context, snapshot) {
    if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
    if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
    if (snapshot.data!.isEmpty) return const EmptyState(title: 'No settlement history', message: 'Payment requests and confirmations will be recorded here.', icon: Icons.history);
    return ListView(padding: const EdgeInsets.all(16), children: snapshot.data!.map((item) => ListTile(title: Text('${item['payer']['full_name']} → ${item['requester']['full_name']}'), subtitle: Text('${item['status']} · ${item['group_name']}'), trailing: Text(MoneyFormat.format(item['amount']), style: const TextStyle(fontWeight: FontWeight.bold)), onTap: () => context.go('/settlements/${item['id']}'))).toList());
  }));
}

class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(appBar: AppBar(title: const Text('Notifications'), actions: [TextButton(onPressed: () async { await _repo(ref).markAllNotificationsRead(); ref.invalidate(apiClientProvider); }, child: const Text('Mark all read'))]), body: FutureBuilder<List<Map<String, dynamic>>>(future: _repo(ref).notifications(), builder: (context, snapshot) {
    if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
    if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
    if (snapshot.data!.isEmpty) return const EmptyState(title: 'You’re all caught up', message: 'Group and payment activity will appear here.', icon: Icons.notifications_none);
    return ListView(children: snapshot.data!.map((item) => ListTile(leading: Icon(item['is_read'] == true ? Icons.notifications_none : Icons.notifications_active_outlined), title: Text(item['title'].toString()), subtitle: Text(item['message'].toString()), onTap: () async { await _repo(ref).markNotificationRead(item['id'] as int); if (item['related_entity_type'] == 'settlement' && context.mounted) { context.go('/settlements/${item['related_entity_id']}'); } else { ref.invalidate(apiClientProvider); } })).toList());
  }));
}

class ExpenseHistoryScreen extends ConsumerWidget {
  const ExpenseHistoryScreen({super.key, required this.groupId});
  final int groupId;
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(appBar: AppBar(title: const Text('Expense history')), body: FutureBuilder<Map<String, dynamic>>(future: _repo(ref).expensePage(groupId), builder: (context, snapshot) {
    if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
    if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
    final page = snapshot.data!;
    final items = (page['items'] as List).map((row) => Map<String, dynamic>.from(row)).toList();
    if (items.isEmpty) return const EmptyState(title: 'No expenses yet', message: 'Your group expense history will appear here.', icon: Icons.receipt_long_outlined);
    return ListView(padding: const EdgeInsets.all(20), children: items.map((item) => _ExpenseTile(expense: item)).toList());
  }));
}

class AddExpenseScreen extends ConsumerStatefulWidget {
  const AddExpenseScreen({super.key, this.groupId, this.expenseId});
  final int? groupId;
  final int? expenseId;
  @override
  ConsumerState<AddExpenseScreen> createState() => _AddExpenseScreenState();
}

class _AddExpenseScreenState extends ConsumerState<AddExpenseScreen> {
  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController(), _description = TextEditingController(), _amount = TextEditingController();
  final Map<int, TextEditingController> _splitValues = {};
  List<Map<String, dynamic>> _members = [];
  Set<int> _selected = {};
  int? _payerId, _resolvedGroupId;
  String _splitType = 'EQUAL';
  Map<String, dynamic>? _preview;
  String? _loadError;
  bool _loading = true, _previewing = false, _saving = false;

  @override
  void initState() { super.initState(); _load(); }
  @override
  void dispose() { _title.dispose(); _description.dispose(); _amount.dispose(); for (final c in _splitValues.values) { c.dispose(); } super.dispose(); }

  Future<void> _load() async {
    try {
      final repo = _repo(ref);
      Map<String, dynamic>? expense;
      if (widget.expenseId != null) expense = await repo.expense(widget.expenseId!);
      _resolvedGroupId = widget.groupId ?? expense?['group_id'] as int?;
      if (_resolvedGroupId == null) throw StateError('Could not determine the group for this expense.');
      final group = await repo.group(_resolvedGroupId!);
      _members = (group['members'] as List).map((m) => Map<String, dynamic>.from(m)).toList();
      if (expense != null) {
        _title.text = expense['title']?.toString() ?? '';
        _description.text = expense['description']?.toString() ?? '';
        _amount.text = expense['total_amount']?.toString() ?? '';
        _splitType = expense['split_type']?.toString() ?? 'EQUAL';
        _payerId = expense['paid_by_user_id'] as int?;
        for (final part in (expense['participants'] as List)) {
          final row = Map<String, dynamic>.from(part);
          final userId = row['user_id'] as int;
          _selected.add(userId);
          final value = switch (_splitType) {
            'EXACT' => row['amount_owed'],
            'PERCENTAGE' => row['percentage'],
            'SHARES' => row['shares'],
            _ => null,
          };
          if (value != null) _splitValues[userId] = TextEditingController(text: value.toString());
        }
      } else {
        _selected = _members.map((m) => m['user_id'] as int).toSet();
        final currentId = ref.read(sessionProvider).user?['id'] as int?;
        _payerId = _selected.contains(currentId) ? currentId : (_selected.isEmpty ? null : _selected.first);
      }
    } catch (error) {
      _loadError = apiError(error);
    } finally { if (mounted) setState(() => _loading = false); }
  }

  void _changed() { if (_preview != null) setState(() => _preview = null); }

  Map<String, dynamic> _payload() => {
        'title': _title.text.trim(),
        'description': _description.text.trim().isEmpty ? null : _description.text.trim(),
        'total_amount': _amount.text.trim(),
        'currency': 'PKR',
        'paid_by_user_id': _payerId,
        'split_type': _splitType,
        'participants': _selected.toList()..sort(),
      }..update('participants', (ids) => (ids as List<int>).map((id) {
        final row = <String, dynamic>{'user_id': id};
        final value = _splitValues[id]?.text.trim();
        if (value != null && value.isNotEmpty) {
          if (_splitType == 'EXACT') row['amount'] = value;
          if (_splitType == 'PERCENTAGE') row['percentage'] = value;
          if (_splitType == 'SHARES') row['shares'] = value;
        }
        return row;
      }).toList());

  String? _splitValidator(String? raw) {
    if (raw == null || raw.trim().isEmpty) return 'Enter a value';
    final number = double.tryParse(raw.trim());
    if (number == null || number.isNaN || number.isInfinite) return 'Enter a valid number';
    if (_splitType == 'EXACT' ? number < 0 : number <= 0) return _splitType == 'EXACT' ? 'Amount cannot be negative' : 'Enter a value greater than zero';
    return null;
  }

  Future<void> _previewSplit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selected.isEmpty) { _message(context, 'Choose at least one participant'); return; }
    if (_payerId == null) { _message(context, 'Choose who paid for this expense'); return; }
    setState(() { _previewing = true; _preview = null; });
    try { _preview = await _repo(ref).previewExpense(_resolvedGroupId!, _payload()); }
    catch (error) { if (mounted) _message(context, apiError(error)); }
    finally { if (mounted) setState(() => _previewing = false); }
  }

  Future<void> _save() async {
    if (_preview == null) { _message(context, 'Preview the split before saving'); return; }
    setState(() => _saving = true);
    try {
      final saved = widget.expenseId == null
          ? await _repo(ref).createExpense(_resolvedGroupId!, _payload())
          : await _repo(ref).updateExpense(widget.expenseId!, _payload());
      if (mounted) context.go('/expenses/${saved['id']}');
    } catch (error) { if (mounted) { _message(context, apiError(error)); setState(() => _preview = null); } }
    finally { if (mounted) setState(() => _saving = false); }
  }

  @override
  Widget build(BuildContext context) {
    final editing = widget.expenseId != null;
    return Scaffold(appBar: AppBar(title: Text(editing ? 'Edit expense' : 'Add expense')), body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _loadError != null ? _ErrorState(error: _loadError!, onRetry: _load)
        : Form(key: _formKey, child: ListView(padding: const EdgeInsets.all(20), children: [
            TextFormField(controller: _title, onChanged: (_) => _changed(), decoration: const InputDecoration(labelText: 'Title', hintText: 'Dinner at KFC'), validator: (v) => v == null || v.trim().length < 2 ? 'Enter an expense title' : null),
            const SizedBox(height: 12), TextFormField(controller: _amount, onChanged: (_) => _changed(), keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: const InputDecoration(labelText: 'Total amount', prefixText: 'Rs. '), validator: (v) { final n = double.tryParse(v ?? ''); return n == null || n <= 0 ? 'Enter an amount greater than zero' : null; }),
            const SizedBox(height: 12), TextFormField(controller: _description, onChanged: (_) => _changed(), maxLines: 2, decoration: const InputDecoration(labelText: 'Description (optional)')),
            const SizedBox(height: 16), DropdownButtonFormField<int>(initialValue: _payerId, decoration: const InputDecoration(labelText: 'Paid by'), items: _members.map((m) { final user = m['user']; return DropdownMenuItem<int>(value: m['user_id'] as int, child: Text(user['full_name'].toString())); }).toList(), onChanged: (value) { setState(() { _payerId = value; _preview = null; }); }),
            const SizedBox(height: 20), const _SectionHeading(title: 'Choose participants'),
            ..._members.map((member) { final user = Map<String, dynamic>.from(member['user']); final id = member['user_id'] as int; return CheckboxListTile(contentPadding: EdgeInsets.zero, value: _selected.contains(id), title: Text(user['full_name']), onChanged: (checked) { setState(() { if (checked == true) { _selected.add(id); _splitValues.putIfAbsent(id, TextEditingController.new); } else { _selected.remove(id); } _preview = null; }); }); }),
            if (_selected.isEmpty) const Padding(padding: EdgeInsets.only(bottom: 10), child: Text('Select at least one participant.', style: TextStyle(color: Colors.red))),
            const SizedBox(height: 12), DropdownButtonFormField<String>(initialValue: _splitType, decoration: const InputDecoration(labelText: 'Split method'), items: const [DropdownMenuItem(value: 'EQUAL', child: Text('Equal split')), DropdownMenuItem(value: 'EXACT', child: Text('Exact amounts')), DropdownMenuItem(value: 'PERCENTAGE', child: Text('Percentages')), DropdownMenuItem(value: 'SHARES', child: Text('Shares'))], onChanged: (value) { if (value != null) setState(() { _splitType = value; _preview = null; }); }),
            if (_splitType != 'EQUAL') ..._members.where((m) => _selected.contains(m['user_id'])).map((member) { final id = member['user_id'] as int; final label = switch (_splitType) { 'EXACT' => 'Amount for ${member['user']['full_name']}', 'PERCENTAGE' => 'Percent for ${member['user']['full_name']}', _ => 'Shares for ${member['user']['full_name']}' }; return Padding(padding: const EdgeInsets.only(top: 10), child: TextFormField(controller: _splitValues.putIfAbsent(id, TextEditingController.new), onChanged: (_) => _changed(), keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: InputDecoration(labelText: label, suffixText: _splitType == 'PERCENTAGE' ? '%' : _splitType == 'SHARES' ? 'shares' : 'Rs.'), validator: _splitValidator)); }),
            const SizedBox(height: 20), OutlinedButton.icon(onPressed: _previewing ? null : _previewSplit, icon: _previewing ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2)) : const Icon(Icons.calculate_outlined), label: const Text('Preview split')),
            if (_preview != null) ...[
              const SizedBox(height: 16), AppCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text('Split preview · ${_preview!['split_type']}', style: const TextStyle(fontWeight: FontWeight.bold)), const SizedBox(height: 8), ...( _preview!['allocations'] as List).map((allocation) { final id = allocation['user_id']; final member = _members.firstWhere((m) => m['user_id'] == id); return Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(children: [Expanded(child: Text(member['user']['full_name'])), Text(MoneyFormat.format(allocation['amount_owed']))])); })])),
              const SizedBox(height: 12), FilledButton(onPressed: _saving ? null : _save, child: _saving ? const CircularProgressIndicator() : Text(editing ? 'Save changes' : 'Save expense')),
            ],
          ])));
  }
}

class ExpenseDetailsScreen extends ConsumerWidget {
  const ExpenseDetailsScreen({super.key, required this.expenseId});
  final int expenseId;
  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(appBar: AppBar(title: const Text('Expense details')), body: FutureBuilder<Map<String, dynamic>>(future: _repo(ref).expense(expenseId), builder: (context, snapshot) {
    if (snapshot.hasError) return _ErrorState(error: snapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
    if (!snapshot.hasData) return const Center(child: CircularProgressIndicator());
    final expense = snapshot.data!;
    final currentId = ref.read(sessionProvider).user?['id'];
    return FutureBuilder<Map<String, dynamic>>(future: _repo(ref).group(expense['group_id']), builder: (context, groupSnapshot) {
      if (groupSnapshot.hasError) return _ErrorState(error: groupSnapshot.error!, onRetry: () => ref.invalidate(apiClientProvider));
      if (!groupSnapshot.hasData) return const Center(child: CircularProgressIndicator());
      final group = groupSnapshot.data!;
      final canEdit = expense['created_by'] == currentId || group['current_user_role'] == 'ADMIN';
      final participants = (expense['participants'] as List).map((row) => Map<String, dynamic>.from(row)).toList();
      return ListView(padding: const EdgeInsets.all(20), children: [
        AppCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(expense['title'], style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)), const SizedBox(height: 8), Text(MoneyFormat.format(expense['total_amount']), style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: AppTheme.green, fontWeight: FontWeight.w700)), const SizedBox(height: 14), Text('Paid by ${expense['payer']['full_name']}'), Text('Split ${expense['split_type'].toString().toLowerCase()} · ${expense['expense_date'].toString().split('T').first}'), if ((expense['description'] ?? '').toString().isNotEmpty) ...[const SizedBox(height: 12), Text(expense['description'])]])),
        const SizedBox(height: 20), const _SectionHeading(title: 'Shares'), ...participants.map((row) => _PersonTile(user: Map<String, dynamic>.from(row['user']), subtitle: '${row['percentage'] == null ? '' : '${row['percentage']}% · '}${MoneyFormat.format(row['amount_owed'])}')),
        if (canEdit) ...[const SizedBox(height: 14), Row(children: [Expanded(child: OutlinedButton.icon(onPressed: () => context.go('/expenses/$expenseId/edit'), icon: const Icon(Icons.edit_outlined), label: const Text('Edit'))), const SizedBox(width: 10), Expanded(child: OutlinedButton.icon(onPressed: () async { final yes = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(title: const Text('Delete expense?'), content: const Text('This will update the group balances.'), actions: [TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')), FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete'))])); if (yes == true) { try { await _repo(ref).deleteExpense(expenseId); if (context.mounted) context.go('/groups/${expense['group_id']}'); } catch (error) { if (context.mounted) _message(context, apiError(error)); } } }, icon: const Icon(Icons.delete_outline), label: const Text('Delete')))]),],
      ]);
    });
  }));
}

class _ExpenseTile extends StatelessWidget {
  const _ExpenseTile({required this.expense});
  final Map<String, dynamic> expense;
  @override
  Widget build(BuildContext context) => Padding(padding: const EdgeInsets.only(bottom: 10), child: AppCard(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3), child: ListTile(onTap: () => context.go('/expenses/${expense['id']}'), contentPadding: EdgeInsets.zero, leading: const CircleAvatar(backgroundColor: Color(0xFFE1F1EC), child: Icon(Icons.receipt_long_outlined, color: AppTheme.green)), title: Text(expense['title']?.toString() ?? 'Expense', style: const TextStyle(fontWeight: FontWeight.w600)), subtitle: Text('Paid by ${expense['payer']?['full_name'] ?? 'a group member'} · ${expense['expense_date']?.toString().split('T').first ?? ''}'), trailing: Text(MoneyFormat.format(expense['total_amount']), style: const TextStyle(fontWeight: FontWeight.bold)))));
}

class _MoneyMetric extends StatelessWidget {
  const _MoneyMetric({required this.label, required this.value});
  final String label; final Object? value;
  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label, style: const TextStyle(color: Colors.black54)), const SizedBox(height: 3), Text(MoneyFormat.format(value), style: const TextStyle(fontWeight: FontWeight.w700))]);
}

class AddGroupMembersScreen extends ConsumerStatefulWidget {
  const AddGroupMembersScreen({super.key, required this.groupId});
  final int groupId;
  @override
  ConsumerState<AddGroupMembersScreen> createState() => _AddGroupMembersScreenState();
}

class _AddGroupMembersScreenState extends ConsumerState<AddGroupMembersScreen> {
  bool _loading = true;
  List<Map<String, dynamic>> _friends = [];
  Set<int> _memberIds = {};
  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try { final values = await Future.wait([_repo(ref).friends(), _repo(ref).members(widget.groupId)]); _friends = values[0].map((row) => Map<String, dynamic>.from(row['user'])).toList(); _memberIds = values[1].map((row) => row['user_id'] as int).toSet(); }
    catch (e) { if (mounted) _message(context, apiError(e)); }
    finally { if (mounted) setState(() => _loading = false); }
  }
  @override
  Widget build(BuildContext context) => Scaffold(appBar: AppBar(title: const Text('Add members')), body: _loading ? const Center(child: CircularProgressIndicator()) : _friends.where((f) => !_memberIds.contains(f['id'])).isEmpty ? const EmptyState(title: 'No friends to add', message: 'Accepted friends who are not members will appear here.', icon: Icons.person_add_alt_1) : ListView(padding: const EdgeInsets.all(20), children: _friends.where((f) => !_memberIds.contains(f['id'])).map((user) => _PersonTile(user: user, action: FilledButton.tonal(onPressed: () async { try { await _repo(ref).addMember(widget.groupId, user['id']); setState(() => _memberIds.add(user['id'] as int)); if (context.mounted) _message(context, 'Added to group'); } catch (e) { if (context.mounted) _message(context, apiError(e)); } }, child: const Text('Add')))).toList()));
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();
  @override
  Widget build(BuildContext context) => Row(mainAxisSize: MainAxisSize.min, children: [Container(width: 34, height: 34, decoration: BoxDecoration(color: AppTheme.green, borderRadius: BorderRadius.circular(11)), child: const Icon(Icons.call_split_rounded, size: 20, color: Colors.white)), const SizedBox(width: 9), const Text('GroupPay', style: TextStyle(color: AppTheme.ink, fontWeight: FontWeight.w800, fontSize: 20))]);
}

class _StatCard extends StatelessWidget {
  const _StatCard({required this.label, required this.value, required this.icon});
  final String label, value; final IconData icon;
  @override
  Widget build(BuildContext context) => AppCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Icon(icon, color: AppTheme.green), const SizedBox(height: 14), Text(value, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.bold)), Text(label, style: const TextStyle(color: Colors.black54))]));
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading({required this.title, this.action, this.onTap});
  final String title; final String? action; final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700)), if (action != null) TextButton(onPressed: onTap, child: Text(action!))]);
}

class _GroupTile extends StatelessWidget {
  const _GroupTile({required this.group});
  final Map<String, dynamic> group;
  @override
  Widget build(BuildContext context) => AppCard(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5), child: ListTile(contentPadding: EdgeInsets.zero, onTap: () => context.go('/groups/${group['id']}'), leading: const CircleAvatar(backgroundColor: Color(0xFFE1F1EC), child: Icon(Icons.groups_outlined, color: AppTheme.green)), title: Text(group['name']?.toString() ?? 'Group', style: const TextStyle(fontWeight: FontWeight.w600)), subtitle: Text('${group['members_count']} members · ${group['current_user_role']}'), trailing: const Icon(Icons.chevron_right)));
}

class _PersonTile extends StatelessWidget {
  const _PersonTile({required this.user, this.subtitle, this.action});
  final Map<String, dynamic> user; final String? subtitle; final Widget? action;
  @override
  Widget build(BuildContext context) => AppCard(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4), child: ListTile(contentPadding: EdgeInsets.zero, leading: CircleAvatar(backgroundColor: const Color(0xFFE1F1EC), child: Text(_initials(user['full_name']), style: const TextStyle(color: AppTheme.green, fontWeight: FontWeight.bold))), title: Text(user['full_name']?.toString() ?? 'GroupPay user', style: const TextStyle(fontWeight: FontWeight.w600)), subtitle: Text(subtitle ?? user['email']?.toString() ?? ''), trailing: action));
}

class _RetryCard extends StatelessWidget {
  const _RetryCard({required this.message, required this.onRetry});
  final String message; final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => AppCard(child: Column(children: [Text(message, textAlign: TextAlign.center), TextButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: const Text('Retry'))]));
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.error, required this.onRetry});
  final Object error; final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Center(child: Padding(padding: const EdgeInsets.all(24), child: Column(mainAxisSize: MainAxisSize.min, children: [const Icon(Icons.cloud_off_outlined, size: 42), const SizedBox(height: 12), Text(apiError(error), textAlign: TextAlign.center), const SizedBox(height: 8), TextButton.icon(onPressed: onRetry, icon: const Icon(Icons.refresh), label: const Text('Retry'))])));
}

String? _emailValidator(String? value) => value != null && RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(value.trim()) ? null : 'Enter a valid email';
bool _isZeroMoney(Object? value) => RegExp(r'^-?0(?:\.0+)?$').hasMatch((value ?? '0').toString());
String _firstName(dynamic value) { final parts = (value?.toString() ?? '').trim().split(RegExp(r'\s+')); return parts.isEmpty || parts.first.isEmpty ? 'there' : parts.first; }
String _initials(dynamic value) { final words = (value?.toString() ?? 'G').trim().split(RegExp(r'\s+')); return words.take(2).map((w) => w.isEmpty ? '' : w[0].toUpperCase()).join(); }
void _message(BuildContext context, String message) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
