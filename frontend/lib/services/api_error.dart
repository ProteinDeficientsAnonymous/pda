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
        return _fromResponse(error.response);
      default:
        return const UnknownError();
    }
  }

  static ApiError _fromResponse(Response<dynamic>? response) {
    final statusCode = response?.statusCode;
    final data = response?.data;
    final detail = data is Map ? data['detail'] as String? : null;

    return switch (statusCode) {
      401 => const InvalidCredentials(),
      403 => ForbiddenError(detail ?? "you don't have access"),
      404 => const NotFoundError(),
      409 when detail == 'already_invited' => const AlreadyInvited(),
      429 => RateLimited(
        detail ?? "you're doing that too fast — try again in a bit",
      ),
      400 || 422 => ValidationError(
        detail ?? 'Invalid request. Please check your input.',
      ),
      _ when statusCode != null && statusCode >= 500 => const ServerError(),
      _ => const UnknownError(),
    };
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

class RateLimited extends ApiError {
  const RateLimited(this.detail);

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

class ForbiddenError extends ApiError {
  const ForbiddenError(this.detail);

  final String detail;

  @override
  String get message => detail;
}

class NotFoundError extends ApiError {
  const NotFoundError();

  @override
  String get message => 'not found';
}

class UnknownError extends ApiError {
  const UnknownError();

  @override
  String get message => 'Something went wrong. Please try again.';
}
