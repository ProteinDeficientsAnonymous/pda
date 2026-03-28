import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Auto-formats a US phone number as NXX-NXX-XXXX while the user types.
/// Strips non-digits, inserts dashes after positions 3 and 6.
class _UsPhoneFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    final capped = digits.length > 10 ? digits.substring(0, 10) : digits;

    final buf = StringBuffer();
    for (var i = 0; i < capped.length; i++) {
      if (i == 3 || i == 6) buf.write('-');
      buf.write(capped[i]);
    }
    final formatted = buf.toString();
    return TextEditingValue(
      text: formatted,
      selection: TextSelection.collapsed(offset: formatted.length),
    );
  }
}

/// A phone number input field for US numbers.
///
/// Displays as NXX-NXX-XXXX with automatic dash insertion.
/// [onChanged] is called with the E.164-style number (e.g. +12025551234).
class PhoneFormField extends StatelessWidget {
  final ValueChanged<String> onChanged;
  final String? labelText;
  final String? helperText;

  const PhoneFormField({
    super.key,
    required this.onChanged,
    this.labelText = 'Phone number',
    this.helperText,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      decoration: InputDecoration(
        labelText: labelText,
        border: const OutlineInputBorder(),
        prefixText: '+1 ',
        helperText: helperText,
        helperMaxLines: 2,
      ),
      keyboardType: TextInputType.phone,
      autofillHints: const [AutofillHints.telephoneNumber],
      inputFormatters: [_UsPhoneFormatter()],
      onChanged: (value) {
        final digits = value.replaceAll(RegExp(r'\D'), '');
        onChanged('+1$digits');
      },
      validator: (value) {
        final digits = (value ?? '').replaceAll(RegExp(r'\D'), '');
        if (digits.isEmpty) return 'Required';
        if (digits.length != 10) return 'Enter a 10-digit US number';
        return null;
      },
    );
  }
}
