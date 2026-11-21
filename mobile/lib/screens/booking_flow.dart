import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../services/api_service.dart';


/// Multi-step booking wizard:
/// 1. Category (if not preselected)  2. Service  3. Details  4. Date/Time  5. Confirm
class BookingFlow extends StatefulWidget {
  final int? categoryId;
  const BookingFlow({super.key, this.categoryId});

  @override
  State<BookingFlow> createState() => _BookingFlowState();
}

class _BookingFlowState extends State<BookingFlow> {
  int _step = 0;
  Map<String, dynamic>? _category;
  Map<String, dynamic>? _service;

  final _problemCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _instructionsCtrl = TextEditingController();
  DateTime? _date;
  String _slot = '10:00 AM - 12:00 PM';

  static const _slots = [
    '09:00 AM - 11:00 AM',
    '10:00 AM - 12:00 PM',
    '01:00 PM - 03:00 PM',
    '04:00 PM - 06:00 PM',
    '06:00 PM - 08:00 PM',
  ];

  @override
  Widget build(BuildContext context) {
    final steps = ['Appliance', 'Service', 'Details', 'Schedule', 'Confirm'];
    return Scaffold(
      appBar: AppBar(title: Text('New Booking — ${steps[_step]}')),
      body: Stepper(
        currentStep: _step,
        onStepCancel: () => setState(() => _step = (_step - 1).clamp(0, 4)),
        onStepContinue: _onNext,
        controlsBuilder: (context, details) => Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Row(children: [
            FilledButton(onPressed: details.onStepContinue, child: const Text('Continue')),
            const SizedBox(width: 8),
            TextButton(onPressed: details.onStepCancel, child: const Text('Back')),
          ]),
        ),
        steps: [
          _categoryStep(),
          _serviceStep(),
          _detailsStep(),
          _scheduleStep(),
          _confirmStep(),
        ],
      ),
    );
  }

  Step _categoryStep() {
    final app = context.watch<AppState>();
    final cats = widget.categoryId == null
        ? app.categories
        : app.categories.where((c) => c['id'] == widget.categoryId).toList();
    return Step(
      title: const Text('Appliance'),
      isActive: _step >= 0,
      state: _category != null ? StepState.complete : StepState.indexed,
      content: Column(
        children: cats
            .map((c) => RadioListTile<int>(
                  value: c['id'] as int,
                  groupValue: _category?['id'],
                  title: Text(c['name'].toString()),
                  onChanged: (v) => setState(() {
                    _category = c;
                    _service = null;
                  }),
                ))
            .toList(),
      ),
    );
  }

  Step _serviceStep() {
    final services =
        (_category?['services'] as List?)?.cast<Map<String, dynamic>>() ?? [];
    return Step(
      title: const Text('Service'),
      isActive: _step >= 1,
      state: _service != null ? StepState.complete : StepState.indexed,
      content: _category == null
          ? const Text('Select an appliance first.')
          : Column(
              children: services
                  .map((s) => RadioListTile<int>(
                        value: s['id'] as int,
                        groupValue: _service?['id'],
                        title: Text(s['name'].toString()),
                        subtitle: Text('Rs. ${s['base_price']}'),
                        onChanged: (v) => setState(() => _service = s),
                      ))
                  .toList(),
            ),
    );
  }

  Step _detailsStep() => Step(
        title: const Text('Details'),
        isActive: _step >= 2,
        state: _problemCtrl.text.isNotEmpty ? StepState.complete : StepState.indexed,
        content: Column(children: [
          TextField(
            controller: _problemCtrl,
            maxLines: 3,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
                labelText: 'Describe the problem', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _addressCtrl,
            maxLines: 2,
            decoration: const InputDecoration(
                labelText: 'Service address', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _instructionsCtrl,
            decoration: const InputDecoration(
                labelText: 'Additional instructions (optional)',
                border: OutlineInputBorder()),
          ),
        ]),
      );

  Step _scheduleStep() => Step(
        title: const Text('Schedule'),
        isActive: _step >= 3,
        state: _date != null ? StepState.complete : StepState.indexed,
        content: Column(children: [
          ListTile(
            title: Text(_date == null
                ? 'Select date'
                : DateFormat('EEE, MMM d').format(_date!)),
            leading: const Icon(Icons.calendar_today),
            onTap: () async {
              final d = await showDatePicker(
                context: context,
                initialDate: DateTime.now().add(const Duration(days: 1)),
                firstDate: DateTime.now(),
                lastDate: DateTime.now().add(const Duration(days: 60)),
              );
              if (d != null) setState(() => _date = d);
            },
          ),
          DropdownButtonFormField<String>(
            value: _slot,
            decoration: const InputDecoration(
                labelText: 'Time slot', border: OutlineInputBorder()),
            items: _slots.map((s) => DropdownMenuItem(value: s, child: Text(s))).toList(),
            onChanged: (v) => setState(() => _slot = v!),
          ),
        ]),
      );

  Step _confirmStep() => Step(
        title: const Text('Confirm'),
        isActive: _step >= 4,
        content: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Appliance: ${_category?['name'] ?? '-'}'),
          Text('Service: ${_service?['name'] ?? '-'}'),
          Text('Problem: ${_problemCtrl.text.isEmpty ? '-' : _problemCtrl.text}'),
          Text('Address: ${_addressCtrl.text.isEmpty ? '-' : _addressCtrl.text}'),
          Text(
              'Date: ${_date == null ? '-' : DateFormat('yyyy-MM-dd').format(_date!)}'),
          Text('Slot: $_slot'),
          Text('Estimated charges: Rs. ${_service?['base_price'] ?? '-'}'),
          const SizedBox(height: 16),
          const Text('Payment is collected after service completion via the app.',
              style: TextStyle(color: Colors.grey)),
        ]),
      );

  Future<void> _onNext() async {
    if (_step == 0 && _category == null) return _warn('Select an appliance');
    if (_step == 1 && _service == null) return _warn('Select a service');
    if (_step == 2 && _problemCtrl.text.trim().isEmpty) {
      return _warn('Describe the problem');
    }
    if (_step == 2 && _addressCtrl.text.trim().isEmpty) {
      return _warn('Enter service address');
    }
    if (_step == 3 && _date == null) return _warn('Select a date');

    if (_step < 4) {
      setState(() => _step++);
      return;
    }

    // Submit booking
    final app = context.read<AppState>();
    try {
      final res = await app.api.post('bookings/', body: {
        'service': _service!['id'],
        'problem_description': _problemCtrl.text.trim(),
        'preferred_date': DateFormat('yyyy-MM-dd').format(_date!),
        'preferred_slot': _slot,
        'address': _addressCtrl.text.trim(),
        'instructions': _instructionsCtrl.text.trim(),
      });
      await app.refreshData();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('Booking ${res['booking_id']} created successfully!')));
        Navigator.of(context).pop();
      }
    } on ApiException catch (e) {
      _warn(e.message);
    }
  }

  void _warn(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }
}
