import 'dart:convert';
import 'package:barcode_widget/barcode_widget.dart';
import 'package:jennys_rewards/loyalty_scan.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

class VisualBinding extends AutomatedTestWidgetsFlutterBinding {
  @override
  bool get disableShadows => false;
}

class CountingApi extends DemoApi {
  int reads = 0;
  @override
  Future<Json> bootstrap() async {
    reads++;
    return super.bootstrap();
  }
}

void main() {
  VisualBinding();
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
  Future<void> load(
    WidgetTester tester, {
    Size size = const Size(393, 852),
  }) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(JennysApp(initialApi: DemoApi()));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    // Decode the assets before visual comparison, including isolated runs.
    // pumpAndSettle alone does not wait for asynchronous image decoding.
    await tester.runAsync(() async {
      for (final name in [
        'jennys-logo.jpg',
        'dish-feature.jpg',
        'jennys-buffet.jpg',
        'cocktail-lounge.jpg',
      ]) {
        await precacheImage(
          AssetImage('assets/images/$name'),
          tester.element(find.byType(MaterialApp)),
        );
      }
    });
    await tester.pumpAndSettle();
  }

  testWidgets(
    'Small Android screen can navigate, add and remove an item without overflow',
    (tester) async {
      await load(tester, size: const Size(360, 800));
      expect(find.text('Make today\na Jenny’s day.'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('Order').last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Jenny’s Special Noodles').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Add to order · TT\$98.00'));
      await tester.pumpAndSettle();
      await tester.drag(find.byType(ListView).first, const Offset(0, -700));
      await tester.pumpAndSettle();
      await tester.tap(find.text('View order · TT\$98.00'));
      await tester.pumpAndSettle();
      expect(find.text('Total'), findsOneWidget);
      await tester.tap(find.byTooltip('Decrease Jenny’s Special Noodles'));
      await tester.pumpAndSettle();
      expect(find.text('Room for a favourite.'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  testWidgets('Card is a normal membership card and all tabs fit', (
    tester,
  ) async {
    await load(tester);
    for (final label in ['Rewards', 'My card', 'You', 'Home']) {
      await tester.tap(find.text(label).last);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: '$label layout overflow');
      if (label == 'My card') {
        expect(find.text('JB 0019 8726').hitTestable(), findsOneWidget);
        expect(find.text('Copy card number'), findsOneWidget);
      }
    }
  });
  testWidgets('Native screen visual snapshots', (tester) async {
    Future<void> decodedImages() async {
      final elements = find.byType(Image).evaluate().toList();
      await tester.runAsync(() async {
        for (final element in elements) {
          await precacheImage((element.widget as Image).image, element);
        }
      });
      await tester.pumpAndSettle();
    }

    await load(tester);
    await decodedImages();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/home.png'),
    );
    await tester.tap(find.text('My card').last);
    await tester.pumpAndSettle();
    await decodedImages();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/card.png'),
    );
    await tester.tap(find.text('Order').last);
    await tester.pumpAndSettle();
    await decodedImages();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/menu.png'),
    );
    await tester.tap(find.text('Rewards').last);
    await tester.pumpAndSettle();
    await decodedImages();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/rewards.png'),
    );
    await tester.tap(find.text('You').last);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Leave preview'), 400);
    await tester.tap(find.text('Leave preview'));
    await tester.pumpAndSettle();
    expect(find.text('Sign in to Jenny’s'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await decodedImages();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/welcome.png'),
    );
  });
  testWidgets(
    'Scan opens exact card, enlarges and refreshes without awarding points',
    (tester) async {
      final api = CountingApi();
      tester.view.physicalSize = const Size(360, 800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(JennysApp(initialApi: api));
      await tester.pumpAndSettle();
      await tester.pump(const Duration(seconds: 2));
      await tester.pumpAndSettle();
      await tester.tap(find.text('My card').last);
      await tester.pumpAndSettle();
      final before = api.reads;
      await tester.tap(find.text('Scan at Jenny’s'));
      await tester.pumpAndSettle();
      expect(
        tester.widget<BarcodeWidget>(find.byType(BarcodeWidget)).data,
        utf8.encode('JB 0019 8726'),
      );
      expect(find.text('PREVIEW CARD · NOT VALID AT THE TILL'), findsOneWidget);
      expect(api.reads, before);
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/card_back.png'),
      );
      await tester.tap(find.text('Enlarge barcode'));
      await tester.pumpAndSettle();
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/scan.png'),
      );
      await tester.tap(find.text('Enlarge barcode'));
      await tester.pumpAndSettle();
      expect(
        tester.widget<BarcodeWidget>(find.byType(BarcodeWidget)).data,
        utf8.encode('JB 0019 8726'),
      );
      expect(tester.takeException(), isNull);
      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/scan_enlarged.png'),
      );
      await tester.tap(find.byTooltip('Back to card'));
      await tester.pumpAndSettle();
      await tester.tap(find.byTooltip('Close scan card'));
      await tester.pumpAndSettle();
      await tester.pump(const Duration(seconds: 2));
      await tester.pumpAndSettle();
      expect(api.reads, before + 1);
      await tester.tap(find.text('Show card front'));
      await tester.pumpAndSettle();
      await tester.pump(const Duration(seconds: 2));
      await tester.pumpAndSettle();
      expect(api.reads, before + 2);
      expect(find.text('850').hitTestable(), findsWidgets);
    },
  );
  testWidgets(
    'Native card payload retains punctuation and case in portrait and landscape',
    (tester) async {
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      for (final size in [const Size(360, 800), const Size(800, 360)]) {
        tester.view.physicalSize = size;
        await tester.pumpWidget(
          MaterialApp(
            home: LoyaltyScanPage(
              code: '044a-b123-C456',
              program: 'Jenny’s Rewards',
              customer: 'Test Customer',
              isDemo: false,
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(
          tester.widget<BarcodeWidget>(find.byType(BarcodeWidget)).data,
          utf8.encode('044a-b123-C456'),
        );
        expect(find.text('PREVIEW CARD · NOT VALID AT THE TILL'), findsNothing);
        expect(tester.takeException(), isNull);
        if (size.width == 360) {
          await expectLater(
            find.byType(MaterialApp),
            matchesGoldenFile('goldens/scan_native.png'),
          );
        }
      }
    },
  );
  testWidgets(
    'Unencodable card offers manual entry instead of changing its code',
    (tester) async {
      for (final code in ['', 'Jenny’s–特殊']) {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(body: LoyaltyBarcode(code: code)),
          ),
        );
        expect(find.byType(BarcodeWidget), findsNothing);
        expect(find.textContaining('enter your card number'), findsOneWidget);
        expect(tester.takeException(), isNull);
      }
    },
  );
  testWidgets('Customer sign-in only asks for email and password', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await load(tester, size: const Size(360, 800));
    await tester.tap(find.text('You').last);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Leave preview'), 400);
    await tester.tap(find.text('Leave preview'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sign in to Jenny’s'));
    await tester.pumpAndSettle();
    expect(find.byType(TextField), findsNWidgets(2));
    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);
    for (final text in tester.widgetList<Text>(find.byType(Text))) {
      expect(
        text.data ?? '',
        isNot(
          matches(
            RegExp(
              r'odoo|database|connector|portal|server',
              caseSensitive: false,
            ),
          ),
        ),
      );
    }
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/sign_in.png'),
    );
    await tester.enterText(
      find.byType(TextField).first,
      'customer@example.com',
    );
    await tester.enterText(find.byType(TextField).last, 'test-only');
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('Sign-in is not available in this preview'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });
  test(
    'Customer errors hide connection details while keeping useful reward feedback',
    () {
      for (final value in [
        'Odoo database unavailable',
        'Portal connector missing',
        'https://private-server.invalid',
        'loyalty.card failed',
      ]) {
        expect(customerMessage(value), isNot(contains(value)));
      }
      expect(
        customerMessage('Not enough points for this reward.'),
        'Not enough points for this reward.',
      );
      expect(
        customerError(StateError('private configuration')),
        'Something went wrong. Please try again.',
      );
    },
  );
  test('HTTPS origins reject credentials, page paths and insecure schemes', () {
    for (final value in [
      'http://odoo.example',
      'https://user:pass@odoo.example',
      'https://odoo.example/shop',
      'https://odoo.example?x=y',
      'file:///etc/passwd',
    ]) {
      expect(() => OdooApi.validateOrigin(value), throwsA(isA<AppError>()));
    }
    final api = OdooApi(OdooApi.validateOrigin('https://odoo.example'), 'test');
    expect(
      () => api.page('https://other.example/shop'),
      throwsA(isA<AppError>()),
    );
    expect(() => api.page('//other.example/shop'), throwsA(isA<AppError>()));
  });
  test(
    'RPC does not follow redirects or send passwords outside login',
    () async {
      final client = MockClient((request) async {
        expect(request.followRedirects, isFalse);
        expect(request.url.host, 'odoo.example');
        final body = jsonDecode(request.body) as Json;
        expect(body['params'], isEmpty);
        return http.Response(
          '',
          302,
          headers: {'location': 'https://other.example/'},
        );
      });
      final api = OdooApi(
        Uri.parse('https://odoo.example'),
        'test',
        client: client,
      );
      await expectLater(api.bootstrap(), throwsA(isA<AppError>()));
    },
  );
  test('A mutation is not retried after a network failure', () async {
    var calls = 0;
    final api = OdooApi(
      Uri.parse('https://odoo.example'),
      'test',
      client: MockClient((request) async {
        calls++;
        throw http.ClientException('offline');
      }),
    );
    await expectLater(api.add({'product_id': 1}), throwsA(isA<AppError>()));
    expect(calls, 1);
  });
}
