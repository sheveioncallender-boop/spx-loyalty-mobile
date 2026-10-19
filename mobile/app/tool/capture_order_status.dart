// JENNYS_CAPTURE_DIR=/absolute/output flutter test --no-pub tool/capture_order_status.dart
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/api.dart';
import 'package:jennys_rewards/main.dart';
import 'capture_dine_in.dart' show CaptureBinding;

class StatusPreviewApi extends DemoApi {
  @override
  Future<List<dynamic>> orders() async => [
    {
      'name': '260-1-000001',
      'date': '2026-09-13T18:24:22',
      'total': 300,
      'currency': 'TTD',
      'state': 'draft',
    },
    {
      'name': '259-1-000028',
      'date': '2026-09-12T19:15:00',
      'total': 185,
      'currency': 'TTD',
      'state': 'paid',
    },
    {
      'name': '257-1-000017',
      'date': '2026-09-10T17:30:00',
      'total': 98,
      'currency': 'TTD',
      'state': 'cancel',
    },
  ];
}

void main() {
  CaptureBinding();
  final folder = Platform.environment['JENNYS_CAPTURE_DIR'];
  testWidgets('Capture order statuses with sample records', (tester) async {
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
    final key = GlobalKey();
    await tester.pumpWidget(
      RepaintBoundary(
        key: key,
        child: JennysApp(initialApi: StatusPreviewApi()),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('You').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Your orders'));
    await tester.pumpAndSettle();
    final boundary =
        key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
    await tester.runAsync(() async {
      final image = await boundary.toImage(pixelRatio: 2);
      final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
      await Directory(folder!).create(recursive: true);
      await File(
        '$folder/Jennys-Order-Status.png',
      ).writeAsBytes(bytes!.buffer.asUint8List());
      image.dispose();
    });
    await tester.pumpWidget(const SizedBox());
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  }, skip: folder == null);
}
