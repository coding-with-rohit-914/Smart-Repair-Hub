import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import '../state/app_state.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

@override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _emailCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();

int _stage = 0; // 0 = email, 1 = code + new password
  bool _busy = false;
  bool _obscure = true;
  String? _error;
  String? _devOtp;

static final _emailRe = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

@override
  void dispose() {
    _emailCtrl.dispose();
    _otpCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

Future<void> _sendCode() async {
    final email = _emailCtrl.text.trim().toLowerCase();

if (!_emailRe.hasMatch(email)) {
      setState(() => _error = 'Enter a valid email');
      return;
    }

setState(() {
      _busy = true;
      _error = null;
    });

final app = context.read<AppState>();

try {
      final res = await app.api.post(
        'auth/password/request-otp/',
        body: {'email': email},
        allowRefresh: false,
      );

if (!mounted) return;

setState(() {
        _stage = 1;
        if (kDebugMode && res is Map && res['otp'] is String) {
          // Shown only because the backend runs with OTP_DEV_MODE=True.
          _devOtp = res['otp'] as String;
        }
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Connection error. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

Future<void> _reset() async {
    final email = _emailCtrl.text.trim().toLowerCase();
    final otp = _otpCtrl.text.trim();
    final password = _passwordCtrl.text;

if (otp.length != 6) {
      setState(() => _error = 'Enter the 6-digit code');
      return;
    }

if (password.length < 6) {
      setState(() => _error = 'Password must be at least 6 characters');
      return;
    }

if (password != _confirmCtrl.text) {
      setState(() => _error = 'Passwords do not match');
      return;
    }

setState(() {
      _busy = true;
      _error = null;
    });

final app = context.read<AppState>();

try {
      await app.api.post(
        'auth/password/reset/',
        body: {
          'email': email,
          'otp': otp,
          'new_password': password,
        },
        allowRefresh: false,
      );

if (!mounted) return;

ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Password reset. Please log in with your new password.'),
        ),
      );

Navigator.of(context).pop(); // back to the login screen
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Connection error. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

@override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Reset password')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(
                Icons.lock_reset,
                size: 48,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                _stage == 0
                    ? "Enter your account email and we'll send a reset code."
                    : 'Enter the code we emailed you and choose a new password.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              if (_stage == 0) ...[
                TextField(
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.email),
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _busy ? null : _sendCode,
                  child: _busy
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Send reset code'),
                ),
              ] else ...[
                if (_devOtp != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      'Dev mode — your code: $_devOtp',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.grey, fontSize: 12),
                    ),
                  ),
                TextField(
                  controller: _otpCtrl,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 24, letterSpacing: 8),
                  decoration: const InputDecoration(
                    labelText: '6-digit code',
                    border: OutlineInputBorder(),
                    counterText: '',
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _passwordCtrl,
                  obscureText: _obscure,
                  decoration: InputDecoration(
                    labelText: 'New password (min 6 characters)',
                    border: const OutlineInputBorder(),
                    prefixIcon: const Icon(Icons.lock),
                    suffixIcon: IconButton(
                      icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _confirmCtrl,
                  obscureText: _obscure,
                  onSubmitted: (_) => _reset(),
                  decoration: const InputDecoration(
                    labelText: 'Confirm new password',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.lock_outline),
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: _busy ? null : _reset,
                  child: _busy
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Reset password'),
                ),
                TextButton(
                  onPressed: _busy
                      ? null
                      : () => setState(() {
                            _stage = 0;
                            _devOtp = null;
                            _otpCtrl.clear();
                          }),
                  child: const Text('Use a different email'),
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
