import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/app_screens.dart';
import '../auth/session_controller.dart';

class RouterRefresh extends ChangeNotifier {
  RouterRefresh(Ref ref) {
    ref.listen(sessionProvider, (_, __) => notifyListeners());
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = RouterRefresh(ref);
  ref.onDispose(refresh.dispose);
  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final session = ref.read(sessionProvider);
      if (!session.ready) return state.matchedLocation == '/splash' ? null : '/splash';
      final isAuth = state.matchedLocation == '/login' || state.matchedLocation == '/register' || state.matchedLocation == '/splash';
      if (!session.signedIn && !isAuth) return '/login';
      if (session.signedIn && (state.matchedLocation == '/login' || state.matchedLocation == '/register' || state.matchedLocation == '/splash')) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, __) => const SplashScreen()),
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
      ShellRoute(
        builder: (_, state, child) => AppShell(location: state.matchedLocation, child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
          GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
          GoRoute(path: '/notifications', builder: (_, __) => const NotificationsScreen()),
          GoRoute(path: '/payment-requests', builder: (_, __) => const PaymentRequestsScreen()),
          GoRoute(path: '/settlements/:id', builder: (_, state) => SettlementDetailScreen(id: int.parse(state.pathParameters['id']!))),
          GoRoute(path: '/search', builder: (_, __) => const UserSearchScreen()),
          GoRoute(path: '/friends', builder: (_, __) => const FriendsScreen()),
          GoRoute(path: '/requests', builder: (_, __) => const FriendRequestsScreen()),
          GoRoute(path: '/groups', builder: (_, __) => const GroupsScreen()),
          GoRoute(path: '/groups/create', builder: (_, __) => const CreateGroupScreen()),
          GoRoute(path: '/groups/:id', builder: (_, state) => GroupDetailsScreen(groupId: int.parse(state.pathParameters['id']!))),
          GoRoute(path: '/groups/:id/add-members', builder: (_, state) => AddGroupMembersScreen(groupId: int.parse(state.pathParameters['id']!))),
          GoRoute(path: '/groups/:id/expenses/add', builder: (_, state) => AddExpenseScreen(groupId: int.parse(state.pathParameters['id']!))),
          GoRoute(path: '/groups/:id/expenses', builder: (_, state) => ExpenseHistoryScreen(groupId: int.parse(state.pathParameters['id']!))),
          GoRoute(path: '/groups/:id/balances', builder: (_, state) => GroupBalancesScreen(groupId: int.parse(state.pathParameters['id']!))),
          GoRoute(path: '/groups/:id/settlement-history', builder: (_, state) => SettlementHistoryScreen(groupId: int.parse(state.pathParameters['id']!))),
          GoRoute(path: '/expenses/:expenseId', builder: (_, state) => ExpenseDetailsScreen(expenseId: int.parse(state.pathParameters['expenseId']!))),
          GoRoute(path: '/expenses/:expenseId/edit', builder: (_, state) => AddExpenseScreen(expenseId: int.parse(state.pathParameters['expenseId']!))),
        ],
      ),
    ],
  );
});
