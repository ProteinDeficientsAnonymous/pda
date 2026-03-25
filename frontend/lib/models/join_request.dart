class JoinRequest {
  final String id;
  final String name;
  final String email;
  final String pronouns;
  final String howTheyHeard;
  final String whyJoin;
  final DateTime submittedAt;
  final String status; // pending, approved, rejected

  const JoinRequest({
    required this.id,
    required this.name,
    required this.email,
    required this.pronouns,
    required this.howTheyHeard,
    required this.whyJoin,
    required this.submittedAt,
    required this.status,
  });

  factory JoinRequest.fromJson(Map<String, dynamic> json) {
    return JoinRequest(
      id: json['id'] as String,
      name: json['name'] as String,
      email: json['email'] as String,
      pronouns: json['pronouns'] as String,
      howTheyHeard: json['how_they_heard'] as String,
      whyJoin: json['why_join'] as String,
      submittedAt: DateTime.parse(json['submitted_at'] as String),
      status: json['status'] as String,
    );
  }
}
