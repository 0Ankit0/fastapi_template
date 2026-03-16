import '../../../../core/error/error_handler.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/network/graphql_client.dart';
import '../models/payment.dart';

class PaymentRepository {
  final GraphQLClient _graphql;

  PaymentRepository(DioClient dioClient) : _graphql = GraphQLClient(dioClient.dio);

  Future<List<String>> getProviders() async {
    try {
      final data = await _graphql.query(r'''
        query PaymentProviders {
          paymentProviders
        }
      ''');
      final list = data['paymentProviders'] as List<dynamic>? ?? [];
      return list.map((e) => e.toString()).toList();
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<InitiatePaymentResponse> initiatePayment(InitiatePaymentRequest request) async {
    try {
      final data = await _graphql.mutation(
        r'''
        mutation InitiatePayment($input: InitiatePaymentInput!) {
          initiatePayment(input: $input) {
            transaction_id
            provider
            status
            payment_url
            provider_pidx
            extra
          }
        }
        ''',
        variables: {'input': request.toJson()},
      );
      return InitiatePaymentResponse.fromJson(data['initiatePayment'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<VerifyPaymentResponse> verifyPayment(VerifyPaymentRequest request) async {
    try {
      final data = await _graphql.mutation(
        r'''
        mutation VerifyPayment($input: VerifyPaymentInput!) {
          verifyPayment(input: $input) {
            transaction_id
            provider
            status
            amount
            provider_transaction_id
            extra
          }
        }
        ''',
        variables: {'input': request.toJson()},
      );
      return VerifyPaymentResponse.fromJson(data['verifyPayment'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<List<PaymentTransaction>> getTransactions() async {
    try {
      final data = await _graphql.query(r'''
        query PaymentTransactions($input: PaymentTransactionsFilterInput) {
          paymentTransactions(input: $input) {
            id
            provider
            status
            amount
            currency
            purchase_order_id
            purchase_order_name
            provider_transaction_id
            provider_pidx
            return_url
            website_url
            failure_reason
          }
        }
      ''', variables: {'input': {}});
      final list = data['paymentTransactions'] as List<dynamic>? ?? [];
      return list
          .map((e) => PaymentTransaction.fromJson(e as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<PaymentTransaction> getTransaction(int transactionId) async {
    try {
      final data = await _graphql.query(
        r'''
        query PaymentTransaction($transactionId: Int!) {
          paymentTransaction(transactionId: $transactionId) {
            id
            provider
            status
            amount
            currency
            purchase_order_id
            purchase_order_name
            provider_transaction_id
            provider_pidx
            return_url
            website_url
            failure_reason
          }
        }
        ''',
        variables: {'transactionId': transactionId},
      );
      return PaymentTransaction.fromJson(data['paymentTransaction'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }
}
