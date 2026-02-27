enum IpAccessStatus {
  whitelisted,
  blacklisted,
  pending;

  static IpAccessStatus fromString(String v) {
    switch (v.toLowerCase()) {
      case 'whitelisted':
        return IpAccessStatus.whitelisted;
      case 'blacklisted':
        return IpAccessStatus.blacklisted;
      default:
        return IpAccessStatus.pending;
    }
  }

  String toJson() => name;
}

class IpAccess {
  final String id;
  final String userId;
  final String ipAddress;
  final IpAccessStatus status;
  final String reason;
  final String lastSeen;
  final String createdAt;

  const IpAccess({
    required this.id,
    required this.userId,
    required this.ipAddress,
    required this.status,
    required this.reason,
    required this.lastSeen,
    required this.createdAt,
  });

  factory IpAccess.fromJson(Map<String, dynamic> json) {
    return IpAccess(
      id: json['id'].toString(),
      userId: json['user_id']?.toString() ?? '',
      ipAddress: json['ip_address'] as String? ?? '',
      status: IpAccessStatus.fromString(json['status'] as String? ?? 'pending'),
      reason: json['reason'] as String? ?? '',
      lastSeen: json['last_seen'] as String? ?? '',
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}

class IpAccessUpdate {
  final IpAccessStatus status;
  final String? reason;

  const IpAccessUpdate({required this.status, this.reason});

  Map<String, dynamic> toJson() => {
        'status': status.toJson(),
        if (reason != null) 'reason': reason,
      };
}
