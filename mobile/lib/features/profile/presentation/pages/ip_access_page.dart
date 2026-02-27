import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/constants/colors.dart';
import '../../../../core/error/error_handler.dart';
import '../../data/models/ip_access.dart';
import '../../../ip_access/presentation/providers/ip_access_provider.dart';

class IpAccessPage extends ConsumerWidget {
  const IpAccessPage({super.key});

  Color _statusColor(IpAccessStatus status) {
    switch (status) {
      case IpAccessStatus.whitelisted:
        return AppColors.whitelisted;
      case IpAccessStatus.blacklisted:
        return AppColors.blacklisted;
      default:
        return AppColors.pending;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ipAccessAsync = ref.watch(ipAccessListProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('IP Access Control')),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(ipAccessProvider),
        child: ipAccessAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 48, color: Colors.red),
                const SizedBox(height: 12),
                Text(ErrorHandler.handle(err).message,
                    textAlign: TextAlign.center),
                const SizedBox(height: 12),
                ElevatedButton(
                  onPressed: () => ref.invalidate(ipAccessListProvider),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
          data: (ips) => ips.isEmpty
              ? const Center(
                  child: Text('No IP access records found.',
                      style: TextStyle(color: Colors.grey)))
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: ips.length,
                  itemBuilder: (context, index) {
                    final ip = ips[index];
                    return _IpAccessCard(
                      ip: ip,
                      statusColor: _statusColor(ip.status),
                      onStatusChange: (newStatus) async {
                        try {
                          await ref
                              .read(ipAccessRepositoryProvider)
                              .updateIpAccess(ip.id, IpAccessUpdate(status: newStatus));
                          ref.invalidate(ipAccessListProvider);
                        } catch (e) {
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                  content: Text(ErrorHandler.handle(e).message),
                                  backgroundColor: Colors.red),
                            );
                          }
                        }
                      },
                    ).animate().fadeIn(delay: Duration(milliseconds: index * 50)).slideY(begin: 0.05);
                  },
                ),
        ),
      ),
    );
  }
}

class _IpAccessCard extends StatelessWidget {
  final IpAccess ip;
  final Color statusColor;
  final void Function(IpAccessStatus) onStatusChange;

  const _IpAccessCard({
    required this.ip,
    required this.statusColor,
    required this.onStatusChange,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.computer_outlined, color: statusColor),
                const SizedBox(width: 8),
                Text(
                  ip.ipAddress,
                  style: const TextStyle(
                      fontWeight: FontWeight.bold, fontSize: 16),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    ip.status.name.toUpperCase(),
                    style: TextStyle(
                      color: statusColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ),
            if (ip.reason.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Reason: ${ip.reason}',
                  style: const TextStyle(color: Colors.grey, fontSize: 13)),
            ],
            if (ip.lastSeen.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('Last seen: ${_formatDate(ip.lastSeen)}',
                  style: const TextStyle(color: Colors.grey, fontSize: 13)),
            ],
            const SizedBox(height: 12),
            Row(
              children: [
                if (ip.status != IpAccessStatus.whitelisted)
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => onStatusChange(IpAccessStatus.whitelisted),
                      icon: const Icon(Icons.check_circle_outline,
                          color: Colors.green, size: 16),
                      label: const Text('Whitelist',
                          style: TextStyle(color: Colors.green)),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Colors.green),
                      ),
                    ),
                  ),
                if (ip.status != IpAccessStatus.whitelisted &&
                    ip.status != IpAccessStatus.blacklisted)
                  const SizedBox(width: 8),
                if (ip.status != IpAccessStatus.blacklisted)
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => onStatusChange(IpAccessStatus.blacklisted),
                      icon: const Icon(Icons.block_outlined,
                          color: Colors.red, size: 16),
                      label: const Text('Blacklist',
                          style: TextStyle(color: Colors.red)),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Colors.red),
                      ),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatDate(String dateStr) {
    try {
      final dt = DateTime.parse(dateStr).toLocal();
      return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';
    } catch (_) {
      return dateStr;
    }
  }
}
