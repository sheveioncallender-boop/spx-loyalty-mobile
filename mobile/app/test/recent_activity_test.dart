import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';
import 'automatic_refresh_test.dart' show LiveTestApi;

Json event(
  int id, {
  int card = 19,
  num issued = 0,
  num used = 0,
  String? date,
}) => {
  'id': id,
  'card_id': card,
  'issued': issued,
  'used': used,
  'name': 'Visit reference $id',
  'date': date ?? '2026-09-13T18:30:00',
};

void main() {
  Future<void> open(
    WidgetTester tester,
    LiveTestApi api, {
    double scale = 1,
  }) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = scale;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpWidget(JennysApp(initialApi: api));
    await tester.pumpAndSettle();
    await tester.tap(find.text('You').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Recent activity'));
    await tester.pumpAndSettle();
  }

  Future<void> close(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  }

  Finder row(int id) => find.byKey(ValueKey('activity-entry-$id'));
  Finder scrollable() => find
      .descendant(
        of: find.byType(RecentActivityPage),
        matching: find.byType(Scrollable),
      )
      .first;

  testWidgets(
    'Recent activity keeps both movements, filters by card and refreshes open details',
    (tester) async {
      final api = LiveTestApi()
        ..balance = 850
        ..loyaltyHistory = [
          event(1, issued: 150, used: 200),
          event(2, issued: 30, date: '2026-09-12T16:00:00'),
          event(3, card: 99, issued: 999),
        ];
      await open(tester, api);
      expect(find.byKey(const ValueKey('activity-balance')), findsOneWidget);
      expect(find.text('850'), findsOneWidget);
      expect(row(3), findsNothing);
      await tester.scrollUntilVisible(row(1), 200, scrollable: scrollable());
      await tester.tap(find.text('Points earned & used'));
      await tester.pumpAndSettle();
      expect(find.text('+150 pts'), findsOneWidget);
      expect(find.text('−200 pts'), findsOneWidget);
      expect(find.text('Net points change: −50'), findsOneWidget);
      api.loyaltyHistory[0]['name'] = 'Updated visit reference';
      api.balance = 875;
      await tester.pump(const Duration(seconds: 15));
      await tester.pumpAndSettle();
      expect(find.text('Updated visit reference'), findsOneWidget);
      expect(find.text('875'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.widgetWithText(ChoiceChip, 'Used'),
        -200,
        scrollable: scrollable(),
      );
      await tester.tap(find.widgetWithText(ChoiceChip, 'Used'));
      await tester.pumpAndSettle();
      expect(row(1), findsOneWidget);
      expect(row(2), findsNothing);
      await close(tester);
    },
  );

  testWidgets(
    'Empty and removed card states do not show stale activity at large text size',
    (tester) async {
      final api = LiveTestApi();
      await open(tester, api, scale: 1.5);
      await tester.scrollUntilVisible(
        find.text('No recent activity.'),
        200,
        scrollable: scrollable(),
      );
      expect(find.text('No recent activity.'), findsOneWidget);
      api.loyaltyHistory = [event(1, issued: -20, used: -5)];
      await tester.pump(const Duration(seconds: 15));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(row(1), 200, scrollable: scrollable());
      expect(find.text('Points adjusted'), findsOneWidget);
      expect(find.text('−20 pts'), findsOneWidget);
      expect(find.text('+5 pts'), findsOneWidget);
      api.customCards = [];
      await tester.pump(const Duration(seconds: 15));
      await tester.pumpAndSettle();
      expect(row(1), findsNothing);
      expect(find.text('Your story starts here.'), findsOneWidget);
      await close(tester);
    },
  );

  test('History timestamps treat unzoned native datetimes as UTC', () {
    expect(
      loyaltyActivityDate('2026-09-13T18:30:00')!.toUtc(),
      DateTime.utc(2026, 9, 13, 18, 30),
    );
    expect(
      loyaltyActivityDate('2026-09-13T14:30:00-04:00')!.toUtc(),
      DateTime.utc(2026, 9, 13, 18, 30),
    );
    expect(loyaltyActivityDate('2026-09-13')!.day, 13);
    expect(loyaltyActivityDate(null), isNull);
  });
}
