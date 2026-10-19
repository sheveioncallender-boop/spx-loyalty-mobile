import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

class LiveTestApi extends DemoApi {
  @override
  bool get isDemo => false;
  int reads = 0, adds = 0;
  num balance = 0;
  bool offline = false;
  int pageSize = 40;
  Completer<void>? holdCart;
  List<Json> menu = DemoApi.items
      .map((item) => Map<String, dynamic>.from(item))
      .toList();
  List<Json> messages = [];
  List<Json> offers = [];
  List<Json> loyaltyHistory = [];
  List<Json> onlineOrders = [];
  List<Json>? customCards;

  @override
  Future<Json> bootstrap() async {
    reads++;
    if (offline) throw AppError('Check your connection and try again.');
    return {
      'customer': {
        'name': 'Jenny’s Test Customer',
        'email': 'test@example.com',
      },
      'currency': 'TTD',
      'cards': customCards != null
          ? jsonDecode(jsonEncode(customCards))
          : [
              {
                'id': 19,
                'program_id': 1,
                'name': 'Jenny’s Rewards',
                'number': '0444-2cd7-45a6',
                'points': balance,
                'point_name': 'Points',
                'since': '2026-09-08T12:00:00',
              },
            ],
      'rewards': jsonDecode(jsonEncode(offers)),
      'activity': jsonDecode(jsonEncode(loyaltyHistory)),
      'messages': jsonDecode(jsonEncode(messages)),
    };
  }

  @override
  Future<Json> catalog({int offset = 0}) async => {
    'items': jsonDecode(jsonEncode(menu.skip(offset).take(pageSize).toList())),
    'next_offset': offset + pageSize < menu.length ? offset + pageSize : null,
  };

  @override
  Future<Json> cart() async {
    final gate = holdCart;
    holdCart = null;
    final snapshot = await super.cart();
    if (gate != null) await gate.future;
    return snapshot;
  }

  @override
  Future<Json> add(Json item) async {
    adds++;
    return super.add(item);
  }

  @override
  Future<List<dynamic>> orders() async =>
      jsonDecode(jsonEncode(onlineOrders)) as List<dynamic>;
}

void main() {
  Future<void> open(WidgetTester tester, LiveTestApi api) async {
    tester.view.physicalSize = const Size(393, 852);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpWidget(JennysApp(initialApi: api));
    await tester.pumpAndSettle();
  }

  Future<void> tick(WidgetTester tester) async {
    await tester.pump(const Duration(seconds: 15));
    await tester.pumpAndSettle();
  }

  Future<void> close(WidgetTester tester) async {
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  }

  testWidgets(
    'Published changes arrive automatically without clearing search or scroll',
    (tester) async {
      final api = LiveTestApi();
      await open(tester, api);
      await tester.tap(find.text('Order').last);
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextField), 'noodles');
      await tester.pumpAndSettle();
      await tester.drag(find.byType(ListView).first, const Offset(0, -100));
      await tester.pumpAndSettle();
      final before = tester
          .state<ScrollableState>(find.byType(Scrollable).first)
          .position
          .pixels;
      api.menu[0]['name'] = 'Fresh noodles';
      api.menu[0]['price'] = 105;
      await tick(tester);
      expect(find.text('Fresh noodles'), findsOneWidget);
      expect(find.text('TT\$105.00'), findsOneWidget);
      expect(
        tester.widget<TextField>(find.byType(TextField)).controller!.text,
        'noodles',
      );
      expect(
        tester
            .state<ScrollableState>(find.byType(Scrollable).first)
            .position
            .pixels,
        before,
      );
      expect(find.byType(LoadingSkeleton), findsNothing);
      await close(tester);
    },
  );

  testWidgets(
    'Card points recover after offline polling and refresh on resume',
    (tester) async {
      final api = LiveTestApi();
      await open(tester, api);
      await tester.tap(find.text('My card').last);
      await tester.pumpAndSettle();
      api.balance = 50;
      api.offline = true;
      await tick(tester);
      expect(find.text('0').hitTestable(), findsWidgets);
      expect(find.text('Let’s reconnect.'), findsNothing);
      api.offline = false;
      await tick(tester);
      expect(find.text('50').hitTestable(), findsWidgets);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
      final count = api.reads;
      api.balance = 75;
      await tester.pump(const Duration(minutes: 1));
      expect(api.reads, count);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.hidden);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.inactive);
      tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
      await tester.pumpAndSettle();
      expect(find.text('75').hitTestable(), findsWidgets);
      await close(tester);
    },
  );

  testWidgets(
    'Changed loyalty discounts and required points refresh on Rewards',
    (tester) async {
      final api = LiveTestApi()
        ..offers = [
          {
            'id': 7,
            'program_id': 1,
            'name': '5% on your order',
            'points': 200,
            'type': 'discount',
            'needs_selection': false,
          },
        ];
      await open(tester, api);
      await tester.tap(find.text('Rewards').last);
      await tester.pumpAndSettle();
      expect(find.text('5% on your order'), findsOneWidget);
      expect(find.text('200 points'), findsOneWidget);
      api.offers = [
        {...api.offers.first, 'name': '10% on your order', 'points': 150},
      ];
      await tick(tester);
      expect(find.text('10% on your order'), findsOneWidget);
      expect(find.text('150 points'), findsOneWidget);
      expect(find.text('5% on your order'), findsNothing);
      expect(find.text('200 points'), findsNothing);
      api.offers.clear();
      await tick(tester);
      expect(find.text('10% on your order'), findsNothing);
      await close(tester);
    },
  );

  testWidgets('An older refresh cannot overwrite a successful cart add', (
    tester,
  ) async {
    final api = LiveTestApi();
    await open(tester, api);
    await tester.tap(find.text('Order').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Jenny’s Special Noodles').first);
    await tester.pumpAndSettle();
    final gate = Completer<void>();
    api.holdCart = gate;
    await tick(tester);
    await tester.tap(find.text('Add to order · TT\$98.00'));
    await tester.pumpAndSettle();
    gate.complete();
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('View order · TT\$98.00'),
      400,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('View order · TT\$98.00'), findsOneWidget);
    expect(api.adds, 1);
    await close(tester);
  });

  testWidgets('Previously loaded catalogue pages survive automatic refresh', (
    tester,
  ) async {
    final api = LiveTestApi()..pageSize = 2;
    await open(tester, api);
    await tester.tap(find.text('Order').last);
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Load more'),
      350,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Load more'));
    await tester.pumpAndSettle();
    final fourth = api.menu[3]['name'] as String;
    await tester.scrollUntilVisible(
      find.text(fourth),
      350,
      scrollable: find.byType(Scrollable).first,
    );
    await tick(tester);
    expect(find.text(fourth), findsOneWidget);
    api.menu.removeAt(0);
    await tick(tester);
    expect(find.text('Jenny’s Special Noodles'), findsNothing);
    expect(find.text(fourth), findsOneWidget);
    await close(tester);
  });

  testWidgets(
    'Selected card stays consistent when cards are added or removed',
    (tester) async {
      Json membership(int id, String name) => {
        'id': id,
        'program_id': id,
        'name': name,
        'number': '044-card-$id',
        'points': 0,
        'point_name': 'Points',
        'since': '2026-09-08T12:00:00',
      };
      final api = LiveTestApi()
        ..customCards = [
          membership(19, 'First program'),
          membership(27, 'Second program'),
        ];
      await open(tester, api);
      await tester.tap(find.text('My card').last);
      await tester.pumpAndSettle();
      await tester.tap(find.byType(DropdownButtonFormField<int>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Second program').last);
      await tester.pumpAndSettle();
      Finder selectedLabel(String label) => find
          .descendant(
            of: find.byType(DropdownButtonFormField<int>),
            matching: find.text(label),
          )
          .hitTestable();
      expect(selectedLabel('Second program'), findsOneWidget);
      api.customCards!.insert(0, membership(44, 'New program'));
      await tick(tester);
      expect(selectedLabel('Second program'), findsOneWidget);
      expect(find.text('044-card-27'), findsWidgets);
      api.customCards!.removeWhere((entry) => entry['id'] == 27);
      await tick(tester);
      expect(selectedLabel('New program'), findsOneWidget);
      expect(find.text('044-card-44'), findsWidgets);
      expect(find.text('044-card-27'), findsNothing);
      await close(tester);
    },
  );

  testWidgets('Open product sheet disables an unpublished product', (
    tester,
  ) async {
    final api = LiveTestApi();
    await open(tester, api);
    await tester.tap(find.text('Order').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Jenny’s Special Noodles').first);
    await tester.pumpAndSettle();
    api.menu.removeAt(0);
    await tick(tester);
    expect(find.text('Currently unavailable'), findsOneWidget);
    expect(find.text('Add to order · TT\$98.00'), findsNothing);
    expect(api.adds, 0);
    await close(tester);
  });

  testWidgets('Open inbox and order history update without reopening', (
    tester,
  ) async {
    final api = LiveTestApi();
    await open(tester, api);
    await tester.tap(find.text('You').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Messages from Jenny’s'));
    await tester.pumpAndSettle();
    api.messages = [
      {
        'id': 1,
        'name': 'A new welcome',
        'body': 'See you soon.',
        'date': '2026-09-13T12:00:00',
        'read': false,
      },
    ];
    await tick(tester);
    expect(find.text('A new welcome'), findsOneWidget);
    await tester.tapAt(const Offset(10, 150));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Your orders'));
    await tester.pumpAndSettle();
    api.onlineOrders = [
      {
        'id': 1,
        'name': '260-1-000001',
        'state': 'draft',
        'total': 98,
        'currency': 'TTD',
        'date': '2026-09-13T12:00:00',
      },
    ];
    await tick(tester);
    expect(find.text('Order 260-1-000001'), findsOneWidget);
    expect(find.text('Order received'), findsOneWidget);
    await close(tester);
  });
}
