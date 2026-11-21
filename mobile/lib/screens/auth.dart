import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'home.dart';

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
        builder: (_) => app.isLoggedIn ? const HomeShell() : const LoginScreen(),
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
            const Icon(Icons.home_repair_service, size: 96, color: Color(0xFF0D6EFD)),
            const SizedBox(height: 16),
            Text('RepairService',
                style: Theme.of(context)
                    .textTheme
                    .headlineMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            const Text('AC • TV • Fridge — repairs at your doorstep'),
          ],
        ),
      ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _form = GlobalKey<FormState>();
  final _username = TextEditingController();
  final _password = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Navigate to home as soon as login succeeds.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final app = context.read<AppState>();
      app.addListener(_onAppChanged);
    });
  }

  void _onAppChanged() {
    final app = context.read<AppState>();
    if (app.isLoggedIn && mounted) {
      Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const HomeShell()));
    }
  }

  @override
  void dispose() {
    // Listener removal is handled by provider dispose; safe no-op here.
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _form,
            child: Column(
              children: [
                const Icon(Icons.home_repair_service,
                    size: 72, color: Color(0xFF0D6EFD)),
                const SizedBox(height: 8),
                Text('Welcome back',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 24),
                TextFormField(
                  controller: _username,
                  decoration: const InputDecoration(
                      labelText: 'Username', border: OutlineInputBorder()),
                  validator: (v) =>
                      (v == null || v.isEmpty) ? 'Required' : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _password,
                  obscureText: true,
                  decoration: const InputDecoration(
                      labelText: 'Password', border: OutlineInputBorder()),
                  validator: (v) =>
                      (v == null || v.isEmpty) ? 'Required' : null,
                ),
                if (app.error != null) ...[
                  const SizedBox(height: 12),
                  Text(app.error!,
                      style: const TextStyle(color: Colors.red)),
                ],
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  height: 48,
                  child: FilledButton(
                    onPressed: app.loading
                        ? null
                        : () => app.login(_username.text.trim(), _password.text),
                    child: app.loading
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : const Text('Login'),
                  ),
                ),
                TextButton(
                  onPressed: () => Navigator.of(context).push(MaterialPageRoute(
                      builder: (_) => const RegisterScreen())),
                  child: const Text('New here? Create an account'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _username = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  String _role = 'CUSTOMER';

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _form,
          child: Column(
            children: [
              DropdownButtonFormField<String>(
                value: _role,
                decoration: const InputDecoration(
                    labelText: 'Register as', border: OutlineInputBorder()),
                items: const [
                  DropdownMenuItem(value: 'CUSTOMER', child: Text('Customer')),
                  DropdownMenuItem(
                      value: 'TECHNICIAN', child: Text('Technician')),
                ],
                onChanged: (v) => setState(() => _role = v!),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _username,
                decoration: const InputDecoration(
                    labelText: 'Username', border: OutlineInputBorder()),
                validator: (v) =>
                    (v == null || v.isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(
                    labelText: 'Email', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                decoration: const InputDecoration(
                    labelText: 'Phone', border: OutlineInputBorder()),
                validator: (v) =>
                    (v == null || v.isEmpty) ? 'Required' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _password,
                obscureText: true,
                decoration: const InputDecoration(
                    labelText: 'Password (min 6 chars)',
                    border: OutlineInputBorder()),
                validator: (v) =>
                    (v == null || v.length < 6) ? 'Too short' : null,
              ),
              if (app.error != null) ...[
                const SizedBox(height: 12),
                Text(app.error!, style: const TextStyle(color: Colors.red)),
              ],
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: FilledButton(
                  onPressed: app.loading
                      ? null
                      : () async {
                          if (_form.currentState!.validate()) {
                            final ok = await app.register(
                              username: _username.text.trim(),
                              password: _password.text,
                              email: _email.text.trim(),
                              phone: _phone.text.trim(),
                              role: _role,
                            );
                            if (ok && context.mounted) {
                              // Registered & auto-logged in -> pop back; the
                              // LoginScreen listener routes to HomeShell.
                              Navigator.of(context).pop();
                            }
                          }
                        },
                  child: app.loading
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
                      : const Text('Register'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
