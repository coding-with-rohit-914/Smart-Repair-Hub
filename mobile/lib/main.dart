import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'services/api_service.dart';
import 'screens/splash_screen.dart';
import 'state/app_state.dart';

void main() {
  runApp(const RepairServiceApp());
}

class RepairServiceApp extends StatelessWidget {
  const RepairServiceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppState()..bootstrap(),
      child: MaterialApp(
        title: 'Repair Service',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0D6EFD)),
          useMaterial3: true,
          scaffoldBackgroundColor: const Color(0xFFF6F8FB),
        ),
        home: const SplashScreen(),
      ),
    );
  }
}
