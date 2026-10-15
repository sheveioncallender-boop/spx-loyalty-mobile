import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(() async {
    final loader = FontLoader('Manrope');
    for (final weight in [400, 500, 600, 700, 800]) {
      loader.addFont(rootBundle.load('assets/fonts/manrope-$weight.ttf'));
    }
    await loader.load();
  });
  for (final spec in [
    (name: 'iPhone X size', size: const Size(375, 812), top: 44.0),
    (name: 'newer compact size', size: const Size(393, 852), top: 59.0),
    (name: 'newer large size', size: const Size(430, 932), top: 59.0),
  ]) {
    testWidgets(
      '${spec.name}: navigation, card flip and introduction fit safe areas',
      (tester) async {
        tester.view.physicalSize = spec.size;
        tester.view.devicePixelRatio = 1;
        tester.view.padding = FakeViewPadding(top: spec.top, bottom: 34);
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        addTearDown(tester.view.resetPadding);
        await tester.pumpWidget(JennysApp(initialApi: DemoApi()));
        await tester.pumpAndSettle();
        expect(find.text('Home').last.hitTestable(), findsOneWidget);
        await tester.tap(find.text('My card').last);
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.text('Scan at Jenny’s'));
        await tester.tap(find.text('Scan at Jenny’s'));
        await tester.pumpAndSettle();
        expect(find.byKey(const ValueKey('membership-barcode')), findsWidgets);
        expect(tester.takeException(), isNull);
        await tester.tap(find.text('You').last);
        await tester.pumpAndSettle();
        await tester.ensureVisible(find.text('Discover the app'));
        await tester.tap(find.text('Discover the app'));
        await tester.pumpAndSettle();
        for (var page = 0; page < 4; page++) {
          final action = find.byKey(const Key('intro-next'));
          expect(action.hitTestable(), findsOneWidget);
          expect(
            tester.getBottomRight(action).dy,
            lessThanOrEqualTo(spec.size.height - 34),
          );
          expect(tester.takeException(), isNull);
          if (page < 3) {
            await tester.tap(action);
            await tester.pumpAndSettle();
          }
        }
        await tester.tap(find.text('Back to Jenny’s'));
        await tester.pumpAndSettle();
        expect(find.byType(AppIntroduction), findsNothing);
        await tester.pumpWidget(const SizedBox());
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      },
      variant: TargetPlatformVariant.only(TargetPlatform.iOS),
    );
  }
}
