import '../../../../core/error/error_handler.dart';
import '../../../../core/models/paginated_response.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/network/graphql_client.dart';
import '../../../profile/data/models/token_tracking.dart';

class TokenRepository {
  final GraphQLClient _graphql;

  TokenRepository(DioClient dioClient) : _graphql = GraphQLClient(dioClient.dio);

  Future<PaginatedResponse<TokenTracking>> getTokens({
    int skip = 0,
    int limit = 20,
  }) async {
    try {
      final data = await _graphql.query(
        r'''
        query Tokens($input: PaginationInput) {
          tokens(input: $input) {
            items {
              id
              user_id
              token_jti
              token_type
              ip_address
              user_agent
              is_active
              revoked_at
              revoke_reason
              expires_at
              created_at
            }
            total
            skip
            limit
            has_more
          }
        }
        ''',
        variables: {
          'input': {'skip': skip, 'limit': limit}
        },
      );
      return PaginatedResponse.fromJson(
        data['tokens'] as Map<String, dynamic>,
        TokenTracking.fromJson,
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> revokeToken(String tokenId) async {
    try {
      await _graphql.mutation(
        r'''
        mutation RevokeToken($tokenId: ID!) {
          revokeToken(tokenId: $tokenId)
        }
        ''',
        variables: {'tokenId': tokenId},
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> revokeAllTokens() async {
    try {
      await _graphql.mutation(r'''mutation RevokeAllTokens { revokeAllTokens }''');
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }
}
