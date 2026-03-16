'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/store/auth-store';
import * as authApi from '@/lib/graphql/auth';
import { analytics } from '@/lib/analytics';
import { AuthEvents } from '@/lib/analytics/events';
import type {
  LoginCredentials,
  SignupData,
  AuthTokens,
  OTPLoginResponse,
  VerifyOTPData,
  ChangePasswordData,
  ResetPasswordRequestData,
  ResetPasswordConfirmData,
} from '@/types';

export function useAuth() {
  const queryClient = useQueryClient();
  const { user, setUser, setTokens, logout: storeLogout } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      return authApi.login(credentials);
    },
    onSuccess: (data) => {
      if ('requires_otp' in data) return;
      const tokens = data as AuthTokens;
      setTokens(tokens.access, tokens.refresh);
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      analytics.capture(AuthEvents.LOGGED_IN, { method: 'email' });
    },
  });

  const signupMutation = useMutation({
    mutationFn: async (data: SignupData) => {
      return authApi.signup(data);
    },
    onSuccess: (data) => {
      setTokens(data.access, data.refresh);
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      analytics.capture(AuthEvents.SIGNED_UP);
    },
  });

  const { data: currentUser, refetch: refetchUser } = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const u = await authApi.currentUser();
      setUser(u);
      analytics.identify(String(u.id), { email: u.email, username: u.username });
      return u;
    },
    enabled: typeof window !== 'undefined' && !!localStorage.getItem('access_token'),
  });

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // ignore logout errors
    } finally {
      analytics.capture(AuthEvents.LOGGED_OUT);
      analytics.reset();
      storeLogout();
      queryClient.clear();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  };

  return {
    user: currentUser || user,
    isAuthenticated: !!(currentUser || user),
    login: loginMutation.mutate,
    loginAsync: loginMutation.mutateAsync,
    signup: signupMutation.mutate,
    signupAsync: signupMutation.mutateAsync,
    logout,
    refetchUser,
    isLoading: loginMutation.isPending || signupMutation.isPending,
    loginError: loginMutation.error,
    signupError: signupMutation.error,
  };
}

export function useVerifyOTP() {
  const { setTokens } = useAuthStore();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: VerifyOTPData) => {
      return authApi.verifyOtp(data);
    },
    onSuccess: (data) => {
      setTokens(data.access, data.refresh);
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      analytics.capture(AuthEvents.LOGGED_IN, { method: 'otp' });
    },
  });
}

export function useEnableOTP() {
  return useMutation({
    mutationFn: async () => {
      return authApi.enableOtp();
    },
  });
}

export function useConfirmOTP() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (otp_code: string) => {
      return authApi.confirmOtp(otp_code);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      analytics.capture(AuthEvents.OTP_ENABLED);
    },
  });
}

export function useDisableOTP() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (password: string) => {
      return authApi.disableOtp(password);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      analytics.capture(AuthEvents.OTP_DISABLED);
    },
  });
}

export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: async (data: ResetPasswordRequestData) => {
      return authApi.requestPasswordReset(data);
    },
    onSuccess: () => {
      analytics.capture(AuthEvents.PASSWORD_RESET_REQUESTED);
    },
  });
}

export function useConfirmPasswordReset() {
  return useMutation({
    mutationFn: async (data: ResetPasswordConfirmData) => {
      return authApi.confirmPasswordReset(data);
    },
    onSuccess: () => {
      analytics.capture(AuthEvents.PASSWORD_RESET_COMPLETED);
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (data: ChangePasswordData) => {
      return authApi.changePassword(data);
    },
    onSuccess: () => {
      analytics.capture(AuthEvents.PASSWORD_CHANGED);
    },
  });
}

export function useVerifyEmail() {
  return useMutation({
    mutationFn: async (t: string) => {
      return authApi.verifyEmail(t);
    },
    onSuccess: () => {
      analytics.capture(AuthEvents.EMAIL_VERIFIED);
    },
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: async (email?: string) => authApi.resendVerification(email),
  });
}
