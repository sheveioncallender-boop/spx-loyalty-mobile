# Jenny’s Rewards — Odoo 19

Technical module: `spx_loyalty_mobile`. Version: `19.0.1.3.0`.

## Upgrade the existing Cloudpepper installation

1. Replace this module folder in the same custom-addons Git repository and deploy the updated revision through Cloudpepper.
2. Restart/rebuild the Odoo instance using the normal hosting workflow.
3. In Odoo developer mode, open Apps and update the Apps list. Search for **Jenny's Rewards** or `spx_loyalty_mobile` (the previous display name was **SPX Loyalty Mobile Connector**).
4. Use **Upgrade** on the existing module. Do not uninstall it: this is an in-place update using the same module and existing record identifiers.
5. Refresh the browser fully after the upgrade so the new menu icon and frontend assets load.

The launcher is now **Jenny’s Rewards** with the existing Jenny’s logo. It opens a branded overview, with navigation to native customers, loyalty cards, loyalty programs, app messages and website settings. The website’s **Customer App** tab keeps its existing configuration fields and gains a branded heading.

This release does not change native POS, points, products or order processing. Existing configured programs and customer cards stay in their native records. The new home does not display invented statistics or modify records when it opens. Its shortcuts use normal Odoo actions and the current user’s access rights.

The frontend uses Odoo’s bundled Owl and action service, plus the project’s existing logo and licensed Manrope fonts. No external frontend package/CDN is required. After upgrade, verify all five shortcuts and check the overview on desktop and mobile; its layout has not been rendered in a running Odoo session in the build workspace.
