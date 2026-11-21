import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import 'booking_flow.dart';
import 'bookings_screen.dart';
import 'profile_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    final pages = [
      const HomeTab(),
      const BookingsScreen(),
      const ProfileScreen(),
    ];
    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.build), label: 'Bookings'),
          NavigationDestination(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
      floatingActionButton: _index == 0 && !app.isTechnician
          ? FloatingActionButton.extended(
              onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const BookingFlow())),
              icon: const Icon(Icons.add),
              label: const Text('New Booking'),
            )
          : null,
    );
  }
}

class HomeTab extends StatelessWidget {
  const HomeTab({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(
        title: const Text('RepairService'),
        actions: [
          if (app.isTechnician)
            IconButton(
              icon: const Icon(Icons.attach_money),
              onPressed: () => _showEarnings(context),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => app.refreshData(),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Hi ${app.user?['username'] ?? ''}!',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 4),
            Text(
              app.isTechnician
                  ? 'Available service requests appear in Bookings.'
                  : 'Choose an appliance to book a technician.',
              style: TextStyle(color: Colors.grey.shade600),
            ),
            const SizedBox(height: 20),
            if (app.categories.isEmpty)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: Text('Loading services…')),
              ),
            for (final cat in app.categories) ...[
              _CategoryCard(
                icon: _iconFor(cat['icon'] ?? ''),
                title: cat['name'].toString(),
                subtitle:
                    '${((cat['services'] as List?) ?? []).length} services',
                onTap: () => Navigator.of(context).push(MaterialPageRoute(
                    builder: (_) => BookingFlow(categoryId: cat['id']))),
              ),
              const SizedBox(height: 12),
            ],
          ],
        ),
      ),
    );
  }

  IconData _iconFor(String s) {
    switch (s) {
      case '❄️':
        return Icons.ac_unit;
      case '📺':
        return Icons.tv;
      case '🧊':
        return Icons.kitchen;
      default:
        return Icons.home_repair_service;
    }
  }

  void _showEarnings(BuildContext context) async {
    final api = context.read<AppState>().api;
    try {
      final res = await api.get('technician/earnings/');
      if (context.mounted) {
        showDialog(
          context: context,
          builder: (_) => AlertDialog(
            title: const Text('Earnings'),
            content: Text(
              'Total earnings: Rs. ${res['total_earnings']}\n'
              'Paid jobs: ${res['paid_jobs']}\n'
              'Completed jobs: ${res['completed_jobs']}\n'
              'Rating: ${res['rating_avg']}',
            ),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('OK'))
            ],
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.toString())));
      }
    }
  }
}

class _CategoryCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _CategoryCard(
      {required this.icon,
      required this.title,
      required this.subtitle,
      required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: CircleAvatar(
            backgroundColor: const Color(0xFFE7F0FF),
            child: Icon(icon, color: const Color(0xFF0D6EFD))),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
