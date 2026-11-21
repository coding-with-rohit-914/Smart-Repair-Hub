
import 'package:flutter_test/flutter_test.dart';
import 'package:repair_service/main.dart';

void main() {
  testWidgets('Repair Service app loads successfully',
      (WidgetTester tester) async {
    await tester.pumpWidget(const RepairServiceApp());

    expect(find.byType(RepairServiceApp), findsOneWidget);
  });
}
