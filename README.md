# Jenny’s Odoo connector and native app

Odoo **19.0.4.2.0** · Flutter app source **0.8.0+15**

Read [installation, retention options and validation status](INSTALL_AND_RETENTION.md) before deployment. Both addon directories are required. **Upgrade an existing installation before testing uninstall**; earlier connector versions do not retain their app data.

| Directory | Purpose |
| --- | --- |
| `spx_loyalty_mobile` | Active connector, customer API, administrator screens and app jobs |
| `spx_loyalty_mobile_data` | Passive app records/settings retained by default on connector uninstall |
| `mobile` | Android/iOS Flutter source, publisher-side connection builder and tests |

Customer screens contain no connection/test controls. Native Odoo customers, orders, payments, loyalty and gift-card balances remain authoritative. Explicit full app-data removal is available through Odoo’s confirmation flow.

This branch is for testing. A successful local source check is not approval for live installation; follow the acceptance checks linked above.
