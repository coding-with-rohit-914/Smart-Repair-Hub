
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../services/api_service.dart';

/// Multi-step booking wizard:
/// 1. Category (if not preselected)
/// 2. Service
/// 3. Details
/// 4. Date/Time
/// 5. Confirm
class BookingFlow extends StatefulWidget {
  final int? categoryId;

  const BookingFlow({
    super.key,
    this.categoryId,
  });

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

  static const List<String> _slots = [
    '09:00 AM - 11:00 AM',
    '10:00 AM - 12:00 PM',
    '01:00 PM - 03:00 PM',
    '04:00 PM - 06:00 PM',
    '06:00 PM - 08:00 PM',
  ];

  @override
  void dispose() {
    _problemCtrl.dispose();
    _addressCtrl.dispose();
    _instructionsCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final steps = [
      'Appliance',
      'Service',
      'Details',
      'Schedule',
      'Confirm',
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text('New Booking — ${steps[_step]}'),
      ),
      body: Stepper(
        currentStep: _step,
        onStepCancel: () {
          setState(() {
            _step = (_step - 1).clamp(0, 4).toInt();
          });
        },
        onStepContinue: _onNext,
        controlsBuilder: (context, details) {
          return Padding(
            padding: const EdgeInsets.only(top: 12),
            child: Row(
              children: [
                FilledButton(
                  onPressed: details.onStepContinue,
                  child: const Text('Continue'),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: details.onStepCancel,
                  child: const Text('Back'),
                ),
              ],
            ),
          );
        },
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

  // --------------------------------------------------
  // STEP 1: APPLIANCE CATEGORY
  // --------------------------------------------------

  Step _categoryStep() {
    final app = context.watch<AppState>();

    final cats = widget.categoryId == null
        ? app.categories
        : app.categories
            .where((c) => c['id'] == widget.categoryId)
            .toList();

    return Step(
      title: const Text('Appliance'),
      isActive: _step >= 0,
      state: _category != null
          ? StepState.complete
          : StepState.indexed,
      content: cats.isEmpty
          ? const Text('No appliances available.')
          : RadioGroup<int>(
              groupValue: _category?['id'] as int?,
              onChanged: (v) {
                if (v == null) return;

                final match = cats
                    .where((c) => c['id'] == v)
                    .toList();

                if (match.isEmpty) return;

                setState(() {
                  _category = match.first;
                  _service = null;
                });
              },
              child: Column(
                children: cats.map((c) {
                  return RadioListTile<int>(
                    value: c['id'] as int,
                    title: Text(c['name'].toString()),
                  );
                }).toList(),
              ),
            ),
    );
  }

  // --------------------------------------------------
  // STEP 2: SERVICE SELECTION
  // --------------------------------------------------

  Step _serviceStep() {
    final services =
        (_category?['services'] as List?)
                ?.cast<Map<String, dynamic>>() ??
            [];

    return Step(
      title: const Text('Service'),
      isActive: _step >= 1,
      state: _service != null
          ? StepState.complete
          : StepState.indexed,
      content: _category == null
          ? const Text('Select an appliance first.')
          : services.isEmpty
              ? const Text('No services available for this appliance.')
              : RadioGroup<int>(
                  groupValue: _service?['id'] as int?,
                  onChanged: (v) {
                    if (v == null) return;

                    final match = services
                        .where((s) => s['id'] == v)
                        .toList();

                    if (match.isEmpty) return;

                    setState(() {
                      _service = match.first;
                    });
                  },
                  child: Column(
                    children: services.map((s) {
                      return RadioListTile<int>(
                        value: s['id'] as int,
                        title: Text(s['name'].toString()),
                        subtitle: Text(
                          'Rs. ${s['base_price']}',
                        ),
                      );
                    }).toList(),
                  ),
                ),
    );
  }

  // --------------------------------------------------
  // STEP 3: PROBLEM DETAILS
  // --------------------------------------------------

  Step _detailsStep() {
    return Step(
      title: const Text('Details'),
      isActive: _step >= 2,
      state: _problemCtrl.text.trim().isNotEmpty &&
              _addressCtrl.text.trim().isNotEmpty
          ? StepState.complete
          : StepState.indexed,
      content: Column(
        children: [
          TextField(
            controller: _problemCtrl,
            maxLines: 3,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              labelText: 'Describe the problem',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _addressCtrl,
            maxLines: 2,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(
              labelText: 'Service address',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _instructionsCtrl,
            maxLines: 2,
            decoration: const InputDecoration(
              labelText: 'Additional instructions (optional)',
              border: OutlineInputBorder(),
            ),
          ),
        ],
      ),
    );
  }

  // --------------------------------------------------
  // STEP 4: DATE AND TIME SCHEDULE
  // --------------------------------------------------

  Step _scheduleStep() {
    return Step(
      title: const Text('Schedule'),
      isActive: _step >= 3,
      state: _date != null
          ? StepState.complete
          : StepState.indexed,
      content: Column(
        children: [
          ListTile(
            title: Text(
              _date == null
                  ? 'Select date'
                  : DateFormat('EEE, MMM d').format(_date!),
            ),
            leading: const Icon(Icons.calendar_today),
            onTap: () async {
              final now = DateTime.now();

              final initialDate = DateTime(
                now.year,
                now.month,
                now.day + 1,
              );

              final firstDate = DateTime(
                now.year,
                now.month,
                now.day,
              );

              final selectedDate = await showDatePicker(
                context: context,
                initialDate: _date ?? initialDate,
                firstDate: firstDate,
                lastDate: firstDate.add(
                  const Duration(days: 60),
                ),
              );

              if (selectedDate != null && mounted) {
                setState(() {
                  _date = selectedDate;
                });
              }
            },
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: _slot,
            decoration: const InputDecoration(
              labelText: 'Time slot',
              border: OutlineInputBorder(),
            ),
            items: _slots.map((s) {
              return DropdownMenuItem<String>(
                value: s,
                child: Text(s),
              );
            }).toList(),
            onChanged: (v) {
              if (v == null) return;

              setState(() {
                _slot = v;
              });
            },
          ),
        ],
      ),
    );
  }

  // --------------------------------------------------
  // STEP 5: BOOKING CONFIRMATION
  // --------------------------------------------------

  Step _confirmStep() {
    return Step(
      title: const Text('Confirm'),
      isActive: _step >= 4,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Appliance: ${_category?['name'] ?? '-'}',
          ),
          const SizedBox(height: 8),
          Text(
            'Service: ${_service?['name'] ?? '-'}',
          ),
          const SizedBox(height: 8),
          Text(
            'Problem: ${_problemCtrl.text.trim().isEmpty ? '-' : _problemCtrl.text.trim()}',
          ),
          const SizedBox(height: 8),
          Text(
            'Address: ${_addressCtrl.text.trim().isEmpty ? '-' : _addressCtrl.text.trim()}',
          ),
          const SizedBox(height: 8),
          Text(
            'Date: ${_date == null ? '-' : DateFormat('yyyy-MM-dd').format(_date!)}',
          ),
          const SizedBox(height: 8),
          Text('Slot: $_slot'),
          const SizedBox(height: 8),
          Text(
            'Estimated charges: Rs. ${_service?['base_price'] ?? '-'}',
          ),
          const SizedBox(height: 16),
          const Text(
            'Payment is collected after service completion via the app.',
            style: TextStyle(
              color: Colors.grey,
            ),
          ),
        ],
      ),
    );
  }

  // --------------------------------------------------
  // VALIDATION AND BOOKING SUBMISSION
  // --------------------------------------------------

  Future<void> _onNext() async {
    if (_step == 0 && _category == null) {
      _warn('Select an appliance');
      return;
    }

    if (_step == 1 && _service == null) {
      _warn('Select a service');
      return;
    }

    if (_step == 2 && _problemCtrl.text.trim().isEmpty) {
      _warn('Describe the problem');
      return;
    }

    if (_step == 2 && _addressCtrl.text.trim().isEmpty) {
      _warn('Enter service address');
      return;
    }

    if (_step == 3 && _date == null) {
      _warn('Select a date');
      return;
    }

    // Move to the next step.
    if (_step < 4) {
      setState(() {
        _step++;
      });
      return;
    }

    // Submit booking.
    final app = context.read<AppState>();

    try {
      final res = await app.api.post(
        'bookings/',
        body: {
          'service': _service!['id'],
          'problem_description': _problemCtrl.text.trim(),
          'preferred_date': DateFormat('yyyy-MM-dd').format(_date!),
          'preferred_slot': _slot,
          'address': _addressCtrl.text.trim(),
          'instructions': _instructionsCtrl.text.trim(),
        },
      );

      await app.refreshData();

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Booking ${res['booking_id']} created successfully!',
          ),
        ),
      );

      Navigator.of(context).pop();
    } on ApiException catch (e) {
      if (mounted) {
        _warn(e.message);
      }
    } catch (e) {
      if (mounted) {
        _warn('Something went wrong. Please try again.');
      }
    }
  }

  // --------------------------------------------------
  // ERROR MESSAGE
  // --------------------------------------------------

  void _warn(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
      ),
    );
  }
}
