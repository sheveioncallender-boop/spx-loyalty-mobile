def preserve_existing_members(env):
    portal = env.ref('base.group_portal')
    env['res.users'].sudo().with_context(active_test=False).search([
        ('group_ids', 'in', portal.id), ('share', '=', True),
        ('spx_mobile_verified_email', '=', False),
    ]).write({'spx_mobile_legacy_access': True})
