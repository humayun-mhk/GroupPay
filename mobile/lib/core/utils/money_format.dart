class MoneyFormat {
  const MoneyFormat._();

  static String format(Object? value, {String currency = 'Rs.'}) {
    var raw = (value ?? '0').toString().trim();
    if (raw.isEmpty) raw = '0';
    final negative = raw.startsWith('-');
    if (negative) raw = raw.substring(1);
    final pieces = raw.split('.');
    final integer = pieces.first.replaceAll(RegExp(r'[^0-9]'), '');
    final fraction = pieces.length > 1 ? pieces[1].replaceAll(RegExp(r'[^0-9]'), '') : '';
    final grouped = integer.replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (_) => ',');
    final cents = ('${fraction}00').substring(0, 2);
    return '$currency ${negative ? '-' : ''}${grouped.isEmpty ? '0' : grouped}.$cents';
  }
}
