/// Simple Success/Failure Result monad for clean error propagation
sealed class Result<T> {
  const Result();

  bool get isSuccess => this is Success<T>;
  bool get isFailure => this is Failure<T>;

  T? get dataOrNull => switch (this) {
    Success(data: final d) => d,
    Failure() => null,
  };

  String? get errorOrNull => switch (this) {
    Success() => null,
    Failure(message: final m) => m,
  };
}

class Success<T> extends Result<T> {
  final T data;
  const Success(this.data);
}

class Failure<T> extends Result<T> {
  final String message;
  final dynamic cause;
  const Failure(this.message, [this.cause]);
}
