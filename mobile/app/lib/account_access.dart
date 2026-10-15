part of 'main.dart';

class AccountReturn extends StatefulWidget {
  final Uri link;
  final OdooApi? accountApi;
  final ValueChanged<OdooApi>? onAuthenticated;
  const AccountReturn({
    super.key,
    required this.link,
    this.accountApi,
    this.onAuthenticated,
  });
  @override
  State<AccountReturn> createState() => _AccountReturnState();
}

class _AccountReturnState extends State<AccountReturn> {
  OdooApi? api;
  bool loading = true;
  String? notice;
  @override
  void initState() {
    super.initState();
    finish();
  }

  Future<void> finish() async {
    try {
      api = widget.accountApi ?? OdooApi.configured();
      final code = widget.link.queryParameters['code'];
      if (widget.link.path == '/verified' &&
          code != null &&
          RegExp(r'^[A-Za-z0-9_-]{30,100}$').hasMatch(code)) {
        await api!.finishSignup(code);
        if (mounted) {
          if (widget.onAuthenticated != null) {
            widget.onAuthenticated!(api!);
          } else {
            acceptAccount(api!, context);
          }
        }
        return;
      }
      notice = widget.link.path == '/forgot-password'
          ? 'Enter your email to request a new password reset link.'
          : widget.link.path == '/password-updated'
          ? 'Your password is updated. Sign in with your new password.'
          : 'Your email is verified. Sign in to open your account.';
    } catch (e) {
      notice = customerError(e);
    }
    if (mounted) setState(() => loading = false);
  }

  @override
  Widget build(BuildContext context) => loading
      ? Scaffold(
          appBar: accountHeader(),
          body: const Center(
            child: Padding(
              padding: EdgeInsets.all(28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Brand(size: 78),
                  SizedBox(height: 28),
                  CircularProgressIndicator(),
                  SizedBox(height: 24),
                  Text(
                    'Opening your Jenny’s account…',
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
        )
      : AccountAccess(
          accountApi: api,
          initialPage: widget.link.path == '/forgot-password'
              ? 'forgot'
              : 'login',
          initialNotice: notice,
          onAuthenticated: (value) => widget.onAuthenticated != null
              ? widget.onAuthenticated!(value)
              : acceptAccount(value, context),
        );
}

AppBar accountHeader() => AppBar(
  backgroundColor: paper,
  toolbarHeight: 88,
  title: const Row(
    children: [
      Brand(size: 44),
      SizedBox(width: 12),
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Jenny’s',
              style: TextStyle(fontSize: 23, fontWeight: FontWeight.w800),
            ),
            Text(
              'ON THE BOULEVARD',
              style: TextStyle(fontSize: 8, letterSpacing: 1.8, color: muted),
            ),
          ],
        ),
      ),
    ],
  ),
);

class SignIn extends AccountAccess {
  const SignIn({super.key}) : super(initialPage: 'login');
}

class AccountAccess extends StatefulWidget {
  final String initialPage;
  final OdooApi? accountApi;
  final String? initialNotice;
  final ValueChanged<OdooApi>? onAuthenticated;
  const AccountAccess({
    super.key,
    this.initialPage = 'login',
    this.accountApi,
    this.initialNotice,
    this.onAuthenticated,
  });
  @override
  State<AccountAccess> createState() => _AccountAccessState();
}

class _AccountAccessState extends State<AccountAccess>
    with WidgetsBindingObserver {
  final email = TextEditingController(), password = TextEditingController();
  final first = TextEditingController(), last = TextEditingController();
  final phone = TextEditingController(), city = TextEditingController();
  final form = GlobalKey<FormState>();
  late String page;
  OdooApi? api;
  Json? config;
  String? error, notice, receipt;
  bool busy = false, loadingConfig = false, hidden = true;
  bool emailOffers = false, smsOffers = false, terms = false;
  int? year, month, day;
  int cooldown = 0;
  Timer? timer;
  String? _signupPassword;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    page = widget.initialPage;
    notice = widget.initialNotice;
    try {
      api = widget.accountApi ?? OdooApi.configured();
    } catch (_) {
      /* Show a customer error on action. */
    }
    if (page == 'signup') loadConfig();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _signupPassword = null;
    timer?.cancel();
    for (final c in [email, password, first, last, phone, city]) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      Future<void>.delayed(
        const Duration(milliseconds: 450),
        checkVerification,
      );
    }
  }

  void authenticated() {
    _signupPassword = null;
    password.clear();
    if (widget.onAuthenticated != null) {
      widget.onAuthenticated!(api!);
    } else {
      Navigator.pop(context, api);
    }
  }

  Future<void> checkVerification() async {
    if (!mounted ||
        busy ||
        page != 'verify' ||
        _signupPassword == null ||
        receipt == null ||
        ModalRoute.of(context)?.isCurrent != true) {
      return;
    }
    setState(() {
      busy = true;
      error = null;
    });
    try {
      if (await api!.signupVerified(receipt!)) {
        await api!.login(email.text, _signupPassword!);
        if (mounted) authenticated();
      }
    } catch (e) {
      if (mounted) setState(() => error = customerError(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> loadConfig() async {
    setState(() {
      loadingConfig = true;
      error = null;
    });
    try {
      if (api == null) {
        throw AppError('Joining is not available in this build.');
      }
      final result = await api!.accountConfig();
      if (mounted) setState(() => config = result);
    } catch (e) {
      if (mounted) setState(() => error = customerError(e));
    } finally {
      if (mounted) setState(() => loadingConfig = false);
    }
  }

  void go(String value) {
    if (busy) return;
    FocusScope.of(context).unfocus();
    password.clear();
    if (value != 'verify') _signupPassword = null;
    setState(() {
      page = value;
      error = null;
      notice = null;
    });
    if (value == 'signup' && config == null) loadConfig();
  }

  String? validEmail(String? value) =>
      value != null &&
          RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$').hasMatch(value.trim())
      ? null
      : 'Enter a valid email address.';
  String? requiredText(String? value) =>
      value?.trim().isNotEmpty == true ? null : 'This field is required.';
  void policy(String title, String content) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => SafeArea(
        child: SizedBox(
          height: MediaQuery.sizeOf(context).height * .75,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 18),
                Expanded(
                  child: SingleChildScrollView(
                    child: Text(content, style: const TextStyle(height: 1.8)),
                  ),
                ),
                const SizedBox(height: 14),
                ActionButton('Close', onTap: () => Navigator.pop(context)),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> submit() async {
    if (busy || !(form.currentState?.validate() ?? false)) return;
    if (page == 'signup' &&
        (year == null || month == null || day == null || !terms)) {
      setState(
        () => error =
            'Choose your birthday and accept the terms and privacy policy.',
      );
      return;
    }
    final action = page;
    FocusScope.of(context).unfocus();
    setState(() {
      busy = true;
      error = null;
      notice = null;
    });
    try {
      if (api == null) {
        throw AppError('This service is not available in this build.');
      }
      if (action == 'signup') {
        final birthday = DateTime(year!, month!, day!);
        if (birthday.isAfter(DateTime.now())) {
          throw AppError('Please choose a birthday in the past.');
        }
        receipt = await api!.register({
          'first_name': first.text.trim(),
          'last_name': last.text.trim(),
          'phone': phone.text.trim(),
          'email': email.text.trim(),
          'password': password.text,
          'birthday':
              '${year!.toString().padLeft(4, '0')}-${month!.toString().padLeft(2, '0')}-${day!.toString().padLeft(2, '0')}',
          'city': city.text.trim(),
          'marketing_email': emailOffers,
          'marketing_sms': smsOffers,
          'terms': terms,
          'policy_version': config?['policy_version'],
        });
        _signupPassword =
            password.text; // Memory only, until verification/exit.
        password.clear();
        if (mounted) {
          setState(() => page = 'verify');
          startCooldown();
        }
      } else if (action == 'forgot') {
        await api!.forgotPassword(email.text);
        if (mounted) setState(() => page = 'sent');
      } else {
        await api!.login(email.text, password.text);
        password.clear();
        if (mounted) authenticated();
      }
    } catch (e) {
      if (mounted) {
        if (action == 'signup' && e is AppError && e.code == 'account_exists') {
          password.clear();
          _signupPassword = null;
          receipt = null;
          setState(() {
            page = 'exists';
            error = null;
          });
        } else {
          setState(() => error = customerError(e));
        }
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void startCooldown() {
    timer?.cancel();
    cooldown = 60;
    timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted || cooldown <= 1) {
        t.cancel();
        if (mounted) setState(() => cooldown = 0);
      } else {
        setState(() => cooldown--);
      }
    });
  }

  Future<void> resend() async {
    if (busy || cooldown > 0 || receipt == null) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await api!.resendVerification(receipt!);
      if (mounted) {
        setState(() {
          notice =
              'A new email has been requested. Use the most recent link in your inbox.';
          startCooldown();
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = customerError(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Widget heading(String overline, String title, String description) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Eyebrow(overline),
      const SizedBox(height: 14),
      Text(title, style: Theme.of(context).textTheme.headlineLarge),
      const SizedBox(height: 16),
      Text(description, style: const TextStyle(color: muted, height: 1.8)),
      const SizedBox(height: 28),
    ],
  );
  Widget input(
    String label,
    TextEditingController c, {
    TextInputType? keyboard,
    String? Function(String?)? validator,
    Iterable<String>? autofill,
    int maxLength = 100,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: TextFormField(
      controller: c,
      enabled: !busy,
      keyboardType: keyboard,
      autofillHints: autofill,
      maxLength: maxLength,
      validator: validator ?? requiredText,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(labelText: label, counterText: ''),
      autocorrect: false,
    ),
  );
  Widget passwordInput({bool creating = false}) => TextFormField(
    controller: password,
    enabled: !busy,
    obscureText: hidden,
    autocorrect: false,
    enableSuggestions: false,
    autofillHints: [
      creating ? AutofillHints.newPassword : AutofillHints.password,
    ],
    maxLength: 256,
    validator: (v) => creating && (v?.length ?? 0) < 12
        ? 'Use at least 12 characters.'
        : requiredText(v),
    onFieldSubmitted: (_) {
      if (!creating) submit();
    },
    decoration: InputDecoration(
      labelText: 'Password',
      counterText: '',
      helperText: creating ? 'Use at least 12 characters.' : null,
      suffixIcon: IconButton(
        tooltip: hidden ? 'Show password' : 'Hide password',
        onPressed: () => setState(() => hidden = !hidden),
        icon: Icon(
          hidden ? Icons.visibility_off_outlined : Icons.visibility_outlined,
        ),
      ),
    ),
  );
  Widget birthdayField() {
    final days = DateTime(year ?? 2000, (month ?? 1) + 1, 0).day;
    Widget select(
      String label,
      int? value,
      List<int> values,
      void Function(int?) change, {
      List<String>? labels,
    }) => Expanded(
      child: DropdownButtonFormField<int>(
        initialValue: value,
        isExpanded: true,
        decoration: InputDecoration(
          labelText: label,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 10,
            vertical: 16,
          ),
        ),
        items: values
            .asMap()
            .entries
            .map(
              (e) => DropdownMenuItem(
                value: e.value,
                child: Text(
                  labels?[e.key] ?? '${e.value}',
                  style: const TextStyle(fontSize: 13),
                ),
              ),
            )
            .toList(),
        onChanged: busy ? null : change,
        validator: (v) => v == null ? 'Required' : null,
      ),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Your birthday',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            select(
              'Year',
              year,
              List.generate(
                DateTime.now().year - 1899,
                (i) => DateTime.now().year - i,
              ),
              (v) => setState(() {
                year = v;
                day = null;
              }),
            ),
            const SizedBox(width: 8),
            select(
              'Month',
              month,
              List.generate(12, (i) => i + 1),
              (v) => setState(() {
                month = v;
                day = null;
              }),
              labels: const [
                'Jan',
                'Feb',
                'Mar',
                'Apr',
                'May',
                'Jun',
                'Jul',
                'Aug',
                'Sep',
                'Oct',
                'Nov',
                'Dec',
              ],
            ),
            const SizedBox(width: 8),
            KeyedSubtree(
              key: ValueKey('day-$year-$month'),
              child: SizedBox(
                width: 100,
                child: Row(
                  children: [
                    select(
                      'Day',
                      day,
                      List.generate(days, (i) => i + 1),
                      (v) => setState(() => day = v),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 18),
      ],
    );
  }

  List<Widget> content() {
    if (page == 'signup') {
      if (loadingConfig) {
        return [
          heading(
            'Make yourself at home',
            'Your Jenny’s\nstarts here.',
            'Getting everything ready for you…',
          ),
          const Center(child: CircularProgressIndicator()),
        ];
      }
      if (config?['enabled'] != true) {
        return [
          heading(
            'Make yourself at home',
            'Join Jenny’s.',
            'Joining is temporarily unavailable. Please try again shortly.',
          ),
          ActionButton('Try again', onTap: loadConfig),
          TextButton(
            onPressed: () => go('login'),
            child: const Text('Already a member? Sign in'),
          ),
        ];
      }
      return [
        heading(
          'Make yourself at home',
          'Your Jenny’s\nstarts here.',
          'One account for your card, rewards and orders.',
        ),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: input(
                'First name',
                first,
                maxLength: 80,
                autofill: const [AutofillHints.givenName],
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: input(
                'Last name',
                last,
                maxLength: 80,
                autofill: const [AutofillHints.familyName],
              ),
            ),
          ],
        ),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 58,
              padding: const EdgeInsets.symmetric(horizontal: 11),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: const Color(0xFFEEF1F5),
                borderRadius: BorderRadius.circular(14),
              ),
              child: const Text(
                '+1 (868)',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: input(
                'Phone number',
                phone,
                maxLength: 8,
                keyboard: TextInputType.phone,
                autofill: const [AutofillHints.telephoneNumberNational],
                validator: (v) =>
                    RegExp(r'^[0-9]{3} ?[0-9]{4}$').hasMatch(v?.trim() ?? '')
                    ? null
                    : 'Enter seven digits.',
              ),
            ),
          ],
        ),
        input(
          'Email address',
          email,
          keyboard: TextInputType.emailAddress,
          maxLength: 254,
          validator: validEmail,
          autofill: const [AutofillHints.email],
        ),
        passwordInput(creating: true),
        const SizedBox(height: 22),
        birthdayField(),
        input(
          'City / town (optional)',
          city,
          validator: (_) => null,
          autofill: const [AutofillHints.addressCity],
        ),
        const Text(
          'Keep in touch (optional)',
          style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          title: const Text(
            'Email me Jenny’s news and offers.',
            style: TextStyle(fontSize: 13),
          ),
          value: emailOffers,
          onChanged: busy
              ? null
              : (v) => setState(() => emailOffers = v ?? false),
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          title: const Text(
            'Text me Jenny’s news and offers.',
            style: TextStyle(fontSize: 13),
          ),
          value: smsOffers,
          onChanged: busy
              ? null
              : (v) => setState(() => smsOffers = v ?? false),
        ),
        const Text(
          'You can change your preferences at any time.',
          style: TextStyle(fontSize: 11, color: muted),
        ),
        const SizedBox(height: 12),
        const Divider(),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          title: const Text(
            'I agree to the Terms of Use and have read the Privacy Policy.',
            style: TextStyle(fontSize: 13),
          ),
          value: terms,
          onChanged: busy ? null : (v) => setState(() => terms = v ?? false),
        ),
        Wrap(
          spacing: 8,
          children: [
            TextButton(
              onPressed: () => policy('Terms of Use', '${config!['terms']}'),
              child: const Text('Terms of Use'),
            ),
            TextButton(
              onPressed: () =>
                  policy('Privacy Policy', '${config!['privacy']}'),
              child: const Text('Privacy Policy'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        ActionButton('Create account', onTap: submit, loading: busy),
        const SizedBox(height: 12),
        const Text(
          'We’ll email you a link to verify your account.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 12, color: muted),
        ),
        TextButton(
          onPressed: () => go('login'),
          child: const Text('Already a member? Sign in'),
        ),
      ];
    }
    if (page == 'exists') {
      return [
        heading(
          'Welcome back',
          'You already have\nan account.',
          'An account is already associated with this email address. Sign in or reset your password to continue.',
        ),
        Text(
          email.text.trim(),
          style: const TextStyle(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 24),
        ActionButton('Sign in', onTap: () => go('login')),
        TextButton(
          onPressed: () => go('forgot'),
          child: const Text('Forgot password?'),
        ),
        TextButton(
          onPressed: () => go('signup'),
          child: const Text('Use a different email'),
        ),
      ];
    }
    if (page == 'verify' || page == 'sent') {
      return [
        Container(
          width: 78,
          height: 78,
          alignment: Alignment.centerLeft,
          child: const Icon(
            Icons.mark_email_unread_outlined,
            color: blue,
            size: 42,
          ),
        ),
        const SizedBox(height: 16),
        heading(
          'One more thing',
          'Check your inbox.',
          page == 'verify'
              ? 'Open the email from Jenny’s and confirm your email address to finish setting up your account.'
              : 'If an account matches that email, you’ll receive a password reset link shortly.',
        ),
        if (page == 'verify')
          Text(
            email.text.trim(),
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
        const SizedBox(height: 20),
        Container(
          padding: const EdgeInsets.all(22),
          decoration: BoxDecoration(
            color: cream,
            borderRadius: BorderRadius.circular(18),
          ),
          child: Text(
            page == 'verify'
                ? 'Verify your email, then return here. We’ll sign you in and have your digital card ready.'
                : 'Your reset link is valid for 24 hours. Use the newest email to choose a new password, then return here to sign in.',
            style: const TextStyle(height: 1.8),
          ),
        ),
        const SizedBox(height: 20),
        const Text(
          'Can’t find it? Check your junk or spam folder.',
          style: TextStyle(fontSize: 12, color: muted),
        ),
        if (page == 'verify') ...[
          ActionButton(
            'I’ve verified my email',
            onTap: checkVerification,
            loading: busy,
          ),
          TextButton(
            onPressed: busy || cooldown > 0 ? null : resend,
            child: Text(
              cooldown > 0
                  ? 'Resend email in ${cooldown}s'
                  : 'Resend verification email',
            ),
          ),
          TextButton(
            onPressed: () => go('signup'),
            child: const Text('Change email address'),
          ),
        ],
        const SizedBox(height: 16),
        ActionButton('Back to sign in', onTap: () => go('login')),
      ];
    }
    if (page == 'forgot') {
      return [
        heading(
          'Let’s get you back in',
          'Forgot your\npassword?',
          'Enter your email address and we’ll help you reset it.',
        ),
        input(
          'Email address',
          email,
          keyboard: TextInputType.emailAddress,
          maxLength: 254,
          validator: validEmail,
          autofill: const [AutofillHints.email],
        ),
        const SizedBox(height: 16),
        ActionButton('Send reset link', onTap: submit, loading: busy),
        TextButton(
          onPressed: () => go('login'),
          child: const Text('Back to sign in'),
        ),
      ];
    }
    return [
      heading(
        'A warm welcome back',
        'Your Jenny’s\nis waiting.',
        'Sign in with the same account you use on our website or in the app.',
      ),
      input(
        'Email address',
        email,
        keyboard: TextInputType.emailAddress,
        maxLength: 254,
        validator: validEmail,
        autofill: const [AutofillHints.username],
      ),
      passwordInput(),
      Align(
        alignment: Alignment.centerRight,
        child: TextButton(
          onPressed: () => go('forgot'),
          child: const Text('Forgot password?'),
        ),
      ),
      const SizedBox(height: 16),
      ActionButton('Sign in', onTap: submit, loading: busy),
      const SizedBox(height: 12),
      const Text(
        'New account? Verify your email before signing in.',
        style: TextStyle(fontSize: 12, color: muted),
        textAlign: TextAlign.center,
      ),
      TextButton(
        onPressed: () => go('signup'),
        child: const Text('New to Jenny’s? Create an account'),
      ),
    ];
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !busy,
    child: Scaffold(
      appBar: accountHeader(),
      body: SafeArea(
        child: AutofillGroup(
          child: Form(
            key: form,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(26, 22, 26, 32),
              children: [
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 18),
                    child: Semantics(
                      liveRegion: true,
                      child: Text(
                        error!,
                        style: const TextStyle(
                          color: Color(0xFFA83238),
                          height: 1.6,
                        ),
                      ),
                    ),
                  ),
                if (notice != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 18),
                    child: Semantics(
                      liveRegion: true,
                      child: Text(
                        notice!,
                        style: const TextStyle(
                          color: Color(0xFF286245),
                          height: 1.6,
                        ),
                      ),
                    ),
                  ),
                ...content(),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
