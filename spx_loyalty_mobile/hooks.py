def preserve_existing_members(env):
    portal = env.ref('base.group_portal')
    env['res.users'].sudo().with_context(active_test=False).search([
        ('group_ids', 'in', portal.id), ('share', '=', True),
        ('spx_mobile_verified_email', '=', False),
    ]).write({'spx_mobile_legacy_access': True})


def disconnect_app(env):
    """Retain history in the data dependency; invalidate temporary auth links.

    Native records, balances and website settings are left intact. The routes
    and app-specific scheduled actions disappear with this connector. Its
    retained data dependency defines no HTTP routes or birthday scheduler.
    """
    registrations = env['spx.mobile.registration'].sudo().search([])
    registrations.filtered(lambda r: r.state == 'pending').write({'state': 'expired'})
    registrations.write({
        'password_hash': False, 'token_hash': False, 'receipt_hash': False,
        'handoff_hash': False, 'handoff_expires_at': False,
    })
    mail = env['mail.mail'].sudo().search([
        ('model', '=like', 'spx.mobile.%'), ('state', 'in', ('outgoing', 'exception')),
    ])
    # Earlier inbox email did not set mail.model. Follow its explicit link too.
    mail |= env['spx.mobile.message'].sudo().search([]).mail_id.filtered(
        lambda m: m.state in ('outgoing', 'exception'))
    mail.write({'state': 'cancel'})
    env['spx.mobile.announcement'].sudo().search([('state', '=', 'scheduled')]).write({
        'state': 'cancelled',
    })
