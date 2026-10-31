enum VerificationStatus {
  pending,
  confirmed,
  denied,
  expired,
  noContactMatch,
}

class VerificationRequest {
  final String requestId;
  final String callId;
  final String contactId;
  final String contactName;
  final String claimedIdentity;
  final String action;
  final double? amount;
  final String matchCode; // 6-character match code e.g. "K7M2P9"
  final VerificationStatus status;
  final DateTime createdAt;
  final DateTime expiresAt;
  final DateTime? resolvedAt;

  const VerificationRequest({
    required this.requestId,
    required this.callId,
    required this.contactId,
    required this.contactName,
    required this.claimedIdentity,
    required this.action,
    this.amount,
    required this.matchCode,
    required this.status,
    required this.createdAt,
    required this.expiresAt,
    this.resolvedAt,
  });

  bool get isPending => status == VerificationStatus.pending;
  bool get isConfirmed => status == VerificationStatus.confirmed;
  bool get isDenied => status == VerificationStatus.denied;
  bool get isExpired => status == VerificationStatus.expired;

  int get remainingSeconds {
    final diff = expiresAt.difference(DateTime.now()).inSeconds;
    return diff > 0 ? diff : 0;
  }

  Map<String, dynamic> toJson() => {
        'requestId': requestId,
        'callId': callId,
        'contactId': contactId,
        'contactName': contactName,
        'claimedIdentity': claimedIdentity,
        'action': action,
        'amount': amount,
        'matchCode': matchCode,
        'status': status.name,
        'createdAt': createdAt.toIso8601String(),
        'expiresAt': expiresAt.toIso8601String(),
        'resolvedAt': resolvedAt?.toIso8601String(),
      };

  factory VerificationRequest.fromJson(Map<String, dynamic> json) {
    final rawStatus = json['status'] as String? ?? 'pending';
    VerificationStatus stat;
    switch (rawStatus) {
      case 'confirmed':
        stat = VerificationStatus.confirmed;
        break;
      case 'denied':
        stat = VerificationStatus.denied;
        break;
      case 'expired':
        stat = VerificationStatus.expired;
        break;
      case 'noContactMatch':
        stat = VerificationStatus.noContactMatch;
        break;
      default:
        stat = VerificationStatus.pending;
    }

    return VerificationRequest(
      requestId: json['requestId'] as String,
      callId: json['callId'] as String,
      contactId: json['contactId'] as String,
      contactName: json['contactName'] as String,
      claimedIdentity: json['claimedIdentity'] as String,
      action: json['action'] as String? ?? 'Transfer',
      amount: (json['amount'] as num?)?.toDouble(),
      matchCode: json['matchCode'] as String? ?? '------',
      status: stat,
      createdAt: json['createdAt'] != null
          ? DateTime.tryParse(json['createdAt'] as String) ?? DateTime.now()
          : DateTime.now(),
      expiresAt: json['expiresAt'] != null
          ? DateTime.tryParse(json['expiresAt'] as String) ??
              DateTime.now().add(const Duration(seconds: 45))
          : DateTime.now().add(const Duration(seconds: 45)),
      resolvedAt: json['resolvedAt'] != null
          ? DateTime.tryParse(json['resolvedAt'] as String)
          : null,
    );
  }

  VerificationRequest copyWith({
    VerificationStatus? status,
    DateTime? resolvedAt,
  }) {
    return VerificationRequest(
      requestId: requestId,
      callId: callId,
      contactId: contactId,
      contactName: contactName,
      claimedIdentity: claimedIdentity,
      action: action,
      amount: amount,
      matchCode: matchCode,
      status: status ?? this.status,
      createdAt: createdAt,
      expiresAt: expiresAt,
      resolvedAt: resolvedAt ?? this.resolvedAt,
    );
  }
}
