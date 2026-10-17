import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

typedef Json = Map<String, dynamic>;

class AppError implements Exception {
  final String message;
  final bool expired;
  final String? code;
  AppError(this.message, {this.expired = false, this.code});
  @override
  String toString() => message;
}

/// Only customer-appropriate errors are shown. Technical server errors remain
/// outside the app UI; ordinary validation messages keep their useful detail.
String customerMessage(dynamic message) {
  final value = message is String ? message : '';
  if (value.trim().isEmpty ||
      value.length > 400 ||
      RegExp(
        r'odoo|database|connector|traceback|portal|proxy|https?://|\b(?:res|loyalty|sale|pos)\.[a-z_]+',
        caseSensitive: false,
      ).hasMatch(value)) {
    return 'This action is unavailable right now. Please try again or contact Jenny’s.';
  }
  return value;
}

String customerError(Object error) => error is AppError
    ? customerMessage(error.message)
    : 'Something went wrong. Please try again.';

abstract class MobileApi {
  bool get isDemo;
  Future<Json> bootstrap();
  Future<Json> catalog({int offset = 0});
  Future<Json> cart();
  Future<Json> add(Json item);
  Future<Json> update(int lineId, num quantity);
  Future<Json> reward(Json reward, {int? productId});
  Future<Json> submit(Json basket);
  Future<List<dynamic>> orders();
  Future<void> preferences(bool enabled);
  Future<void> readMessage(int id);
  Future<void> logout();
}

class OdooApi implements MobileApi {
  static const configuredOrigin = String.fromEnvironment('JENNYS_API_URL');
  static const configuredDatabase = String.fromEnvironment('JENNYS_DATABASE');
  static bool get isConfigured =>
      configuredOrigin.isNotEmpty && configuredDatabase.isNotEmpty;
  factory OdooApi.configured() {
    if (!isConfigured) {
      throw AppError(
        'Sign-in is not available in this preview. Please explore Jenny’s using Try the preview.',
      );
    }
    return OdooApi(validateOrigin(configuredOrigin), configuredDatabase);
  }
  static const _storage = FlutterSecureStorage();
  static const _storageKey = 'jennys.odoo.session.v1';
  static const _pendingKey = 'jennys.signup.pending.v1';
  static const _deploymentKey = 'jennys.deployment.v1';
  final Uri origin;
  final String database;
  String? sessionId;
  String? _basketKey;
  int _basketEpoch = 0, _basketWrites = 0;
  bool _authenticated = false;
  final http.Client _client;
  OdooApi(this.origin, this.database, {this.sessionId, http.Client? client})
    : _client = client ?? http.Client();
  @override
  bool get isDemo => false;

  static Uri validateOrigin(String input) {
    final uri = Uri.tryParse(input.trim());
    if (uri == null ||
        uri.scheme != 'https' ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        (uri.path.isNotEmpty && uri.path != '/')) {
      throw AppError(
        'Jenny’s sign-in is temporarily unavailable. Please try again later.',
      );
    }
    return Uri(
      scheme: 'https',
      host: uri.host,
      port: uri.hasPort ? uri.port : null,
    );
  }

  Uri page(String path) {
    final result = origin.resolve(path);
    if (result.scheme != origin.scheme ||
        result.host != origin.host ||
        result.port != origin.port) {
      throw AppError('This link is outside your Jenny’s website.');
    }
    return result;
  }

  Future<void> _save() => _storage.write(
    key: _storageKey,
    value: jsonEncode({
      'origin': origin.toString(),
      'database': database,
      'session': sessionId,
    }),
  );

  static Future<void> prepareDeployment(
    String address,
    String database, {
    Future<void> Function()? clearWebsiteSession,
  }) async {
    final origin = validateOrigin(address).toString();
    bool matches(String value) {
      try {
        final data = jsonDecode(value) as Json;
        return validateOrigin(data['origin'] as String).toString() == origin &&
            data['database'] == database;
      } catch (_) {
        return false;
      }
    }

    final stored = await Future.wait([
      _storage.read(key: _deploymentKey),
      _storage.read(key: _storageKey),
      _storage.read(key: _pendingKey),
    ]);
    if (stored.any((value) => value != null && !matches(value))) {
      await clearWebsiteSession?.call();
      await _storage.delete(key: _storageKey);
      await _storage.delete(key: _pendingKey);
    }
    await _storage.write(
      key: _deploymentKey,
      value: jsonEncode({'origin': origin, 'database': database}),
    );
  }

  static Future<OdooApi?> restore({
    Future<void> Function()? clearWebsiteSession,
  }) async {
    // A previous test build must never restore a user-selected connection into
    // a build configured for a different Jenny’s environment.
    if (!isConfigured) {
      await _storage.delete(key: _storageKey);
      await _storage.delete(key: _pendingKey);
      await _storage.delete(key: _deploymentKey);
      return null;
    }
    await prepareDeployment(
      configuredOrigin,
      configuredDatabase,
      clearWebsiteSession: clearWebsiteSession,
    );
    final stored = await _storage.read(key: _storageKey);
    if (stored == null) return null;
    try {
      final data = jsonDecode(stored) as Json;
      if (validateOrigin(data['origin'] as String) !=
              validateOrigin(configuredOrigin) ||
          data['database'] != configuredDatabase) {
        await _storage.delete(key: _storageKey);
        return null;
      }
      final sid = data['session'];
      if (sid is! String || !RegExp(r'^[A-Za-z0-9_-]{20,256}$').hasMatch(sid)) {
        return null;
      }
      return OdooApi(
        validateOrigin(data['origin'] as String),
        data['database'] as String,
        sessionId: sid,
      ).._authenticated = true;
    } catch (_) {
      await _storage.delete(key: _storageKey);
      return null;
    }
  }

  Future<dynamic> rpc(String path, [Json params = const {}]) async {
    // Redirects stay disabled: credentials and session cookies never follow a different host.
    final request = http.Request('POST', page(path))..followRedirects = false;
    request.headers['Content-Type'] = 'application/json';
    if (sessionId != null) request.headers['Cookie'] = 'session_id=$sessionId';
    request.body = jsonEncode({
      'jsonrpc': '2.0',
      'method': 'call',
      'params': params,
      'id': 1,
    });
    try {
      final response = await http.Response.fromStream(
        await _client.send(request),
      ).timeout(const Duration(seconds: 25));
      if (response.statusCode >= 300 && response.statusCode < 400) {
        throw AppError(
          'Jenny’s is temporarily unavailable. Please try again later.',
        );
      }
      if (response.statusCode == 404) {
        throw AppError(
          'This service is not available yet. Please try again later.',
        );
      }
      if (response.statusCode >= 500) {
        throw AppError('Jenny’s is temporarily unavailable. Please try again.');
      }
      final body = jsonDecode(response.body) as Json;
      if (body['error'] != null) {
        final error = body['error'] as Json;
        final data = error['data'] as Json? ?? {};
        final name = '${data['name']}';
        if (name.contains('AccountExistsUserError')) {
          throw AppError(
            customerMessage(data['message']),
            code: 'account_exists',
          );
        }
        if (name.contains('SessionExpired')) {
          throw AppError(
            'Your session has ended. Please sign in again.',
            expired: true,
          );
        }
        if (name.contains('AccessDenied')) {
          throw AppError('Check your email and password and try again.');
        }
        if (name.contains('AccessError') ||
            name.contains('UserError') ||
            name.contains('ValidationError')) {
          throw AppError(customerMessage(data['message']));
        }
        throw AppError('We couldn’t complete that request. Please try again.');
      }
      final cookies = response.headers['set-cookie'];
      final sid = cookies == null
          ? null
          : RegExp(
              r'(?:^|[,;]\s*)session_id=([A-Za-z0-9_-]{20,256})',
            ).firstMatch(cookies)?.group(1);
      if (sid != null && sid != sessionId) {
        sessionId = sid;
        // Persist only after a verified authenticated response, or an existing session rotation.
        if (_authenticated &&
            ![
              '/web/session/authenticate',
              '/spx/mobile/v1/account/signin',
              '/spx/mobile/v1/account/exchange',
            ].contains(path)) {
          await _save();
        }
      }
      return body['result'];
    } on AppError {
      rethrow;
    } catch (_) {
      // Never retry a mutation automatically: its result may have reached Odoo.
      throw AppError(
        'Connection interrupted. Refresh before trying your action again.',
      );
    }
  }

  Future<Json> accountConfig() async =>
      (await rpc('/spx/mobile/v1/account/config')) as Json;

  Future<void> accountPreferences(bool email, bool sms) async {
    await rpc('/spx/mobile/v1/preferences', {
      'promotional_email': email,
      'promotional_sms': sms,
    });
  }

  Future<String> register(Json details) async {
    final result =
        (await rpc('/spx/mobile/v1/account/signup', details)) as Json;
    final receipt = result['receipt'] as String;
    await _storage.write(
      key: _pendingKey,
      value: jsonEncode({
        'origin': origin.toString(),
        'database': database,
        'receipt': receipt,
        'email': details['email'],
        'created': DateTime.now().toUtc().toIso8601String(),
      }),
    );
    return receipt;
  }

  Future<bool> signupVerified(String receipt) async =>
      (await rpc('/spx/mobile/v1/account/status', {
        'receipt': receipt,
      }))['verified'] ==
      true;

  Future<void> finishSignup(String code) async {
    final saved = await _storage.read(key: _pendingKey);
    Json? pending;
    try {
      pending = saved == null ? null : jsonDecode(saved) as Json;
    } catch (_) {
      /* invalid local record */
    }
    final created = DateTime.tryParse('${pending?['created']}');
    if (pending == null ||
        pending['origin'] != origin.toString() ||
        pending['database'] != database ||
        created == null ||
        DateTime.now().toUtc().difference(created) >
            const Duration(hours: 24)) {
      throw AppError(
        'Your email is verified. Please sign in with your email and password on this device.',
      );
    }
    final result = await rpc('/spx/mobile/v1/account/exchange', {
      'code': code,
      'receipt': pending['receipt'],
    });
    if (result['uid'] == null || result['uid'] == false || sessionId == null) {
      throw AppError('Please sign in to continue to your account.');
    }
    await bootstrap();
    _authenticated = true;
    await _save();
    await _storage.delete(key: _pendingKey);
  }

  Future<void> resendVerification(String receipt) async {
    await rpc('/spx/mobile/v1/account/resend', {'receipt': receipt});
  }

  Future<void> forgotPassword(String email) async {
    await rpc('/spx/mobile/v1/account/forgot', {'email': email.trim()});
  }

  Future<void> login(String email, String password) async {
    final result =
        await rpc('/spx/mobile/v1/account/signin', {
              'email': email.trim(),
              'password': password,
            })
            as Json;
    if (result['uid'] == null || result['uid'] == false) {
      sessionId = null;
      throw AppError(
        'This account needs an additional sign-in step that is not available in this preview. Please contact Jenny’s for help.',
      );
    }
    if (sessionId == null) {
      throw AppError('We couldn’t sign you in. Please try again later.');
    }
    await bootstrap(); // Enforce connector scope before persisting the session.
    _authenticated = true;
    await _save();
    await _storage.delete(key: _pendingKey);
  }

  @override
  Future<Json> bootstrap() async =>
      await rpc('/spx/mobile/v1/bootstrap') as Json;
  @override
  Future<Json> catalog({int offset = 0}) async =>
      await rpc('/spx/mobile/v2/dine-in/catalog', {'offset': offset}) as Json;
  @override
  Future<Json> cart() async {
    final epoch = _basketEpoch;
    final result = await rpc('/spx/mobile/v2/dine-in/cart') as Json;
    if (epoch == _basketEpoch && _basketWrites == 0) {
      _basketKey = result['basket_key'] as String?;
    }
    return result;
  }

  Future<Json> _changeBasket(String route, Json params) async {
    final epoch = ++_basketEpoch;
    _basketWrites++;
    try {
      final result =
          await rpc('/spx/mobile/v2/dine-in/cart/$route', {
                ...params,
                'basket_key': _basketKey,
              })
              as Json;
      if (epoch == _basketEpoch) _basketKey = result['basket_key'] as String?;
      return result;
    } finally {
      _basketWrites--;
      _basketEpoch++;
    }
  }

  @override
  Future<Json> add(Json item) =>
      _changeBasket('add', {'product_id': item['product_id'], 'qty': 1});

  @override
  Future<Json> update(int lineId, num quantity) =>
      _changeBasket('update', {'line_id': lineId, 'qty': quantity});
  @override
  Future<Json> reward(Json reward, {int? productId}) async => throw AppError(
    'Our team can apply eligible rewards when you settle your bill.',
  );
  @override
  Future<Json> submit(Json basket) async {
    _basketEpoch++;
    _basketWrites++;
    try {
      return await rpc('/spx/mobile/v2/dine-in/submit', {
            'basket_key': basket['basket_key'],
            'quote': basket['quote'],
          })
          as Json;
    } finally {
      _basketWrites--;
      _basketEpoch++;
    }
  }

  @override
  Future<List<dynamic>> orders() async =>
      await rpc('/spx/mobile/v2/dine-in/orders') as List<dynamic>;

  Future<String> paymentPage(int orderId) async {
    final result =
        await rpc('/spx/mobile/v2/dine-in/payment', {'order_id': orderId})
            as Json;
    final path = result['path'];
    if (result['order_id'] != orderId || path is! String) {
      throw AppError('This bill is unavailable. Please refresh your orders.');
    }
    final uri = page(path);
    if (uri.userInfo.isNotEmpty ||
        uri.hasFragment ||
        uri.path != '/pos/pay/$orderId' ||
        uri.queryParameters['access_token']?.isNotEmpty != true ||
        uri.queryParameters.keys.any((key) => key != 'access_token')) {
      throw AppError('This bill is unavailable. Please refresh your orders.');
    }
    return path;
  }

  @override
  Future<void> preferences(bool enabled) async {
    await rpc('/spx/mobile/v1/preferences', {'promotional_email': enabled});
  }

  @override
  Future<void> readMessage(int id) async {
    await rpc('/spx/mobile/v1/messages/read', {'message_id': id});
  }

  @override
  Future<void> logout() async {
    try {
      await rpc('/web/session/destroy');
    } finally {
      sessionId = null;
      await _storage.delete(key: _storageKey);
      _client.close();
    }
  }
}

class DemoApi implements MobileApi {
  @override
  bool get isDemo => true;
  bool email = false;
  final List<Json> _lines = [];
  final Set<int> _read = {};
  final List<Json> _orders = [];
  final Map<String, Json> _receipts = {};
  int _basketVersion = 0;
  Future<void> _delay() => Future.delayed(const Duration(milliseconds: 420));
  static const items = <Json>[
    {
      'id': 1,
      'product_id': 1,
      'name': 'Jenny’s Special Noodles',
      'description':
          'Wok-tossed noodles, crisp vegetables and roasted chicken.',
      'price': 98.0,
      'category': 'Mains',
      'image': 'dish-feature.jpg',
      'direct_add': true,
    },
    {
      'id': 2,
      'product_id': 2,
      'name': 'Boulevard Fried Rice',
      'description': 'Our familiar favourite, made for sharing.',
      'price': 86.0,
      'category': 'Mains',
      'image': 'jennys-buffet.jpg',
      'direct_add': true,
    },
    {
      'id': 3,
      'product_id': 3,
      'name': 'Signature Rum Punch',
      'description': 'Tropical fruit, fresh lime and a little island spirit.',
      'price': 54.0,
      'category': 'Drinks',
      'image': 'cocktail-lounge.jpg',
      'direct_add': true,
    },
    {
      'id': 4,
      'product_id': 4,
      'name': 'Crispy Chicken Bites',
      'description': 'Sweet chilli glaze and a satisfying crunch.',
      'price': 72.0,
      'category': 'Starters',
      'image': 'jennys-buffet.jpg',
      'direct_add': true,
    },
  ];
  @override
  Future<Json> bootstrap() async {
    await _delay();
    return {
      'brand': 'Jenny’s on the Boulevard',
      'api_version': 1,
      'currency': 'TTD',
      'customer': {
        'name': 'Jenny’s Guest',
        'email': 'guest@example.com',
        'promotional_email': email,
      },
      'cards': [
        {
          'id': 1,
          'program_id': 1,
          'name': 'Jenny’s Rewards',
          'number': 'JB 0019 8726',
          'points': 850.0,
          'point_name': 'Points',
          'since': '2026-01-01',
          'expires': null,
        },
      ],
      'rewards': [
        {
          'id': 1,
          'program_id': 1,
          'name': 'A little treat on us',
          'points': 500.0,
          'type': 'product',
          'needs_selection': false,
        },
        {
          'id': 2,
          'program_id': 1,
          'name': 'More to enjoy together',
          'points': 1000.0,
          'type': 'discount',
          'needs_selection': false,
        },
      ],
      'activity': [
        {
          'id': 1,
          'card_id': 1,
          'name': 'A visit to the Boulevard',
          'issued': 150,
          'used': 0,
          'date': '2026-09-04T18:30:00',
        },
        {
          'id': 2,
          'card_id': 1,
          'name': 'A well-earned treat',
          'issued': 0,
          'used': 500,
          'date': '2026-08-30T18:30:00',
        },
      ],
      'messages': [
        {
          'id': 1,
          'name': 'A warm welcome to Jenny’s',
          'body':
              'Your favourites, your membership card and a little more to look forward to. Enjoy exploring this sample app.',
          'read': _read.contains(1),
          'date': '2026-09-08',
        },
      ],
      'capabilities': {
        'cart': true,
        'inbox': true,
        'push': false,
        'checkout': 'dine_in',
        'ordering_api': 2,
      },
    };
  }

  @override
  Future<Json> catalog({int offset = 0}) async {
    await _delay();
    return {'items': offset == 0 ? items : [], 'next_offset': null};
  }

  @override
  Future<Json> cart() async {
    final total = _lines.fold<num>(
      0,
      (sum, item) => sum + (item['total'] as num),
    );
    return {
      'lines': _lines.map((e) => Map<String, dynamic>.from(e)).toList(),
      'total': total,
      'subtotal': total,
      'tax': 0.0,
      'currency': 'TTD',
      'rewards': [],
      'basket_key': 'sample-basket-$_basketVersion',
      'quote': 'sample-quote-$_basketVersion',
      'can_submit': _lines.isNotEmpty,
      'last_order': _orders.isEmpty ? null : _orders.last,
    };
  }

  @override
  Future<Json> add(Json item) async {
    await _delay();
    _basketVersion++;
    final existing = _lines.where((line) => line['id'] == item['id']);
    if (existing.isNotEmpty) {
      existing.first['qty'] += 1;
      existing.first['total'] = existing.first['qty'] * item['price'];
    } else {
      _lines.add({
        'id': item['id'],
        'name': item['name'],
        'qty': 1,
        'price': item['price'],
        'total': item['price'],
        'editable': true,
        'reward': false,
        'image': item['image'],
      });
    }
    return cart();
  }

  @override
  Future<Json> update(int lineId, num quantity) async {
    await _delay();
    _basketVersion++;
    if (quantity == 0) {
      _lines.removeWhere((line) => line['id'] == lineId);
    } else {
      final line = _lines.firstWhere((line) => line['id'] == lineId);
      line['qty'] = quantity;
      line['total'] = quantity * line['price'];
    }
    return cart();
  }

  @override
  Future<Json> reward(Json reward, {int? productId}) async => throw AppError(
    'Reward redemption will be available when Jenny’s launches.',
  );
  @override
  Future<List<dynamic>> orders() async {
    await _delay();
    return _orders.reversed.toList();
  }

  @override
  Future<Json> submit(Json basket) async {
    await _delay();
    final key = '${basket['basket_key']}';
    if (_receipts.containsKey(key)) {
      return {'status': 'received', 'order': _receipts[key]};
    }
    final current = await cart();
    if (current['quote'] != basket['quote'] || _lines.isEmpty) {
      return {'status': 'changed', 'cart': current};
    }
    final receipt = <String, dynamic>{
      'name': 'Jenny’s order ${_orders.length + 1}',
      'date': DateTime.now().toIso8601String(),
      'total': current['total'],
      'currency': 'TTD',
      'state': 'draft',
      'submission_key': key,
    };
    _receipts[key] = receipt;
    _orders.add(receipt);
    _lines.clear();
    _basketVersion++;
    return {'status': 'received', 'order': receipt};
  }

  @override
  Future<void> preferences(bool enabled) async {
    await _delay();
    email = enabled;
  }

  @override
  Future<void> readMessage(int id) async {
    _read.add(id);
  }

  @override
  Future<void> logout() async {}
}
