import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/models/paginated_response.dart';
import '../../../../core/providers/dio_provider.dart';
import '../../../profile/data/models/ip_access.dart';
import '../../data/repositories/ip_access_repository.dart';

final ipAccessRepositoryProvider = Provider<IpAccessRepository>((ref) {
  return IpAccessRepository(ref.watch(dioClientProvider));
});

final ipAccessProvider =
    FutureProvider.family<PaginatedResponse<IpAccess>, ({int skip, int limit})>(
  (ref, params) => ref
      .watch(ipAccessRepositoryProvider)
      .getIpAccessList(skip: params.skip, limit: params.limit),
);

final ipAccessListProvider = FutureProvider<List<IpAccess>>((ref) async {
  final result = await ref.watch(ipAccessRepositoryProvider).getIpAccessList();
  return result.items;
});
