// JENNYS_CAPTURE_DIR=/absolute/output flutter test --no-pub tool/capture_app_intro.dart
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/main.dart';
import 'capture_dine_in.dart' show CaptureBinding;

void main() {
  CaptureBinding();
  final folder = Platform.environment['JENNYS_CAPTURE_DIR'];
  testWidgets('Capture the real introduction screens', (tester) async {
    final loader = FontLoader('Manrope');
    for (final weight in [400, 500, 600, 700, 800]) {
      loader.addFont(rootBundle.load('assets/fonts/manrope-$weight.ttf'));
    }
    await loader.load();
    final icons = FontLoader('MaterialIcons');
    icons.addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final key = GlobalKey();
    await tester.pumpWidget(
      Builder(
        builder: (context) => MaterialApp(
          theme: (const JennysApp().build(context) as MaterialApp).theme,
          home: RepaintBoundary(
            key: key,
            child: MediaQuery(
              data: const MediaQueryData(
                size: Size(390, 844),
                padding: EdgeInsets.only(top: 28, bottom: 22),
              ),
              child: AppIntroduction(onFinish: (_) async {}),
            ),
          ),
        ),
      ),
    );
    await tester.runAsync(() async {
      for (final name in [
        'jennys-exterior.jpg',
        'jennys-evening.jpg',
        'jennys-logo.jpg',
        'dish-feature.jpg',
      ]) {
        await precacheImage(
          AssetImage('assets/images/$name'),
          key.currentContext!,
        );
      }
    });
    await tester.pumpAndSettle();
    for (final name in ['Card', 'Rewards', 'Ordering', 'Activity']) {
      final boundary =
          key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
      await tester.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: 2);
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        await Directory(folder!).create(recursive: true);
        await File(
          '$folder/Jennys-Welcome-$name.png',
        ).writeAsBytes(bytes!.buffer.asUint8List());
        image.dispose();
      });
      if (name != 'Activity') {
        await tester.tap(find.byKey(const Key('intro-next')));
        await tester.pumpAndSettle();
      }
    }
    await tester.pumpWidget(const SizedBox());
    expect(tester.takeException(), isNull);
  }, skip: folder == null);
}
