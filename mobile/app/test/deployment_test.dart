import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:jennys_rewards/api.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  const storage = FlutterSecureStorage();
  const sessionKey = 'jennys.odoo.session.v1';
  const pendingKey = 'jennys.signup.pending.v1';
  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  String record(String origin, String database) =>
      jsonEncode({'origin': origin, 'database': database, 'session': 's' * 43});

  test(
    'new deployment clears old sign-in, signup receipt and website session',
    () async {
      FlutterSecureStorage.setMockInitialValues({
        sessionKey: record('https://old.example', 'old-db'),
        pendingKey: record('https://old.example', 'old-db'),
      });
      bool cleared = false;
      await OdooApi.prepareDeployment(
        'https://new.example',
        'new-db',
        clearWebsiteSession: () async {
          cleared = true;
        },
      );
      expect(cleared, isTrue);
      expect(await storage.read(key: sessionKey), isNull);
      expect(await storage.read(key: pendingKey), isNull);
    },
  );

  test(
    'ordinary upgrade keeps a matching account and pending signup',
    () async {
      final saved = record('https://same.example', 'same-db');
      FlutterSecureStorage.setMockInitialValues({
        sessionKey: saved,
        pendingKey: saved,
      });
      await OdooApi.prepareDeployment(
        'https://same.example/',
        'same-db',
        clearWebsiteSession: () async {
          fail('Matching deployment must keep its session');
        },
      );
      expect(await storage.read(key: sessionKey), saved);
      expect(await storage.read(key: pendingKey), saved);
    },
  );

  test(
    'database change on the same host resets the previous environment',
    () async {
      FlutterSecureStorage.setMockInitialValues({
        sessionKey: record('https://same.example', 'old-db'),
      });
      bool cleared = false;
      await OdooApi.prepareDeployment(
        'https://same.example',
        'new-db',
        clearWebsiteSession: () async {
          cleared = true;
        },
      );
      expect(cleared, isTrue);
      expect(await storage.read(key: sessionKey), isNull);
    },
  );

  test(
    'failed native cookie clearing does not mark the new deployment ready',
    () async {
      final saved = record('https://old.example', 'old-db');
      FlutterSecureStorage.setMockInitialValues({sessionKey: saved});
      await expectLater(
        OdooApi.prepareDeployment(
          'https://new.example',
          'new-db',
          clearWebsiteSession: () async {
            throw StateError('Unavailable');
          },
        ),
        throwsStateError,
      );
      expect(await storage.read(key: 'jennys.deployment.v1'), isNull);
      expect(await storage.read(key: sessionKey), saved);
    },
  );
}
