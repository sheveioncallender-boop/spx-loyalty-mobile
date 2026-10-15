import 'dart:math' as math;

import 'package:flutter/material.dart';

/// A single half-turn: the reverse is counter-rotated so its barcode is never
/// mirrored. Both faces retain their space to avoid moving the controls below.
class LoyaltyCardFlip extends StatefulWidget {
  final Widget front, back;
  final bool showBack;
  const LoyaltyCardFlip({
    super.key,
    required this.front,
    required this.back,
    required this.showBack,
  });

  @override
  State<LoyaltyCardFlip> createState() => _LoyaltyCardFlipState();
}

class _LoyaltyCardFlipState extends State<LoyaltyCardFlip>
    with SingleTickerProviderStateMixin {
  late final AnimationController _turn = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 720),
    value: widget.showBack ? 1 : 0,
  );
  bool _reducedMotion = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _reducedMotion = MediaQuery.disableAnimationsOf(context);
    if (_reducedMotion) {
      _turn.stop();
      _turn.value = widget.showBack ? 1 : 0;
    }
  }

  @override
  void didUpdateWidget(covariant LoyaltyCardFlip oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.showBack == widget.showBack) return;
    final target = widget.showBack ? 1.0 : 0.0;
    if (_reducedMotion) {
      _turn.value = target;
    } else {
      _turn.animateTo(target, curve: Curves.easeInOutCubic);
    }
  }

  @override
  void dispose() {
    _turn.dispose();
    super.dispose();
  }

  Widget face(Widget child, bool visible) => Visibility(
    visible: visible,
    maintainSize: true,
    maintainState: true,
    maintainAnimation: true,
    child: child,
  );

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: _turn,
    builder: (context, _) {
      final progress = _turn.value;
      final backVisible = progress >= .5;
      final lift = math.sin(progress * math.pi);
      return Transform.translate(
        offset: Offset(0, -5 * lift),
        child: Transform.scale(
          scale: 1 + .02 * lift,
          child: Transform(
            key: const ValueKey('loyalty-card-turn'),
            alignment: Alignment.center,
            transform: Matrix4.identity()
              ..setEntry(3, 2, .0014)
              ..rotateY(-math.pi * progress),
            child: Stack(
              alignment: Alignment.center,
              children: [
                face(widget.front, !backVisible),
                face(
                  Transform(
                    alignment: Alignment.center,
                    transform: Matrix4.rotationY(math.pi),
                    child: widget.back,
                  ),
                  backVisible,
                ),
              ],
            ),
          ),
        ),
      );
    },
  );
}
