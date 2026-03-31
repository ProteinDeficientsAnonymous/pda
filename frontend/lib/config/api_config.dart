const String apiBaseUrl = String.fromEnvironment(
  'API_URL',
  defaultValue: 'http://localhost:8000',
);

const bool enableFeedback = bool.fromEnvironment('ENABLE_FEEDBACK');

const String gitSha = String.fromEnvironment('GIT_SHA', defaultValue: 'dev');
