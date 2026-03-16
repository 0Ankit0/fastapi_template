import { graphqlRequest } from '@/lib/graphql-client';
import type {
  AuthTokens,
  ChangePasswordData,
  LoginCredentials,
  OTPLoginResponse,
  OTPSetupResponse,
  ResetPasswordConfirmData,
  ResetPasswordRequestData,
  SignupData,
  User,
  VerifyOTPData,
} from '@/types';

interface LoginMutationData {
  login: AuthTokens | OTPLoginResponse;
}

interface SignupMutationData {
  signup: AuthTokens;
}

interface RefreshMutationData {
  refreshToken: AuthTokens;
}

interface CurrentUserQueryData {
  currentUser: User;
}

export async function login(credentials: LoginCredentials): Promise<AuthTokens | OTPLoginResponse> {
  const data = await graphqlRequest<LoginMutationData, { input: LoginCredentials }>(
    `mutation Login($input: LoginInput!) {
      login(input: $input) {
        ... on AuthTokens {
          access
          refresh
          token_type
        }
        ... on OTPLoginResponse {
          requires_otp
          temp_token
          message
        }
      }
    }`,
    { input: credentials }
  );

  return data.login;
}

export async function signup(payload: SignupData): Promise<AuthTokens> {
  const data = await graphqlRequest<SignupMutationData, { input: SignupData }>(
    `mutation Signup($input: SignupInput!) {
      signup(input: $input) {
        access
        refresh
        token_type
      }
    }`,
    { input: payload }
  );

  return data.signup;
}

export async function refreshToken(refreshToken: string): Promise<AuthTokens> {
  const data = await graphqlRequest<RefreshMutationData, { refreshToken: string }>(
    `mutation RefreshToken($refreshToken: String!) {
      refreshToken(refreshToken: $refreshToken) {
        access
        refresh
        token_type
      }
    }`,
    { refreshToken }
  );

  return data.refreshToken;
}

export async function currentUser(): Promise<User> {
  const data = await graphqlRequest<CurrentUserQueryData>(
    `query CurrentUser {
      currentUser {
        id
        username
        email
        first_name
        last_name
        phone
        is_active
        is_verified
        is_superuser
        avatar
        image_url
        bio
        roles
      }
    }`
  );

  return data.currentUser;
}

export async function logout(): Promise<void> {
  await graphqlRequest<{ logout: boolean }>(`mutation Logout { logout }`);
}

export async function verifyOtp(data: VerifyOTPData): Promise<AuthTokens> {
  const gql = await graphqlRequest<{ validateOtp: AuthTokens }, { input: VerifyOTPData }>(
    `mutation ValidateOtp($input: VerifyOtpInput!) {
      validateOtp(input: $input) {
        access
        refresh
        token_type
      }
    }`,
    { input: data }
  );

  return gql.validateOtp;
}

export async function enableOtp(): Promise<OTPSetupResponse> {
  const gql = await graphqlRequest<{ enableOtp: OTPSetupResponse }>(
    `mutation EnableOtp {
      enableOtp {
        otp_base32
        otp_auth_url
        qr_code
      }
    }`
  );

  return gql.enableOtp;
}

export async function confirmOtp(otp_code: string): Promise<unknown> {
  const gql = await graphqlRequest<{ verifyOtp: boolean }, { otpCode: string }>(
    `mutation VerifyOtp($otpCode: String!) {
      verifyOtp(otpCode: $otpCode)
    }`,
    { otpCode: otp_code }
  );

  return gql.verifyOtp;
}

export async function disableOtp(password: string): Promise<unknown> {
  const gql = await graphqlRequest<{ disableOtp: boolean }, { password: string }>(
    `mutation DisableOtp($password: String!) {
      disableOtp(password: $password)
    }`,
    { password }
  );

  return gql.disableOtp;
}

export async function requestPasswordReset(data: ResetPasswordRequestData): Promise<unknown> {
  const gql = await graphqlRequest<{ requestPasswordReset: boolean }, { email: string }>(
    `mutation RequestPasswordReset($email: String!) {
      requestPasswordReset(email: $email)
    }`,
    { email: data.email }
  );

  return gql.requestPasswordReset;
}

export async function confirmPasswordReset(data: ResetPasswordConfirmData): Promise<unknown> {
  const gql = await graphqlRequest<
    { confirmPasswordReset: boolean },
    { input: ResetPasswordConfirmData }
  >(
    `mutation ConfirmPasswordReset($input: ResetPasswordConfirmInput!) {
      confirmPasswordReset(input: $input)
    }`,
    { input: data }
  );

  return gql.confirmPasswordReset;
}

export async function changePassword(data: ChangePasswordData): Promise<unknown> {
  const gql = await graphqlRequest<{ changePassword: boolean }, { input: ChangePasswordData }>(
    `mutation ChangePassword($input: ChangePasswordInput!) {
      changePassword(input: $input)
    }`,
    { input: data }
  );

  return gql.changePassword;
}

export async function verifyEmail(token: string): Promise<unknown> {
  const gql = await graphqlRequest<{ verifyEmail: boolean }, { token: string }>(
    `mutation VerifyEmail($token: String!) {
      verifyEmail(token: $token)
    }`,
    { token }
  );

  return gql.verifyEmail;
}

export async function resendVerification(email?: string): Promise<unknown> {
  const gql = await graphqlRequest<{ resendVerificationEmail: boolean }, { email?: string }>(
    `mutation ResendVerification($email: String) {
      resendVerificationEmail(email: $email)
    }`,
    { email }
  );

  return gql.resendVerificationEmail;
}
