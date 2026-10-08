import 'package:dio/dio.dart';

class GroupPayRepository {
  GroupPayRepository(this.dio);
  final Dio dio;

  Future<List<Map<String, dynamic>>> groups() async => _maps((await dio.get('groups')).data);
  Future<List<Map<String, dynamic>>> friends() async => _maps((await dio.get('friends')).data);
  Future<List<Map<String, dynamic>>> incoming() async => _maps((await dio.get('friends/requests/incoming')).data);
  Future<List<Map<String, dynamic>>> outgoing() async => _maps((await dio.get('friends/requests/outgoing')).data);
  Future<List<Map<String, dynamic>>> search(String query) async => _maps((await dio.get('users/search', queryParameters: {'q': query})).data);
  Future<Map<String, dynamic>> group(int id) async => Map<String, dynamic>.from((await dio.get('groups/$id')).data);
  Future<List<Map<String, dynamic>>> members(int id) async => _maps((await dio.get('groups/$id/members')).data);
  Future<Map<String, dynamic>> expense(int id) async => Map<String, dynamic>.from((await dio.get('expenses/$id')).data);
  Future<Map<String, dynamic>> groupSummary(int id) async => Map<String, dynamic>.from((await dio.get('groups/$id/summary')).data);
  Future<Map<String, dynamic>> expensePage(int id, {int offset = 0, int limit = 20}) async => Map<String, dynamic>.from((await dio.get('groups/$id/expenses', queryParameters: {'offset': offset, 'limit': limit})).data);
  Future<List<Map<String, dynamic>>> balances(int id) async => _maps((await dio.get('groups/$id/balances')).data);
  Future<List<Map<String, dynamic>>> settlements(int id) async => _maps((await dio.get('groups/$id/settlements')).data);
  Future<List<Map<String, dynamic>>> settlementHistory(int id) async => _maps((await dio.get('groups/$id/settlement-history')).data);
  Future<List<Map<String, dynamic>>> incomingPayments() async => _maps((await dio.get('settlement-requests/incoming')).data);
  Future<List<Map<String, dynamic>>> outgoingPayments() async => _maps((await dio.get('settlement-requests/outgoing')).data);
  Future<List<Map<String, dynamic>>> notifications() async => _maps((await dio.get('notifications')).data);
  Future<int> unreadCount() async => (await dio.get('notifications/unread-count')).data['unread_count'] as int;
  Future<Map<String, dynamic>> settlement(int id) async => Map<String, dynamic>.from((await dio.get('settlement-requests/$id')).data);

  Future<void> sendFriendRequest(int userId) async => dio.post('friends/requests/$userId');
  Future<void> respondFriendRequest(int requestId, bool accept) async => dio.post('friends/requests/$requestId/${accept ? 'accept' : 'reject'}');
  Future<void> createGroup(String name, String description) async => dio.post('groups', data: {'name': name, 'description': description.isEmpty ? null : description});
  Future<void> addMember(int groupId, int userId) async => dio.post('groups/$groupId/members', data: {'user_id': userId});
  Future<void> removeMember(int groupId, int userId) async => dio.delete('groups/$groupId/members/$userId');
  Future<void> updateMemberRole(int groupId, int userId, String role) async => dio.patch('groups/$groupId/members/$userId', data: {'role': role});
  Future<Map<String, dynamic>> previewExpense(int groupId, Map<String, dynamic> data) async => Map<String, dynamic>.from((await dio.post('groups/$groupId/expenses/preview', data: data)).data);
  Future<Map<String, dynamic>> createExpense(int groupId, Map<String, dynamic> data) async => Map<String, dynamic>.from((await dio.post('groups/$groupId/expenses', data: data)).data);
  Future<Map<String, dynamic>> updateExpense(int expenseId, Map<String, dynamic> data) async => Map<String, dynamic>.from((await dio.patch('expenses/$expenseId', data: data)).data);
  Future<void> deleteExpense(int expenseId) async => dio.delete('expenses/$expenseId');
  Future<Map<String, dynamic>> requestPayment(int groupId, int payerId, String amount, {String? note}) async => Map<String, dynamic>.from((await dio.post('groups/$groupId/settlement-requests', data: {'payer_id': payerId, 'amount': amount, 'note': note})).data);
  Future<Map<String, dynamic>> transitionSettlement(int id, String action, {String? note}) async => Map<String, dynamic>.from((await dio.post('settlement-requests/$id/$action', queryParameters: action == 'reject' && note != null ? {'note': note} : null)).data);
  Future<void> markNotificationRead(int id) async => dio.post('notifications/$id/read');
  Future<void> markAllNotificationsRead() async => dio.post('notifications/read-all');

  List<Map<String, dynamic>> _maps(dynamic value) => (value as List).map((item) => Map<String, dynamic>.from(item as Map)).toList();
}
