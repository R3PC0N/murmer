enum TranscriptionStyle { none, formal, informal, technical, custom }

extension TranscriptionStyleExt on TranscriptionStyle {
  String get label => switch (this) {
        TranscriptionStyle.none => 'None',
        TranscriptionStyle.formal => 'Formal',
        TranscriptionStyle.informal => 'Informal',
        TranscriptionStyle.technical => 'Technical',
        TranscriptionStyle.custom => 'Custom',
      };

  String get description => switch (this) {
        TranscriptionStyle.none => 'Only filler removal and punctuation fixes',
        TranscriptionStyle.formal => 'Complete sentences, professional tone',
        TranscriptionStyle.informal => 'Casual tone, contractions allowed',
        TranscriptionStyle.technical => 'Technical terms and acronyms preserved exactly',
        TranscriptionStyle.custom => 'Your own instruction',
      };

  String get systemPrompt => switch (this) {
        TranscriptionStyle.none => '',
        TranscriptionStyle.formal =>
          'Rewrite in formal, complete sentences with proper punctuation.',
        TranscriptionStyle.informal =>
          'Keep a casual tone; contractions are fine; light punctuation.',
        TranscriptionStyle.technical =>
          'Preserve technical terms and acronyms exactly as spoken. Minimal reformatting.',
        TranscriptionStyle.custom => '',
      };
}

class Profile {
  final String id;
  final String name;
  final TranscriptionStyle style;
  final String customInstruction;
  final String userContext;
  final Map<String, String> wordCorrections;

  const Profile({
    required this.id,
    required this.name,
    this.style = TranscriptionStyle.none,
    this.customInstruction = '',
    this.userContext = '',
    this.wordCorrections = const {},
  });

  Profile copyWith({
    String? name,
    TranscriptionStyle? style,
    String? customInstruction,
    String? userContext,
    Map<String, String>? wordCorrections,
  }) =>
      Profile(
        id: id,
        name: name ?? this.name,
        style: style ?? this.style,
        customInstruction: customInstruction ?? this.customInstruction,
        userContext: userContext ?? this.userContext,
        wordCorrections: wordCorrections ?? this.wordCorrections,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'style': style.name,
        'customInstruction': customInstruction,
        'userContext': userContext,
        'wordCorrections': wordCorrections,
      };

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
        id: json['id'] as String,
        name: json['name'] as String,
        style: TranscriptionStyle.values.firstWhere(
          (s) => s.name == (json['style'] as String? ?? 'none'),
          orElse: () => TranscriptionStyle.none,
        ),
        customInstruction: json['customInstruction'] as String? ?? '',
        userContext: json['userContext'] as String? ?? '',
        wordCorrections: Map<String, String>.from(
          json['wordCorrections'] as Map? ?? {},
        ),
      );

  static Profile get defaultProfile => const Profile(
        id: 'default',
        name: 'Default',
      );

  String get effectiveStylePrompt =>
      style == TranscriptionStyle.custom ? customInstruction : style.systemPrompt;
}
