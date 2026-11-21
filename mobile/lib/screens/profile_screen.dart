import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'auth.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final user = app.user ?? {};
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          CircleAvatar(
            radius: 40,
            child: Text((user['username'] ?? '?')[0].toUpperCase(),
                style: const TextStyle(fontSize: 32)),
          ),
          const SizedBox(height: 16),
          ListTile(
            leading: const Icon(Icons.person),
            title: const Text('Username'),
            subtitle: Text(user['username'] ?? ''),
          ),
          ListTile(
            leading: const Icon(Icons.email),
            title: const Text('Email'),
            subtitle: Text(user['email'] ?? ''),
          ),
          ListTile(
            leading: const Icon(Icons.phone),
            title: const Text('Phone'),
            subtitle: Text(user['phone'] ?? ''),
          ),
          ListTile(
            leading: const Icon(Icons.badge),
            title: const Text('Role'),
            subtitle: Text(user['role'] ?? ''),
          ),
          if (app.isTechnician) ...[
            const Divider(),
            FutureBuilder<dynamic>(
              future: app.api.get('technician/profile/'),
              builder: (context, snap) {
                if (!snap.hasData) {
                  return const Center(child: CircularProgressIndicator());
                }
                final p = (snap.data as Map).cast<String, dynamic>();
                return Column(children: [
                  ListTile(
                    leading: const Icon(Icons.verified),
                    title: const Text('Approval status'),
                    subtitle: Text(p['approval_status'].toString()),
                  ),
                  ListTile(
                    leading: const Icon(Icons.star),
                    title: const Text('Rating'),
                    subtitle:
                        Text('${p['rating_avg']} (${p['rating_count']} reviews)'),
                  ),
                  SwitchListTile(
                    secondary: const Icon(Icons.work_history),
                    title: const Text('Available for jobs'),
                    value: p['is_available'] == true,
                    onChanged: (v) => app.api
                        .patch('technician/profile/', body: {'is_available': v})
                        .then((_) => app.refreshData()),
                  ),
                ]);
              },
            ),
          ],
          const SizedBox(height: 24),
          OutlinedButton.icon(
            onPressed: () async {
              await app.logout();
              if (context.mounted) {
                Navigator.of(context).pushReplacement(
                    MaterialPageRoute(builder: (_) => const LoginScreen()));
              }
            },
            icon: const Icon(Icons.logout),
            label: const Text('Logout'),
          ),
        ],
      ),
    );
  }
}
