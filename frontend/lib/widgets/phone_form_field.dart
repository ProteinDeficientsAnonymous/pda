import 'package:flutter/material.dart';
import 'package:intl_phone_field/intl_phone_field.dart';

/// A phone number input field using IntlPhoneField, defaulting to US.
///
/// [onChanged] is called with the complete E.164 number (e.g. +12025551234)
/// whenever the value changes.
class PhoneFormField extends StatelessWidget {
  final ValueChanged<String> onChanged;
  final String? labelText;

  const PhoneFormField({
    super.key,
    required this.onChanged,
    this.labelText = 'Phone number',
  });

  @override
  Widget build(BuildContext context) {
    return IntlPhoneField(
      initialCountryCode: 'US',
      decoration: InputDecoration(
        labelText: labelText,
        border: const OutlineInputBorder(),
      ),
      onChanged: (phone) => onChanged(phone.completeNumber),
      validator: (phone) {
        if (phone == null || phone.number.isEmpty) return 'Required';
        return null;
      },
    );
  }
}
