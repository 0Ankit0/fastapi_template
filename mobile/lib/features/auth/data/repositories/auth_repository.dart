import 'dart:convert';

import '../../../../core/error/error_handler.dart';
import '../../../../core/network/dio_client.dart';
import '../../../../core/network/graphql_client.dart';
import '../models/auth_response.dart';
import '../models/login_request.dart';
import '../models/otp_setup_response.dart';
import '../models/register_request.dart';
import '../models/user.dart';

class AuthRepository {
  final GraphQLClient _graphql;

  AuthRepository(DioClient dioClient) : _graphql = GraphQLClient(dioClient.dio);

  Future<AuthResponse> login(LoginRequest request) async {
    try {
      final data = await _graphql.mutation(
        r'''
        mutation Login($input: LoginInput!) {
          login(input: $input) {
            ... on AuthTokens {
              access
              refresh
              token_type
            }
            ... on OTPLoginResponse {
              requires_otp
              temp_token
            }
          }
        }
        ''',
        variables: {'input': request.toJson()},
      );
      return AuthResponse.fromJson(data['login'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<AuthResponse> register(RegisterRequest request) async {
    try {
      final data = await _graphql.mutation(
        r'''
        mutation Signup($input: SignupInput!) {
          signup(input: $input) {
            access
            refresh
            token_type
          }
        }
        ''',
        variables: {'input': request.toJson()},
      );
      return AuthResponse.fromJson(data['signup'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> logout() async {
    try {
      await _graphql.mutation(r'''mutation Logout { logout }''');
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<User> getMe() async {
    try {
      final data = await _graphql.query(r'''
        query CurrentUser {
          currentUser {
            id
            username
            email
            is_confirmed: isConfirmed
            is_active: isActive
            is_superuser: isSuperuser
            otp_enabled: otpEnabled
            otp_verified: otpVerified
            first_name: firstName
            last_name: lastName
            phone
            image_url: imageUrl
            created_at: createdAt
            bio
            roles
          }
        }
      ''');
      return User.fromJson(data['currentUser'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<User> updateMe(Map<String, dynamic> input) async {
    try {
      final data = await _graphql.mutation(
        r'''
        mutation UpdateProfile($input: UserUpdateInput!) {
          updateProfile(input: $input) {
            id
            username
            email
            is_confirmed: isConfirmed
            is_active: isActive
            is_superuser: isSuperuser
            otp_enabled: otpEnabled
            otp_verified: otpVerified
            first_name: firstName
            last_name: lastName
            phone
            image_url: imageUrl
            created_at: createdAt
            bio
            roles
          }
        }
        ''',
        variables: {'input': input},
      );
      return User.fromJson(data['updateProfile'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<User> uploadAvatar(List<int> fileBytes, String fileName) async {
    try {
      final base64Data = base64Encode(fileBytes);
      final data = await _graphql.mutation(
        r'''
        mutation UploadAvatar($input: AvatarUploadInput!) {
          uploadAvatar(input: $input) {
            id
            username
            email
            is_confirmed: isConfirmed
            is_active: isActive
            is_superuser: isSuperuser
            otp_enabled: otpEnabled
            otp_verified: otpVerified
            first_name: firstName
            last_name: lastName
            phone
            image_url: imageUrl
            created_at: createdAt
            bio
            roles
          }
        }
        ''',
        variables: {
          'input': {
            'fileName': fileName,
            'contentType': 'image/*',
            'base64Data': base64Data,
          }
        },
      );
      return User.fromJson(data['uploadAvatar'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<AuthResponse> refreshToken(String refreshToken) async {
    try {
      final data = await _graphql.mutation(
        r'''
        mutation RefreshToken($refreshToken: String!) {
          refreshToken(refreshToken: $refreshToken) {
            access
            refresh
            token_type
          }
        }
        ''',
        variables: {'refreshToken': refreshToken},
      );
      return AuthResponse.fromJson(data['refreshToken'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
    required String confirmPassword,
  }) async {
    try {
      await _graphql.mutation(
        r'''
        mutation ChangePassword($input: ChangePasswordInput!) {
          changePassword(input: $input)
        }
        ''',
        variables: {
          'input': {
            'current_password': currentPassword,
            'new_password': newPassword,
            'confirm_password': confirmPassword,
          }
        },
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> passwordResetRequest(String email) async {
    try {
      await _graphql.mutation(
        r'''
        mutation RequestPasswordReset($email: String!) {
          requestPasswordReset(email: $email)
        }
        ''',
        variables: {'email': email},
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> passwordResetConfirm({
    required String token,
    required String newPassword,
    required String confirmPassword,
  }) async {
    try {
      await _graphql.mutation(
        r'''
        mutation ConfirmPasswordReset($input: ResetPasswordConfirmInput!) {
          confirmPasswordReset(input: $input)
        }
        ''',
        variables: {
          'input': {
            'token': token,
            'new_password': newPassword,
            'confirm_password': confirmPassword,
          }
        },
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<OtpSetupResponse> enableOtp() async {
    try {
      final data = await _graphql.mutation(r'''
        mutation EnableOtp {
          enableOtp {
            otp_base32
            otp_auth_url
            qr_code
          }
        }
      ''');
      return OtpSetupResponse.fromJson(data['enableOtp'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> confirmOtpSetup(String otpCode, String tempToken) async {
    try {
      await _graphql.mutation(
        r'''
        mutation VerifyOtp($otpCode: String!, $tempToken: String!) {
          verifyOtp(otpCode: $otpCode, tempToken: $tempToken)
        }
        ''',
        variables: {'otpCode': otpCode, 'tempToken': tempToken},
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<AuthResponse> validateOtp(String otpCode, String tempToken) async {
    try {
      final data = await _graphql.mutation(
        r'''
        mutation ValidateOtp($input: VerifyOtpInput!) {
          validateOtp(input: $input) {
            access
            refresh
            token_type
          }
        }
        ''',
        variables: {
          'input': {'otp_code': otpCode, 'temp_token': tempToken}
        },
      );
      return AuthResponse.fromJson(data['validateOtp'] as Map<String, dynamic>);
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<void> disableOtp(String password) async {
    try {
      await _graphql.mutation(
        r'''
        mutation DisableOtp($password: String!) {
          disableOtp(password: $password)
        }
        ''',
        variables: {'password': password},
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }

  Future<List<String>> getEnabledSocialProviders() async {
    try {
      final data = await _graphql.query(r'''
        query SocialProviders {
          socialProviders
        }
      ''');
      final providers = data['socialProviders'] as List<dynamic>? ?? [];
      return providers.map((e) => e.toString()).toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> resendVerification([String? email]) async {
    try {
      await _graphql.mutation(
        r'''
        mutation ResendVerification($email: String) {
          resendVerificationEmail(email: $email)
        }
        ''',
        variables: {'email': email},
      );
    } catch (e) {
      throw ErrorHandler.handle(e);
    }
  }
}
