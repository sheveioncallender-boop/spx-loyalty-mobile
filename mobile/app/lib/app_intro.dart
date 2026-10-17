part of 'main.dart';

/// Presentation preference only. Account/session storage remains separate.
class IntroStore {
  const IntroStore();
  static const channel = MethodChannel('net.spxcorp.jennys/experience');
  Future<bool> hasSeen() async {
    try {
      return await channel
              .invokeMethod<bool>('hasSeenIntroduction')
              .timeout(const Duration(seconds: 2)) ??
          false;
    } catch (_) {
      return false;
    }
  }

  Future<void> complete() async {
    try {
      await channel
          .invokeMethod<void>('completeIntroduction')
          .timeout(const Duration(seconds: 2));
    } catch (_) {
      // A presentation preference must never prevent entry to an account.
    }
  }
}

enum IntroAction { skip, signup, signin }

class LaunchLoading extends StatelessWidget {
  const LaunchLoading({super.key});
  @override
  Widget build(BuildContext context) => AnnotatedRegion<SystemUiOverlayStyle>(
    value: SystemUiOverlayStyle.light.copyWith(systemNavigationBarColor: navy),
    child: const Scaffold(
      backgroundColor: navy,
      body: Center(child: Brand(size: 110)),
    ),
  );
}

class AppIntroduction extends StatefulWidget {
  final Future<void> Function(IntroAction) onFinish;
  final bool replay;
  const AppIntroduction({
    super.key,
    required this.onFinish,
    this.replay = false,
  });
  @override
  State<AppIntroduction> createState() => _AppIntroductionState();
}

class _AppIntroductionState extends State<AppIntroduction> {
  final controller = PageController();
  int index = 0;
  bool finishing = false;
  static const pages = [
    (
      image: 'jennys-exterior.jpg',
      eyebrow: 'Always welcome',
      title: 'A little Jenny’s.\nAlways with you.',
      body:
          'Your digital loyalty card, ready for every visit. Show it to our team to collect points on eligible purchases.',
    ),
    (
      image: 'jennys-evening.jpg',
      eyebrow: 'A little thank you',
      title: 'Every visit.\nA little more.',
      body:
          'Keep your points close and discover available rewards. Your next little thank you could be waiting.',
    ),
    (
      image: 'dish-feature.jpg',
      eyebrow: 'Made to be enjoyed',
      title: 'Order here.\nEnjoy it there.',
      body:
          'Dining with us? Choose your favourites and send your order to our team. Pay in the restaurant when you’re ready.',
    ),
    (
      image: 'jennys-evening.jpg',
      eyebrow: 'All in one place',
      title: 'Your visits.\nAll together.',
      body:
          'Follow your order status, look back at your points activity and stay in the loop with messages from Jenny’s.',
    ),
  ];

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    for (final image in {
      'jennys-exterior.jpg',
      'jennys-evening.jpg',
      'dish-feature.jpg',
    }) {
      unawaited(precacheImage(AssetImage('assets/images/$image'), context));
    }
  }

  Future<void> finish(IntroAction action) async {
    if (finishing) return;
    setState(() => finishing = true);
    try {
      await widget.onFinish(action);
    } finally {
      if (mounted) setState(() => finishing = false);
    }
  }

  void go(int page) {
    if (finishing) return;
    if (MediaQuery.disableAnimationsOf(context)) {
      controller.jumpToPage(page);
    } else {
      unawaited(
        controller.animateToPage(
          page,
          duration: const Duration(milliseconds: 440),
          curve: Curves.easeInOutCubic,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final reduced = MediaQuery.disableAnimationsOf(context);
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle.light.copyWith(
        systemNavigationBarColor: navy,
      ),
      child: Scaffold(
        backgroundColor: navy,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(24, 8, 14, 12),
                    child: Row(
                      children: [
                        const Brand(size: 42),
                        const SizedBox(width: 11),
                        const Expanded(
                          child: Text(
                            'Jenny’s',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 22,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: finishing
                              ? null
                              : () => finish(IntroAction.skip),
                          style: TextButton.styleFrom(
                            foregroundColor: const Color(0xFFD9E2F0),
                            minimumSize: const Size(60, 48),
                          ),
                          child: Text(widget.replay ? 'Close' : 'Skip'),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: PageView.builder(
                      key: const Key('intro-pages'),
                      controller: controller,
                      itemCount: pages.length,
                      onPageChanged: (value) => setState(() => index = value),
                      itemBuilder: (context, page) => LayoutBuilder(
                        builder: (context, constraints) {
                          final data = pages[page];
                          final textScale =
                              MediaQuery.textScalerOf(context).scale(12) / 12;
                          final imageHeight = math.max(
                            (constraints.maxHeight * .50).clamp(205.0, 335.0),
                            205.0 + 100 * math.max(0, textScale - 1),
                          );
                          return SingleChildScrollView(
                            key: PageStorageKey('intro-$page'),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Padding(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 22,
                                  ),
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(26),
                                    child: SizedBox(
                                      height: imageHeight,
                                      child: Stack(
                                        fit: StackFit.expand,
                                        children: [
                                          AnimatedScale(
                                            scale: index == page ? 1 : 1.035,
                                            duration: reduced
                                                ? Duration.zero
                                                : const Duration(
                                                    milliseconds: 700,
                                                  ),
                                            child: Image.asset(
                                              'assets/images/${data.image}',
                                              fit: BoxFit.cover,
                                              alignment: page == 0
                                                  ? const Alignment(0, -.2)
                                                  : Alignment.center,
                                              excludeFromSemantics: true,
                                            ),
                                          ),
                                          const DecoratedBox(
                                            decoration: BoxDecoration(
                                              gradient: LinearGradient(
                                                begin: Alignment.topCenter,
                                                end: Alignment.bottomCenter,
                                                colors: [
                                                  Color(0x000A172C),
                                                  Color(0x220A172C),
                                                  Color(0xE60A172C),
                                                ],
                                                stops: [0, .38, 1],
                                              ),
                                            ),
                                          ),
                                          Positioned(
                                            left: 18,
                                            right: 18,
                                            bottom: 18,
                                            child: AnimatedSlide(
                                              offset: index == page
                                                  ? Offset.zero
                                                  : const Offset(0, .07),
                                              duration: reduced
                                                  ? Duration.zero
                                                  : const Duration(
                                                      milliseconds: 500,
                                                    ),
                                              child: _IntroFeature(page: page),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ),
                                ),
                                Padding(
                                  padding: const EdgeInsets.fromLTRB(
                                    27,
                                    24,
                                    27,
                                    12,
                                  ),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Eyebrow(data.eyebrow, color: gold),
                                      const SizedBox(height: 12),
                                      Text(
                                        data.title,
                                        style: const TextStyle(
                                          fontSize: 32,
                                          height: 1.13,
                                          letterSpacing: -.9,
                                          color: Colors.white,
                                          fontWeight: FontWeight.w800,
                                        ),
                                      ),
                                      const SizedBox(height: 14),
                                      Text(
                                        data.body,
                                        style: const TextStyle(
                                          fontSize: 13,
                                          height: 1.7,
                                          color: Color(0xFFCFD9E8),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(25, 0, 25, 8),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: List.generate(
                            pages.length,
                            (page) => Semantics(
                              selected: page == index,
                              label:
                                  'Introduction ${page + 1} of ${pages.length}',
                              child: InkWell(
                                onTap: () => go(page),
                                borderRadius: BorderRadius.circular(24),
                                child: SizedBox(
                                  width: 44,
                                  height: 44,
                                  child: Center(
                                    child: AnimatedContainer(
                                      duration: reduced
                                          ? Duration.zero
                                          : const Duration(milliseconds: 220),
                                      width: page == index ? 24 : 6,
                                      height: 6,
                                      decoration: BoxDecoration(
                                        color: page == index
                                            ? gold
                                            : const Color(0xFF60728E),
                                        borderRadius: BorderRadius.circular(5),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 6),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            key: const Key('intro-next'),
                            onPressed: finishing
                                ? null
                                : () => index < pages.length - 1
                                      ? go(index + 1)
                                      : finish(
                                          widget.replay
                                              ? IntroAction.skip
                                              : IntroAction.signup,
                                        ),
                            style: FilledButton.styleFrom(
                              backgroundColor: gold,
                              foregroundColor: navy,
                              disabledBackgroundColor: gold.withValues(
                                alpha: .65,
                              ),
                            ),
                            child: finishing
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: navy,
                                    ),
                                  )
                                : Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      Flexible(
                                        child: Text(
                                          index == pages.length - 1
                                              ? (widget.replay
                                                    ? 'Back to Jenny’s'
                                                    : 'Create my account')
                                              : 'Next',
                                        ),
                                      ),
                                      const SizedBox(width: 16),
                                      const Icon(
                                        Icons.arrow_forward_rounded,
                                        size: 19,
                                      ),
                                    ],
                                  ),
                          ),
                        ),
                        if (!widget.replay)
                          TextButton(
                            onPressed: finishing
                                ? null
                                : () => finish(IntroAction.signin),
                            style: TextButton.styleFrom(
                              foregroundColor: const Color(0xFFE4EAF3),
                            ),
                            child: const Text(
                              'Already a member? Sign in',
                              style: TextStyle(fontSize: 12),
                            ),
                          )
                        else
                          const SizedBox(height: 12),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _IntroFeature extends StatelessWidget {
  final int page;
  const _IntroFeature({required this.page});
  @override
  Widget build(BuildContext context) {
    // Illustrative features only: no fabricated balance, reward, order or barcode.
    if (page == 0) {
      return Container(
        padding: const EdgeInsets.all(17),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: gold.withValues(alpha: .55)),
          gradient: const LinearGradient(
            colors: [Color(0xF22A55A1), Color(0xF2102343)],
          ),
          boxShadow: const [
            BoxShadow(
              color: Color(0x55000000),
              blurRadius: 24,
              offset: Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Brand(size: 32),
                Spacer(),
                Icon(Icons.credit_card_rounded, color: gold, size: 23),
              ],
            ),
            const SizedBox(height: 16),
            const Text(
              'THE JENNY’S CARD',
              style: TextStyle(
                color: gold,
                fontSize: 11,
                letterSpacing: 2,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 5),
            Text(
              'Made for every visit.',
              style: TextStyle(
                color: Colors.white.withValues(alpha: .90),
                fontSize: 11,
              ),
            ),
          ],
        ),
      );
    }
    final items = switch (page) {
      1 => [
        (Icons.auto_awesome_outlined, 'Collect points'),
        (Icons.card_giftcard_rounded, 'Discover rewards'),
      ],
      2 => [
        (Icons.restaurant_menu_rounded, 'Choose your favourites'),
        (Icons.check_circle_outline_rounded, 'Pay with our team'),
      ],
      _ => [
        (Icons.receipt_long_outlined, 'Your order status'),
        (Icons.history_rounded, 'Your points activity'),
      ],
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
      decoration: BoxDecoration(
        color: const Color(0xF7F9F7F2),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        children: [
          for (final (i, item) in items.indexed) ...[
            if (i > 0)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 9),
                child: Divider(height: 1, color: Color(0xFFDFE3E9)),
              ),
            Row(
              children: [
                Icon(item.$1, size: 21, color: blue),
                const SizedBox(width: 13),
                Expanded(
                  child: Text(
                    item.$2,
                    style: const TextStyle(
                      fontSize: 12,
                      color: navy,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const Icon(Icons.chevron_right_rounded, size: 18, color: muted),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
