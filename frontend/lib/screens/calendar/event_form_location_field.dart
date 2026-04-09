import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:pda/screens/calendar/event_form_models.dart';
import 'package:pda/utils/validators.dart' as v;

class EventFormLocationField extends StatefulWidget {
  final TextEditingController controller;
  final ValueChanged<({double lat, double lon})> onLocationSelected;

  const EventFormLocationField({
    super.key,
    required this.controller,
    required this.onLocationSelected,
  });

  @override
  State<EventFormLocationField> createState() => _EventFormLocationFieldState();
}

class _EventFormLocationFieldState extends State<EventFormLocationField> {
  List<EventPhotonResult> _locationResults = [];
  bool _locationSearching = false;
  Timer? _debounceTimer;

  @override
  void dispose() {
    _debounceTimer?.cancel();
    super.dispose();
  }

  void _searchLocation(String query) {
    _debounceTimer?.cancel();
    if (query.trim().length < 3) {
      setState(() {
        _locationResults = [];
      });
      return;
    }
    _debounceTimer = Timer(const Duration(milliseconds: 400), () async {
      if (!mounted) return;
      setState(() => _locationSearching = true);
      try {
        final resp = await Dio().get<Map<String, dynamic>>(
          'https://photon.komoot.io/api/',
          queryParameters: {
            'q': query.trim(),
            'limit': 5,
            'lat': 40.7128, // bias results toward NYC
            'lon': -74.006,
          },
        );
        final features = (resp.data?['features'] as List<dynamic>?) ?? const [];
        if (!mounted) return;
        setState(() {
          _locationResults = features.map((f) {
            final props = f['properties'] as Map<String, dynamic>;
            final coords = f['geometry']['coordinates'] as List<dynamic>;
            final name = props['name'] as String? ?? '';
            final city = props['city'] as String?;
            final parts = <String>[
              if (name.isNotEmpty) name,
              if (city != null) city,
              if (props['state'] != null) props['state'] as String,
              if (props['country'] != null) props['country'] as String,
            ];
            return EventPhotonResult(
              name: name,
              city: city != null && city != name ? city : null,
              fullAddress: parts.join(', '),
              lat: (coords[1] as num).toDouble(),
              lon: (coords[0] as num).toDouble(),
            );
          }).toList();
        });
      } catch (_) {
        if (mounted) setState(() => _locationResults = []);
      } finally {
        if (mounted) setState(() => _locationSearching = false);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: widget.controller,
          decoration: InputDecoration(
            labelText: 'where?',
            prefixIcon: const Icon(Icons.place_outlined),
            suffixIcon: _locationSearching
                ? const Padding(
                    padding: EdgeInsets.all(10),
                    child: SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                : null,
          ),
          onChanged: _searchLocation,
          validator: v.maxLength(300),
        ),
        if (_locationResults.isNotEmpty) ...[
          const SizedBox(height: 4),
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: theme.colorScheme.outlineVariant),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: _locationResults.map((r) {
                return ListTile(
                  dense: true,
                  title: Text(r.name, style: const TextStyle(fontSize: 13)),
                  subtitle: r.city != null
                      ? Text(
                          r.city!,
                          style: TextStyle(
                            fontSize: 12,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        )
                      : null,
                  onTap: () {
                    widget.controller.text = r.fullAddress;
                    widget.onLocationSelected((lat: r.lat, lon: r.lon));
                    setState(() => _locationResults = []);
                  },
                );
              }).toList(),
            ),
          ),
        ],
      ],
    );
  }
}
