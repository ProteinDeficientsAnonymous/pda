class JoinFormQuestion {
  final String id;
  final String label;
  final String fieldType;
  final List<String> options;
  final bool required;
  final int displayOrder;

  const JoinFormQuestion({
    required this.id,
    required this.label,
    required this.fieldType,
    this.options = const [],
    required this.required,
    required this.displayOrder,
  });

  factory JoinFormQuestion.fromJson(Map<String, dynamic> json) {
    return JoinFormQuestion(
      id: json['id'] as String,
      label: json['label'] as String,
      fieldType: json['field_type'] as String,
      options:
          (json['options'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      required: json['required'] as bool,
      displayOrder: json['display_order'] as int,
    );
  }
}
