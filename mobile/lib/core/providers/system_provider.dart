import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/capability_summary.dart';
import '../repositories/system_repository.dart';
import 'dio_provider.dart';

final systemRepositoryProvider = Provider<SystemRepository>((ref) {
  return SystemRepository(ref.watch(dioClientProvider));
});

final systemCapabilitiesProvider = FutureProvider<CapabilitySummary>((ref) async {
  return ref.watch(systemRepositoryProvider).getCapabilities();
});
