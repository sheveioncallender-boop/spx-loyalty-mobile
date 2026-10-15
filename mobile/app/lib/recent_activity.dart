part of 'main.dart';

// Odoo serializes its UTC create_date without a zone. Convert it to the
// device's local time, while keeping date-only values as calendar dates.
DateTime? loyaltyActivityDate(dynamic value) {
  final raw = '$value';
  final hasTime = raw.contains('T') || raw.contains(' ');
  final hasZone = RegExp(r'(Z|[+-]\d{2}:?\d{2})$').hasMatch(raw);
  final date = DateTime.tryParse(hasTime && !hasZone ? '${raw}Z' : raw);
  return hasTime ? date?.toLocal() : date;
}

class RecentActivityPage extends StatefulWidget {
  final Json Function() snapshot;
  final Listenable updates;
  final Future<void> Function() onRefresh;
  final int? initialCardId;
  const RecentActivityPage({
    super.key,
    required this.snapshot,
    required this.updates,
    required this.onRefresh,
    this.initialCardId,
  });

  @override
  State<RecentActivityPage> createState() => _RecentActivityPageState();
}

class _RecentActivityPageState extends State<RecentActivityPage> {
  int? _cardId;
  String _filter = 'All';
  final Set<int> _expanded = {};
  static const _months = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  @override
  void initState() {
    super.initState();
    _cardId = widget.initialCardId;
    widget.updates.addListener(_updated);
  }

  @override
  void dispose() {
    widget.updates.removeListener(_updated);
    super.dispose();
  }

  void _updated() {
    if (mounted) setState(() {});
  }

  String _timestamp(dynamic value) {
    final date = loyaltyActivityDate(value);
    if (date == null) return 'Date unavailable';
    final time = MaterialLocalizations.of(context).formatTimeOfDay(
      TimeOfDay.fromDateTime(date),
      alwaysUse24HourFormat: MediaQuery.alwaysUse24HourFormatOf(context),
    );
    return '${date.day} ${_months[date.month - 1]} · $time';
  }

  String _signed(num amount) =>
      '${amount > 0
          ? '+'
          : amount < 0
          ? '−'
          : ''}${points(amount.abs())}';

  @override
  Widget build(BuildContext context) {
    final data = widget.snapshot();
    final cards = (data['cards'] as List<dynamic>? ?? []).cast<Json>();
    if (!cards.any((card) => card['id'] == _cardId)) {
      _cardId = cards.isEmpty ? null : cards.first['id'] as int;
    }
    final card = cards.isEmpty
        ? null
        : cards.firstWhere((card) => card['id'] == _cardId);
    final activity =
        (data['activity'] as List<dynamic>? ?? [])
            .cast<Json>()
            .where((entry) => card != null && entry['card_id'] == _cardId)
            .where(
              (entry) =>
                  _filter == 'All' ||
                  (_filter == 'Earned' &&
                      ((entry['issued'] as num?) ?? 0) > 0) ||
                  (_filter == 'Used' && ((entry['used'] as num?) ?? 0) > 0),
            )
            .toList()
          ..sort((a, b) {
            final ad = loyaltyActivityDate(a['date']);
            final bd = loyaltyActivityDate(b['date']);
            final byDate = (bd?.millisecondsSinceEpoch ?? 0).compareTo(
              ad?.millisecondsSinceEpoch ?? 0,
            );
            return byDate != 0
                ? byDate
                : (b['id'] as int).compareTo(a['id'] as int);
          });
    String? previousMonth;
    final rows = <Widget>[];
    for (final entry in activity) {
      final date = loyaltyActivityDate(entry['date']);
      final month = date == null
          ? 'Undated activity'
          : '${_months[date.month - 1]} ${date.year}';
      if (month != previousMonth) {
        rows.add(
          Padding(
            padding: const EdgeInsets.fromLTRB(2, 22, 0, 12),
            child: Eyebrow(month),
          ),
        );
        previousMonth = month;
      }
      rows.add(_entry(entry));
    }
    return Scaffold(
      appBar: AppBar(
        backgroundColor: paper,
        surfaceTintColor: Colors.transparent,
        title: const Text(
          'Recent activity',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w800,
            color: ink,
          ),
        ),
        actions: const [
          Padding(padding: EdgeInsets.only(right: 22), child: Brand(size: 33)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: widget.onRefresh,
        child: ListView(
          key: const PageStorageKey('recent-activity-scroll'),
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
          children: [
            if (cards.length > 1)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: DropdownButtonFormField<int>(
                  key: ValueKey(_cardId),
                  initialValue: _cardId,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Your cards'),
                  items: cards
                      .map(
                        (card) => DropdownMenuItem<int>(
                          value: card['id'] as int,
                          child: Text('${card['name']}'),
                        ),
                      )
                      .toList(),
                  onChanged: (id) => setState(() {
                    _cardId = id;
                    _expanded.clear();
                  }),
                ),
              ),
            if (card != null) _summary(card),
            const SizedBox(height: 28),
            const Eyebrow('Every visit, a little more'),
            const SizedBox(height: 7),
            Text(
              'Your points story.',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 7),
            const Text(
              'The little thank-yous, all in one place.',
              style: TextStyle(fontSize: 12, color: muted),
            ),
            if (card != null) ...[
              const SizedBox(height: 20),
              Wrap(
                spacing: 9,
                runSpacing: 8,
                children: ['All', 'Earned', 'Used']
                    .map(
                      (filter) => ChoiceChip(
                        label: Text(filter),
                        selected: _filter == filter,
                        showCheckmark: false,
                        selectedColor: blue,
                        backgroundColor: Colors.white,
                        side: BorderSide(
                          color: _filter == filter
                              ? blue
                              : const Color(0xFFE0E5EE),
                        ),
                        shape: const StadiumBorder(),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 9,
                        ),
                        labelStyle: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: _filter == filter ? Colors.white : muted,
                        ),
                        onSelected: (_) => setState(() => _filter = filter),
                      ),
                    )
                    .toList(),
              ),
            ],
            if (activity.isEmpty)
              EmptyState(
                icon: Icons.history_rounded,
                title: card == null
                    ? 'Your story starts here.'
                    : _filter == 'All'
                    ? 'No recent activity.'
                    : 'No ${_filter.toLowerCase()} points to show.',
                detail: card == null
                    ? 'Once your membership card is ready, your points activity will appear here.'
                    : _filter == 'All'
                    ? 'Your points activity will appear here as you collect and enjoy your rewards.'
                    : 'Try All to see your other recent activity.',
              )
            else ...[
              ...rows,
              const Padding(
                padding: EdgeInsets.only(top: 18),
                child: Text(
                  'Showing your most recent points activity.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 11, color: muted),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _summary(Json card) {
    final issued = loyaltyActivityDate(card['since']);
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(26),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [blue, navy],
        ),
        boxShadow: [
          BoxShadow(
            color: navy.withValues(alpha: .13),
            blurRadius: 22,
            offset: const Offset(0, 9),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome_rounded, color: gold, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '${card['name']}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 25),
          const Eyebrow('Your points balance', color: Color(0xFFCAD6EE)),
          const SizedBox(height: 5),
          Text(
            points(card['points']),
            key: const ValueKey('activity-balance'),
            style: const TextStyle(
              fontSize: 46,
              height: 1.1,
              letterSpacing: -1.5,
              fontWeight: FontWeight.w800,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'A little more to look forward to.',
            style: TextStyle(fontSize: 11, color: Color(0xFFCAD6EE)),
          ),
          if (issued != null) ...[
            const SizedBox(height: 22),
            const Divider(color: Color(0xFF53698C), height: 1),
            const SizedBox(height: 15),
            Wrap(
              spacing: 12,
              runSpacing: 4,
              children: [
                const Text(
                  'Card issued',
                  style: TextStyle(fontSize: 11, color: Color(0xFFCAD6EE)),
                ),
                Text(
                  dateLabel(issued.toIso8601String()),
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    color: gold,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _entry(Json entry) {
    final issued = (entry['issued'] as num?) ?? 0;
    final used = (entry['used'] as num?) ?? 0;
    final adjusted = issued < 0 || used < 0;
    final title = adjusted
        ? 'Points adjusted'
        : issued > 0 && used > 0
        ? 'Points earned & used'
        : issued > 0
        ? 'Points earned'
        : used > 0
        ? 'Points used'
        : 'Points activity';
    final id = entry['id'] as int;
    final expanded = _expanded.contains(id);
    final duration = MediaQuery.disableAnimationsOf(context)
        ? Duration.zero
        : const Duration(milliseconds: 220);
    final amounts = [
      if (issued != 0) '${_signed(issued)} pts',
      if (used != 0) '${_signed(-used)} pts',
    ];
    final description = '${entry['name'] ?? ''}'.trim();
    return Padding(
      key: ValueKey('activity-entry-$id'),
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(
              button: true,
              expanded: expanded,
              child: InkWell(
                onTap: () {
                  HapticFeedback.selectionClick();
                  setState(() {
                    expanded ? _expanded.remove(id) : _expanded.add(id);
                  });
                },
                child: Padding(
                  padding: const EdgeInsets.all(17),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: used > 0 ? cream : const Color(0xFFEDF2FC),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: Icon(
                          adjusted
                              ? Icons.swap_vert_rounded
                              : used > 0
                              ? Icons.card_giftcard_rounded
                              : Icons.add_rounded,
                          color: blue,
                          size: 20,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              title,
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w800,
                                color: ink,
                              ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              _timestamp(entry['date']),
                              style: const TextStyle(
                                fontSize: 10,
                                color: muted,
                              ),
                            ),
                            const SizedBox(height: 7),
                            Wrap(
                              spacing: 12,
                              runSpacing: 3,
                              children: (amounts.isEmpty ? ['0 pts'] : amounts)
                                  .map(
                                    (amount) => Text(
                                      amount,
                                      style: const TextStyle(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w800,
                                        color: blue,
                                      ),
                                    ),
                                  )
                                  .toList(),
                            ),
                          ],
                        ),
                      ),
                      AnimatedRotation(
                        turns: expanded ? .5 : 0,
                        duration: duration,
                        child: const Icon(
                          Icons.keyboard_arrow_down_rounded,
                          color: muted,
                          size: 21,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            AnimatedSize(
              duration: duration,
              curve: Curves.easeInOutCubic,
              alignment: Alignment.topCenter,
              child: expanded
                  ? Padding(
                      padding: const EdgeInsets.fromLTRB(18, 0, 18, 18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Divider(color: Color(0xFFE5EAF2), height: 1),
                          const SizedBox(height: 14),
                          const Eyebrow('Activity details'),
                          const SizedBox(height: 7),
                          Text(
                            description.isEmpty
                                ? 'Points activity recorded for your card.'
                                : description,
                            style: const TextStyle(
                              fontSize: 12,
                              color: ink,
                              height: 1.6,
                            ),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'Net points change: ${_signed(issued - used)}',
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: blue,
                            ),
                          ),
                        ],
                      ),
                    )
                  : const SizedBox(width: double.infinity),
            ),
          ],
        ),
      ),
    );
  }
}
