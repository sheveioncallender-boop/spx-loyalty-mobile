// JENNYS_CAPTURE_DIR=/absolute/output flutter test --no-pub tool/capture_recent_activity.dart
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
  testWidgets('Capture dine-in basket with sample data', (tester) async {
    final loader = FontLoader('Manrope');
    for (final weight in [400, 500, 600, 700, 800]) {
      loader.addFont(rootBundle.load('assets/fonts/manrope-$weight.ttf'));
    }
    await loader.load();
    final icons = FontLoader('MaterialIcons');
    icons.addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
    tester.view.physicalSize = const Size(393, 900);
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
    await tester.tap(find.text('Order').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Jenny’s Special Noodles').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Add to order · TT\$98.00'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.textContaining('View order ·'),
      350,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.textContaining('View order ·'));
    await tester.pumpAndSettle();
    await tester.runAsync(() async {
      for (final element in find.byType(Image).evaluate()) {
        await precacheImage((element.widget as Image).image, element);
      }
    });
    await tester.pumpAndSettle();
    Future<void> capture(String name) async {
      final boundary =
          boundaryKey.currentContext!.findRenderObject()!
              as RenderRepaintBoundary;
      await tester.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: 2);
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        await Directory(folder!).create(recursive: true);
        await File(
          '$folder/$name.png',
        ).writeAsBytes(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }

    await capture('Jennys-Dine-In-Basket');
    await tester.ensureVisible(find.text('Send sample order'));
    await tester.tap(find.text('Send sample order'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 1));
    await tester.pumpAndSettle();
    await capture('Jennys-Dine-In-Confirmation');
    await tester.pumpWidget(const SizedBox());
    await tester.pump(const Duration(seconds: 1));
    expect(tester.takeException(), isNull);
  }, skip: folder == null);
}
