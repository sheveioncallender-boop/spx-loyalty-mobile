/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import "@pos_loyalty/app/services/pos_store";
import "@pos_online_payment/app/services/pos_store";
import { captureNativeLoyalty } from "./loyalty_handoff";

patch(PosStore.prototype, {
    async postProcessLoyalty(order) {
        const result = await super.postProcessLoyalty(...arguments);
        if (order.isSynced && order.lines.some((line) => line.refunded_orderline_id)) {
            try {
                const response = await this.data.call(
                    "pos.order", "spx_reconcile_refund_loyalty", [order.id]
                );
                if (response.card_ids?.length) {
                    await this.data.read("loyalty.card", response.card_ids);
                }
            } catch {
                this.notification.add(
                    "Refund completed. Loyalty points need staff review on the refund order.",
                    { type: "warning", sticky: true }
                );
            }
        }
        return result;
    },

    async updateOnlinePaymentsDataWithServer(order, amount) {
        if (typeof amount === "number" && amount > 0 && order.isSynced) {
            // Native validation already synced the bill at this point. Persist
            // the native loyalty payload BEFORE exposing the online pay amount.
            const data = await captureNativeLoyalty(this, order);
            await this.data.call("pos.order", "spx_prepare_loyalty", [order.id, data]);
        }
        return await super.updateOnlinePaymentsDataWithServer(...arguments);
    },

    async setup() {
        await super.setup(...arguments);
        try {
            const pending = await this.data.call(
                "pos.order", "spx_loyalty_recovery_orders", [this.config.id]
            );
            if (!pending.orders?.["pos.order"]?.length) {
                return;
            }
            const data = await this.data.missingRecursive(pending.orders);
            const loaded = this.models.connectNewData(data);
            for (const order of loaded["pos.order"]) {
                const allowed = pending.programs[order.id];
                if (!allowed?.length) {
                    continue;
                }
                const coupons = await captureNativeLoyalty(this, order, allowed);
                if (!Object.keys(coupons).length) {
                    continue;
                }
                const response = await this.data.call(
                    "pos.order", "spx_prepare_loyalty", [order.id, coupons, true]
                );
                const ids = response.result?.coupon_updates?.map((coupon) => coupon.id) || [];
                if (ids.length) {
                    await this.data.read("loyalty.card", ids);
                }
            }
        } catch {
            // The next POS startup can retry. Never modify payments or mark a
            // recovery complete if the native calculation/confirmation failed.
            console.warn("Jenny's Rewards: loyalty recovery will retry on POS reconnect.");
        }
    },
});

