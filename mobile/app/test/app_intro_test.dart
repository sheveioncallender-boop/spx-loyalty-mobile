import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

class MemoryIntroStore extends IntroStore {
  bool seen;
  MemoryIntroStore({this.seen = false});
  @override
  Future<bool> hasSeen() async => seen;
  @override
  Future<void> complete() async {
    seen = true;
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
  });

  Future<void> open(
    WidgetTester tester,
    Widget child, {
    Size size = const Size(390, 844),
    double scale = 1,
    bool reduced = false,
  }) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      Builder(
        builder: (context) => MaterialApp(
          theme: (const JennysApp().build(context) as MaterialApp).theme,
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(context).copyWith(
              textScaler: TextScaler.linear(scale),
              disableAnimations: reduced,
            ),
            child: child!,
          ),
          home: child,
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('First use can be skipped and stays skipped on reopening', (
    tester,
  ) async {
    final store = MemoryIntroStore();
    await open(
      tester,
      Entry(introStore: store, restoreAccount: () async => null),
    );
    expect(find.byType(AppIntroduction), findsOneWidget);
    await tester.tap(find.text('Skip'));
    await tester.pumpAndSettle();
    expect(store.seen, isTrue);
    expect(find.byType(Welcome), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
    await open(
      tester,
      Entry(introStore: store, restoreAccount: () async => null),
    );
    expect(find.byType(AppIntroduction), findsNothing);
    expect(find.byType(Welcome), findsOneWidget);
  });

  testWidgets('Restored member skips introduction and can replay from You', (
    tester,
  ) async {
    final store = MemoryIntroStore();
    final api = DemoApi();
    await open(
      tester,
      Entry(introStore: store, restoreAccount: () async => api),
    );
    expect(find.byType(AppShell), findsOneWidget);
    expect(find.byType(AppIntroduction), findsNothing);
    expect(store.seen, isTrue);
    await tester.tap(find.text('You').last);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Discover the app'));
    await tester.tap(find.text('Discover the app'));
    await tester.pumpAndSettle();
    expect(
      tester.widget<AppIntroduction>(find.byType(AppIntroduction)).replay,
      isTrue,
    );
    expect(find.text('Already a member? Sign in'), findsNothing);
    for (var i = 0; i < 3; i++) {
      await tester.tap(find.byKey(const Key('intro-next')));
      await tester.pumpAndSettle();
    }
    await tester.tap(find.text('Back to Jenny’s'));
    await tester.pumpAndSettle();
    expect(find.byType(AppIntroduction), findsNothing);
    expect(tester.widget<AppShell>(find.byType(AppShell)).api, same(api));
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
  });

  testWidgets('Swipe and Next introduce all four features then offer signup', (
    tester,
  ) async {
    IntroAction? result;
    await open(
      tester,
      AppIntroduction(onFinish: (value) async => result = value),
    );
    expect(find.text('A little Jenny’s.\nAlways with you.'), findsOneWidget);
    await tester.drag(
      find.byKey(const Key('intro-pages')),
      const Offset(-390, 0),
    );
    await tester.pumpAndSettle();
    expect(find.text('Every visit.\nA little more.'), findsOneWidget);
    await tester.tap(find.byKey(const Key('intro-next')));
    await tester.pumpAndSettle();
    expect(find.text('Order here.\nEnjoy it there.'), findsOneWidget);
    await tester.tap(find.byKey(const Key('intro-next')));
    await tester.pumpAndSettle();
    expect(find.text('Your visits.\nAll together.'), findsOneWidget);
    await tester.tap(find.text('Create my account'));
    await tester.pumpAndSettle();
    expect(result, IntroAction.signup);
  });

  testWidgets('Sign in remains available without completing the tour', (
    tester,
  ) async {
    IntroAction? result;
    await open(
      tester,
      AppIntroduction(onFinish: (value) async => result = value),
    );
    await tester.tap(find.text('Already a member? Sign in'));
    await tester.pumpAndSettle();
    expect(result, IntroAction.signin);
  });

  testWidgets(
    'Small display supports large text and reduced motion on every page',
    (tester) async {
      await open(
        tester,
        AppIntroduction(onFinish: (_) async {}),
        size: const Size(320, 640),
        scale: 2,
        reduced: true,
      );
      for (var i = 0; i < 4; i++) {
        expect(tester.takeException(), isNull);
        expect(
          find.byKey(const Key('intro-next')).hitTestable(),
          findsOneWidget,
        );
        if (i < 3) {
          await tester.tap(find.byKey(const Key('intro-next')));
          await tester.pump();
        }
      }
      expect(find.text('Create my account'), findsOneWidget);
      await tester.ensureVisible(find.text('Your visits.\nAll together.'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    },
  );

  test(
    'Preference channel persists the introduction flag independently',
    () async {
      var saved = false;
      final messenger =
          TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;
      messenger.setMockMethodCallHandler(IntroStore.channel, (call) async {
        if (call.method == 'hasSeenIntroduction') return saved;
        if (call.method == 'completeIntroduction') {
          saved = true;
          return null;
        }
        throw MissingPluginException();
      });
      addTearDown(
        () => messenger.setMockMethodCallHandler(IntroStore.channel, null),
      );
      expect(await const IntroStore().hasSeen(), isFalse);
      await const IntroStore().complete();
      expect(await const IntroStore().hasSeen(), isTrue);
    },
  );
}
