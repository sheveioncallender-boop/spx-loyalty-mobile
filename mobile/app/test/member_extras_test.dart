import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

void main() {
  testWidgets(
    'Birthday and gift values stay separate from loyalty points on a small screen',
    (tester) async {
      tester.view.physicalSize = const Size(360, 800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        MaterialApp(home: MemberWalletPage(api: DemoApi())),
      );
      await tester.pumpAndSettle();
      expect(find.text('TTD 100.00'), findsOneWidget);
      expect(find.text('TTD 250.00'), findsOneWidget);
      expect(find.textContaining('points').hitTestable(), findsNothing);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets('Assigned cards appear with no claim-code step', (tester) async {
    await tester.pumpWidget(
      MaterialApp(home: MemberWalletPage(api: DemoApi())),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('appear here automatically'), findsOneWidget);
    expect(find.text('Add an existing gift card'), findsNothing);
    expect(find.text('Gift card code'), findsNothing);
    await tester.scrollUntilVisible(
      find.textContaining('After payment, it appears here.'),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      find.textContaining('After payment, it appears here.'),
      findsOneWidget,
    );
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Sending requires recipient details and an explicit review', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: SendGiftPage(
          api: DemoApi(),
          card: {
            'id': 1,
            'balance': 250.0,
            'currency': 'TTD',
            'state': 'active',
          },
        ),
      ),
    );
    await tester.scrollUntilVisible(
      find.text('Review & send'),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Review & send'));
    await tester.pumpAndSettle();
    expect(find.text('Send this gift?'), findsNothing);
    await tester.scrollUntilVisible(
      find.widgetWithText(TextFormField, 'Their name'),
      -250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Enter their name.'), findsOneWidget);
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Their name'),
      'Test Recipient',
    );
    await tester.enterText(
      find.widgetWithText(TextFormField, 'Their email'),
      'gift@example.test',
    );
    await tester.scrollUntilVisible(
      find.text('Review & send'),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Review & send'));
    await tester.pumpAndSettle();
    expect(find.text('Send this gift?'), findsOneWidget);
    await tester.tap(find.text('Not yet'));
    await tester.pumpAndSettle();
    expect(find.text('Send this gift?'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });
}
