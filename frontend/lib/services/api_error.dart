import 'package:dio/dio.dart';

sealed class ApiError {
  const ApiError();

  String get message;

  factory ApiError.from(Object error) {
    if (error is! DioException) return const UnknownError();

    switch (error.type) {
      case DioExceptionType.connectionError:
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const NetworkError();
      case DioExceptionType.badResponse:
        final statusCode = error.response?.statusCode;
        if (statusCode == 401) return const InvalidCredentials();
        if (statusCode == 409) {
          final data = error.response?.data;
          final detail = data is Map ? data['detail'] as String? : null;
          if (detail == 'already_invited') return const AlreadyInvited();
        }
        if (statusCode == 400 || statusCode == 422) {
          final data = error.response?.data;
          final detail = data is Map ? data['detail'] as String? : null;
          return ValidationError(
            detail ?? 'Invalid request. Please check your input.',
          );
        }
        if (statusCode != null && statusCode >= 500) {
          return const ServerError();
        }
        return const UnknownError();
      default:
        return const UnknownError();
    }
  }
}

class AlreadyInvited extends ApiError {
  const AlreadyInvited();

  @override
  String get message => 'already_invited';
}

class InvalidCredentials extends ApiError {
  const InvalidCredentials();

  @override
  String get message => 'wrong number or password';
}

class ValidationError extends ApiError {
  const ValidationError(this.detail);

  final String detail;

  @override
  String get message => detail;
}

class NetworkError extends ApiError {
  const NetworkError();

  @override
  String get message =>
      'Could not connect to server. Check your internet connection.';
}

class ServerError extends ApiError {
  const ServerError();

  @override
  String get message => 'Server error — please try again later.';
}

class UnknownError extends ApiError {
  const UnknownError();

  @override
  String get message => 'Something went wrong. Please try again.';
}
