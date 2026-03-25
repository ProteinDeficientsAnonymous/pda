import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/services/api_error.dart';

void main() {
  RequestOptions options() => RequestOptions(path: '/test');

  group('ApiError.from', () {
    test('returns invalidCredentials for 401 DioException', () {
      final error = DioException(
        requestOptions: options(),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: options(),
          statusCode: 401,
          data: {'detail': 'Invalid credentials'},
        ),
      );

      final result = ApiError.from(error);
      expect(result, isA<InvalidCredentials>());
    });

    test('returns validationError with detail for 400 DioException', () {
      final error = DioException(
        requestOptions: options(),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: options(),
          statusCode: 400,
          data: {'detail': 'Name, email, and why_join are required.'},
        ),
      );

      final result = ApiError.from(error);
      expect(result, isA<ValidationError>());
      expect(
        (result as ValidationError).detail,
        'Name, email, and why_join are required.',
      );
    });

    test('returns validationError with detail for 422 DioException', () {
      final error = DioException(
        requestOptions: options(),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: options(),
          statusCode: 422,
          data: {'detail': 'Validation failed'},
        ),
      );

      final result = ApiError.from(error);
      expect(result, isA<ValidationError>());
      expect((result as ValidationError).detail, 'Validation failed');
    });

    test('returns serverError for 500 DioException', () {
      final error = DioException(
        requestOptions: options(),
        type: DioExceptionType.badResponse,
        response: Response(requestOptions: options(), statusCode: 500),
      );

      final result = ApiError.from(error);
      expect(result, isA<ServerError>());
    });

    test('returns networkError for connectionError DioException', () {
      final error = DioException(
        requestOptions: options(),
        type: DioExceptionType.connectionError,
      );

      final result = ApiError.from(error);
      expect(result, isA<NetworkError>());
    });

    test('returns networkError for connectionTimeout DioException', () {
      final error = DioException(
        requestOptions: options(),
        type: DioExceptionType.connectionTimeout,
      );

      final result = ApiError.from(error);
      expect(result, isA<NetworkError>());
    });

    test('returns unknownError for non-DioException', () {
      final error = Exception('something unexpected');

      final result = ApiError.from(error);
      expect(result, isA<UnknownError>());
    });

    test('returns validationError with fallback when detail is missing', () {
      final error = DioException(
        requestOptions: options(),
        type: DioExceptionType.badResponse,
        response: Response(
          requestOptions: options(),
          statusCode: 400,
          data: 'not a map',
        ),
      );

      final result = ApiError.from(error);
      expect(result, isA<ValidationError>());
      expect(
        (result as ValidationError).detail,
        'Invalid request. Please check your input.',
      );
    });
  });

  group('ApiError.message', () {
    test('invalidCredentials has correct message', () {
      expect(const InvalidCredentials().message, 'Invalid email or password.');
    });

    test('networkError has correct message', () {
      expect(
        const NetworkError().message,
        'Could not connect to server. Check your internet connection.',
      );
    });

    test('serverError has correct message', () {
      expect(
        const ServerError().message,
        'Server error — please try again later.',
      );
    });

    test('unknownError has correct message', () {
      expect(
        const UnknownError().message,
        'Something went wrong. Please try again.',
      );
    });

    test('validationError message is the detail', () {
      expect(
        const ValidationError('Name is required.').message,
        'Name is required.',
      );
    });
  });
}
