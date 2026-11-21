import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'auth.dart';
import 'home.dart';

/// 2-second splash, then routes to HomeShell (logged in) or LoginScreen.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

@override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(seconds: 2), () {
      if (!mounted) return;
      final app = context.read<AppState>();
      Navigator.of(context).pushReplacement(MaterialPageRoute(
        builder: (_) =>
            app.isLoggedIn ? const HomeShell() : const LoginScreen(),
      ));
    });
  }

@override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.home_repair_service,
                size: 96, color: Color(0xFF0D6EFD)),
            const SizedBox(height: 16),
            Text(
              'RepairService',
              style: Theme.of(context)
                  .textTheme
                  .headlineMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'AC • TV • Fridge — repairs at your doorstep',
              style: TextStyle(color: Colors.grey.shade600),
            ),
            const SizedBox(height: 32),
            const SizedBox(
              width: 32,
              height: 32,
              child: CircularProgressIndicator(strokeWidth: 2.5),
            ),
          ],
        ),
      ),
    );
  }
}
