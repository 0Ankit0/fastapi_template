import 'package:dio/dio.dart';

class GraphQLClient {
  final Dio _dio;

  GraphQLClient(this._dio);

  Future<Map<String, dynamic>> query(
    String document, {
    Map<String, dynamic>? variables,
  }) {
    return _request(document, variables: variables);
  }

  Future<Map<String, dynamic>> mutation(
    String document, {
    Map<String, dynamic>? variables,
  }) {
    return _request(document, variables: variables);
  }

  Future<Map<String, dynamic>> _request(
    String document, {
    Map<String, dynamic>? variables,
  }) async {
    final response = await _dio.post(
      '/graphql',
      data: {
        'query': document,
        'variables': variables ?? <String, dynamic>{},
      },
    );

    final payload = response.data;
    if (payload is! Map<String, dynamic>) {
      throw Exception('Invalid GraphQL response payload');
    }

    final errors = payload['errors'];
    if (errors is List && errors.isNotEmpty) {
      final first = errors.first;
      if (first is Map<String, dynamic>) {
        throw Exception(first['message']?.toString() ?? 'GraphQL request failed');
      }
      throw Exception('GraphQL request failed');
    }

    final data = payload['data'];
    if (data is! Map<String, dynamic>) {
      throw Exception('GraphQL response has no data');
    }

    return data;
  }
}
