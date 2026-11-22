import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'home.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

@override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();

String _role = 'CUSTOMER';
  bool _obscure = true;

static final _emailRe = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

@override
  void dispose() {
    _usernameCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

final app = context.read<AppState>();

// On success this also logs the user in (see app_state.dart).
    final ok = await app.register(
      username: _usernameCtrl.text.trim(),
      password: _passwordCtrl.text,
      email: _emailCtrl.text.trim(),
      phone: _phoneCtrl.text.trim(),
      role: _role,
    );

if (ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Account created. Welcome!')),
      );

// Tear down the whole stack and land on HomeShell fresh.
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const HomeShell()),
        (route) => false,
      );
    }
  }

@override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();

return Scaffold(
      appBar: AppBar(title: const Text('Create account')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _usernameCtrl,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(
                    labelText: 'Username',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.person),
                  ),
                  validator: (v) =>
                      (v == null || v.trim().length < 3)
                          ? 'Username must be at least 3 characters'
                          : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.email),
                  ),
                  validator: (v) => !_emailRe.hasMatch((v ?? '').trim())
                      ? 'Enter a valid email'
                      : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _phoneCtrl,
                  keyboardType: TextInputType.phone,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(
                    labelText: 'Phone number',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.phone),
                  ),
                  validator: (v) => (v == null || v.trim().length < 10)
                      ? 'Enter a valid phone number'
                      : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _passwordCtrl,
                  obscureText: _obscure,
                  textInputAction: TextInputAction.next,
                  decoration: InputDecoration(
                    labelText: 'Password (min 6 characters)',
                    border: const OutlineInputBorder(),
                    prefixIcon: const Icon(Icons.lock),
                    suffixIcon: IconButton(
                      icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  ),
                  validator: (v) =>
                      (v == null || v.length < 6) ? 'Minimum 6 characters' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _confirmCtrl,
                  obscureText: _obscure,
                  onFieldSubmitted: (_) => _submit(),
                  decoration: const InputDecoration(
                    labelText: 'Confirm password',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.lock_outline),
                  ),
                  validator: (v) => (v != _passwordCtrl.text)
                      ? 'Passwords do not match'
                      : null,
                ),
                const SizedBox(height: 16),
                const Text('I am a:'),
                Row(
                  children: [
                    ChoiceChip(
                      label: const Text('Customer'),
                      selected: _role == 'CUSTOMER',
                      onSelected: app.loading
                          ? null
                          : (_) => setState(() => _role = 'CUSTOMER'),
                    ),
                    const SizedBox(width: 12),
                    ChoiceChip(
                      label: const Text('Technician'),
                      selected: _role == 'TECHNICIAN',
                      onSelected: app.loading
                          ? null
                          : (_) => setState(() => _role = 'TECHNICIAN'),
                    ),
                  ],
                ),
                if (_role == 'TECHNICIAN')
                  const Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: Text(
                      'Technician accounts need admin approval before accepting jobs.',
                      style: TextStyle(color: Colors.grey, fontSize: 12),
                    ),
                  ),
                const SizedBox(height: 16),
                if (app.error != null) ...[
                  Text(
                    app.error!,
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                  const SizedBox(height: 12),
                ],
                FilledButton(
                  onPressed: app.loading ? null : _submit,
                  child: app.loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Create account'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
