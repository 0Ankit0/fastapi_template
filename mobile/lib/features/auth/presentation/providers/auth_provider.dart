import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/error/app_exception.dart';
import '../../../../core/providers/dio_provider.dart';
import '../../../../core/storage/secure_storage.dart';
import '../../data/models/login_request.dart';
import '../../data/models/register_request.dart';
import '../../data/models/user.dart';
import '../../data/repositories/auth_repository.dart';

class AuthState {
  final User? user;
  final bool isAuthenticated;
  final String? error;
  final bool requiresOtp;
  final String? tempToken;

  const AuthState({
    this.user,
    this.isAuthenticated = false,
    this.error,
    this.requiresOtp = false,
    this.tempToken,
  });

  AuthState copyWith({
    User? user,
    bool? isAuthenticated,
    String? error,
    bool clearError = false,
    bool? requiresOtp,
    String? tempToken,
    bool clearOtp = false,
  }) {
    return AuthState(
      user: user ?? this.user,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      error: clearError ? null : (error ?? this.error),
      requiresOtp: clearOtp ? false : (requiresOtp ?? this.requiresOtp),
      tempToken: clearOtp ? null : (tempToken ?? this.tempToken),
    );
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final dioClient = ref.watch(dioClientProvider);
  return AuthRepository(dioClient);
});

final authNotifierProvider =
    AsyncNotifierProvider<AuthNotifier, AuthState>(AuthNotifier.new);

class AuthNotifier extends AsyncNotifier<AuthState> {
  late AuthRepository _authRepository;
  late SecureStorage _secureStorage;

  @override
  Future<AuthState> build() async {
    _authRepository = ref.watch(authRepositoryProvider);
    _secureStorage = ref.watch(secureStorageProvider);
    return _restoreSession();
  }

  Future<AuthState> _restoreSession() async {
    try {
      final accessToken = await _secureStorage.getAccessToken();
      if (accessToken == null) return const AuthState();

      final user = await _authRepository.getMe();
      return AuthState(user: user, isAuthenticated: true);
    } catch (_) {
      await _secureStorage.clearTokens();
      return const AuthState();
    }
  }

  Future<void> login(String username, String password) async {
    state = const AsyncLoading();
    try {
      final request = LoginRequest(username: username, password: password);
      final authResponse = await _authRepository.login(request);

      if (authResponse.requiresOtp && authResponse.tempToken != null) {
        state = AsyncData(AuthState(
          requiresOtp: true,
          tempToken: authResponse.tempToken,
        ));
        return;
      }

      if (authResponse.access != null) {
        await _secureStorage.saveAccessToken(authResponse.access!);
      }
      if (authResponse.refresh != null) {
        await _secureStorage.saveRefreshToken(authResponse.refresh!);
      }
      final user = await _authRepository.getMe();
      state = AsyncData(AuthState(user: user, isAuthenticated: true));
    } on AppException catch (e) {
      state = AsyncData(AuthState(error: e.message));
    } catch (e) {
      state = AsyncData(AuthState(error: e.toString()));
    }
  }

  Future<void> validateOtp(String otpCode, String tempToken) async {
    state = const AsyncLoading();
    try {
      final authResponse = await _authRepository.validateOtp(otpCode, tempToken);
      if (authResponse.access != null) {
        await _secureStorage.saveAccessToken(authResponse.access!);
      }
      if (authResponse.refresh != null) {
        await _secureStorage.saveRefreshToken(authResponse.refresh!);
      }
      final user = await _authRepository.getMe();
      state = AsyncData(AuthState(user: user, isAuthenticated: true));
    } on AppException catch (e) {
      state = AsyncData(AuthState(error: e.message));
    } catch (e) {
      state = AsyncData(AuthState(error: e.toString()));
    }
  }

  Future<void> register(String username, String email, String password) async {
    state = const AsyncLoading();
    try {
      final request = RegisterRequest(
          username: username, email: email, password: password, confirmPassword: password);
      final authResponse = await _authRepository.register(request);
      if (authResponse.access != null) {
        await _secureStorage.saveAccessToken(authResponse.access!);
      }
      if (authResponse.refresh != null) {
        await _secureStorage.saveRefreshToken(authResponse.refresh!);
      }
      final user = await _authRepository.getMe();
      state = AsyncData(AuthState(user: user, isAuthenticated: true));
    } on AppException catch (e) {
      state = AsyncData(AuthState(error: e.message));
    } catch (e) {
      state = AsyncData(AuthState(error: e.toString()));
    }
  }

  Future<void> logout() async {
    try {
      await _authRepository.logout();
    } catch (_) {}
    await _secureStorage.clearTokens();
    state = const AsyncData(AuthState());
  }

  void updateUser(User user) {
    final current = state.valueOrNull;
    if (current != null) {
      state = AsyncData(current.copyWith(user: user));
    }
  }

  void clearError() {
    final current = state.valueOrNull;
    if (current != null) {
      state = AsyncData(current.copyWith(clearError: true));
    }
  }
}
