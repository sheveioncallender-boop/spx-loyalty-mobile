import 'dart:async';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'api.dart';
import 'card_flip.dart';
import 'loyalty_scan.dart';

part 'recent_activity.dart';
part 'order_status.dart';
part 'account_access.dart';
part 'app_intro.dart';
part 'member_extras.dart';

const navy = Color(0xFF112444);
const blue = Color(0xFF244E9D);
const gold = Color(0xFFE5C68C);
const ink = Color(0xFF172840);
const muted = Color(0xFF697386);
const paper = Color(0xFFF7F8FA);
const cream = Color(0xFFF5EFE4);
const appSystemStyle = SystemUiOverlayStyle(
  statusBarColor: Colors.transparent,
  statusBarIconBrightness: Brightness.dark,
  statusBarBrightness: Brightness.light,
  systemNavigationBarColor: Colors.white,
  systemNavigationBarIconBrightness: Brightness.dark,
);
const sessionChannel = MethodChannel('net.spxcorp.jennys/session');
final _entryKey = GlobalKey<_EntryState>();

Uri? accountLink(String? value) {
  final uri = Uri.tryParse(value ?? '');
  if (uri == null || uri.hasFragment || uri.userInfo.isNotEmpty) return null;
  if (uri.hasScheme && (uri.scheme != 'jennys' || uri.host != 'account')) {
    return null;
  }
  if (!uri.hasScheme && uri.hasAuthority) return null;
  if (![
    '/verified',
    '/password-updated',
    '/forgot-password',
  ].contains(uri.path)) {
    return null;
  }
  return uri;
}

void acceptAccount(OdooApi api, BuildContext context) {
  _entryKey.currentState?.acceptAccount(api);
  Navigator.of(context).popUntil((route) => route.isFirst);
}

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(appSystemStyle);
  runApp(const JennysApp());
}

class JennysApp extends StatelessWidget {
  final MobileApi? initialApi;
  const JennysApp({super.key, this.initialApi});
  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'Jenny’s',
    builder: (context, child) => AnnotatedRegion<SystemUiOverlayStyle>(
      value: appSystemStyle,
      child: child!,
    ),
    theme: ThemeData(
      useMaterial3: true,
      fontFamily: 'Manrope',
      scaffoldBackgroundColor: paper,
      colorScheme: ColorScheme.fromSeed(
        seedColor: blue,
        primary: blue,
        surface: Colors.white,
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(
          fontSize: 34,
          height: 1.15,
          letterSpacing: -1.3,
          fontWeight: FontWeight.w800,
          color: ink,
        ),
        headlineMedium: TextStyle(
          fontSize: 28,
          height: 1.2,
          letterSpacing: -1,
          fontWeight: FontWeight.w800,
          color: ink,
        ),
        titleLarge: TextStyle(
          fontSize: 21,
          fontWeight: FontWeight.w800,
          letterSpacing: -.5,
          color: ink,
        ),
        titleMedium: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w700,
          color: ink,
        ),
        bodyMedium: TextStyle(fontSize: 14, height: 1.6, color: muted),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 17),
          minimumSize: const Size(48, 54),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          textStyle: const TextStyle(
            fontFamily: 'Manrope',
            fontSize: 14,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFDFE4ED)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFDFE4ED)),
        ),
        contentPadding: const EdgeInsets.all(18),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: navy,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    ),
    onGenerateInitialRoutes: (initialRoute) => [
      MaterialPageRoute<void>(
        settings: const RouteSettings(name: '/'),
        builder: (_) => Entry(key: _entryKey, initialApi: initialApi),
      ),
      if (accountLink(initialRoute) case final Uri link)
        MaterialPageRoute<void>(builder: (_) => AccountReturn(link: link)),
    ],
    onGenerateRoute: (settings) {
      if (settings.name == '/') {
        return MaterialPageRoute<void>(
          settings: settings,
          builder: (_) => Entry(key: _entryKey, initialApi: initialApi),
        );
      }
      final link = accountLink(settings.name);
      if (link == null) return null;
      return MaterialPageRoute<void>(
        settings: settings,
        builder: (_) => AccountReturn(link: link),
      );
    },
  );
}

String points(dynamic value) {
  final n = (value as num?) ?? 0;
  final text = n == n.roundToDouble()
      ? n.toInt().toString()
      : n.toStringAsFixed(2);
  final parts = text.split('.');
  parts[0] = parts[0].replaceAllMapped(
    RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
    (m) => '${m[1]},',
  );
  return parts.join('.');
}

String money(dynamic amount, [String currency = 'TTD']) =>
    '${currency == 'TTD' ? 'TT\$' : '$currency '}${((amount as num?) ?? 0).toStringAsFixed(2)}';
String dateLabel(dynamic value) {
  final date = DateTime.tryParse('$value');
  if (date == null) return '';
  const months = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ];
  return '${date.day} ${months[date.month - 1]} ${date.year}';
}

void toast(BuildContext context, String text) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

class Entry extends StatefulWidget {
  final MobileApi? initialApi;
  final IntroStore introStore;
  final Future<MobileApi?> Function()? restoreAccount;
  const Entry({
    super.key,
    this.initialApi,
    this.introStore = const IntroStore(),
    this.restoreAccount,
  });
  @override
  State<Entry> createState() => _EntryState();
}

class _EntryState extends State<Entry> {
  MobileApi? api;
  bool restoring = true;
  bool showIntro = false;
  bool _acceptedAccount = false;
  void acceptAccount(OdooApi value) {
    _acceptedAccount = true;
    setState(() {
      api = value;
      showIntro = false;
      restoring = false;
    });
    unawaited(widget.introStore.complete());
  }

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    final seenFuture = widget.introStore.hasSeen();
    MobileApi? restored = widget.initialApi;
    if (restored == null) {
      try {
        restored =
            await (widget.restoreAccount?.call() ??
                OdooApi.restore(
                  clearWebsiteSession: () =>
                      sessionChannel.invokeMethod<void>('clear'),
                ));
      } catch (_) {
        /* Device storage unavailable: offer sign-in. */
      }
    }
    // An authenticated customer never waits for an onboarding preference.
    final seen = restored != null ? true : await seenFuture;
    if (mounted && !_acceptedAccount) {
      setState(() {
        api = restored;
        showIntro = restored == null && !seen;
        restoring = false;
      });
      if (restored != null) unawaited(widget.introStore.complete());
    }
  }

  Future<void> finishIntro(IntroAction action) async {
    await widget.introStore.complete();
    if (!mounted) return;
    setState(() => showIntro = false);
    if (action == IntroAction.skip) return;
    final result = await Navigator.of(context).push<OdooApi>(
      MaterialPageRoute(
        builder: (_) => AccountAccess(
          initialPage: action == IntroAction.signup ? 'signup' : 'login',
        ),
      ),
    );
    if (result != null && mounted) acceptAccount(result);
  }

  @override
  Widget build(BuildContext context) {
    if (restoring) return const LaunchLoading();
    if (api != null) {
      return AppShell(api: api!, onLogout: () => setState(() => api = null));
    }
    if (showIntro) return AppIntroduction(onFinish: finishIntro);
    return Welcome(
      onDemo: () => setState(() => api = DemoApi()),
      onSignup: () async {
        final result = await Navigator.of(context).push<OdooApi>(
          MaterialPageRoute(
            builder: (_) => const AccountAccess(initialPage: 'signup'),
          ),
        );
        if (result != null && mounted) setState(() => api = result);
      },
      onLogin: () async {
        final result = await Navigator.of(
          context,
        ).push<OdooApi>(MaterialPageRoute(builder: (_) => const SignIn()));
        if (result != null && mounted) setState(() => api = result);
      },
    );
  }
}

class Brand extends StatelessWidget {
  final double size;
  const Brand({super.key, this.size = 48});
  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Jenny’s on the Boulevard',
    image: true,
    child: ClipOval(
      child: Image.asset(
        'assets/images/jennys-logo.jpg',
        width: size,
        height: size,
        fit: BoxFit.cover,
      ),
    ),
  );
}

class Eyebrow extends StatelessWidget {
  final String text;
  final Color color;
  const Eyebrow(this.text, {super.key, this.color = muted});
  @override
  Widget build(BuildContext context) => Text(
    text.toUpperCase(),
    style: TextStyle(
      fontSize: 10,
      letterSpacing: 2,
      fontWeight: FontWeight.w800,
      color: color,
    ),
  );
}

class ActionButton extends StatelessWidget {
  final String text;
  final VoidCallback? onTap;
  final bool loading;
  final IconData? icon;
  const ActionButton(
    this.text, {
    super.key,
    this.onTap,
    this.loading = false,
    this.icon = Icons.arrow_forward_rounded,
  });
  @override
  Widget build(BuildContext context) => FilledButton(
    onPressed: loading ? null : onTap,
    child: Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (loading)
          const SizedBox(
            width: 19,
            height: 19,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: Colors.white,
            ),
          )
        else ...[
          Flexible(child: Text(text, textAlign: TextAlign.center)),
          if (icon != null) ...[
            const SizedBox(width: 14),
            Icon(icon, size: 18),
          ],
        ],
      ],
    ),
  );
}

class Welcome extends StatelessWidget {
  final VoidCallback onDemo, onLogin;
  final VoidCallback? onSignup;
  const Welcome({
    super.key,
    required this.onDemo,
    required this.onLogin,
    this.onSignup,
  });
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: accountHeader(),
    body: SafeArea(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(26, 22, 26, 32),
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(22),
            child: Image.asset(
              'assets/images/jennys-exterior.jpg',
              height: 210,
              fit: BoxFit.cover,
            ),
          ),
          const SizedBox(height: 28),
          const Eyebrow('Your place on the Boulevard'),
          const SizedBox(height: 14),
          Text(
            'Make every visit\na Jenny’s visit.',
            style: Theme.of(context).textTheme.headlineLarge,
          ),
          const SizedBox(height: 16),
          const Text(
            'Join Jenny’s for your digital card, rewards and a little more to look forward to.',
            style: TextStyle(color: muted, height: 1.8),
          ),
          const SizedBox(height: 30),
          ActionButton('Create an account', onTap: onSignup ?? onLogin),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onLogin, child: const Text('Sign in')),
          if (!OdooApi.isConfigured)
            TextButton(onPressed: onDemo, child: const Text('Try the preview')),
          const SizedBox(height: 28),
          const Text(
            'GOOD FOOD. GREAT COMPANY. SINCE 1987.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 9, letterSpacing: 1.3, color: muted),
          ),
        ],
      ),
    ),
  );
}

class AppShell extends StatefulWidget {
  final MobileApi api;
  final VoidCallback onLogout;
  const AppShell({super.key, required this.api, required this.onLogout});
  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> with WidgetsBindingObserver {
  int tab = 0, selectedCard = 0;
  Json? data;
  Json cart = {'lines': [], 'total': 0, 'rewards': []};
  Json? _pendingSubmission;
  String? _submissionMessage;
  List<dynamic> items = [];
  int? nextOffset;
  bool loading = true, loadingMore = false, busy = false;
  String? error;
  String category = 'All', search = '';
  final searchController = TextEditingController();
  final _sheetUpdates = ValueNotifier<int>(0);
  Timer? _refreshTimer;
  Future<void>? _refreshing;
  int _revision = 0, _writes = 0, _catalogPages = 1;
  bool _active = true, _signingOut = false, _webOpen = false;
  bool _sessionExpired = false, _ordersOpen = false, _ordersReading = false;
  List<dynamic>? _orderData;
  String? _orderError;
  MobileApi get api => widget.api;
  List<dynamic> get cards => data?['cards'] as List<dynamic>? ?? [];
  Json? get card => cards.isEmpty
      ? null
      : cards[math.min(selectedCard, cards.length - 1)] as Json;
  Json get customer => data?['customer'] as Json? ?? {};
  List<dynamic> get cardRewards => (data?['rewards'] as List<dynamic>? ?? [])
      .where((r) => card == null || r['program_id'] == card!['program_id'])
      .toList();
  List<dynamic> get lines => cart['lines'] as List<dynamic>? ?? [];
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _active =
        WidgetsBinding.instance.lifecycleState == null ||
        WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed;
    unawaited(refresh());
    _startRefreshTimer();
  }

  @override
  void dispose() {
    _signingOut = true;
    _revision++;
    _refreshTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _sheetUpdates.dispose();
    searchController.dispose();
    super.dispose();
  }

  void _startRefreshTimer() {
    _refreshTimer?.cancel();
    if (api.isDemo || !_active || _signingOut || _sessionExpired) return;
    _refreshTimer = Timer.periodic(const Duration(seconds: 15), (_) {
      unawaited(_autoRefresh());
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _active = state == AppLifecycleState.resumed;
    if (!_active) {
      _refreshTimer?.cancel();
      return;
    }
    _startRefreshTimer();
    unawaited(_autoRefresh());
  }

  Future<void> _autoRefresh() async {
    if (api.isDemo || !_active || _signingOut || _sessionExpired || _webOpen) {
      return;
    }
    await refresh(silent: true);
  }

  bool _canApply(int revision) =>
      mounted && !_signingOut && revision == _revision && _writes == 0;

  void _notifySheets() {
    if (mounted && !_signingOut) _sheetUpdates.value++;
  }

  Future<void> refresh({bool silent = false}) {
    if (_signingOut || _webOpen || _writes > 0 || loadingMore) {
      return Future<void>.value();
    }
    return _refreshing ??= _refreshCycle(silent: silent).whenComplete(() {
      _refreshing = null;
    });
  }

  Future<void> _refreshCycle({required bool silent}) async {
    final revision = _revision;
    if (!silent && mounted) setState(() => error = null);
    try {
      final info = await api.bootstrap();
      if (!_canApply(revision)) return;
      final cardId = card?['id'];
      setState(() {
        data = info;
        final index = cards.indexWhere((entry) => entry['id'] == cardId);
        selectedCard = index < 0 ? 0 : index;
        error = null;
      });
      _notifySheets();
      // Reload every page already viewed so polling never collapses the menu
      // back to its first page. These calls only read native records.
      final results = await Future.wait([_readCatalog(), api.cart()]);
      if (!_canApply(revision)) return;
      setState(() {
        items = results[0]['items'] as List<dynamic>;
        nextOffset = results[0]['next_offset'] as int?;
        cart = results[1];
        if (_pendingSubmission != null &&
            cart['last_order']?['submission_key'] ==
                _pendingSubmission!['basket_key']) {
          _pendingSubmission = null;
          _submissionMessage =
              'Your order has reached Jenny’s. Our team will take it from here.';
        }
        if (category != 'All' &&
            !items.any((item) => item['category'] == category)) {
          category = 'All';
        }
      });
      _notifySheets();
    } catch (e) {
      if (_canApply(revision)) {
        final expired = e is AppError && e.expired;
        if (!silent || data == null || expired) {
          setState(() {
            error = customerError(e);
            _sessionExpired = expired;
          });
        }
        if (expired) _refreshTimer?.cancel();
      }
    } finally {
      if (mounted) setState(() => loading = false);
    }
    if (_canApply(revision) && _ordersOpen) await _refreshOrders();
  }

  Future<Json> _readCatalog() async {
    final entries = <dynamic>[];
    final seen = <dynamic>{};
    int? offset = 0;
    for (var page = 0; page < _catalogPages && offset != null; page++) {
      final result = await api.catalog(offset: offset);
      for (final item in result['items'] as List<dynamic>) {
        if (seen.add(item['id'])) entries.add(item);
      }
      final next = result['next_offset'] as int?;
      offset = next != null && next > offset ? next : null;
    }
    return {'items': entries, 'next_offset': offset};
  }

  Future<T> _write<T>(Future<T> Function() action) async {
    _revision++;
    _writes++;
    try {
      return await action();
    } finally {
      _writes--;
      _revision++;
      // A read started before a write is discarded rather than overwriting
      // the successful mutation. Mutations themselves are never retried.
    }
  }

  Future<void> loadMore() async {
    if (loadingMore ||
        nextOffset == null ||
        _refreshing != null ||
        _writes > 0) {
      return;
    }
    final revision = _revision;
    setState(() => loadingMore = true);
    try {
      final result = await api.catalog(offset: nextOffset!);
      if (_canApply(revision)) {
        setState(() {
          final ids = items.map((item) => item['id']).toSet();
          items.addAll(
            (result['items'] as List<dynamic>).where(
              (item) => ids.add(item['id']),
            ),
          );
          nextOffset = result['next_offset'] as int?;
          _catalogPages++;
        });
        _notifySheets();
      }
    } catch (e) {
      if (mounted) toast(context, customerError(e));
    } finally {
      if (mounted) setState(() => loadingMore = false);
    }
  }

  void go(int value) {
    if (value != tab) {
      HapticFeedback.selectionClick();
      setState(() => tab = value);
    }
    unawaited(_autoRefresh());
  }

  Future<void> mutate(Future<Json> Function() action, {String? success}) async {
    if (busy) return;
    if (_pendingSubmission != null) {
      toast(context, 'Check your last order before changing your basket.');
      return;
    }
    setState(() {
      busy = true;
      _submissionMessage = null;
    });
    _notifySheets();
    try {
      final result = await _write(action);
      if (!mounted) return;
      setState(() => cart = result);
      HapticFeedback.lightImpact();
      if (result['warning'] != null) {
        toast(context, customerMessage(result['warning']));
      } else if (success != null) {
        toast(context, success);
      }
    } catch (e) {
      if (mounted) toast(context, customerError(e));
    } finally {
      if (mounted) setState(() => busy = false);
      _notifySheets();
    }
  }

  Future<void> submitOrder(BuildContext sheetContext) async {
    if (busy) return;
    final submission =
        _pendingSubmission ??
        {'basket_key': cart['basket_key'], 'quote': cart['quote']};
    setState(() {
      busy = true;
      _pendingSubmission = submission;
      _submissionMessage = null;
    });
    _notifySheets();
    try {
      final result = await _write(() => api.submit(submission));
      if (!mounted) return;
      if (result['status'] == 'changed') {
        setState(() {
          cart = result['cart'] as Json;
          _pendingSubmission = null;
          _submissionMessage =
              'Your basket changed. Please review the items and total before sending.';
        });
      } else if (result['status'] == 'received' && result['order'] is Json) {
        final receipt = result['order'] as Json;
        setState(() {
          _pendingSubmission = null;
          cart = {
            'lines': [],
            'total': 0,
            'rewards': [],
            'last_order': receipt,
          };
        });
        HapticFeedback.mediumImpact();
        if (sheetContext.mounted) Navigator.pop(sheetContext);
        if (!mounted) return;
        unawaited(
          showDialog<void>(
            context: context,
            builder: (context) => AlertDialog(
              icon: const Icon(
                Icons.check_circle_outline_rounded,
                color: blue,
                size: 42,
              ),
              title: Text(
                api.isDemo ? 'Your sample order is ready.' : 'Order received',
              ),
              content: Text(
                api.isDemo
                    ? 'This is a sample order. No order was sent and no points were changed.'
                    : '${receipt['name']}\n\nYour order has reached Jenny’s. Our team will confirm your table and send it to the kitchen. Pay after your meal.',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Lovely, thank you'),
                ),
              ],
            ),
          ),
        );
      } else {
        throw AppError('We couldn’t confirm your order. Please check again.');
      }
    } catch (e) {
      if (mounted) {
        setState(
          () => _submissionMessage =
              '${customerError(e)} Check Your orders or use Check order again below.',
        );
      }
      // Keep the same key and quote for a user-requested retry. A received
      // submission returns its saved receipt even after native table merging.
    } finally {
      if (mounted) setState(() => busy = false);
      _notifySheets();
    }
    if (mounted) unawaited(refresh(silent: true));
  }

  Future<void> openWeb(
    String path,
    String title, {
    bool checkout = false,
  }) async {
    if (api is! OdooApi) {
      toast(
        context,
        'This feature will be available when Jenny’s launches. Enjoy exploring the preview.',
      );
      return;
    }
    try {
      final live = api as OdooApi;
      live.page(
        path,
      ); // Reject links outside the configured origin before navigation.
      _webOpen = true;
      _revision++;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => WebsitePage(
            api: live,
            path: path,
            title: title,
            checkout: checkout,
          ),
        ),
      );
      _webOpen = false;
      if (mounted) await refresh();
    } catch (e) {
      if (mounted) toast(context, customerError(e));
    } finally {
      _webOpen = false;
    }
  }

  Future<void> signOut() async {
    _signingOut = true;
    _revision++;
    _refreshTimer?.cancel();
    try {
      await api.logout();
    } catch (_) {
      /* Local session is still cleared by OdooApi. */
    }
    try {
      if (Platform.isAndroid || Platform.isIOS) {
        await sessionChannel.invokeMethod<void>('clear');
      }
    } catch (_) {}
    if (mounted) widget.onLogout();
  }

  @override
  Widget build(BuildContext context) {
    const labels = ['Home', 'Order', 'Rewards', 'My card', 'You'];
    const icons = [
      Icons.home_outlined,
      Icons.restaurant_menu_rounded,
      Icons.card_giftcard_rounded,
      Icons.credit_card_rounded,
      Icons.person_outline_rounded,
    ];
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            if (api.isDemo)
              Container(
                width: double.infinity,
                color: cream,
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: const Text(
                  'PREVIEW  ·  SAMPLE ACCOUNT & MENU',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 8,
                    color: navy,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.3,
                  ),
                ),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 14, 16, 10),
              child: Row(
                children: [
                  const Brand(size: 44),
                  const SizedBox(width: 11),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Jenny’s',
                          style: TextStyle(
                            fontSize: 19,
                            fontWeight: FontWeight.w800,
                            color: ink,
                            height: 1.2,
                          ),
                        ),
                        Eyebrow('On the Boulevard'),
                      ],
                    ),
                  ),
                  IconButton(
                    tooltip: 'Messages',
                    onPressed: data == null ? null : inbox,
                    icon: Badge(
                      isLabelVisible:
                          (data?['messages'] as List<dynamic>? ?? []).any(
                            (m) => m['read'] == false,
                          ),
                      smallSize: 6,
                      backgroundColor: blue,
                      child: const Icon(
                        Icons.notifications_none_rounded,
                        color: ink,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            if (error != null)
              Material(
                color: const Color(0xFFFFF0EA),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 7,
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          error!,
                          style: const TextStyle(
                            fontSize: 11,
                            color: Color(0xFF903C28),
                          ),
                        ),
                      ),
                      TextButton(
                        onPressed: refresh,
                        child: const Text('Retry'),
                      ),
                      if (data == null || _sessionExpired)
                        TextButton(
                          onPressed: signOut,
                          child: const Text('Sign out'),
                        ),
                    ],
                  ),
                ),
              ),
            Expanded(
              child: loading
                  ? const LoadingSkeleton()
                  : data == null
                  ? EmptyState(
                      icon: Icons.cloud_off_outlined,
                      title: 'Let’s reconnect.',
                      detail:
                          'Your account is waiting. Check your connection and try again.',
                      action: 'Try again',
                      onTap: refresh,
                    )
                  : AnimatedSwitcher(
                      duration: MediaQuery.disableAnimationsOf(context)
                          ? Duration.zero
                          : const Duration(milliseconds: 240),
                      transitionBuilder: (child, animation) => FadeTransition(
                        opacity: animation,
                        child: SlideTransition(
                          position: Tween(
                            begin: const Offset(0, .025),
                            end: Offset.zero,
                          ).animate(animation),
                          child: child,
                        ),
                      ),
                      child: RefreshIndicator(
                        key: ValueKey(tab),
                        color: blue,
                        onRefresh: refresh,
                        child: [
                          home(),
                          menu(),
                          rewards(),
                          membership(),
                          profile(),
                        ][tab],
                      ),
                    ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(top: BorderSide(color: Color(0xFFE9EDF3))),
        ),
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(10, 8, 10, 7),
            child: Row(
              children: List.generate(
                5,
                (index) => Expanded(
                  child: Semantics(
                    selected: tab == index,
                    button: true,
                    label: labels[index],
                    child: InkWell(
                      borderRadius: BorderRadius.circular(18),
                      onTap: () => go(index),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 5),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 17,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: tab == index
                                    ? const Color(0xFFEAF0FC)
                                    : Colors.transparent,
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: Badge(
                                isLabelVisible: index == 1 && lines.isNotEmpty,
                                label: Text(
                                  '${lines.where((l) => l['editable'] == true).length}',
                                ),
                                child: Icon(
                                  icons[index],
                                  size: 22,
                                  color: tab == index ? blue : muted,
                                ),
                              ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              labels[index],
                              maxLines: 1,
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: tab == index
                                    ? FontWeight.w800
                                    : FontWeight.w600,
                                color: tab == index ? blue : muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget scroll(List<Widget> children) => ListView(
    key: PageStorageKey('jennys-tab-$tab'),
    padding: const EdgeInsets.fromLTRB(24, 16, 24, 28),
    physics: const AlwaysScrollableScrollPhysics(),
    children: children,
  );
  Widget heading(String eyebrow, String title, {Widget? trailing}) => Padding(
    padding: const EdgeInsets.only(bottom: 18),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Eyebrow(eyebrow),
              const SizedBox(height: 7),
              Text(title, style: Theme.of(context).textTheme.titleLarge),
            ],
          ),
        ),
        ?trailing,
      ],
    ),
  );
  Widget home() => scroll([
    const Eyebrow('A warm welcome back'),
    const SizedBox(height: 10),
    Text(
      'Make today\na Jenny’s day.',
      style: Theme.of(context).textTheme.headlineLarge,
    ),
    const SizedBox(height: 24),
    Material(
      color: navy,
      borderRadius: BorderRadius.circular(22),
      child: InkWell(
        key: const ValueKey('home-orders-bill'),
        onTap: orderHistory,
        borderRadius: BorderRadius.circular(22),
        child: const Padding(
          padding: EdgeInsets.all(20),
          child: Row(
            children: [
              Icon(Icons.receipt_long_outlined, color: Colors.white, size: 27),
              SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Your orders & bill',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    SizedBox(height: 5),
                    Text(
                      'Track your order. Pay when your bill is ready.',
                      style: TextStyle(color: Color(0xFFDCE5F4), fontSize: 12),
                    ),
                  ],
                ),
              ),
              SizedBox(width: 8),
              Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 21),
            ],
          ),
        ),
      ),
    ),
    const SizedBox(height: 16),
    GestureDetector(
      onTap: () => go(3),
      child: Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: cream,
          borderRadius: BorderRadius.circular(24),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Eyebrow(card?['name'] ?? 'Your membership', color: navy),
                  const SizedBox(height: 8),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.baseline,
                    textBaseline: TextBaseline.alphabetic,
                    children: [
                      Flexible(
                        child: Text(
                          card == null ? 'Welcome' : points(card!['points']),
                          style: const TextStyle(
                            fontSize: 33,
                            fontWeight: FontWeight.w800,
                            letterSpacing: -1.5,
                            color: navy,
                          ),
                        ),
                      ),
                      if (card != null) ...[
                        const SizedBox(width: 7),
                        const Text(
                          'points',
                          style: TextStyle(fontSize: 12, color: navy),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    card == null
                        ? 'Your card will appear here when it is ready.'
                        : 'A little thank you for every visit.',
                    style: const TextStyle(fontSize: 11, color: muted),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const CircleAvatar(
              radius: 24,
              backgroundColor: Color(0xFFEBD9B7),
              child: Icon(Icons.north_east_rounded, color: navy, size: 21),
            ),
          ],
        ),
      ),
    ),
    const SizedBox(height: 16),
    IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: quickAction(
              Icons.restaurant_menu_rounded,
              'Order your favourites',
              'Something delicious awaits',
              () => go(1),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: quickAction(
              Icons.credit_card_rounded,
              'Your Jenny’s card',
              'Made for every visit',
              () => go(3),
            ),
          ),
        ],
      ),
    ),
    const SizedBox(height: 30),
    heading(
      'At the Boulevard',
      'Always a good idea.',
      trailing: TextButton(
        onPressed: () => go(1),
        child: const Text('View menu', style: TextStyle(fontSize: 11)),
      ),
    ),
    ClipRRect(
      borderRadius: BorderRadius.circular(25),
      child: SizedBox(
        height: 310,
        child: Stack(
          fit: StackFit.expand,
          children: [
            Image.asset('assets/images/jennys-evening.jpg', fit: BoxFit.cover),
            const DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Colors.transparent, Color(0xED0B1D36)],
                  stops: [.2, 1],
                ),
              ),
            ),
            Positioned(
              left: 22,
              top: 21,
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 13,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: .95),
                  borderRadius: BorderRadius.circular(30),
                ),
                child: const Eyebrow('On the Boulevard', color: navy),
              ),
            ),
            Positioned(
              left: 24,
              right: 24,
              bottom: 22,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'The place you\ncome back to.',
                    style: TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                      fontSize: 28,
                      height: 1.15,
                      letterSpacing: -.8,
                    ),
                  ),
                  const SizedBox(height: 15),
                  TextButton(
                    style: TextButton.styleFrom(
                      padding: EdgeInsets.zero,
                      foregroundColor: gold,
                    ),
                    onPressed: () => go(1),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'Explore the menu',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        SizedBox(width: 15),
                        Icon(Icons.arrow_forward_rounded, size: 18),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
    const SizedBox(height: 24),
    const Center(child: Eyebrow('Good food. Great company. Since 1987.')),
  ]);
  Widget quickAction(
    IconData icon,
    String title,
    String detail,
    VoidCallback onTap,
  ) => Material(
    color: Colors.white,
    borderRadius: BorderRadius.circular(22),
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(22),
      child: Padding(
        padding: const EdgeInsets.all(17),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: blue, size: 25),
            const SizedBox(height: 17),
            Text(
              title,
              style: const TextStyle(
                fontWeight: FontWeight.w800,
                fontSize: 13,
                height: 1.45,
                color: ink,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              detail,
              style: const TextStyle(fontSize: 10, color: muted, height: 1.5),
            ),
          ],
        ),
      ),
    ),
  );

  Widget menu() {
    final categories = ['All', ...items.map((p) => '${p['category']}').toSet()];
    final filtered = items
        .where(
          (p) =>
              (category == 'All' || p['category'] == category) &&
              '${p['name']} ${p['description']}'.toLowerCase().contains(
                search.toLowerCase(),
              ),
        )
        .toList();
    return scroll([
      const Eyebrow('Made to be enjoyed'),
      const SizedBox(height: 10),
      Text(
        'What are you\ncraving today?',
        style: Theme.of(context).textTheme.headlineLarge,
      ),
      const SizedBox(height: 20),
      TextField(
        controller: searchController,
        onChanged: (value) => setState(() => search = value),
        decoration: InputDecoration(
          hintText: 'Find a favourite',
          prefixIcon: const Icon(Icons.search_rounded),
          suffixIcon: search.isEmpty
              ? null
              : IconButton(
                  tooltip: 'Clear search',
                  icon: const Icon(Icons.close_rounded),
                  onPressed: () {
                    searchController.clear();
                    setState(() => search = '');
                  },
                ),
        ),
      ),
      const SizedBox(height: 16),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: categories
              .map(
                (value) => Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(
                      value,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: category == value ? Colors.white : ink,
                      ),
                    ),
                    selected: category == value,
                    onSelected: (_) {
                      HapticFeedback.selectionClick();
                      setState(() => category = value);
                    },
                    selectedColor: blue,
                    backgroundColor: Colors.white,
                    showCheckmark: false,
                    side: BorderSide.none,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 9,
                    ),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(30),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
      ),
      const SizedBox(height: 24),
      if (filtered.isEmpty)
        const EmptyState(
          icon: Icons.restaurant_outlined,
          title: 'Something else in mind?',
          detail:
              'Try another search or category. Published items from Jenny’s menu will appear here.',
        ),
      ...filtered.map(
        (item) => Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: Material(
            color: Colors.white,
            borderRadius: BorderRadius.circular(22),
            child: InkWell(
              borderRadius: BorderRadius.circular(22),
              onTap: () => productSheet(item as Json),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(15),
                      child: FoodImage(
                        api: api,
                        path: '${item['image']}',
                        width: 92,
                        height: 111,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${item['name']}',
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w800,
                              color: ink,
                              height: 1.4,
                            ),
                          ),
                          const SizedBox(height: 5),
                          Text(
                            '${item['description']}',
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 10,
                              height: 1.5,
                              color: muted,
                            ),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            item['price'] == null
                                ? 'Order with our team'
                                : money(
                                    item['price'],
                                    item['currency'] as String? ?? 'TTD',
                                  ),
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w800,
                              color: navy,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 5),
                    IconButton(
                      tooltip: 'View ${item['name']}',
                      onPressed: () => productSheet(item),
                      style: IconButton.styleFrom(
                        backgroundColor: const Color(0xFFEEF3FC),
                        foregroundColor: blue,
                        minimumSize: const Size(44, 44),
                      ),
                      icon: const Icon(Icons.add_rounded, size: 21),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
      if (nextOffset != null)
        ActionButton(
          'Load more',
          onTap: loadMore,
          loading: loadingMore,
          icon: Icons.expand_more_rounded,
        ),
      if (lines.isNotEmpty || _pendingSubmission != null)
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: ActionButton(
            _pendingSubmission != null
                ? 'Check your last order'
                : 'View order · ${money(cart['total'], cart['currency'] as String? ?? 'TTD')}',
            onTap: cartSheet,
            icon: Icons.shopping_bag_outlined,
          ),
        ),
      const SizedBox(height: 12),
      Text(
        api.isDemo
            ? 'Sample menu and prices. Ordering is not available in the preview.'
            : 'Dine in with us. Order here and pay after your meal.',
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 10, color: muted),
      ),
    ]);
  }

  void productSheet(Json original) => showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    backgroundColor: paper,
    builder: (sheetContext) => ListenableBuilder(
      listenable: _sheetUpdates,
      builder: (context, _) {
        final matching = items.where((item) => item['id'] == original['id']);
        final unavailable = matching.isEmpty;
        final item = unavailable ? original : matching.first as Json;
        return StatefulBuilder(
          builder: (context, setLocal) => SafeArea(
            child: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(22),
                      child: FoodImage(
                        api: api,
                        path: '${item['image']}',
                        height: 230,
                        width: double.infinity,
                      ),
                    ),
                    const SizedBox(height: 24),
                    Eyebrow('${item['category']}'),
                    const SizedBox(height: 9),
                    Text(
                      '${item['name']}',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 12),
                    Text('${item['description']}'),
                    const SizedBox(height: 24),
                    ActionButton(
                      unavailable
                          ? 'Currently unavailable'
                          : item['direct_add'] == true
                          ? 'Add to order · ${money(item['price'], item['currency'] as String? ?? 'TTD')}'
                          : 'Order with our team',
                      loading: busy,
                      onTap: unavailable
                          ? null
                          : () async {
                              if (item['direct_add'] != true) {
                                toast(
                                  context,
                                  'Our team will help you choose the options for this item.',
                                );
                                return;
                              }
                              final future = mutate(
                                () => api.add(item),
                                success: 'Added to your order',
                              );
                              setLocal(() {});
                              await future;
                              if (sheetContext.mounted) {
                                Navigator.pop(sheetContext);
                              }
                            },
                    ),
                    const SizedBox(height: 8),
                    const Center(
                      child: Text(
                        'Have an allergy? Please speak to Jenny’s before ordering.',
                        style: TextStyle(fontSize: 10, color: muted),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    ),
  );

  void memberWallet() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => MemberWalletPage(
          api: api,
          announcements: customer['announcements'] != false,
        ),
      ),
    );
    if (mounted) await refresh();
  }

  Widget rewards() => scroll([
    const Eyebrow('A little thank you'),
    const SizedBox(height: 10),
    Text(
      'Good things\ncome back to you.',
      style: Theme.of(context).textTheme.headlineLarge,
    ),
    const SizedBox(height: 24),
    if (card != null)
      Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: navy,
          borderRadius: BorderRadius.circular(25),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Eyebrow('${card!['name']}', color: gold),
            const SizedBox(height: 14),
            Text(
              '${points(card!['points'])} points',
              style: const TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                letterSpacing: -1,
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Your next little moment of joy.',
              style: TextStyle(fontSize: 12, color: Color(0xFFBCCAE0)),
            ),
          ],
        ),
      ),
    const SizedBox(height: 28),
    if (api.isDemo || data?['capabilities']?['wallet'] == true)
      profileRow(
        Icons.card_giftcard_rounded,
        'Gifts & birthday treats',
        memberWallet,
      ),
    heading('Made for members', 'Your rewards'),
    if (cardRewards.isEmpty)
      const EmptyState(
        icon: Icons.card_giftcard_rounded,
        title: 'More to look forward to.',
        detail: 'Your available loyalty programs and rewards will appear here.',
      ),
    ...cardRewards.asMap().entries.map((entry) {
      final reward = entry.value as Json;
      return Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: Material(
          color: Colors.white,
          borderRadius: BorderRadius.circular(23),
          child: InkWell(
            borderRadius: BorderRadius.circular(23),
            onTap: () => rewardDetail(reward),
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Container(
                    width: 54,
                    height: 62,
                    decoration: BoxDecoration(
                      color: entry.key.isEven ? cream : const Color(0xFFEDF2FD),
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Icon(
                      entry.key.isEven
                          ? Icons.auto_awesome_outlined
                          : Icons.card_giftcard_rounded,
                      color: entry.key.isEven ? const Color(0xFF94753F) : blue,
                    ),
                  ),
                  const SizedBox(width: 17),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${reward['name']}',
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w800,
                            color: ink,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          '${points(reward['points'])} points',
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: blue,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right_rounded, color: muted),
                ],
              ),
            ),
          ),
        ),
      );
    }),
    const SizedBox(height: 8),
    const Text(
      'Ask our team to apply eligible rewards when you settle your bill. Availability depends on your order and the program terms.',
      style: TextStyle(fontSize: 11, height: 1.7, color: muted),
    ),
  ]);
  void rewardDetail(Json reward) => showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (context) => SafeArea(
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(28, 8, 28, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const CircleAvatar(
                radius: 30,
                backgroundColor: cream,
                child: Icon(Icons.card_giftcard_rounded, color: navy, size: 28),
              ),
              const SizedBox(height: 24),
              Text(
                '${reward['name']}',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 12),
              Eyebrow('${points(reward['points'])} points', color: blue),
              const SizedBox(height: 20),
              const Text(
                'Our team can apply this reward to an eligible bill. Your points update when your purchase or reward is processed under the program’s rules.',
              ),
              const SizedBox(height: 24),
              ActionButton(
                'Explore the menu',
                onTap: () {
                  Navigator.pop(context);
                  go(1);
                },
              ),
            ],
          ),
        ),
      ),
    ),
  );

  Widget membership() => scroll([
    const Eyebrow('Always welcome'),
    const SizedBox(height: 10),
    Text(
      'A little Jenny’s.\nJust for you.',
      style: Theme.of(context).textTheme.headlineLarge,
    ),
    const SizedBox(height: 24),
    if (cards.length > 1)
      Padding(
        padding: const EdgeInsets.only(bottom: 14),
        child: DropdownButtonFormField<int>(
          key: ValueKey(card?['id']),
          initialValue: card?['id'] as int?,
          isExpanded: true,
          decoration: const InputDecoration(labelText: 'Your cards'),
          items: cards
              .map(
                (entry) => DropdownMenuItem<int>(
                  value: entry['id'] as int,
                  child: Text('${entry['name']}'),
                ),
              )
              .toList(),
          onChanged: (value) {
            final index = cards.indexWhere((entry) => entry['id'] == value);
            if (index >= 0) setState(() => selectedCard = index);
          },
        ),
      ),
    if (card == null)
      const EmptyState(
        icon: Icons.credit_card_rounded,
        title: 'Your card is on its way.',
        detail:
            'Once Jenny’s links a loyalty card to your customer account, it will appear here.',
      )
    else ...[
      LoyaltyCardActions(
        key: ValueKey(card!['id']),
        card: card!,
        name: '${customer['name']}',
        isDemo: api.isDemo,
        onRefresh: refresh,
      ),
      if (card!['expires'] != null)
        Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Text(
            'Card expiry: ${dateLabel(card!['expires'])}',
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 11),
          ),
        ),
      const SizedBox(height: 28),
      profileRow(Icons.history_rounded, 'Recent activity', recentActivity),
    ],
  ]);
  void recentActivity() {
    unawaited(_autoRefresh());
    Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => RecentActivityPage(
          snapshot: () => data ?? {},
          updates: _sheetUpdates,
          onRefresh: () => refresh(),
          initialCardId: card?['id'] as int?,
        ),
      ),
    );
  }

  Widget profile() => scroll([
    const Eyebrow('Make yourself at home'),
    const SizedBox(height: 10),
    Text(
      '${customer['name'] ?? 'Welcome'}',
      style: Theme.of(context).textTheme.headlineMedium,
    ),
    const SizedBox(height: 8),
    Text('${customer['email'] ?? ''}', style: const TextStyle(fontSize: 12)),
    const SizedBox(height: 26),
    profileRow(Icons.history_rounded, 'Recent activity', recentActivity),
    if (api.isDemo || data?['capabilities']?['wallet'] == true)
      profileRow(
        Icons.card_giftcard_rounded,
        'Gifts & birthday treats',
        memberWallet,
      ),
    profileRow(Icons.receipt_long_outlined, 'Your orders', orderHistory),
    profileRow(Icons.mail_outline_rounded, 'Messages from Jenny’s', inbox),
    profileRow(Icons.tune_rounded, 'Communication preferences', preferences),
    profileRow(Icons.auto_awesome_outlined, 'Discover the app', () {
      Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (introContext) => AppIntroduction(
            replay: true,
            onFinish: (_) async => Navigator.of(introContext).pop(),
          ),
        ),
      );
    }),
    profileRow(
      Icons.account_circle_outlined,
      'Manage your account',
      () => openWeb('/my/home', 'Your account'),
    ),
    const SizedBox(height: 28),
    ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AspectRatio(
            aspectRatio: 1280 / 915,
            child: Image.asset(
              'assets/images/jennys-exterior.jpg',
              fit: BoxFit.cover,
            ),
          ),
          Container(
            color: Colors.white,
            padding: const EdgeInsets.all(20),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Eyebrow('Our home, since 1987'),
                SizedBox(height: 10),
                Text(
                  'On the Boulevard',
                  style: TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 18,
                    color: ink,
                  ),
                ),
                SizedBox(height: 6),
                Text(
                  '6 Cipriani Boulevard\nPort of Spain, Trinidad & Tobago',
                  style: TextStyle(fontSize: 11, height: 1.7),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
    const SizedBox(height: 22),
    TextButton(
      onPressed: signOut,
      child: Text(api.isDemo ? 'Leave preview' : 'Sign out'),
    ),
    const SizedBox(height: 12),
    const Center(child: Eyebrow('Jenny’s · Since 1987')),
  ]);
  Widget profileRow(IconData icon, String title, VoidCallback onTap) => Padding(
    padding: const EdgeInsets.only(bottom: 9),
    child: Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(18),
      child: ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        contentPadding: const EdgeInsets.symmetric(horizontal: 19, vertical: 4),
        leading: Icon(icon, color: blue, size: 23),
        title: Text(
          title,
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
        ),
        trailing: const Icon(
          Icons.chevron_right_rounded,
          color: muted,
          size: 21,
        ),
        onTap: onTap,
      ),
    ),
  );

  void inbox() => showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    builder: (context) => ListenableBuilder(
      listenable: _sheetUpdates,
      builder: (context, _) => SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'A little hello.',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 20),
                if ((data?['messages'] as List<dynamic>? ?? []).isEmpty)
                  const EmptyState(
                    icon: Icons.mail_outline_rounded,
                    title: 'All caught up.',
                    detail: 'News from Jenny’s will arrive here.',
                  ),
                ...(data?['messages'] as List<dynamic>? ?? []).map(
                  (m) => Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Material(
                      color: paper,
                      borderRadius: BorderRadius.circular(19),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(19),
                        onTap: () async {
                          try {
                            await _write(() => api.readMessage(m['id'] as int));
                            if (mounted) setState(() => m['read'] = true);
                            _notifySheets();
                          } catch (e) {
                            if (context.mounted) {
                              toast(context, customerError(e));
                            }
                          }
                        },
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '${m['name']}',
                                style: const TextStyle(
                                  fontWeight: FontWeight.w800,
                                  fontSize: 15,
                                  color: ink,
                                ),
                              ),
                              const SizedBox(height: 10),
                              Text(
                                '${m['body']}',
                                style: const TextStyle(
                                  fontSize: 12,
                                  height: 1.7,
                                ),
                              ),
                              const SizedBox(height: 12),
                              Eyebrow(dateLabel(m['date'])),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
  void preferences() {
    bool enabled = customer['promotional_email'] == true,
        smsEnabled = customer['promotional_sms'] == true,
        saving = false;
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => SafeArea(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Keep in touch.',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 20),
                  SwitchListTile.adaptive(
                    contentPadding: EdgeInsets.zero,
                    title: const Text(
                      'News & offers by email',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    subtitle: const Text(
                      'A little Jenny’s in your inbox. You can change this anytime.',
                      style: TextStyle(fontSize: 11),
                    ),
                    value: enabled,
                    onChanged: saving
                        ? null
                        : (value) => setLocal(() => enabled = value),
                  ),
                  if (api is OdooApi)
                    SwitchListTile.adaptive(
                      contentPadding: EdgeInsets.zero,
                      title: const Text(
                        'News & offers by text',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      value: smsEnabled,
                      onChanged: saving
                          ? null
                          : (value) => setLocal(() => smsEnabled = value),
                    ),
                  const SizedBox(height: 14),
                  const Text(
                    'You’ll still receive your order receipts and essential updates about your account.',
                    style: TextStyle(fontSize: 11),
                  ),
                  const SizedBox(height: 24),
                  ActionButton(
                    'Save preferences',
                    loading: saving,
                    icon: Icons.check_rounded,
                    onTap: () async {
                      setLocal(() => saving = true);
                      try {
                        await _write(
                          () => api is OdooApi
                              ? (api as OdooApi).accountPreferences(
                                  enabled,
                                  smsEnabled,
                                )
                              : api.preferences(enabled),
                        );
                        if (mounted) {
                          setState(() {
                            customer['promotional_email'] = enabled;
                            customer['promotional_sms'] = smsEnabled;
                          });
                        }
                        if (context.mounted) Navigator.pop(context);
                      } catch (e) {
                        if (context.mounted) {
                          toast(context, customerError(e));
                          setLocal(() => saving = false);
                        }
                      }
                    },
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _refreshOrders() async {
    if (_ordersReading || !_ordersOpen || _signingOut || _writes > 0) return;
    _ordersReading = true;
    final revision = _revision;
    try {
      final result = await api.orders();
      if (_canApply(revision) && _ordersOpen) {
        _orderData = result;
        _orderError = null;
        _notifySheets();
      }
    } catch (e) {
      if (_canApply(revision) && _ordersOpen && _orderData == null) {
        _orderError = customerError(e);
        _notifySheets();
      }
    } finally {
      _ordersReading = false;
    }
  }

  bool _startingPayment = false;

  Future<void> payOrder(Json order) async {
    if (_startingPayment || api is! OdooApi || order['id'] is! int) return;
    _startingPayment = true;
    _notifySheets();
    try {
      final path = await (api as OdooApi).paymentPage(order['id'] as int);
      if (!mounted || _signingOut) return;
      await openWeb(path, 'Pay your bill', checkout: true);
    } catch (e) {
      if (mounted) toast(context, customerError(e));
    } finally {
      _startingPayment = false;
      if (mounted) {
        await _refreshOrders();
        _notifySheets();
      }
    }
  }

  Future<void> orderHistory() async {
    _ordersOpen = true;
    _orderData = null;
    _orderError = null;
    unawaited(_refreshOrders());
    try {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (context) => Scaffold(
            appBar: AppBar(
              title: const Text('Your orders'),
              actions: [
                IconButton(
                  tooltip: 'Refresh orders',
                  onPressed: _refreshOrders,
                  icon: const Icon(Icons.refresh_rounded),
                ),
              ],
            ),
            body: ListenableBuilder(
              listenable: _sheetUpdates,
              builder: (context, _) {
                if (_orderData == null && _orderError == null) {
                  return const LoadingSkeleton();
                }
                if (_orderData == null && _orderError != null) {
                  return EmptyState(
                    icon: Icons.cloud_off_outlined,
                    title: 'Couldn’t load your orders.',
                    detail: _orderError!,
                    action: 'Try again',
                    onTap: _refreshOrders,
                  );
                }
                final orders = _orderData ?? [];
                if (orders.isEmpty) {
                  return const EmptyState(
                    icon: Icons.shopping_bag_outlined,
                    title: 'Your next favourite awaits.',
                    detail:
                        'Your dine-in orders and open bills will appear here.',
                  );
                }
                return ListView(
                  padding: const EdgeInsets.all(24),
                  children: orders
                      .map(
                        (o) => OrderStatusCard(
                          key: ValueKey(o['name']),
                          order: o as Json,
                          onPay: api is OdooApi ? () => payOrder(o) : null,
                          paymentBusy: _startingPayment,
                        ),
                      )
                      .toList(),
                );
              },
            ),
          ),
        ),
      );
    } finally {
      _ordersOpen = false;
    }
  }

  Widget totalRow(String label, dynamic amount, {bool strong = false}) => Row(
    children: [
      Expanded(
        child: Text(
          label,
          style: TextStyle(
            fontSize: strong ? 18 : 12,
            color: strong ? ink : muted,
            fontWeight: strong ? FontWeight.w800 : FontWeight.w500,
          ),
        ),
      ),
      const SizedBox(width: 16),
      Flexible(
        child: Text(
          money(amount, cart['currency'] as String? ?? 'TTD'),
          textAlign: TextAlign.right,
          style: TextStyle(
            fontSize: strong ? 20 : 13,
            color: ink,
            fontWeight: strong ? FontWeight.w800 : FontWeight.w700,
          ),
        ),
      ),
    ],
  );

  void cartSheet() => showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    isScrollControlled: true,
    backgroundColor: paper,
    builder: (sheetContext) => ListenableBuilder(
      listenable: _sheetUpdates,
      builder: (context, _) => StatefulBuilder(
        builder: (context, setLocal) => SafeArea(
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.sizeOf(context).height * .82,
            ),
            child: SingleChildScrollView(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 28),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Eyebrow('Something to look forward to'),
                    const SizedBox(height: 8),
                    Text(
                      'Your order',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 20),
                    if (_submissionMessage != null || cart['warning'] != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 18),
                        child: Text(
                          _submissionMessage ??
                              customerMessage(cart['warning']),
                          style: const TextStyle(
                            fontSize: 12,
                            color: blue,
                            height: 1.6,
                          ),
                        ),
                      ),
                    if (lines.isEmpty && _pendingSubmission == null)
                      const EmptyState(
                        icon: Icons.shopping_bag_outlined,
                        title: 'Room for a favourite.',
                        detail: 'Add something from the menu to get started.',
                      ),
                    ...lines.map(
                      (line) => Padding(
                        padding: const EdgeInsets.only(bottom: 18),
                        child: Row(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(13),
                              child: FoodImage(
                                api: api,
                                path: '${line['image']}',
                                width: 58,
                                height: 64,
                              ),
                            ),
                            const SizedBox(width: 13),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '${line['name']}${line['available'] == false ? ' · unavailable' : ''}',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w800,
                                      color: ink,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    money(
                                      line['total'],
                                      cart['currency'] as String? ?? 'TTD',
                                    ),
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: blue,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  if (line['editable'] == true)
                                    Row(
                                      mainAxisSize: MainAxisSize.min,
                                      children: [
                                        IconButton(
                                          tooltip: 'Decrease ${line['name']}',
                                          onPressed:
                                              busy || _pendingSubmission != null
                                              ? null
                                              : () async {
                                                  final task = mutate(
                                                    () => api.update(
                                                      line['id'] as int,
                                                      (line['qty'] as num) - 1,
                                                    ),
                                                  );
                                                  setLocal(() {});
                                                  await task;
                                                  if (context.mounted) {
                                                    setLocal(() {});
                                                  }
                                                },
                                          icon: const Icon(
                                            Icons.remove_rounded,
                                            size: 17,
                                          ),
                                        ),
                                        Text(
                                          points(line['qty']),
                                          style: const TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w800,
                                          ),
                                        ),
                                        IconButton(
                                          tooltip: 'Increase ${line['name']}',
                                          onPressed:
                                              busy ||
                                                  _pendingSubmission != null ||
                                                  (line['qty'] as num) >= 99
                                              ? null
                                              : () async {
                                                  final task = mutate(
                                                    () => api.update(
                                                      line['id'] as int,
                                                      (line['qty'] as num) + 1,
                                                    ),
                                                  );
                                                  setLocal(() {});
                                                  await task;
                                                  if (context.mounted) {
                                                    setLocal(() {});
                                                  }
                                                },
                                          icon: const Icon(
                                            Icons.add_rounded,
                                            size: 17,
                                          ),
                                        ),
                                      ],
                                    ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    if (lines.isNotEmpty) ...[
                      const Divider(height: 32),
                      totalRow('Subtotal', cart['subtotal']),
                      const SizedBox(height: 10),
                      totalRow(api.isDemo ? 'Sample tax' : 'Tax', cart['tax']),
                      const SizedBox(height: 17),
                      totalRow('Total', cart['total'], strong: true),
                      const SizedBox(height: 24),
                    ],
                    if (lines.isNotEmpty || _pendingSubmission != null) ...[
                      ActionButton(
                        _pendingSubmission != null
                            ? 'Check order again'
                            : api.isDemo
                            ? 'Send sample order'
                            : 'Place order',
                        loading: busy,
                        onTap:
                            busy ||
                                (_pendingSubmission == null &&
                                    cart['can_submit'] != true)
                            ? null
                            : () => submitOrder(sheetContext),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        api.isDemo
                            ? 'Preview only. No payment is taken.'
                            : 'Our team will confirm your table and prepare your order. Pay after your meal; eligible rewards are applied with our team.',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 11,
                          color: muted,
                          height: 1.6,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    ),
  );
}

class LoyaltyCardActions extends StatefulWidget {
  final Json card;
  final String name;
  final bool isDemo;
  final Future<void> Function() onRefresh;
  const LoyaltyCardActions({
    super.key,
    required this.card,
    required this.name,
    required this.isDemo,
    required this.onRefresh,
  });
  @override
  State<LoyaltyCardActions> createState() => _LoyaltyCardActionsState();
}

class _LoyaltyCardActionsState extends State<LoyaltyCardActions> {
  bool showBack = false;
  final display = CardDisplayLease();
  String get code => widget.card['number'] as String? ?? '';
  @override
  void dispose() {
    display.setVisible(false);
    super.dispose();
  }

  void flip() {
    HapticFeedback.lightImpact();
    setState(() => showBack = !showBack);
    display.setVisible(showBack);
    if (!showBack) widget.onRefresh();
  }

  Future<void> enlarge() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => LoyaltyScanPage(
          code: code,
          program: '${widget.card['name']}',
          customer: widget.name,
          isDemo: widget.isDemo,
        ),
      ),
    );
    if (mounted) await widget.onRefresh();
  }

  Widget get reverse => Semantics(
    label: 'Jenny’s membership card, barcode side',
    child: Container(
      key: const ValueKey('loyalty-card-back'),
      constraints: const BoxConstraints(minHeight: 232),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(23),
        boxShadow: [
          BoxShadow(
            color: navy.withValues(alpha: .18),
            blurRadius: 28,
            offset: const Offset(0, 13),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 13),
            decoration: const BoxDecoration(
              gradient: LinearGradient(colors: [blue, navy]),
            ),
            child: const Row(
              children: [
                Brand(size: 30),
                Spacer(),
                Eyebrow('Made for every visit', color: gold),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            widget.isDemo
                ? 'PREVIEW CARD · NOT VALID AT THE TILL'
                : 'SHOW TO THE TEAM BEFORE YOU PAY',
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: muted,
              fontSize: 9,
              fontWeight: FontWeight.w700,
              letterSpacing: .5,
            ),
          ),
          LoyaltyBarcode(code: code, height: 70),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18),
            child: SelectableText(
              code,
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: navy,
                fontWeight: FontWeight.w800,
                fontSize: 14,
                letterSpacing: 1.5,
              ),
            ),
          ),
          const SizedBox(height: 6),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 0, 18, 14),
            child: Text(
              widget.name,
              textAlign: TextAlign.center,
              style: const TextStyle(color: muted, fontSize: 10),
            ),
          ),
        ],
      ),
    ),
  );
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      LoyaltyCardFlip(
        front: LoyaltyCard(card: widget.card, name: widget.name),
        back: reverse,
        showBack: showBack,
      ),
      const SizedBox(height: 16),
      FilledButton.icon(
        onPressed: flip,
        icon: Icon(showBack ? Icons.flip_rounded : Icons.barcode_reader),
        label: Text(showBack ? 'Show card front' : 'Scan at Jenny’s'),
      ),
      const SizedBox(height: 8),
      OutlinedButton.icon(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(double.infinity, 52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
          side: const BorderSide(color: Color(0xFFDCE3EF)),
        ),
        onPressed: showBack
            ? enlarge
            : () async {
                await Clipboard.setData(ClipboardData(text: code));
                if (context.mounted) toast(context, 'Card number copied');
              },
        icon: Icon(
          showBack ? Icons.fullscreen_rounded : Icons.copy_rounded,
          size: 18,
        ),
        label: Text(
          showBack ? 'Enlarge barcode' : 'Copy card number',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
        ),
      ),
      const SizedBox(height: 13),
      Text(
        showBack
            ? 'Show this barcode before you pay. Turn your card back to refresh your points.'
            : 'Have your card scanned before you pay to collect points on eligible purchases.',
        textAlign: TextAlign.center,
        style: const TextStyle(fontSize: 11, height: 1.7, color: muted),
      ),
    ],
  );
}

class LoyaltyCard extends StatelessWidget {
  final Json card;
  final String name;
  const LoyaltyCard({super.key, required this.card, required this.name});
  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Jenny’s membership card',
    child: Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(23),
        boxShadow: [
          BoxShadow(
            color: navy.withValues(alpha: .22),
            blurRadius: 28,
            offset: const Offset(0, 13),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(23),
        child: Container(
          constraints: const BoxConstraints(minHeight: 232),
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [Color(0xFF244E9D), Color(0xFF152E5B), Color(0xFF0F2140)],
            ),
          ),
          child: Stack(
            children: [
              Positioned.fill(child: CustomPaint(painter: CardLines())),
              Padding(
                padding: const EdgeInsets.all(23),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Row(
                      children: [
                        Brand(size: 44),
                        Spacer(),
                        Eyebrow('The Jenny’s card', color: gold),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Text(
                      '${card['name']}',
                      style: const TextStyle(
                        color: Color(0xFFDCE5F6),
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 6),
                    SelectableText(
                      '${card['number']}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        letterSpacing: 2.1,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 15),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Eyebrow(
                                'Cardholder',
                                color: Color(0xFFAFBED8),
                              ),
                              const SizedBox(height: 5),
                              Text(
                                name,
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            const Eyebrow(
                              'Your points',
                              color: Color(0xFFAFBED8),
                            ),
                            const SizedBox(height: 5),
                            Text(
                              points(card['points']),
                              style: const TextStyle(
                                color: gold,
                                fontWeight: FontWeight.w800,
                                fontSize: 15,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class CardLines extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = gold.withValues(alpha: .12)
      ..style = PaintingStyle.stroke
      ..strokeWidth = .7;
    for (var i = 0; i < 9; i++) {
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(size.width * 1.05, size.height * .08),
          width: 110 + i * 34,
          height: 150 + i * 34,
        ),
        paint,
      );
    }
    canvas.drawLine(
      Offset(23, size.height - 67),
      Offset(size.width - 23, size.height - 67),
      Paint()
        ..color = Colors.white.withValues(alpha: .12)
        ..strokeWidth = .7,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class FoodImage extends StatelessWidget {
  final MobileApi api;
  final String path;
  final double width, height;
  const FoodImage({
    super.key,
    required this.api,
    required this.path,
    required this.width,
    required this.height,
  });
  Widget fallback() => Container(
    width: width,
    height: height,
    color: cream,
    child: const Icon(Icons.restaurant_rounded, color: muted),
  );
  @override
  Widget build(BuildContext context) {
    if (api.isDemo) {
      return Image.asset(
        'assets/images/$path',
        width: width,
        height: height,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => fallback(),
      );
    }
    try {
      final live = api as OdooApi;
      // Published product images are public. Do not put customer session cookies into image requests.
      return Image.network(
        live.page(path).toString(),
        width: width,
        height: height,
        fit: BoxFit.cover,
        errorBuilder: (_, _, _) => fallback(),
        loadingBuilder: (context, child, progress) => progress == null
            ? child
            : Container(width: width, height: height, color: cream),
      );
    } catch (_) {
      return fallback();
    }
  }
}

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title, detail;
  final String? action;
  final VoidCallback? onTap;
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.detail,
    this.action,
    this.onTap,
  });
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 34, horizontal: 14),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        CircleAvatar(
          radius: 33,
          backgroundColor: cream,
          child: Icon(icon, color: blue, size: 27),
        ),
        const SizedBox(height: 20),
        Text(
          title,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 10),
        Text(
          detail,
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 12, height: 1.7, color: muted),
        ),
        if (action != null) ...[
          const SizedBox(height: 16),
          TextButton(onPressed: onTap, child: Text(action!)),
        ],
      ],
    ),
  );
}

class LoadingSkeleton extends StatefulWidget {
  const LoadingSkeleton({super.key});
  @override
  State<LoadingSkeleton> createState() => _LoadingSkeletonState();
}

class _LoadingSkeletonState extends State<LoadingSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat(reverse: true);
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Semantics(
    label: 'Loading your Jenny’s account',
    child: AnimatedBuilder(
      animation: controller,
      builder: (context, _) => Opacity(
        opacity: MediaQuery.disableAnimationsOf(context)
            ? .8
            : .45 + controller.value * .45,
        child: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            for (final h in [26.0, 64.0, 148.0, 100.0, 260.0])
              Container(
                height: h,
                margin: const EdgeInsets.only(bottom: 19),
                decoration: BoxDecoration(
                  color: const Color(0xFFE1E6EF),
                  borderRadius: BorderRadius.circular(23),
                ),
              ),
          ],
        ),
      ),
    ),
  );
}

class WebsitePage extends StatefulWidget {
  final OdooApi api;
  final String path, title;
  final bool checkout;
  const WebsitePage({
    super.key,
    required this.api,
    required this.path,
    required this.title,
    this.checkout = false,
  });
  @override
  State<WebsitePage> createState() => _WebsitePageState();
}

class _WebsitePageState extends State<WebsitePage> {
  WebViewController? controller;
  String? error;
  String host = '';
  int progress = 0;
  @override
  void initState() {
    super.initState();
    start();
  }

  Future<void> start() async {
    try {
      final uri = widget.api.page(widget.path);
      host = uri.host;
      if (!Platform.isAndroid && !Platform.isIOS) {
        throw AppError('Account pages are not available on this device yet.');
      }
      // Native cookie stores set Secure, HttpOnly and SameSite before navigation.
      await sessionChannel.invokeMethod<void>('set', {
        'origin': widget.api.origin.toString(),
        'session': widget.api.sessionId,
      });
      final web = WebViewController()
        ..setJavaScriptMode(JavaScriptMode.unrestricted)
        ..setBackgroundColor(Colors.white)
        ..setNavigationDelegate(
          NavigationDelegate(
            onProgress: (value) {
              if (mounted) setState(() => progress = value);
            },
            onNavigationRequest: (request) {
              final uri = Uri.tryParse(request.url);
              if (uri?.scheme != 'https' && request.url != 'about:blank') {
                return NavigationDecision.prevent;
              }
              // HTTPS payment-provider redirects work normally; cookies remain host-scoped.
              if (mounted &&
                  request.isMainFrame &&
                  uri?.host.isNotEmpty == true) {
                setState(() => host = uri!.host);
              }
              return NavigationDecision.navigate;
            },
            onWebResourceError: (event) {
              if (mounted && event.isForMainFrame == true) {
                setState(
                  () => error =
                      'This page couldn’t load. Check your connection and try again.',
                );
              }
            },
          ),
        )
        ..loadRequest(uri);
      if (mounted) setState(() => controller = web);
    } catch (e) {
      if (mounted) setState(() => error = customerError(e));
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    bottomNavigationBar: widget.checkout
        ? SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: FilledButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Back to my orders'),
              ),
            ),
          )
        : null,
    appBar: AppBar(
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.title,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
          ),
          Text(host, style: const TextStyle(fontSize: 10, color: muted)),
        ],
      ),
      actions: [
        IconButton(
          tooltip: 'Reload page',
          onPressed: () {
            setState(() => error = null);
            controller?.reload();
          },
          icon: const Icon(Icons.refresh_rounded),
        ),
      ],
    ),
    body: SafeArea(
      child: Column(
        children: [
          if (progress < 100 && error == null)
            LinearProgressIndicator(value: progress / 100, minHeight: 2),
          Expanded(
            child: error != null
                ? EmptyState(
                    icon: Icons.cloud_off_outlined,
                    title: 'Let’s try that again.',
                    detail: error!,
                    action: 'Reload',
                    onTap: () {
                      setState(() => error = null);
                      if (controller == null) {
                        start();
                      } else {
                        controller!.reload();
                      }
                    },
                  )
                : controller == null
                ? const LoadingSkeleton()
                : WebViewWidget(controller: controller!),
          ),
        ],
      ),
    ),
  );
}
