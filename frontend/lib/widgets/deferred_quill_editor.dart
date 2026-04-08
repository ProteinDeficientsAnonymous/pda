import 'package:flutter/material.dart';
import 'quill_content_editor.dart' deferred as quill;

/// Wraps [QuillContentEditor] behind a deferred import.
///
/// flutter_quill is only loaded the first time this widget is built, keeping
/// it out of the initial JS bundle. Shows a loading indicator while the
/// library downloads.
class DeferredQuillEditor extends StatefulWidget {
  const DeferredQuillEditor({
    super.key,
    required this.jsonContent,
    this.editing = false,
    this.onChanged,
    this.expands = false,
    this.hintText = 'Write something…',
  });

  final String jsonContent;
  final bool editing;
  final void Function(String)? onChanged;
  final bool expands;
  final String hintText;

  @override
  State<DeferredQuillEditor> createState() => _DeferredQuillEditorState();
}

class _DeferredQuillEditorState extends State<DeferredQuillEditor> {
  bool _loaded = false;

  @override
  void initState() {
    super.initState();
    quill.loadLibrary().then((_) {
      if (mounted) setState(() => _loaded = true);
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) {
      return const Center(child: CircularProgressIndicator());
    }
    return quill.QuillContentEditor(
      jsonContent: widget.jsonContent,
      editing: widget.editing,
      onChanged: widget.onChanged,
      expands: widget.expands,
      hintText: widget.hintText,
    );
  }
}
