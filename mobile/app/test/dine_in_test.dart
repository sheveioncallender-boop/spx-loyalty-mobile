import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

class OrderingApi extends DemoApi {
  @override
  bool get isDemo => false;
  final List<Json> submissions = [];
  bool failOnce = false, changeOnce = false;
  Completer<void>? hold;
  List<Json>? history;
  @override
  Future<List<dynamic>> orders() async => history ?? await super.orders();
  @override
  Future<Json> submit(Json basket) async {
    submissions.add(Map.of(basket));
    if (hold != null) await hold!.future;
    if (failOnce) {
      failOnce = false;
      throw AppError('Connection interrupted.');
    }
    if (changeOnce) {
      changeOnce = false;
      final updated = await cart();
      return {
        'status': 'changed',
        'cart': {...updated, 'total': 110, 'subtotal': 110},
      };
    }
    return super.submit(basket);
  }
}

void main() {
  Future<void> openBasket(WidgetTester tester, OrderingApi api) async {
    tester.view.physicalSize = const Size(393, 852);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    unawaited(api.add(DemoApi.items.first));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpWidget(JennysApp(initialApi: api));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Order').last);
    await tester.pumpAndSettle();
    final button = find.textContaining('View order ·');
    await tester.scrollUntilVisible(
      button,
      350,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(button);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Place order'));
  }

  Future<void> close(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  }

  testWidgets(
    'Dine-in submit is single-flight and does not change loyalty points',
    (tester) async {
      final api = OrderingApi()..hold = Completer<void>();
      await openBasket(tester, api);
      await tester.tap(find.text('Place order'));
      await tester.pump();
      expect(api.submissions.length, 1);
      expect(find.text('Continue to checkout'), findsNothing);
      api.hold!.complete();
      await tester.pumpAndSettle();
      expect(find.text('Order received'), findsOneWidget);
      expect((await tester.runAsync(api.orders))!.length, 1);
      expect(
        (await tester.runAsync(api.bootstrap))!['cards'][0]['points'],
        850,
      );
      expect((await api.cart())['lines'], isEmpty);
      await close(tester);
    },
  );

  testWidgets('Unconfirmed submission retries with the same key and quote', (
    tester,
  ) async {
    final api = OrderingApi()..failOnce = true;
    await openBasket(tester, api);
    await tester.tap(find.text('Place order'));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<SegmentedButton<String>>(find.byType(SegmentedButton<String>))
          .onSelectionChanged,
      isNull,
    );
    expect(api.submissions.length, 1);
    await tester.ensureVisible(find.text('Check order again'));
    await tester.tap(find.text('Check order again'));
    await tester.pumpAndSettle();
    expect(api.submissions.length, 2);
    expect(api.submissions[0], api.submissions[1]);
    expect((await tester.runAsync(api.orders))!.length, 1);
    await close(tester);
  });

  testWidgets(
    'Your orders refreshes native received, paid, posted and cancelled states',
    (tester) async {
      tester.view.physicalSize = const Size(393, 852);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final api = OrderingApi()
        ..history = [
          {
            'name': '260-1-000001',
            'date': '2026-09-13T18:24:22',
            'total': 300,
            'currency': 'TTD',
            'state': 'draft',
          },
        ];
      await tester.pumpWidget(JennysApp(initialApi: api));
      await tester.pumpAndSettle();
      await tester.tap(find.text('You').last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Your orders'));
      await tester.pumpAndSettle();
      expect(find.text('Order received'), findsOneWidget);
      expect(find.textContaining('Your bill is open.'), findsOneWidget);
      for (final entry in {
        'paid': 'Paid',
        'done': 'Paid',
        'cancel': 'Cancelled',
      }.entries) {
        api.history = [
          {...api.history!.first, 'state': entry.key},
        ];
        await tester.pump(const Duration(seconds: 16));
        await tester.pumpAndSettle();
        expect(find.text(entry.value), findsOneWidget);
        expect(find.text('Order 260-1-000001'), findsOneWidget);
        expect(find.text('Order received'), findsNothing);
        expect(find.text('Preparing'), findsNothing);
      }
      await close(tester);
    },
  );

  testWidgets('Price change returns to review without creating an order', (
    tester,
  ) async {
    final api = OrderingApi()..changeOnce = true;
    await openBasket(tester, api);
    await tester.tap(find.text('Place order'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Your basket changed.'), findsOneWidget);
    expect(find.text('Order received'), findsNothing);
    expect(await tester.runAsync(api.orders), isEmpty);
    expect(api.submissions.length, 1);
    await close(tester);
  });

  testWidgets('Takeaway selection reaches submission and survives a retry', (
    tester,
  ) async {
    final api = OrderingApi()..failOnce = true;
    await openBasket(tester, api);
    tester.view.physicalSize = const Size(320, 700);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Takeaway'));
    await tester.tap(find.text('Takeaway'));
    await tester.pumpAndSettle();
    expect((await api.cart())['service'], 'takeaway');
    expect(find.textContaining('No table is needed.'), findsOneWidget);
    await tester.ensureVisible(find.text('Place order'));
    await tester.tap(find.text('Place order'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Check order again'));
    await tester.tap(find.text('Check order again'));
    await tester.pumpAndSettle();
    expect(api.submissions[0], api.submissions[1]);
    expect(
      find.textContaining('Your takeaway order has reached'),
      findsOneWidget,
    );
    expect((await tester.runAsync(api.orders))!.single['service'], 'takeaway');
    await close(tester);
  });

  test(
    'Late read cannot replace the basket key obtained from an add',
    () async {
      final late = Completer<http.Response>();
      final calls = <Json>[];
      int reads = 0;
      http.Response reply(Json data) =>
          http.Response(jsonEncode({'result': data}), 200);
      final api = OdooApi(
        Uri.parse('https://jennys.example'),
        'test',
        client: MockClient((r) async {
          final params = (jsonDecode(r.body) as Json)['params'] as Json;
          calls.add({'path': r.url.path, ...params});
          if (r.url.path.endsWith('/cart')) {
            if (++reads == 2) return late.future;
            return reply({'basket_key': 'initial-key'});
          }
          return reply({'basket_key': 'new-key'});
        }),
      );
      await api.cart();
      final reading = api.cart();
      await Future<void>.delayed(Duration.zero);
      await api.add({'product_id': 9, 'price': 0.01, 'partner_id': 90});
      late.complete(reply({'basket_key': 'stale-key'}));
      await reading;
      await api.update(9, 2);
      expect(calls.last['basket_key'], 'new-key');
      expect(calls[2].keys.toSet(), {
        'path',
        'product_id',
        'qty',
        'basket_key',
      });
      expect(
        calls.every((call) => '${call['path']}'.contains('/v2/dine-in/')),
        isTrue,
      );
    },
  );
}
