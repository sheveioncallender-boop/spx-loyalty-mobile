import 'dart:io';

import 'package:barcode_widget/barcode_widget.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

const _navy = Color(0xFF112444);
const _blue = Color(0xFF244E9D);
const _muted = Color(0xFF697386);
const cardDisplayChannel = MethodChannel('net.spxcorp.jennys/card_display');

/// Share the display aid across the inline card and enlarged scan route.
/// Closing the enlarged route must not dim a card that is still visible.
class CardDisplayLease {
  static int _count = 0;
  bool _held = false;
  void setVisible(bool visible) {
    if (_held == visible) return;
    _held = visible;
    _count += visible ? 1 : -1;
    if ((visible && _count == 1) || (!visible && _count == 0)) {
      _apply(visible);
    }
  }

  static Future<void> _apply(bool enabled) async {
    if (!Platform.isAndroid && !Platform.isIOS) return;
    try {
      await cardDisplayChannel.invokeMethod<void>(enabled ? 'show' : 'hide');
    } on PlatformException {
      // The barcode remains usable without the optional display aid.
    } on MissingPluginException {
      // Other platforms still display the card.
    }
  }
}

/// The payload is the exact native loyalty.card.code, never a customer ID,
/// display-name, URL, balance, formatted number or app-generated identifier.
class LoyaltyBarcode extends StatelessWidget {
  final String code;
  final double height;
  const LoyaltyBarcode({super.key, required this.code, this.height = 110});

  @override
  Widget build(BuildContext context) {
    final barcode = Barcode.code128(escapes: false);
    // Preserve punctuation, spaces and case. Unsupported codes fall back to
    // manual entry rather than silently encoding a different identifier.
    if (code.isEmpty || !barcode.isValid(code)) {
      return const Padding(
        padding: EdgeInsets.all(24),
        child: Text(
          'This card cannot be shown as a barcode. Please ask the team to enter your card number.',
          textAlign: TextAlign.center,
        ),
      );
    }
    final bars = barcode
        .make(code, width: 1, height: 1, drawText: false)
        .whereType<BarcodeBar>()
        .where((bar) => bar.black);
    final module = bars.map((bar) => bar.width).reduce((a, b) => a < b ? a : b);
    return LayoutBuilder(
      builder: (context, constraints) {
        // Code 128 requires blank quiet zones of at least ten narrow modules
        // on each side. Add two modules of headroom for raster rounding.
        // Keep every narrow bar an integer number of physical pixels. Fitting
        // arbitrary fractional bars can distort a code on low-density screens.
        final ratio = MediaQuery.devicePixelRatioOf(context);
        final modules = (1 / module).round();
        final pixels = (constraints.maxWidth * ratio / (modules + 24)).floor();
        if (pixels < 1) {
          return const Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              'Enlarge this barcode or ask the team to enter your card number.',
              textAlign: TextAlign.center,
            ),
          );
        }
        final width = modules * pixels / ratio;
        final left =
            ((constraints.maxWidth - width) * ratio / 2).floor() / ratio;
        final right = constraints.maxWidth - width - left;
        return Semantics(
          label: 'Membership barcode. Card number $code',
          child: ColoredBox(
            color: Colors.white,
            child: Padding(
              padding: EdgeInsets.fromLTRB(left, 16, right, 16),
              child: BarcodeWidget(
                key: const ValueKey('membership-barcode'),
                barcode: barcode,
                data: code,
                drawText: false,
                color: Colors.black,
                backgroundColor: Colors.white,
                width: width,
                height: height,
              ),
            ),
          ),
        );
      },
    );
  }
}

class LoyaltyScanPage extends StatefulWidget {
  final String code, program, customer;
  final bool isDemo;
  const LoyaltyScanPage({
    super.key,
    required this.code,
    required this.program,
    required this.customer,
    required this.isDemo,
  });

  @override
  State<LoyaltyScanPage> createState() => _LoyaltyScanPageState();
}

class _LoyaltyScanPageState extends State<LoyaltyScanPage> {
  bool enlarged = false;
  final _display = CardDisplayLease();
  @override
  void initState() {
    super.initState();
    _display.setVisible(true);
  }

  @override
  void dispose() {
    _display.setVisible(false);
    super.dispose();
  }

  Widget get barcodePanel => Container(
    padding: const EdgeInsets.symmetric(vertical: 24),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(26),
      border: Border.all(color: const Color(0xFFE4E9F0)),
      boxShadow: const [
        BoxShadow(
          color: Color(0x0C112444),
          blurRadius: 24,
          offset: Offset(0, 10),
        ),
      ],
    ),
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.center_focus_strong_rounded, color: _blue, size: 30),
        const SizedBox(height: 12),
        Text(
          widget.program,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: _navy,
            fontSize: 13,
            fontWeight: FontWeight.w800,
          ),
        ),
        const SizedBox(height: 14),
        LoyaltyBarcode(code: widget.code),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: SelectableText(
            widget.code,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: _navy,
              fontSize: 16,
              letterSpacing: 1.4,
              fontWeight: FontWeight.w800,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Text(
            widget.customer,
            textAlign: TextAlign.center,
            style: const TextStyle(color: _muted, fontSize: 12),
          ),
        ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !enlarged,
    onPopInvokedWithResult: (didPop, _) {
      if (!didPop && enlarged) setState(() => enlarged = false);
    },
    child: Scaffold(
      backgroundColor: enlarged ? Colors.white : const Color(0xFFF7F8FA),
      appBar: AppBar(
        backgroundColor: enlarged ? Colors.white : const Color(0xFFF7F8FA),
        surfaceTintColor: Colors.transparent,
        leading: IconButton(
          tooltip: enlarged ? 'Back to card' : 'Close scan card',
          icon: Icon(
            enlarged ? Icons.fullscreen_exit_rounded : Icons.close_rounded,
          ),
          onPressed: () => enlarged
              ? setState(() => enlarged = false)
              : Navigator.pop(context),
        ),
        title: const Text(
          'Your Jenny’s card',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: enlarged
            ? RotatedBox(
                quarterTurns:
                    MediaQuery.sizeOf(context).height >
                        MediaQuery.sizeOf(context).width
                    ? 1
                    : 0,
                child: Center(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          widget.isDemo
                              ? 'PREVIEW CARD · NOT VALID AT THE TILL'
                              : 'SHOW THIS BARCODE TO THE TEAM',
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w800,
                            color: _muted,
                          ),
                        ),
                        const SizedBox(height: 12),
                        LoyaltyBarcode(code: widget.code, height: 100),
                        Text(
                          widget.code,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 1.4,
                            color: _navy,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              )
            : Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 500),
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(24, 20, 24, 28),
                    children: [
                      const Text(
                        'Every visit.\nA little more rewarding.',
                        style: TextStyle(
                          fontSize: 30,
                          height: 1.16,
                          letterSpacing: -1.1,
                          color: _navy,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 14),
                      const Text(
                        'Show this barcode to the team before you pay.',
                        style: TextStyle(
                          color: _muted,
                          fontSize: 13,
                          height: 1.7,
                        ),
                      ),
                      const SizedBox(height: 22),
                      if (widget.isDemo) ...[
                        const Text(
                          'PREVIEW CARD · NOT VALID AT THE TILL',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: _blue,
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                            letterSpacing: .5,
                          ),
                        ),
                        const SizedBox(height: 12),
                      ],
                      barcodePanel,
                      const SizedBox(height: 20),
                      FilledButton.icon(
                        onPressed: () {
                          HapticFeedback.selectionClick();
                          setState(() => enlarged = true);
                        },
                        icon: const Icon(Icons.fullscreen_rounded, size: 22),
                        label: const Text('Enlarge barcode'),
                      ),
                      TextButton.icon(
                        onPressed: () async {
                          await Clipboard.setData(
                            ClipboardData(text: widget.code),
                          );
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Card number copied'),
                              ),
                            );
                          }
                        },
                        icon: const Icon(Icons.copy_rounded, size: 15),
                        label: const Text('Copy card number'),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'Points are added after an eligible purchase is completed. Close this card to refresh your balance.',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 11,
                          height: 1.8,
                          color: _muted,
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
