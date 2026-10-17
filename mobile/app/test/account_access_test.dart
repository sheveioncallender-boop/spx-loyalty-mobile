import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

class AccountTestApi extends OdooApi {
  AccountTestApi() : super(Uri.parse('https://jennys.example'), 'test');
  Json? registered;
  String? recovery;
  bool failSignup = false;
  bool accountExists = false;
  bool verified = false;
  String? loginEmail, loginPassword, handoff;
  @override
  Future<bool> signupVerified(String receipt) async => verified;
  @override
  Future<void> login(String email, String password) async {
    loginEmail = email;
    loginPassword = password;
  }

  @override
  Future<void> finishSignup(String code) async {
    handoff = code;
  }

  @override
  Future<Json> accountConfig() async => {
    'enabled': true,
    'terms': 'Sample terms for testing.',
    'privacy': 'Sample privacy for testing.',
    'policy_version': 'test-1',
  };
  @override
  Future<String> register(Json details) async {
    if (accountExists) {
      throw AppError('Account already associated.', code: 'account_exists');
    }
    if (failSignup) throw AppError('Connection interrupted. Try again.');
    registered = Map.of(details);
    return 'sample-receipt-that-is-not-a-real-token';
  }

  @override
  Future<void> forgotPassword(String email) async {
    recovery = email;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final loader = FontLoader('Manrope');
    for (final weight in [400, 500, 600, 700, 800]) {
      loader.addFont(rootBundle.load('assets/fonts/manrope-$weight.ttf'));
    }
    await loader.load();
    final icons = FontLoader('MaterialIcons');
    icons.addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
  });
  Future<void> open(
    WidgetTester tester,
    AccountTestApi api,
    String page, {
    ValueChanged<OdooApi>? onAuthenticated,
  }) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      Builder(
        builder: (context) => MaterialApp(
          theme: (const JennysApp().build(context) as MaterialApp).theme,
          home: RepaintBoundary(
            key: const Key('capture'),
            child: AccountAccess(
              initialPage: page,
              accountApi: api,
              onAuthenticated: onAuthenticated,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.runAsync(() async {
      await precacheImage(
        const AssetImage('assets/images/jennys-logo.jpg'),
        tester.element(find.byType(AccountAccess)),
      );
    });
    await tester.pumpAndSettle();
  }

  Future<void> tap(WidgetTester tester, Finder finder) async {
    await tester.ensureVisible(finder);
    await tester.pumpAndSettle();
    await tester.tap(finder);
    await tester.pumpAndSettle();
  }

  testWidgets(
    'Signup sends required fields, preserves opt-outs, then waits for verification',
    (tester) async {
      final api = AccountTestApi();
      OdooApi? authenticated;
      await open(
        tester,
        api,
        'signup',
        onAuthenticated: (value) => authenticated = value,
      );
      final inputs = find.byType(TextFormField);
      await tester.enterText(inputs.at(0), 'Alex');
      await tester.enterText(inputs.at(1), 'Joseph');
      await tester.enterText(inputs.at(2), '5550123');
      await tester.enterText(inputs.at(3), 'alex@example.com');
      await tester.enterText(inputs.at(4), 'A-long-test-password!');
      await tap(tester, find.text('Year'));
      await tap(tester, find.text('2026').last);
      await tap(tester, find.text('Month'));
      await tap(tester, find.text('Jan').last);
      await tap(tester, find.text('Day'));
      await tap(tester, find.text('1').last);
      await tap(tester, find.byType(CheckboxListTile).last);
      await tap(tester, find.text('Create account'));
      expect(api.registered?['email'], 'alex@example.com');
      expect(api.registered?['birthday'], '2026-01-01');
      expect(api.registered?['marketing_email'], false);
      expect(api.registered?['marketing_sms'], false);
      expect(api.registered?['policy_version'], 'test-1');
      expect(find.text('Check your inbox.'), findsOneWidget);
      expect(find.text('Your Jenny’s\nis waiting.'), findsNothing);
      await tap(tester, find.text('I’ve verified my email'));
      expect(authenticated, isNull);
      api.verified = true;
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pumpAndSettle();
      expect(authenticated, same(api));
      expect(api.loginEmail, 'alex@example.com');
      expect(api.loginPassword, 'A-long-test-password!');
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets(
    'Existing email offers sign-in and recovery instead of verification',
    (tester) async {
      final api = AccountTestApi()..accountExists = true;
      await open(tester, api, 'signup');
      final inputs = find.byType(TextFormField);
      for (final entry in {
        0: 'Alex',
        1: 'Joseph',
        2: '5550123',
        3: 'Member@Example.com',
        4: 'A-long-test-password!',
      }.entries) {
        await tester.enterText(inputs.at(entry.key), entry.value);
      }
      await tap(tester, find.text('Year'));
      await tap(tester, find.text('2026').last);
      await tap(tester, find.text('Month'));
      await tap(tester, find.text('Jan').last);
      await tap(tester, find.text('Day'));
      await tap(tester, find.text('1').last);
      await tap(tester, find.byType(CheckboxListTile).last);
      await tap(tester, find.text('Create account'));
      expect(find.text('Check your inbox.'), findsNothing);
      expect(find.text('You already have\nan account.'), findsOneWidget);
      expect(find.text('Sign in'), findsOneWidget);
      await tap(tester, find.text('Forgot password?'));
      expect(find.text('Send reset link'), findsOneWidget);
      expect(
        (tester.widget<TextFormField>(
          find.byType(TextFormField),
        )).controller!.text,
        'Member@Example.com',
      );
      await tap(tester, find.text('Send reset link'));
      expect(api.recovery, 'Member@Example.com');
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('Expired reset app link opens forgot password directly', (
    tester,
  ) async {
    final api = AccountTestApi();
    final link = accountLink('jennys://account/forgot-password');
    expect(link, isNotNull);
    await tester.pumpWidget(
      MaterialApp(
        home: AccountReturn(link: link!, accountApi: api),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Send reset link'), findsOneWidget);
    expect(
      find.text('Enter your email to request a new password reset link.'),
      findsOneWidget,
    );
  });

  testWidgets(
    'Verified deep link exchanges its code without asking for password',
    (tester) async {
      final api = AccountTestApi();
      OdooApi? completed;
      final code = 'a' * 43;
      await tester.pumpWidget(
        MaterialApp(
          home: AccountReturn(
            link: Uri.parse('jennys://account/verified?code=$code'),
            accountApi: api,
            onAuthenticated: (value) => completed = value,
          ),
        ),
      );
      await tester.pump();
      expect(api.handoff, code);
      expect(completed, same(api));
      expect(find.byType(TextFormField), findsNothing);
      await tester.pumpWidget(const SizedBox());
    },
  );
  testWidgets('Password updated link returns to sign in with confirmation', (
    tester,
  ) async {
    final api = AccountTestApi();
    await tester.pumpWidget(
      MaterialApp(
        home: AccountReturn(
          link: Uri.parse('jennys://account/password-updated'),
          accountApi: api,
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('Your password is updated. Sign in with your new password.'),
      findsOneWidget,
    );
    expect(find.byType(TextFormField), findsNWidgets(2));
    expect(api.handoff, isNull);
  });
  test('Only approved account callback routes are accepted', () {
    expect(accountLink('jennys://account/verified?code=abc'), isNotNull);
    expect(accountLink('jennys://account/password-updated'), isNotNull);
    for (final value in [
      'https://evil.example/verified',
      'jennys://evil/verified',
      '//evil/verified',
      'jennys://account/other',
      'jennys://account/verified#token',
    ]) {
      expect(accountLink(value), isNull);
    }
  });
  testWidgets('Recovery submits email and shows neutral inbox confirmation', (
    tester,
  ) async {
    final api = AccountTestApi();
    await open(tester, api, 'login');
    await tap(tester, find.text('Forgot password?'));
    await tester.enterText(find.byType(TextFormField), 'alex@example.com');
    await tap(tester, find.text('Send reset link'));
    expect(api.recovery, 'alex@example.com');
    expect(find.text('Check your inbox.'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Approved account screens render on small phones', (
    tester,
  ) async {
    final api = AccountTestApi();
    await open(tester, api, 'signup');
    expect(find.text('Your Jenny’s\nstarts here.'), findsOneWidget);
    final directory = Platform.environment['JENNYS_ACCOUNT_CAPTURE_DIR'];
    if (directory != null) {
      await tester.runAsync(() async {
        final boundary = tester.renderObject<RenderRepaintBoundary>(
          find.byKey(const Key('capture')),
        );
        final image = await boundary.toImage(pixelRatio: 2);
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        await File(
          '$directory/Jennys-Signup.png',
        ).writeAsBytes(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }
    expect(tester.takeException(), isNull);
  });
}
