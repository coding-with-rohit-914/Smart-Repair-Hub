
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiException implements Exception {
  final String message;

  ApiException(this.message);

  @override
  String toString() => message;
}

class ApiService {
  static const String _override =
      String.fromEnvironment('API_BASE_URL');

  static const String _defaultBaseUrl =
      'https://smart-repair-hub-backend.onrender.com/api';

  late final String baseUrl =
      _override.isNotEmpty ? _override : _defaultBaseUrl;

  String? _token;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Uri _uri(String path) {
    final cleanPath = path.startsWith('/')
        ? path.substring(1)
        : path;

    return Uri.parse('$baseUrl/$cleanPath');
  }

  Future<dynamic> get(String path) async {
    final res = await http.get(
      _uri(path),
      headers: _headers,
    );

    return _handle(res);
  }

  Future<dynamic> post(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final res = await http.post(
      _uri(path),
      headers: _headers,
      body: jsonEncode(body ?? {}),
    );

    return _handle(res);
  }

  Future<dynamic> patch(
    String path, {
    Map<String, dynamic>? body,
  }) async {
    final res = await http.patch(
      _uri(path),
      headers: _headers,
      body: jsonEncode(body ?? {}),
    );

    return _handle(res);
  }

  dynamic _handle(http.Response res) {
    if (res.statusCode >= 400) {
      throw ApiException(_extractMessage(res));
    }

    if (res.body.isEmpty) return null;

    return jsonDecode(res.body);
  }

  String _extractMessage(http.Response res) {
    try {
      final data = jsonDecode(res.body);

      if (data is Map) {
        for (final key in ['detail', 'error', 'message']) {
          if (data[key] != null) {
            return data[key].toString();
          }
        }

        for (final value in data.values) {
          if (value != null) {
            return value.toString();
          }
        }
      }
    } catch (_) {}

    return 'Request failed (HTTP ${res.statusCode})';
  }

  Future<void> loadToken() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('jwt_access');
  }

  Future<void> saveToken(String token) async {
    _token = token;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('jwt_access', token);
  }

  Future<Map<String, dynamic>?> loadUser() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('user');

    if (raw == null || raw.isEmpty) return null;

    return (jsonDecode(raw) as Map).cast<String, dynamic>();
  }

  Future<void> saveUser(Map<String, dynamic> user) async {
    final prefs = await SharedPreferences.getInstance();

    await prefs.setString('user', jsonEncode(user));
  }

  Future<void> clearToken() async {
    _token = null;

    final prefs = await SharedPreferences.getInstance();

    await prefs.remove('jwt_access');
    await prefs.remove('user');
  }
}
