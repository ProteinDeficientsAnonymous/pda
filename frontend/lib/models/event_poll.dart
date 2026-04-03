import 'package:pda/models/survey.dart' show PollVoter;

export 'package:pda/models/survey.dart' show PollVoter;

class EventPollOption {
  final String id;
  final DateTime datetime;
  final int displayOrder;
  final int yesCount;
  final int maybeCount;
  final List<PollVoter> yesVoters;
  final List<PollVoter> maybeVoters;

  const EventPollOption({
    required this.id,
    required this.datetime,
    required this.displayOrder,
    required this.yesCount,
    required this.maybeCount,
    this.yesVoters = const [],
    this.maybeVoters = const [],
  });

  int get totalCount => yesCount + maybeCount;

  List<PollVoter> get allVoters => [...yesVoters, ...maybeVoters];

  factory EventPollOption.fromJson(Map<String, dynamic> json) {
    return EventPollOption(
      id: json['id'] as String,
      datetime: DateTime.parse(json['datetime'] as String),
      displayOrder: json['display_order'] as int,
      yesCount: json['yes_count'] as int,
      maybeCount: json['maybe_count'] as int,
      yesVoters:
          (json['yes_voters'] as List<dynamic>?)
              ?.map((e) => PollVoter.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      maybeVoters:
          (json['maybe_voters'] as List<dynamic>?)
              ?.map((e) => PollVoter.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}

class EventPoll {
  final String id;
  final String eventId;
  final bool isActive;
  final List<EventPollOption> options;
  final String? winningOptionId;
  final DateTime? winningDatetime;
  final String? finalizedById;
  final DateTime? finalizedAt;
  final Map<String, String> myVotes; // optionId -> "yes" | "maybe"

  const EventPoll({
    required this.id,
    required this.eventId,
    required this.isActive,
    this.options = const [],
    this.winningOptionId,
    this.winningDatetime,
    this.finalizedById,
    this.finalizedAt,
    this.myVotes = const {},
  });

  bool get isFinalized => winningOptionId != null;

  factory EventPoll.fromJson(Map<String, dynamic> json) {
    return EventPoll(
      id: json['id'] as String,
      eventId: json['event_id'] as String,
      isActive: json['is_active'] as bool,
      options:
          (json['options'] as List<dynamic>?)
              ?.map((e) => EventPollOption.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      winningOptionId: json['winning_option_id'] as String?,
      winningDatetime: json['winning_datetime'] != null
          ? DateTime.parse(json['winning_datetime'] as String)
          : null,
      finalizedById: json['finalized_by_id'] as String?,
      finalizedAt: json['finalized_at'] != null
          ? DateTime.parse(json['finalized_at'] as String)
          : null,
      myVotes:
          (json['my_votes'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, v as String),
          ) ??
          {},
    );
  }
}
