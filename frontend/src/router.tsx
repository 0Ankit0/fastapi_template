import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { Providers } from '@/components/providers';
import { RootLayout } from '@/app/root-layout';
import HomePage from '@/app/page';
import AuthLayout from '@/app/(auth)/layout';
import LoginPage from '@/app/(auth)/login/page';
import SignupPage from '@/app/(auth)/signup/page';
import ForgotPasswordPage from '@/app/(auth)/forgot-password/page';
import ResetPasswordPage from '@/app/(auth)/reset-password/page';
import OtpVerifyPage from '@/app/(auth)/otp-verify/page';
import VerifyEmailPage from '@/app/(auth)/verify-email/page';
import AcceptInvitationPage from '@/app/(auth)/accept-invitation/page';
import AuthCallbackPage from '@/app/(auth)/auth-callback/page';
import PaymentCallbackPage from '@/app/(auth)/payment-callback/page';
import { SuperuserRoute } from '@/components/auth/superuser-route';
import UserDashboardLayout from '@/app/(user-dashboard)/layout';
import DashboardPage from '@/app/(user-dashboard)/dashboard/page';
import ProfilePage from '@/app/(user-dashboard)/profile/page';
import SettingsPage from '@/app/(user-dashboard)/settings/page';
import NotificationsPage from '@/app/(user-dashboard)/notifications/page';
import FinancesPage from '@/app/(user-dashboard)/finances/page';
import TokensPage from '@/app/(user-dashboard)/tokens/page';
import TenantsPage from '@/app/(user-dashboard)/tenants/page';
import MapsPage from '@/app/(user-dashboard)/maps/page';
import RbacPage from '@/app/(user-dashboard)/rbac/page';
import RoleManagePage from '@/app/(user-dashboard)/rbac/[roleId]/page';
import AdminDashboardLayout from '@/app/(admin-dashboard)/layout';
import AdminDashboardPage from '@/app/(admin-dashboard)/admin/dashboard/page';
import AdminUsersPage from '@/app/(admin-dashboard)/admin/users/page';
import AdminRbacPage from '@/app/(admin-dashboard)/admin/rbac/page';
import AdminRoleManagePage from '@/app/(admin-dashboard)/admin/rbac/[roleId]/page';
import AdminSecurityReviewPage from '@/app/(admin-dashboard)/admin/security-review/page';

function RootProviders() {
  return (
    <RootLayout>
      <Providers>
        <Outlet />
      </Providers>
    </RootLayout>
  );
}

function AuthRouteLayout() {
  return (
    <AuthLayout>
      <Outlet />
    </AuthLayout>
  );
}

function UserRouteLayout() {
  return (
    <UserDashboardLayout>
      <Outlet />
    </UserDashboardLayout>
  );
}

function AdminRouteLayout() {
  return (
    <AdminDashboardLayout>
      <Outlet />
    </AdminDashboardLayout>
  );
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<RootProviders />}>
          <Route index element={<HomePage />} />

          <Route element={<AuthRouteLayout />}>
            <Route path="login" element={<LoginPage />} />
            <Route path="signup" element={<SignupPage />} />
            <Route path="forgot-password" element={<ForgotPasswordPage />} />
            <Route path="reset-password" element={<ResetPasswordPage />} />
            <Route path="otp-verify" element={<OtpVerifyPage />} />
            <Route path="verify-email" element={<VerifyEmailPage />} />
            <Route path="accept-invitation" element={<AcceptInvitationPage />} />
            <Route path="auth-callback" element={<AuthCallbackPage />} />
            <Route path="payment-callback" element={<PaymentCallbackPage />} />
          </Route>

          <Route element={<UserRouteLayout />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="finances" element={<FinancesPage />} />
            <Route path="tokens" element={<TokensPage />} />
            <Route path="tenants" element={<TenantsPage />} />
            <Route path="maps" element={<MapsPage />} />
            <Route
              path="rbac"
              element={
                <SuperuserRoute>
                  <RbacPage />
                </SuperuserRoute>
              }
            />
            <Route
              path="rbac/:roleId"
              element={
                <SuperuserRoute>
                  <RoleManagePage />
                </SuperuserRoute>
              }
            />
          </Route>

          <Route element={<AdminRouteLayout />}>
            <Route path="admin" element={<Navigate to="/admin/dashboard" replace />} />
            <Route path="admin/dashboard" element={<AdminDashboardPage />} />
            <Route path="admin/users" element={<AdminUsersPage />} />
            <Route path="admin/rbac" element={<AdminRbacPage />} />
            <Route path="admin/rbac/:roleId" element={<AdminRoleManagePage />} />
            <Route path="admin/security-review" element={<AdminSecurityReviewPage />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}