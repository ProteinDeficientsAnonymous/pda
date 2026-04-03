import 'package:pda/config/constants.dart';

class SurveyQuestion {
  final String id;
  final String label;
  final String fieldType;
  final List<String> options;
  final bool required;
  final int displayOrder;

  const SurveyQuestion({
    required this.id,
    required this.label,
    required this.fieldType,
    this.options = const [],
    required this.required,
    required this.displayOrder,
  });

  factory SurveyQuestion.fromJson(Map<String, dynamic> json) {
    return SurveyQuestion(
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

class PollResult {
  final String id;
  final DateTime winningDatetime;
  final String? finalizedById;
  final DateTime finalizedAt;

  const PollResult({
    required this.id,
    required this.winningDatetime,
    this.finalizedById,
    required this.finalizedAt,
  });

  factory PollResult.fromJson(Map<String, dynamic> json) {
    return PollResult(
      id: json['id'] as String,
      winningDatetime: DateTime.parse(json['winning_datetime'] as String),
      finalizedById: json['finalized_by_id'] as String?,
      finalizedAt: DateTime.parse(json['finalized_at'] as String),
    );
  }
}

class PollVoter {
  final String userId;
  final String name;
  final String photoUrl;

  const PollVoter({
    required this.userId,
    required this.name,
    required this.photoUrl,
  });

  factory PollVoter.fromJson(Map<String, dynamic> json) {
    return PollVoter(
      userId: json['user_id'] as String,
      name: json['name'] as String,
      photoUrl: json['photo_url'] as String? ?? '',
    );
  }
}

class PollResults {
  final String questionId;
  final Map<String, Map<String, int>>
  tallies; // option -> {"yes": N, "maybe": M}
  final Map<String, List<PollVoter>> voters;
  final int totalResponses;

  const PollResults({
    required this.questionId,
    required this.tallies,
    this.voters = const {},
    required this.totalResponses,
  });

  /// Total votes (yes + maybe) for an option.
  int totalForOption(String option) {
    final counts = tallies[option];
    if (counts == null) return 0;
    return (counts['yes'] ?? 0) + (counts['maybe'] ?? 0);
  }

  factory PollResults.fromJson(Map<String, dynamic> json) {
    final votersRaw = json['voters'] as Map<String, dynamic>? ?? {};
    final talliesRaw = json['tallies'] as Map<String, dynamic>;
    return PollResults(
      questionId: json['question_id'] as String,
      tallies: talliesRaw.map(
        (k, v) => MapEntry(
          k,
          (v as Map<String, dynamic>).map((ik, iv) => MapEntry(ik, iv as int)),
        ),
      ),
      voters: votersRaw.map(
        (k, v) => MapEntry(
          k,
          (v as List<dynamic>)
              .map((e) => PollVoter.fromJson(e as Map<String, dynamic>))
              .toList(),
        ),
      ),
      totalResponses: json['total_responses'] as int,
    );
  }
}

class Survey {
  final String id;
  final String title;
  final String description;
  final String slug;
  final String visibility;
  final bool isActive;
  final bool oneResponsePerUser;
  final String? linkedEventId;
  final String? createdById;
  final DateTime createdAt;
  final List<SurveyQuestion> questions;
  final int responseCount;
  final PollResult? pollResult;
  final String? myResponseId;
  final Map<String, dynamic>? myAnswers;

  const Survey({
    required this.id,
    required this.title,
    this.description = '',
    required this.slug,
    this.visibility = PageVisibility.public_,
    this.isActive = true,
    this.oneResponsePerUser = false,
    this.linkedEventId,
    this.createdById,
    required this.createdAt,
    this.questions = const [],
    this.responseCount = 0,
    this.pollResult,
    this.myResponseId,
    this.myAnswers,
  });

  factory Survey.fromJson(Map<String, dynamic> json) {
    return Survey(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String? ?? '',
      slug: json['slug'] as String,
      visibility: json['visibility'] as String? ?? PageVisibility.public_,
      isActive: json['is_active'] as bool? ?? true,
      oneResponsePerUser: json['one_response_per_user'] as bool? ?? false,
      linkedEventId: json['linked_event_id'] as String?,
      createdById: json['created_by_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      questions:
          (json['questions'] as List<dynamic>?)
              ?.map((e) => SurveyQuestion.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      responseCount: json['response_count'] as int? ?? 0,
      pollResult: json['poll_result'] != null
          ? PollResult.fromJson(json['poll_result'] as Map<String, dynamic>)
          : null,
      myResponseId: json['my_response_id'] as String?,
      myAnswers: json['my_answers'] as Map<String, dynamic>?,
    );
  }
}

class SurveyResponse {
  final String id;
  final String? userId;
  final String? userName;
  final Map<String, dynamic> answers;
  final DateTime submittedAt;

  const SurveyResponse({
    required this.id,
    this.userId,
    this.userName,
    required this.answers,
    required this.submittedAt,
  });

  factory SurveyResponse.fromJson(Map<String, dynamic> json) {
    return SurveyResponse(
      id: json['id'] as String,
      userId: json['user_id'] as String?,
      userName: json['user_name'] as String?,
      answers: json['answers'] as Map<String, dynamic>? ?? {},
      submittedAt: DateTime.parse(json['submitted_at'] as String),
    );
  }
}
