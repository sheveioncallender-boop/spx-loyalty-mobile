import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/card_flip.dart';

void main() {
  testWidgets('Card rotates in place, handles rapid reversal and settles', (
    tester,
  ) async {
    bool back = false;
    late StateSetter update;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: StatefulBuilder(
            builder: (context, setState) {
              update = setState;
              return Center(
                child: SizedBox(
                  width: 300,
                  child: LoyaltyCardFlip(
                    showBack: back,
                    front: const SizedBox(height: 200, child: Text('Front')),
                    back: const SizedBox(
                      height: 200,
                      child: Text('Barcode side'),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
    final card = find.byType(LoyaltyCardFlip);
    final size = tester.getSize(card);
    Matrix4 rotation() => tester
        .widget<Transform>(find.byKey(const ValueKey('loyalty-card-turn')))
        .transform;
    expect(rotation().entry(0, 0), 1);
    update(() => back = true);
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 360));
    expect(rotation().entry(0, 0).abs(), lessThan(.2));
    expect(tester.getSize(card), size);
    // Reversing mid-turn must settle on the requested side without queuing spins.
    update(() => back = false);
    await tester.pumpAndSettle();
    expect(rotation().entry(0, 0), closeTo(1, .00001));
    update(() => back = true);
    await tester.pumpAndSettle();
    expect(rotation().entry(0, 0), closeTo(-1, .00001));
    expect(tester.getSize(card), size);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Reduced motion reveals the reverse immediately', (tester) async {
    bool back = false;
    late StateSetter update;
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(disableAnimations: true),
          child: StatefulBuilder(
            builder: (context, setState) {
              update = setState;
              return LoyaltyCardFlip(
                showBack: back,
                front: const SizedBox(width: 300, height: 200),
                back: const SizedBox(width: 300, height: 200),
              );
            },
          ),
        ),
      ),
    );
    update(() => back = true);
    await tester.pump();
    final transform = tester
        .widget<Transform>(find.byKey(const ValueKey('loyalty-card-turn')))
        .transform;
    expect(transform.entry(0, 0), closeTo(-1, .00001));
    expect(tester.takeException(), isNull);
  });
}
