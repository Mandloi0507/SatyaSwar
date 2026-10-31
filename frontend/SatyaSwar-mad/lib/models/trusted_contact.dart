class TrustedContact {
  final String id;
  final String name;
  final String phoneNumber;
  final String alias;
  final String? inviteCode;
  final bool isVerified;
  final DateTime createdAt;

  const TrustedContact({
    required this.id,
    required this.name,
    required this.phoneNumber,
    required this.alias,
    this.inviteCode,
    this.isVerified = true,
    required this.createdAt,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'phoneNumber': phoneNumber,
        'alias': alias,
        'inviteCode': inviteCode,
        'isVerified': isVerified,
        'createdAt': createdAt.toIso8601String(),
      };

  factory TrustedContact.fromJson(Map<String, dynamic> json) => TrustedContact(
        id: json['id'] as String,
        name: json['name'] as String,
        phoneNumber: json['phoneNumber'] as String,
        alias: json['alias'] as String? ?? 'Contact',
        inviteCode: json['inviteCode'] as String?,
        isVerified: json['isVerified'] as bool? ?? true,
        createdAt: json['createdAt'] != null
            ? DateTime.tryParse(json['createdAt'] as String) ?? DateTime.now()
            : DateTime.now(),
      );
}
