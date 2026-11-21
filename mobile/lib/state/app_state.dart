import 'package:flutter/foundation.dart';

import '../services/api_service.dart';

/// Global app state: auth, catalog, bookings.
class AppState extends ChangeNotifier {
  final api = ApiService();

  bool initialized = false;
  bool loading = false;
  Map<String, dynamic>? user;

  List<Map<String, dynamic>> categories = [];
  List<Map<String, dynamic>> bookings = [];
  List<Map<String, dynamic>> notifications = [];

  String? error;

  bool get isLoggedIn => user != null;
  bool get isTechnician => user?['role'] == 'TECHNICIAN';

  Future<void> bootstrap() async {
    await api.loadToken();
    user = await api.loadUser();
    initialized = true;
    notifyListeners();
    if (isLoggedIn) {
      await refreshData();
    }
  }

  Future<bool> login(String username, String password) async {
    loading = true;
    error = null;
    notifyListeners();
    var ok = false;
    try {
      final res = await api.post('auth/login/', body: {
        'username': username,
        'password': password,
      });
      await api.saveToken(res['access'] as String);
      user = (res['user'] as Map).cast<String, dynamic>();
      await api.saveUser(user!);
      await refreshData();
      ok = true;
    } on ApiException catch (e) {
      error = e.message;
    } finally {
      loading = false;
      notifyListeners();
    }
    return ok;
  }

  Future<bool> register({
    required String username,
    required String password,
    required String email,
    required String phone,
    required String role,
  }) async {
    loading = true;
    error = null;
    notifyListeners();
    var ok = false;
    try {
      await api.post('auth/register/', body: {
        'username': username,
        'password': password,
        'email': email,
        'phone': phone,
        'role': role,
      });
      ok = await login(username, password);
    } on ApiException catch (e) {
      error = e.message;
    } finally {
      loading = false;
      notifyListeners();
    }
    return ok;
  }

  Future<void> logout() async {
    await api.clearToken();
    user = null;
    bookings = [];
    categories = [];
    notifications = [];
    notifyListeners();
  }

  Future<void> refreshData() async {
    try {
      final cats = await api.get('categories/');
      final catList = cats is List ? cats : (cats['results'] as List? ?? []);
      categories = catList.cast<Map<String, dynamic>>();
    } catch (_) {}

    if (isLoggedIn) {
      try {
        final bks = await api.get('bookings/');
        final list = bks is List ? bks : (bks['results'] as List? ?? []);
        bookings = list.cast<Map<String, dynamic>>();
      } catch (_) {}
      try {
        final notifs = await api.get('notifications/');
        final list = notifs is List ? notifs : (notifs['results'] as List? ?? []);
        notifications = list.cast<Map<String, dynamic>>();
      } catch (_) {}
    }
    notifyListeners();
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    loading = true;
    notifyListeners();
    try {
      final res = await api.patch('auth/profile/', body: data);
      user = (res as Map).cast<String, dynamic>();
      await api.saveUser(user!);
    } on ApiException catch (e) {
      error = e.message;
    } finally {
      loading = false;
      notifyListeners();
    }
  }
}
