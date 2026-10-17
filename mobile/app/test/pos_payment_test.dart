import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

void main() {
  final order = <String, dynamic>{
    'id': 8,
    'name': '265-1-000001',
    'date': '2026-10-17T19:44:00',
    'total': 15,
    'currency': 'TTD',
    'state': 'draft',
    'payment_offer': {'amount': 15, 'currency': 'TTD'},
  };
  testWidgets(
    'Paid receipt shows native methods, masked card and change on a small phone',
    (tester) async {
      tester.view.physicalSize = const Size(360, 800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final paidOrder = {
        ...order,
        'state': 'paid',
        'total': 15,
        'payments': [
          {
            'method': 'Cash',
            'amount': 10,
            'currency': 'TTD',
            'date': order['date'],
            'kind': 'payment',
            'card': null,
          },
          {
            'method': 'Scotiabank Online',
            'amount': 10,
            'currency': 'TTD',
            'date': order['date'],
            'kind': 'payment',
            'card': {'brand': 'Visa', 'last4': '0083'},
          },
          {
            'method': 'Cash',
            'amount': -5,
            'currency': 'TTD',
            'date': order['date'],
            'kind': 'change',
            'card': null,
          },
        ],
      };
      Future<void> show(Map<String, dynamic> data) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: OrderStatusCard(order: data, onPay: () {}),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
      }

      await show(paidOrder);
      expect(find.text('Paid'), findsOneWidget);
      expect(find.text('Payment details'), findsOneWidget);
      expect(find.text('Cash'), findsOneWidget);
      expect(find.text('Scotiabank Online'), findsOneWidget);
      expect(find.text('Visa ending 0083'), findsOneWidget);
      expect(find.text('Change · Cash'), findsOneWidget);
      expect(find.text('TT\$10.00'), findsNWidgets(2));
      expect(find.text('TT\$-5.00'), findsOneWidget);
      expect(find.byType(FilledButton), findsNothing);
      expect(tester.takeException(), isNull);
      await show({...paidOrder, 'state': 'draft'});
      expect(find.text('Payment details'), findsNothing);
      expect(find.text('Visa ending 0083'), findsNothing);
      await show({...paidOrder, 'payments': null});
      expect(find.text('Paid'), findsOneWidget);
      expect(find.text('Payment details'), findsNothing);
    },
  );

  testWidgets(
    'Card method without details stays readable and never displays a full card number',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: OrderStatusCard(
              order: {
                ...order,
                'state': 'paid',
                'payments': [
                  {
                    'method': 'Card terminal',
                    'amount': 15,
                    'currency': 'TTD',
                    'date': order['date'],
                    'kind': 'payment',
                    'card': {'brand': '', 'last4': '4111111111111111'},
                  },
                ],
              },
            ),
          ),
        ),
      );
      expect(find.text('Card terminal'), findsOneWidget);
      expect(find.textContaining('4111111111111111'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'Only a prepared open bill offers payment; POS remains an option',
    (tester) async {
      var taps = 0;
      Future<void> show(Map<String, dynamic> data, {bool busy = false}) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: OrderStatusCard(
                order: data,
                onPay: () => taps++,
                paymentBusy: busy,
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
      }

      await show(order);
      expect(find.textContaining('or with our team'), findsOneWidget);
      await tester.tap(find.byType(FilledButton));
      expect(taps, 1);
      await show(order, busy: true);
      expect(
        tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      for (final state in ['paid', 'done', 'cancel']) {
        await show({...order, 'state': state});
        expect(find.byType(FilledButton), findsNothing);
      }
      await show({...order, 'payment_offer': null});
      expect(find.byType(FilledButton), findsNothing);
      expect(find.textContaining('Ask our team'), findsOneWidget);
    },
  );

  test(
    'Payment request sends only the order ID and accepts its native same-origin checkout',
    () async {
      var calls = 0;
      final api = OdooApi(
        Uri.parse('https://jenny.example'),
        'test',
        sessionId: 'test-session',
        client: MockClient((req) async {
          calls++;
          expect(req.url.path, '/spx/mobile/v2/dine-in/payment');
          expect(jsonDecode(req.body)['params'], {'order_id': 8});
          expect(req.headers['Cookie'], 'session_id=test-session');
          return http.Response(
            jsonEncode({
              'result': {
                'order_id': 8,
                'path': '/pos/pay/8?access_token=test-token',
              },
            }),
            200,
          );
        }),
      );
      expect(await api.paymentPage(8), '/pos/pay/8?access_token=test-token');
      expect(calls, 1);
    },
  );

  test(
    'Reject a different bill, foreign origin, injected exit or missing token',
    () async {
      for (final result in [
        {'order_id': 9, 'path': '/pos/pay/8?access_token=a'},
        {
          'order_id': 8,
          'path': 'https://other.example/pos/pay/8?access_token=a',
        },
        {'order_id': 8, 'path': '/pos/pay/9?access_token=a'},
        {'order_id': 8, 'path': '/pos/pay/8'},
        {
          'order_id': 8,
          'path': '/pos/pay/8?access_token=a&exit_route=https://other.example',
        },
      ]) {
        final api = OdooApi(
          Uri.parse('https://jenny.example'),
          'test',
          client: MockClient(
            (req) async => http.Response(jsonEncode({'result': result}), 200),
          ),
        );
        await expectLater(api.paymentPage(8), throwsA(isA<AppError>()));
      }
    },
  );

  test('Interrupted checkout request is not automatically retried', () async {
    var calls = 0;
    final api = OdooApi(
      Uri.parse('https://jenny.example'),
      'test',
      client: MockClient((req) async {
        calls++;
        throw http.ClientException('offline');
      }),
    );
    await expectLater(api.paymentPage(8), throwsA(isA<AppError>()));
    expect(calls, 1);
  });
}
