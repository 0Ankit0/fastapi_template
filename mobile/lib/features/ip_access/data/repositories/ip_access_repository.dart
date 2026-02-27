import '../../../../core/error/error_handler.dart';
import '../../../../core/models/paginated_response.dart';
import '../../../../core/network/api_endpoints.dart';
import '../../../../core/network/dio_client.dart';
import '../../../profile/data/models/ip_access.dart';

class IpAccessRepository {
  final DioClient _dioClient;

  IpAccessRepository(this._dioClient);

  Future<PaginatedResponse<IpAccess>> getIpAccessList({
    int skip = 0,
    int limit = 20,
  }) async {
    try {
      final response = await _dioClient.dio.get(
        ApiEndpoints.ipAccess,
        queryParameters: {'skip': skip, 'limit': limit},
      );
      return PaginatedResponse.fromJson(
        response.data as Map<String, dynamic>,
        IpAccess.fromJson,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<IpAccess> updateIpAccess(String ipId, IpAccessUpdate data) async {
    try {
      final response = await _dioClient.dio.patch(
        ApiEndpoints.updateIpAccess(ipId),
        data: data.toJson(),
      );
      return IpAccess.fromJson(response.data as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }
}
