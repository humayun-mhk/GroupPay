import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_client.dart';
import '../storage/token_storage.dart';

class SessionState {
  const SessionState({this.ready = false, this.signedIn = false, this.user});
  final bool ready;
  final bool signedIn;
  final Map<String, dynamic>? user;
}

final tokenStorageProvider = Provider((ref) => const TokenStorage());
final apiClientProvider = Provider((ref) => ApiClient(ref.watch(tokenStorageProvider)));

class SessionController extends StateNotifier<SessionState> {
  SessionController(this.api) : super(const SessionState()) {
    api.onSessionExpired = () => logout();
    _restore();
  }
  final ApiClient api;

  Future<void> _restore() async {
    final token = await api.storage.accessToken;
    if (token == null) {
      state = const SessionState(ready: true);
      return;
    }
    try {
      final response = await api.dio.get('auth/me');
      state = SessionState(ready: true, signedIn: true, user: Map<String, dynamic>.from(response.data));
    } catch (_) {
      await api.storage.clear();
      state = const SessionState(ready: true);
    }
  }

  Future<void> login(String email, String password) async => _authenticate('auth/login', {'email': email, 'password': password});

  Future<void> register(String name, String email, String? phone, String password) async => _authenticate('auth/register', {
        'full_name': name,
        'email': email,
        if (phone != null && phone.trim().isNotEmpty) 'phone_number': phone.trim(),
        'password': password,
      });

  Future<void> _authenticate(String path, Map<String, dynamic> body) async {
    final response = await api.dio.post(path, data: body);
    final data = Map<String, dynamic>.from(response.data);
    await api.storage.save(access: data['access_token'], refresh: data['refresh_token']);
    state = SessionState(ready: true, signedIn: true, user: Map<String, dynamic>.from(data['user']));
  }

  Future<void> logout() async {
    await api.storage.clear();
    state = const SessionState(ready: true);
  }
}

final sessionProvider = StateNotifierProvider<SessionController, SessionState>((ref) => SessionController(ref.watch(apiClientProvider)));
