import 'package:flutter_test/flutter_test.dart';
import 'package:triaseku/main.dart';

void main() {
  testWidgets('layar login tampil', (tester) async {
    await tester.pumpWidget(const TriaseKuApp());
    expect(find.text('Masuk'), findsOneWidget);
  });
}
