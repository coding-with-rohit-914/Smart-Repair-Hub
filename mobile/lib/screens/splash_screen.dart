import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'home.dart';
import 'login_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

@override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  bool _navigated = false;

@override
  void initState() {
    super.initState();
    _checkInitialization();
  }

Future<void> _checkInitialization() async {
    final app = context.read<AppState>();

while (!app.initialized) {
      await Future.delayed(const Duration(milliseconds: 100));
      if (!mounted) return;
    }

if (!mounted || _navigated) return;

_navigated = true;

Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) =>
            app.isLoggedIn ? const HomeShell() : const LoginScreen(),
      ),
    );
  }

@override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.home_repair_service,
              size: 96,
              color: Color(0xFF0D6EFD),
            ),
            const SizedBox(height: 16),
            Text(
              'RepairService',
              style: Theme.of(context)
                  .textTheme
                  .headlineMedium
                  ?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text('AC • TV • Fridge — repairs at your doorstep'),
          ],
        ),
      ),
    );
  }
}
