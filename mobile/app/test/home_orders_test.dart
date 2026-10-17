import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

class OrdersPreviewApi extends DemoApi {
  @override
  Future<List<dynamic>> orders() async => [
    {
      'id': 10,
      'name': '260-1-000004',
      'state': 'paid',
      'total': 15,
      'currency': 'TTD',
      'date': '2026-10-17T20:40:00',
    },
  ];
}

void main() {
  testWidgets('Home bill shortcut is visible and opens native order history', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(JennysApp(initialApi: OrdersPreviewApi()));
    await tester.pumpAndSettle();
    final shortcut = find.byKey(const ValueKey('home-orders-bill'));
    expect(shortcut.hitTestable(), findsOneWidget);
    await tester.tap(shortcut);
    await tester.pumpAndSettle();
    expect(find.text('Your orders'), findsOneWidget);
    expect(find.text('Order 260-1-000004'), findsOneWidget);
    expect(find.byTooltip('Refresh orders'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(shortcut.hitTestable(), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
}
