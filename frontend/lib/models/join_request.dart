class JoinRequestAnswer {
  final String questionId;
  final String label;
  final String answer;

  const JoinRequestAnswer({
    required this.questionId,
    required this.label,
    required this.answer,
  });

  factory JoinRequestAnswer.fromJson(Map<String, dynamic> json) {
    return JoinRequestAnswer(
      questionId: json['question_id'] as String,
      label: json['label'] as String,
      answer: json['answer'] as String,
    );
  }
}

class JoinRequest {
  final String id;
  final String displayName;
  final String phoneNumber;
  final List<JoinRequestAnswer> answers;
  final DateTime submittedAt;
  final String status;

  const JoinRequest({
    required this.id,
    required this.displayName,
    required this.phoneNumber,
    this.answers = const [],
    required this.submittedAt,
    required this.status,
  });

  factory JoinRequest.fromJson(Map<String, dynamic> json) {
    return JoinRequest(
      id: json['id'] as String,
      displayName: json['display_name'] as String,
      phoneNumber: json['phone_number'] as String,
      answers:
          (json['answers'] as List<dynamic>?)
              ?.map(
                (item) =>
                    JoinRequestAnswer.fromJson(item as Map<String, dynamic>),
              )
              .toList() ??
          [],
      submittedAt: DateTime.parse(json['submitted_at'] as String),
      status: json['status'] as String,
    );
  }
}
