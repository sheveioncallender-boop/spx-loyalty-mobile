// Run with JENNYS_CAPTURE_DIR set to a local output folder:
// flutter test --no-pub tool/capture_card_flip.dart
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';

class CaptureBinding extends AutomatedTestWidgetsFlutterBinding {
  @override
  bool get disableShadows => false;
}

void main() {
  CaptureBinding();
  final folder = Platform.environment['JENNYS_CAPTURE_DIR'];
  testWidgets('Capture actual card flip frames', (tester) async {
    final loader = FontLoader('Manrope');
    for (final weight in [400, 500, 600, 700, 800]) {
      loader.addFont(rootBundle.load('assets/fonts/manrope-$weight.ttf'));
    }
    await loader.load();
    final icons = FontLoader('MaterialIcons');
    icons.addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
    tester.view.physicalSize = const Size(393, 852);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final boundaryKey = GlobalKey();
    await tester.pumpWidget(
      RepaintBoundary(
        key: boundaryKey,
        child: JennysApp(initialApi: DemoApi()),
      ),
    );
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
    await tester.tap(find.text('My card').last);
    await tester.pumpAndSettle();
    await tester.runAsync(() => precacheImage(
      const AssetImage('assets/images/jennys-logo.jpg'),
      tester.element(find.byType(LoyaltyCard).first),
    ));
    await tester.pumpAndSettle();
    var index = 0;
    Future<void> capture() async {
      final boundary =
          boundaryKey.currentContext!.findRenderObject()!
              as RenderRepaintBoundary;
      await tester.runAsync(() async {
        final frame = await boundary.toImage(pixelRatio: 2);
        final bytes = await frame.toByteData(format: ui.ImageByteFormat.png);
        await Directory(folder!).create(recursive: true);
        await File(
          '$folder/frame_${(index++).toString().padLeft(3, '0')}.png',
        ).writeAsBytes(bytes!.buffer.asUint8List());
        frame.dispose();
      });
    }

    await capture();
    await tester.tap(find.text('Scan at Jenny’s'));
    await tester.pump();
    await capture();
    for (var i = 0; i < 24; i++) {
      await tester.pump(const Duration(milliseconds: 30));
      await capture();
    }
    await tester.pumpAndSettle();
    await capture();
    await tester.tap(find.text('Show card front'));
    await tester.pump();
    await capture();
    for (var i = 0; i < 24; i++) {
      await tester.pump(const Duration(milliseconds: 30));
      await capture();
    }
    await tester.pumpAndSettle();
    await capture();
    // Finish the sample account refresh after the return turn.
    await tester.pump(const Duration(seconds: 1));
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  }, skip: folder == null);
}
