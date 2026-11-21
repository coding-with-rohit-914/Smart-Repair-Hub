import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';

class BookingsScreen extends StatelessWidget {
  const BookingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppState>();
    return Scaffold(
      appBar: AppBar(
          title: Text(app.isTechnician ? 'Service Requests' : 'My Bookings')),
      body: RefreshIndicator(
        onRefresh: () => app.refreshData(),
        child: app.bookings.isEmpty
            ? ListView(children: const [
                Padding(
                  padding: EdgeInsets.all(32),
                  child: Center(child: Text('No bookings yet')),
                )
              ])
            : ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: app.bookings.length,
                itemBuilder: (_, i) {
                  final b = app.bookings[i];
                  return _BookingCard(booking: b, isTechnician: app.isTechnician);
                },
              ),
      ),
    );
  }
}

class _BookingCard extends StatelessWidget {
  final Map<String, dynamic> booking;
  final bool isTechnician;
  const _BookingCard({required this.booking, required this.isTechnician});

  String get _status => (booking['status'] ?? '').toString();
  bool get _hasPayment => booking['has_payment'] == true;
  bool get _hasReview => booking['has_review'] == true;

  Color get _statusColor {
    switch (_status) {
      case 'PENDING':
        return Colors.orange;
      case 'ACCEPTED':
      case 'ASSIGNED':
        return Colors.blue;
      case 'IN_PROGRESS':
      case 'ON_THE_WAY':
      case 'ARRIVED':
        return Colors.purple;
      case 'COMPLETED':
        return Colors.green.shade700;
      case 'PAID':
      case 'CLOSED':
        return Colors.green;
      case 'CANCELLED':
      case 'REJECTED':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final service = booking['service_detail'] as Map<String, dynamic>?;
    final customer = booking['customer'] as Map<String, dynamic>?;
    final app = context.read<AppState>();
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text(booking['booking_id'].toString(),
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                  color: _statusColor.withValues(alpha: .12),
                  borderRadius: BorderRadius.circular(20)),
              child: Text(_status,
                  style: TextStyle(color: _statusColor, fontWeight: FontWeight.w600, fontSize: 12)),
            ),
          ]),
          const SizedBox(height: 6),
          Text('${service?['category_name'] ?? ''} — ${service?['name'] ?? ''}'),
          Text(booking['problem_description'].toString(),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: Colors.grey.shade600, fontSize: 13)),
          const SizedBox(height: 6),
          Text('${booking['preferred_date']} • ${booking['preferred_slot']}',
              style: const TextStyle(fontSize: 13)),
          Text('Amount: Rs. ${booking['final_amount'] ?? booking['estimated_amount']}',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
          if (isTechnician && customer != null) ...[
            const Divider(height: 16),
            Text('Customer: ${customer['username']} • ${customer['phone']}',
                style: const TextStyle(fontSize: 13)),
            Text('Address: ${booking['address']}', style: const TextStyle(fontSize: 13)),
          ],
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (isTechnician && _status == 'PENDING')
              _actionBtn(context, app, 'Accept', 'accept'),
            if (isTechnician && _status == 'PENDING')
              _actionBtn(context, app, 'Reject', 'reject'),
            if (isTechnician && _status == 'ACCEPTED')
              _actionBtn(context, app, 'On the way', 'on_the_way'),
            if (isTechnician && _status == 'ON_THE_WAY')
              _actionBtn(context, app, 'Arrived', 'arrived'),
            if (isTechnician && (_status == 'ON_THE_WAY' || _status == 'ARRIVED'))
              _actionBtn(context, app, 'Start service', 'start'),
            if (isTechnician && _status == 'IN_PROGRESS')
              _actionBtn(context, app, 'Complete', 'complete'),
            if (!isTechnician && _status == 'COMPLETED' && !_hasPayment)
              _payBtn(context, app),
            if (!isTechnician &&
                (_status == 'COMPLETED' || _status == 'PAID' || _status == 'CLOSED') &&
                !_hasReview)
              _reviewBtn(context, app),
            if (!isTechnician &&
                !['CANCELLED', 'REJECTED', 'COMPLETED', 'PAID', 'CLOSED']
                    .contains(_status))
              _cancelBtn(context, app),
          ]),
        ]),
      ),
    );
  }

  Widget _actionBtn(BuildContext context, AppState app, String label, String action) =>
      FilledButton.tonal(
        onPressed: () async {
          try {
            await app.api.post('bookings/${booking['id']}/$action/');
            await app.refreshData();
          } catch (e) {
            if (context.mounted) {
              ScaffoldMessenger.of(context)
                  .showSnackBar(SnackBar(content: Text(e.toString())));
            }
          }
        },
        child: Text(label),
      );

  Widget _payBtn(BuildContext context, AppState app) => FilledButton(
        onPressed: () async {
          try {
            await app.api.post('bookings/${booking['id']}/pay/');
            await app.api.post('bookings/${booking['id']}/pay/confirm/');
            await app.refreshData();
            if (context.mounted) {
              ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Payment successful!')));
            }
          } catch (e) {
            if (context.mounted) {
              ScaffoldMessenger.of(context)
                  .showSnackBar(SnackBar(content: Text(e.toString())));
            }
          }
        },
        child: const Text('Pay now'),
      );

  Widget _reviewBtn(BuildContext context, AppState app) => OutlinedButton(
        onPressed: () => _showReviewDialog(context, app),
        child: const Text('Rate technician'),
      );

  Widget _cancelBtn(BuildContext context, AppState app) => OutlinedButton(
        onPressed: () async {
          try {
            await app.api.post('bookings/${booking['id']}/cancel/');
            await app.refreshData();
          } catch (e) {
            if (context.mounted) {
              ScaffoldMessenger.of(context)
                  .showSnackBar(SnackBar(content: Text(e.toString())));
            }
          }
        },
        child: const Text('Cancel'),
      );

  void _showReviewDialog(BuildContext context, AppState app) {
    int rating = 5;
    final commentCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialog) => AlertDialog(
          title: const Text('Rate your technician'),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (i) {
                  return IconButton(
                    icon: Icon(i < rating ? Icons.star : Icons.star_border,
                        color: Colors.amber),
                    onPressed: () => setDialog(() => rating = i + 1),
                  );
                })),
            TextField(
              controller: commentCtrl,
              decoration: const InputDecoration(
                  labelText: 'Review (optional)', border: OutlineInputBorder()),
            ),
          ]),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
            FilledButton(
              onPressed: () async {
                try {
                  await app.api.post('reviews/', body: {
                    'booking': booking['id'],
                    'rating': rating,
                    'comment': commentCtrl.text.trim(),
                  });
                  await app.refreshData();
                  if (ctx.mounted) Navigator.pop(ctx);
                } catch (e) {
                  if (ctx.mounted) {
                    ScaffoldMessenger.of(ctx)
                        .showSnackBar(SnackBar(content: Text(e.toString())));
                  }
                }
              },
              child: const Text('Submit'),
            ),
          ],
        ),
      ),
    );
  }
}
