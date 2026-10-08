import 'package:dio/dio.dart';
import '../constants/api_constants.dart';
import '../storage/token_storage.dart';

class ApiClient {
  ApiClient(this.storage)
      : dio = Dio(BaseOptions(
          baseUrl: ApiConstants.baseUrl,
          // Render's free web service can take about a minute to wake after
          // inactivity, so allow the initial request enough time to complete.
          connectTimeout: const Duration(seconds: 30),
          receiveTimeout: const Duration(seconds: 90),
          headers: {'Accept': 'application/json'},
        )) {
    if (ApiConstants.baseUrl.isEmpty) {
      throw StateError('Provide the API origin with --dart-define=API_BASE_URL=...');
    }
    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await storage.accessToken;
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final request = error.requestOptions;
        if (error.response?.statusCode != 401 ||
            request.path.endsWith('auth/login') ||
            request.path.endsWith('auth/register') ||
            request.path.endsWith('auth/refresh') ||
            request.extra['retried'] == true) {
          handler.next(error);
          return;
        }
        try {
          final refresh = await storage.refreshToken;
          if (refresh == null) throw StateError('No refresh token');
          final fresh = await Dio().post(
            '${dio.options.baseUrl}/auth/refresh',
            data: {'refresh_token': refresh},
          );
          final data = fresh.data as Map<String, dynamic>;
          await storage.save(access: data['access_token'], refresh: data['refresh_token']);
          request.headers['Authorization'] = 'Bearer ${data['access_token']}';
          request.extra['retried'] = true;
          handler.resolve(await dio.fetch(request));
        } catch (_) {
          await storage.clear();
          onSessionExpired?.call();
          handler.next(error);
        }
      },
    ));
  }

  final Dio dio;
  final TokenStorage storage;
  void Function()? onSessionExpired;
}

