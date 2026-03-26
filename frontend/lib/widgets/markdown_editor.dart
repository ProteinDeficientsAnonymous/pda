import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:markdown_toolbar/markdown_toolbar.dart';

/// Shared markdown editor widget: toolbar + text field with list-continuation
/// on Enter and a working numbered-list button (replacing the buggy one from
/// markdown_toolbar).
class MarkdownEditor extends StatefulWidget {
  const MarkdownEditor({
    super.key,
    required this.controller,
    required this.focusNode,
    this.hintText = 'Write content in Markdown…',
    this.expands = false,
    this.minLines,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final String hintText;

  /// If true the text field expands to fill available space (use inside Expanded).
  final bool expands;

  /// Minimum lines when [expands] is false.
  final int? minLines;

  @override
  State<MarkdownEditor> createState() => _MarkdownEditorState();
}

class _MarkdownEditorState extends State<MarkdownEditor> {
  // Matches `  - `, `- `, `  * `, `* ` (unordered)
  static final _unorderedRe = RegExp(r'^(\s*[-*]\s)');
  // Matches `1. `, `12. ` etc. (ordered)
  static final _orderedRe = RegExp(r'^(\s*)(\d+)\.\s');

  /// Called on every key event on the TextField.
  KeyEventResult _onKey(FocusNode _, KeyEvent event) {
    if (event is! KeyDownEvent && event is! KeyRepeatEvent) {
      return KeyEventResult.ignored;
    }
    if (event.logicalKey != LogicalKeyboardKey.enter) {
      return KeyEventResult.ignored;
    }
    return _handleEnter() ? KeyEventResult.handled : KeyEventResult.ignored;
  }

  bool _handleEnter() {
    final text = widget.controller.text;
    final sel = widget.controller.selection;
    if (!sel.isValid || sel.baseOffset != sel.extentOffset) return false;

    final pos = sel.baseOffset;
    // Find start of current line
    final lineStart = text.lastIndexOf('\n', pos - 1) + 1;
    final currentLine = text.substring(lineStart, pos);

    // Check unordered list
    final unorderedMatch = _unorderedRe.firstMatch(currentLine);
    if (unorderedMatch != null) {
      final prefix = unorderedMatch.group(1)!;
      // If the list item is empty (just the prefix), end the list
      if (currentLine.trim() == prefix.trim()) {
        _replaceCurrentLinePrefix(text, pos, lineStart, currentLine, '');
      } else {
        _insertAtCursor(text, pos, '\n$prefix');
      }
      return true;
    }

    // Check ordered list
    final orderedMatch = _orderedRe.firstMatch(currentLine);
    if (orderedMatch != null) {
      final indent = orderedMatch.group(1)!;
      final n = int.parse(orderedMatch.group(2)!);
      if (currentLine.trim() == '$n. ') {
        // Empty item — end the list
        _replaceCurrentLinePrefix(text, pos, lineStart, currentLine, '');
      } else {
        _insertAtCursor(text, pos, '\n$indent${n + 1}. ');
      }
      return true;
    }

    return false;
  }

  void _insertAtCursor(String text, int pos, String insert) {
    final newText = text.substring(0, pos) + insert + text.substring(pos);
    widget.controller.value = TextEditingValue(
      text: newText,
      selection: TextSelection.collapsed(offset: pos + insert.length),
    );
  }

  void _replaceCurrentLinePrefix(
    String text,
    int pos,
    int lineStart,
    String currentLine,
    String newPrefix,
  ) {
    // Remove the list prefix from current line and insert a plain newline
    final prefixLen = currentLine.length;
    final newText =
        text.substring(0, lineStart) +
        newPrefix +
        text.substring(lineStart + prefixLen);
    final newPos = lineStart + newPrefix.length;
    widget.controller.value = TextEditingValue(
      text: newText,
      selection: TextSelection.collapsed(offset: newPos),
    );
  }

  static final _headingRe = RegExp(r'^#{1,3} ');

  /// Apply a specific heading prefix (`# `, `## `, `### `, or `''`) to the current line.
  void _applyHeading(String prefix) {
    final text = widget.controller.text;
    final sel = widget.controller.selection;
    if (!sel.isValid) return;

    final pos = sel.baseOffset;
    final lineStart = text.lastIndexOf('\n', pos - 1) + 1;
    final lineEnd =
        text.contains('\n', pos) ? text.indexOf('\n', pos) : text.length;
    final line = text.substring(lineStart, lineEnd);

    // Strip any existing heading prefix, then apply the chosen one
    final stripped = line.replaceFirst(_headingRe, '');
    final newLine = '$prefix$stripped';

    final delta = newLine.length - line.length;
    final newText =
        text.substring(0, lineStart) + newLine + text.substring(lineEnd);
    widget.controller.value = TextEditingValue(
      text: newText,
      selection: TextSelection.collapsed(
        offset: (pos + delta).clamp(lineStart, lineStart + newLine.length),
      ),
    );
  }

  /// Prepend `1. ` (or increment) to each selected line, or the current line.
  void _toggleNumberedList() {
    final text = widget.controller.text;
    final sel = widget.controller.selection;
    if (!sel.isValid) return;

    final start = sel.start;
    final end = sel.end;

    // Find the start of the first selected line and end of the last
    final blockStart = text.lastIndexOf('\n', start - 1) + 1;
    final blockEnd =
        text.contains('\n', end) ? text.indexOf('\n', end) : text.length;
    final block = text.substring(blockStart, blockEnd);
    final lines = block.split('\n');

    // If all lines already have ordered prefix, remove it; otherwise add it
    final allOrdered = lines.every((l) => _orderedRe.hasMatch(l));
    String newBlock;
    if (allOrdered) {
      newBlock = lines.map((l) => l.replaceFirst(_orderedRe, r'\1')).join('\n');
      // replaceFirst with backreference doesn't work in Dart — do it manually
      newBlock = lines
          .map((l) {
            final m = _orderedRe.firstMatch(l);
            if (m == null) return l;
            return '${m.group(1)}${l.substring(m.end)}';
          })
          .join('\n');
    } else {
      var i = 1;
      newBlock = lines
          .map((l) {
            // Skip already-ordered lines when adding prefix
            if (_orderedRe.hasMatch(l)) return l;
            return '${i++}. $l';
          })
          .join('\n');
    }

    final newText =
        text.substring(0, blockStart) + newBlock + text.substring(blockEnd);
    final delta = newBlock.length - block.length;
    widget.controller.value = TextEditingValue(
      text: newText,
      selection: TextSelection(
        baseOffset: blockStart,
        extentOffset: blockEnd + delta,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final iconColor = Theme.of(context).colorScheme.onSurface;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: widget.expands ? MainAxisSize.max : MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              PopupMenuButton<String>(
                tooltip: 'Heading',
                icon: Icon(Icons.title, color: iconColor, size: 20),
                onSelected: _applyHeading,
                itemBuilder:
                    (_) => const [
                      PopupMenuItem(value: '# ', child: Text('H1')),
                      PopupMenuItem(value: '## ', child: Text('H2')),
                      PopupMenuItem(value: '### ', child: Text('H3')),
                      PopupMenuItem(value: '', child: Text('Remove heading')),
                    ],
              ),
              IconButton(
                tooltip: 'Numbered list',
                iconSize: 20,
                icon: Icon(Icons.format_list_numbered, color: iconColor),
                onPressed: _toggleNumberedList,
              ),
              MarkdownToolbar(
                useIncludedTextField: false,
                controller: widget.controller,
                focusNode: widget.focusNode,
                hideImage: true,
                hideCheckbox: true,
                hideHorizontalRule: true,
                hideHeading: true,
                hideNumberedList: true,
                collapsable: false,
                iconColor: iconColor,
              ),
            ],
          ),
        ),
        // Text field
        widget.expands ? Expanded(child: _buildField()) : _buildField(),
      ],
    );
  }

  Widget _buildField() {
    return Focus(
      onKeyEvent: _onKey,
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: TextField(
          controller: widget.controller,
          focusNode: widget.focusNode,
          maxLines: widget.expands ? null : null,
          minLines: widget.expands ? null : widget.minLines,
          expands: widget.expands,
          textAlignVertical:
              widget.expands ? TextAlignVertical.top : TextAlignVertical.center,
          inputFormatters: [LengthLimitingTextInputFormatter(50000)],
          decoration: InputDecoration(
            border: const OutlineInputBorder(),
            hintText: widget.hintText,
            alignLabelWithHint: true,
          ),
          style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
        ),
      ),
    );
  }
}
