import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:grouppay/core/theme/app_theme.dart';
import 'package:grouppay/core/widgets/ui.dart';
import 'package:grouppay/core/utils/money_format.dart';
import 'package:grouppay/features/data/settlement_action_policy.dart';

void main() {
  testWidgets('empty state displays its title and guidance', (tester) async {
    await tester.pumpWidget(MaterialApp(
      theme: AppTheme.light,
      home: const Scaffold(
        body: EmptyState(
          title: 'No groups yet',
          message: 'Create a group to get started.',
        ),
      ),
    ));

    expect(find.text('No groups yet'), findsOneWidget);
    expect(find.text('Create a group to get started.'), findsOneWidget);
  });

  test('money formatter groups PKR values and preserves cents', () {
    expect(MoneyFormat.format('1000'), 'Rs. 1,000.00');
    expect(MoneyFormat.format('5000.5'), 'Rs. 5,000.50');
    expect(MoneyFormat.format('-25.75'), 'Rs. -25.75');
  });

  test('manual settlement actions follow the allowed actor and status', () {
    expect(SettlementActionPolicy.canClaimPaid('PENDING', true), isTrue);
    expect(SettlementActionPolicy.canClaimPaid('PENDING', false), isFalse);
    expect(SettlementActionPolicy.canConfirmOrReject('PAYMENT_CLAIMED', false), isTrue);
    expect(SettlementActionPolicy.canConfirmOrReject('PAYMENT_CLAIMED', true), isFalse);
    expect(SettlementActionPolicy.canCancel('PENDING', false), isTrue);
    expect(SettlementActionPolicy.canCancel('CONFIRMED', false), isFalse);
    expect(SettlementActionPolicy.canClaimPaid('REJECTED', true), isFalse);
  });
}
