part of 'main.dart';

/// Customer wording for native POS states, without inferring kitchen progress.
class OrderStatusCard extends StatelessWidget {
  final Json order;
  const OrderStatusCard({super.key, required this.order});

  @override
  Widget build(BuildContext context) {
    final (label, detail, icon, color, background) = switch (order['state']) {
      'draft' => (
        'Order received',
        'Your bill is open. Pay with our team after your meal.',
        Icons.receipt_long_rounded,
        blue,
        const Color(0xFFECF1FB),
      ),
      'paid' || 'done' => (
        'Paid',
        'Payment completed. Thank you for visiting Jenny’s.',
        Icons.check_circle_outline_rounded,
        const Color(0xFF236447),
        const Color(0xFFEAF4EF),
      ),
      'cancel' => (
        'Cancelled',
        'This order has been cancelled.',
        Icons.cancel_outlined,
        muted,
        paper,
      ),
      _ => (
        'Status unavailable',
        'Please check with our team for an update.',
        Icons.info_outline_rounded,
        muted,
        paper,
      ),
    };
    return Card(
      color: Colors.white,
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 220),
              child: Container(
                key: ValueKey(label),
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: background,
                  borderRadius: BorderRadius.circular(30),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(icon, size: 18, color: color),
                    const SizedBox(width: 7),
                    Flexible(
                      child: Text(
                        label,
                        style: TextStyle(
                          color: color,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 18),
            Text(
              money(order['total'], '${order['currency']}'),
              style: const TextStyle(
                fontSize: 25,
                fontWeight: FontWeight.w800,
                color: ink,
              ),
            ),
            const SizedBox(height: 7),
            Text(
              'Order ${order['name']}',
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: ink,
              ),
            ),
            Text(
              dateLabel(order['date']),
              style: const TextStyle(fontSize: 11, color: muted),
            ),
            const SizedBox(height: 14),
            Text(
              detail,
              style: const TextStyle(fontSize: 12, height: 1.6, color: muted),
            ),
          ],
        ),
      ),
    );
  }
}
