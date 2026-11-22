import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'home.dart';

class OtpScreen extends StatefulWidget {
  const OtpScreen({super.key});

@override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  final _phoneCtrl = TextEditingController();
  final _otpCtrl = TextEditingController();

bool _codeSent = false;
  int _cooldown = 0;
  Timer? _timer;
  String? _localError;

@override
  void dispose() {
    _timer?.cancel();
    _phoneCtrl.dispose();
    _otpCtrl.dispose();
    super.dispose();
  }

void _startCooldown() {
    _timer?.cancel();
    setState(() => _cooldown = 60);
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return;
      setState(() {
        _cooldown--;
        if (_cooldown <= 0) t.cancel();
      });
    });
  }

Future<void> _requestCode() async {
    final phone = _phoneCtrl.text.trim();

if (phone.length < 10) {
      setState(() => _localError = 'Enter a valid phone number');
      return;
    }

final app = context.read<AppState>();

final ok = await app.requestOtp(phone);

if (!mounted) return;

if (ok) {
      setState(() {
        _codeSent = true;
        _localError = null;
      });
      _startCooldown();
    } else {
      setState(() => _localError = app.error);
    }
  }

Future<void> _verify() async {
    final otp = _otpCtrl.text.trim();

if (otp.length != 6) {
      setState(() => _localError = 'Enter the 6-digit code');
      return;
    }

final app = context.read<AppState>();

final ok = await app.verifyOtp(_phoneCtrl.text.trim(), otp);

if (!mounted) return;

if (ok) {
      // Sign-in complete — tear down the stack, land on HomeShell fresh.
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const HomeShell()),
        (route) => false,
      );
    } else {
      setState(() => _localError = app.error);
    }
  }

@override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final error = _localError ?? app.error;

return Scaffold(
      appBar: AppBar(title: const Text('Login with OTP')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(
                Icons.sms_outlined,
                size: 48,
                color: Theme.of(context).colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                _codeSent
                    ? 'We sent a 6-digit code to ${_phoneCtrl.text.trim()}.'
                    : 'Enter the phone number linked to your account.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              if (!_codeSent) ...[
                TextField(
                  controller: _phoneCtrl,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(
                    labelText: 'Phone number',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.phone),
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: app.loading ? null : _requestCode,
                  child: app.loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Send code'),
                ),
              ] else ...[
                TextField(
                  controller: _otpCtrl,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 24,
                    letterSpacing: 8,
                  ),
                  decoration: const InputDecoration(
                    labelText: '6-digit code',
                    border: OutlineInputBorder(),
                    counterText: '',
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: app.loading ? null : _verify,
                  child: app.loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Verify & sign in'),
                ),
                const SizedBox(height: 8),
                TextButton(
                  onPressed: (_cooldown > 0 || app.loading) ? null : _requestCode,
                  child: Text(
                    _cooldown > 0
                        ? 'Resend code in ${_cooldown}s'
                        : 'Resend code',
                  ),
                ),
                TextButton(
                  onPressed: () => setState(() {
                    _codeSent = false;
                    _otpCtrl.clear();
                    _localError = null;
                  }),
                  child: const Text('Change phone number'),
                ),
              ],
              if (error != null) ...[
                const SizedBox(height: 12),
                Text(
                  error,
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
