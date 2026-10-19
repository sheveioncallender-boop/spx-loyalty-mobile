// Exports the existing Flutter Brand widget for native iOS assets.
// JENNYS_IOS_ASSET_DIR=/absolute/output flutter test --no-pub tool/export_ios_brand.dart
import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jennys_rewards/main.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final output = Platform.environment['JENNYS_IOS_ASSET_DIR'];
  testWidgets('Export Jenny’s native icon and launch branding', (tester) async {
    tester.view.physicalSize = const Size(1024, 1024);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    for (final spec in [
      (name: 'icon-master', size: 840.0),
      (name: 'launch-master', size: 1024.0),
    ]) {
      final key = GlobalKey();
      await tester.pumpWidget(
        RepaintBoundary(
          key: key,
          child: Directionality(
            textDirection: TextDirection.ltr,
            child: ColoredBox(
              color: navy,
              child: Center(child: Brand(size: spec.size)),
            ),
          ),
        ),
      );
      await tester.runAsync(
        () => precacheImage(
          const AssetImage('assets/images/jennys-logo.jpg'),
          key.currentContext!,
        ),
      );
      await tester.pumpAndSettle();
      final boundary =
          key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
      await tester.runAsync(() async {
        final image = await boundary.toImage();
        final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
        await Directory(output!).create(recursive: true);
        await File(
          '$output/${spec.name}.png',
        ).writeAsBytes(bytes!.buffer.asUint8List());
        image.dispose();
      });
    }
  }, skip: output == null);
}
