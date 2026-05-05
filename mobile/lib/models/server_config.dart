class ServerConfig {
  final String id;
  final String name;
  final String url;
  final String apiKey;

  const ServerConfig({
    required this.id,
    required this.name,
    required this.url,
    required this.apiKey,
  });

  ServerConfig copyWith({String? name, String? url, String? apiKey}) => ServerConfig(
        id: id,
        name: name ?? this.name,
        url: url ?? this.url,
        apiKey: apiKey ?? this.apiKey,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'url': url,
        'apiKey': apiKey,
      };

  factory ServerConfig.fromJson(Map<String, dynamic> json) => ServerConfig(
        id: json['id'] as String,
        name: json['name'] as String,
        url: json['url'] as String,
        apiKey: json['apiKey'] as String,
      );

  String get displayUrl {
    final uri = Uri.tryParse(url);
    return uri?.host ?? url;
  }
}
