import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jennys_rewards/api.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const pendingKey = 'jennys.signup.pending.v1';
  const sessionKey = 'jennys.odoo.session.v1';
  const storage = FlutterSecureStorage();
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  test(
    'Duplicate signup reports an account conflict without saving a receipt',
    () async {
      final api = OdooApi(
        Uri.parse('https://jennys.example'),
        'test',
        client: MockClient(
          (req) async => http.Response(
            jsonEncode({
              'error': {
                'data': {
                  'name':
                      'odoo.addons.spx_loyalty_mobile.models.onboarding.AccountExistsUserError',
                  'message':
                      'An account is already associated with this email address. Sign in or use Forgot password.',
                },
              },
            }),
            200,
          ),
        ),
      );
      await expectLater(
        api.register({'email': 'Member@Example.com'}),
        throwsA(
          isA<AppError>().having((e) => e.code, 'code', 'account_exists'),
        ),
      );
      expect(await storage.read(key: pendingKey), isNull);
      expect(await storage.read(key: sessionKey), isNull);
    },
  );

  test(
    'Sign in identifies the native account by email and checks its scope',
    () async {
      final paths = <String>[];
      final api = OdooApi(
        Uri.parse('https://jennys.example'),
        'test',
        client: MockClient((req) async {
          paths.add(req.url.path);
          if (req.url.path.endsWith('/signin')) {
            expect((jsonDecode(req.body) as Json)['params'], {
              'email': 'Member@Example.com',
              'password': 'My-password-123!',
            });
            return http.Response(
              jsonEncode({
                'result': {'uid': 42},
              }),
              200,
              headers: {'set-cookie': 'session_id=${'s' * 43}'},
            );
          }
          return http.Response(jsonEncode({'result': {}}), 200);
        }),
      );
      await api.login(' Member@Example.com ', 'My-password-123!');
      expect(paths, [
        '/spx/mobile/v1/account/signin',
        '/spx/mobile/v1/bootstrap',
      ]);
      expect(await storage.read(key: sessionKey), contains('s' * 43));
    },
  );

  test(
    'Signup stores a device receipt, never its password, and exchanges a grant for a scoped session',
    () async {
      final requests = <String>[];
      final api = OdooApi(
        Uri.parse('https://jennys.example'),
        'test',
        client: MockClient((req) async {
          requests.add(req.url.path);
          final params = (jsonDecode(req.body) as Json)['params'] as Json;
          if (req.url.path.endsWith('/signup')) {
            return http.Response(
              jsonEncode({
                'result': {'receipt': 'r' * 43},
              }),
              200,
            );
          }
          if (req.url.path.endsWith('/exchange')) {
            expect(params, {'code': 'c' * 43, 'receipt': 'r' * 43});
            return http.Response(
              jsonEncode({
                'result': {'uid': 42},
              }),
              200,
              headers: {
                'set-cookie':
                    'session_id=${'s' * 43}; Path=/; Secure; HttpOnly',
              },
            );
          }
          expect(req.url.path, '/spx/mobile/v1/bootstrap');
          expect(req.headers['Cookie'], 'session_id=${'s' * 43}');
          return http.Response(
            jsonEncode({
              'result': {
                'partner': {'id': 42},
              },
            }),
            200,
          );
        }),
      );
      await api.register({
        'email': 'member@example.com',
        'password': 'Signup-password-123!',
      });
      final pending = (await storage.read(key: pendingKey))!;
      expect(pending, isNot(contains('password')));
      expect(await storage.read(key: sessionKey), isNull);
      await api.finishSignup('c' * 43);
      expect(await storage.read(key: pendingKey), isNull);
      expect(await storage.read(key: sessionKey), contains('s' * 43));
      expect(requests.length, 3);
    },
  );

  test('A receipt from another instance cannot be exchanged', () async {
    FlutterSecureStorage.setMockInitialValues({
      pendingKey: jsonEncode({
        'origin': 'https://different.example',
        'database': 'test',
        'receipt': 'r' * 43,
        'created': DateTime.now().toUtc().toIso8601String(),
      }),
    });
    final api = OdooApi(
      Uri.parse('https://jennys.example'),
      'test',
      client: MockClient((_) async {
        fail(
          'No request should leave this instance with another instance’s receipt.',
        );
      }),
    );
    await expectLater(api.finishSignup('c' * 43), throwsA(isA<AppError>()));
  });

  test(
    'No authenticated session is saved when the connector rejects bootstrap',
    () async {
      FlutterSecureStorage.setMockInitialValues({
        pendingKey: jsonEncode({
          'origin': 'https://jennys.example',
          'database': 'test',
          'receipt': 'r' * 43,
          'created': DateTime.now().toUtc().toIso8601String(),
        }),
      });
      final api = OdooApi(
        Uri.parse('https://jennys.example'),
        'test',
        client: MockClient((req) async {
          if (req.url.path.endsWith('/exchange')) {
            return http.Response(
              jsonEncode({
                'result': {'uid': 42},
              }),
              200,
              headers: {'set-cookie': 'session_id=${'s' * 43}'},
            );
          }
          return http.Response(
            jsonEncode({
              'error': {
                'data': {
                  'name': 'odoo.exceptions.AccessError',
                  'message': 'Account unavailable.',
                },
              },
            }),
            200,
          );
        }),
      );
      await expectLater(api.finishSignup('c' * 43), throwsA(isA<AppError>()));
      expect(await storage.read(key: sessionKey), isNull);
    },
  );
}
