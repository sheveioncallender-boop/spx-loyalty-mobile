part of 'main.dart';

/// All monetary values below come from native card records. No local deductions.
class MemberWalletPage extends StatefulWidget {
  final MobileApi api;
  final bool announcements;
  const MemberWalletPage({
    super.key,
    required this.api,
    this.announcements = true,
  });
  @override
  State<MemberWalletPage> createState() => _MemberWalletPageState();
}

class _MemberWalletPageState extends State<MemberWalletPage>
    with WidgetsBindingObserver {
  Json? wallet;
  String? error;
  bool busy = false, _loading = false;
  late bool announcements;
  Timer? _timer;
  final List<Json> _demoGifts = [
    {
      'id': 101,
      'name': 'Jenny’s Gift Card',
      'number': '044-demo-gift',
      'balance': 250.0,
      'currency': 'TTD',
      'expires': null,
      'state': 'active',
      'can_send': true,
    },
  ];
  final List<Json> _demoSent = [];

  @override
  void initState() {
    super.initState();
    announcements = widget.announcements;
    WidgetsBinding.instance.addObserver(this);
    unawaited(load());
    _timer = Timer.periodic(const Duration(seconds: 15), (_) {
      if (WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed &&
          (ModalRoute.of(context)?.isCurrent ?? false)) {
        unawaited(load());
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) unawaited(load());
  }

  Future<void> load() async {
    if (_loading || busy) return;
    _loading = true;
    try {
      final Json result;
      if (widget.api is OdooApi) {
        result =
            await (widget.api as OdooApi).rpc('/spx/mobile/v1/wallet') as Json;
      } else {
        result = {
          'gift_cards': _demoGifts,
          'sent_gifts': _demoSent,
          'birthday_credits': [
            {
              'id': 102,
              'name': 'Your birthday treat',
              'number': '044-demo-birthday',
              'balance': 100.0,
              'currency': 'TTD',
              'state': 'active',
              'expires': DateTime.now()
                  .add(const Duration(days: 20))
                  .toIso8601String(),
            },
          ],
          'products': [
            {'id': 1, 'name': 'A Jenny’s gift card', 'path': '/shop'},
          ],
        };
      }
      if (mounted) {
        setState(() {
          wallet = result;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = customerError(e));
    } finally {
      _loading = false;
    }
  }

  List<Json> rows(String key) =>
      (wallet?[key] as List<dynamic>? ?? []).cast<Json>();
  String value(Json c) =>
      '${c['currency'] ?? 'TTD'} ${(c['balance'] as num? ?? 0).toStringAsFixed(2)}';

  Future<void> purchase(Json product) async {
    if (widget.api is! OdooApi) {
      toast(
        context,
        'Preview only. Purchases use secure checkout in the connected app.',
      );
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => WebsitePage(
          api: widget.api as OdooApi,
          path: '${product['path']}',
          title: 'Buy a gift card',
        ),
      ),
    );
    await load();
  }

  Future<void> sendGift(Json card) async {
    final sent = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => SendGiftPage(api: widget.api, card: card),
      ),
    );
    if (!mounted) return;
    if (sent == true && widget.api.isDemo) {
      _demoGifts.removeWhere((c) => c['id'] == card['id']);
      _demoSent.add({'email': 'Preview recipient', 'state': 'preview'});
    }
    await load();
  }

  Future<void> showCard(Json card) async {
    // Re-read before showing a redeemable code; do not display a stale balance
    // after a transfer or expiry while the app was in the background.
    await load();
    if (!mounted || error != null) return;
    final current = [
      ...rows('gift_cards'),
      ...rows('birthday_credits'),
    ].where((c) => c['id'] == card['id'] && c['state'] == 'active');
    if (current.isEmpty) {
      toast(context, 'This card is no longer available.');
      return;
    }
    final c = current.first;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (ctx) => SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 8, 24, 30),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '${c['name']}',
                style: Theme.of(ctx).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 14),
              Text(
                value(c),
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  fontSize: 28,
                  color: blue,
                ),
              ),
              const SizedBox(height: 24),
              LoyaltyBarcode(code: '${c['number']}'),
              SelectableText(
                '${c['number']}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 18),
              const Text(
                'Show this code when you pay at Jenny’s, or enter it at online checkout.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              TextButton.icon(
                onPressed: () async {
                  await Clipboard.setData(
                    ClipboardData(text: '${c['number']}'),
                  );
                  if (ctx.mounted) toast(ctx, 'Gift card code copied.');
                },
                icon: const Icon(Icons.copy_rounded),
                label: const Text('Copy code'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget cardTile(Json c, {bool birthday = false}) {
    final active = c['state'] == 'active';
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: birthday ? cream : navy,
        borderRadius: BorderRadius.circular(25),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                birthday ? Icons.cake_outlined : Icons.card_giftcard_rounded,
                color: birthday ? blue : gold,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  birthday ? 'A birthday treat' : '${c['name']}',
                  style: TextStyle(
                    color: birthday ? navy : Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Text(
            value(c),
            style: TextStyle(
              fontSize: 30,
              fontWeight: FontWeight.w800,
              color: birthday ? navy : Colors.white,
              letterSpacing: -0.8,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            c['state'] == 'expired'
                ? 'Expired'
                : c['state'] == 'empty'
                ? 'Fully used'
                : c['expires'] == null
                ? 'Ready for your next visit'
                : 'Valid through ${dateLabel(c['expires'])}',
            style: TextStyle(
              fontSize: 12,
              color: birthday ? muted : const Color(0xFFCED8EA),
            ),
          ),
          if (active) ...[
            const SizedBox(height: 22),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: birthday ? blue : Colors.white,
                    foregroundColor: birthday ? Colors.white : navy,
                  ),
                  onPressed: busy ? null : () => showCard(c),
                  icon: const Icon(Icons.barcode_reader),
                  label: const Text('Use card'),
                ),
                if (!birthday && c['can_send'] != false)
                  TextButton.icon(
                    style: TextButton.styleFrom(foregroundColor: Colors.white),
                    onPressed: busy ? null : () => sendGift(c),
                    icon: const Icon(Icons.redeem_rounded),
                    label: const Text('Send as a gift'),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: paper,
    appBar: AppBar(title: const Text('Gifts & birthday treats')),
    body: RefreshIndicator(
      onRefresh: load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(24, 18, 24, 40),
        children: [
          if (widget.api.isDemo)
            const Padding(
              padding: EdgeInsets.only(bottom: 16),
              child: Text(
                'PREVIEW · SAMPLE BALANCES',
                style: TextStyle(color: muted, fontSize: 11),
              ),
            ),
          const Eyebrow('Little moments. Lovely gifts.'),
          const SizedBox(height: 12),
          Text(
            'Share a little\nJenny’s.',
            style: Theme.of(context).textTheme.headlineLarge,
          ),
          const SizedBox(height: 14),
          const Text(
            'Your gift cards and birthday treats appear here automatically when they’re linked to your account.',
          ),
          const SizedBox(height: 28),
          if (busy) const LinearProgressIndicator(),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Column(
                children: [
                  Text(error!, textAlign: TextAlign.center),
                  TextButton(onPressed: load, child: const Text('Try again')),
                ],
              ),
            ),
          if (wallet == null && error == null)
            const Center(child: CircularProgressIndicator()),
          ...rows('birthday_credits').map((c) => cardTile(c, birthday: true)),
          ...rows('gift_cards').map(cardTile),
          if (wallet != null && rows('gift_cards').isEmpty)
            const EmptyState(
              icon: Icons.card_giftcard_rounded,
              title: 'Something lovely to give.',
              detail:
                  'Cards from Jenny’s and gifts sent to your account appear here automatically. No code to enter.',
            ),
          if (wallet != null) ...[
            const SizedBox(height: 28),
            Text(
              'Give the gift of Jenny’s',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 12),
            const Text(
              'Buy a gift card for yourself or someone special. After payment, it appears here. Choose Send as a gift to deliver it to their email and Jenny’s account.',
              style: TextStyle(fontSize: 12, height: 1.7),
            ),
            const SizedBox(height: 16),
            if (rows('products').isEmpty)
              const Text(
                'Gift cards are available from our team at Jenny’s.',
                style: TextStyle(color: muted),
              ),
            ...rows('products').map(
              (p) => Card(
                child: ListTile(
                  title: Text('${p['name']}'),
                  subtitle: const Text('Choose your gift at secure checkout'),
                  trailing: const Icon(Icons.arrow_forward_rounded),
                  onTap: () => purchase(p),
                ),
              ),
            ),
            if (rows('sent_gifts').isNotEmpty) ...[
              const SizedBox(height: 24),
              Text(
                'Gifts you’ve sent',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              ...rows('sent_gifts').map(
                (g) => ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.redeem_rounded, color: blue),
                  title: Text('${g['email']}'),
                  subtitle: Text(
                    g['state'] == 'sent'
                        ? 'Email sent'
                        : g['state'] == 'failed'
                        ? 'Email delivery needs help — contact Jenny’s'
                        : g['state'] == 'preview'
                        ? 'Preview only — no email sent'
                        : 'Email queued',
                  ),
                ),
              ),
            ],
            const SizedBox(height: 28),
            SwitchListTile.adaptive(
              contentPadding: EdgeInsets.zero,
              title: const Text('Events at Jenny’s'),
              subtitle: const Text(
                'Karaoke, Latin Nights and special events in your app inbox.',
              ),
              value: announcements,
              onChanged: busy
                  ? null
                  : (value) async {
                      setState(() => busy = true);
                      try {
                        if (widget.api is OdooApi) {
                          await (widget.api as OdooApi).rpc(
                            '/spx/mobile/v1/announcements/preference',
                            {'enabled': value},
                          );
                        }
                        if (mounted) setState(() => announcements = value);
                      } catch (e) {
                        if (context.mounted) toast(context, customerError(e));
                      } finally {
                        if (mounted) setState(() => busy = false);
                      }
                    },
            ),
            const SizedBox(height: 18),
            const Text(
              'Balances and availability are confirmed when you pay. Gift cards and birthday credit are separate from your loyalty points.',
              style: TextStyle(color: muted, fontSize: 11, height: 1.7),
            ),
          ],
        ],
      ),
    ),
  );
}

class SendGiftPage extends StatefulWidget {
  final MobileApi api;
  final Json card;
  const SendGiftPage({super.key, required this.api, required this.card});
  @override
  State<SendGiftPage> createState() => _SendGiftPageState();
}

class _SendGiftPageState extends State<SendGiftPage> {
  final form = GlobalKey<FormState>();
  final name = TextEditingController(),
      email = TextEditingController(),
      message = TextEditingController();
  late final String requestKey =
      'gift-${DateTime.now().microsecondsSinceEpoch}-${math.Random.secure().nextInt(1 << 32)}';
  bool busy = false, _submitted = false;
  String? error;
  @override
  void dispose() {
    name.dispose();
    email.dispose();
    message.dispose();
    super.dispose();
  }

  Future<void> send() async {
    if (busy || !form.currentState!.validate()) return;
    final yes = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Send this gift?'),
        content: Text(
          'This transfers the full remaining card balance to ${email.text.trim()}. It will no longer be available in your cards.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Not yet'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Send gift'),
          ),
        ],
      ),
    );
    if (yes != true || !mounted) return;
    setState(() {
      busy = true;
      error = null;
      _submitted = true;
    });
    try {
      if (widget.api is OdooApi) {
        await (widget.api as OdooApi).rpc('/spx/mobile/v1/gifts/send', {
          'card_id': widget.card['id'],
          'recipient_name': name.text.trim(),
          'recipient_email': email.text.trim(),
          'message': message.text.trim(),
          'key': requestKey,
        });
      }
      if (mounted) {
        toast(
          context,
          widget.api.isDemo
              ? 'Preview only — no email sent.'
              : 'Your gift email has been queued.',
        );
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) setState(() => error = customerError(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('A gift, from you')),
    body: Form(
      key: form,
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const Eyebrow('Make someone’s day'),
          const SizedBox(height: 12),
          Text(
            'Good moments\nare better shared.',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 20),
          Text(
            '${widget.card['currency']} ${(widget.card['balance'] as num).toStringAsFixed(2)}',
            style: const TextStyle(
              color: blue,
              fontWeight: FontWeight.w800,
              fontSize: 28,
            ),
          ),
          const SizedBox(height: 26),
          TextFormField(
            controller: name,
            readOnly: busy || _submitted,
            maxLength: 100,
            decoration: const InputDecoration(labelText: 'Their name'),
            validator: (v) =>
                v == null || v.trim().isEmpty ? 'Enter their name.' : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: email,
            readOnly: busy || _submitted,
            keyboardType: TextInputType.emailAddress,
            autocorrect: false,
            decoration: const InputDecoration(labelText: 'Their email'),
            validator: (v) =>
                v == null ||
                    !RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(v.trim())
                ? 'Enter their email address.'
                : null,
          ),
          const SizedBox(height: 22),
          TextFormField(
            controller: message,
            readOnly: busy || _submitted,
            maxLines: 4,
            maxLength: 500,
            decoration: const InputDecoration(
              labelText: 'Your message (optional)',
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Your gift appears automatically in their Jenny’s account and arrives by email. If they’re new here, they can sign up with that same email. They can also present the email at Jenny’s.',
            style: TextStyle(fontSize: 12, height: 1.7),
          ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Text(error!, style: const TextStyle(color: Colors.red)),
            ),
          const SizedBox(height: 20),
          FilledButton(
            onPressed: busy ? null : send,
            child: busy
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(_submitted ? 'Retry sending' : 'Review & send'),
          ),
          if (_submitted && !busy)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Text(
                'Details are locked for a safe retry. Return to your cards to start a different gift.',
                style: TextStyle(color: muted, fontSize: 11),
              ),
            ),
        ],
      ),
    ),
  );
}
