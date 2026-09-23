/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class JennysRewardsHome extends Component {
    static template = "spx_loyalty_mobile.Home";
    static props = ["*"];

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ opening: null });
        this.shortcuts = [
            {
                key: "customers", action: "customers_action", title: _t("Customers"),
                description: _t("Care for the people behind every visit."),
                link: _t("Open customers"), tone: "blue",
                icon: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-3.87M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0",
            },
            {
                key: "cards", action: "cards_action", title: _t("Loyalty cards"),
                description: _t("Find a member, their card and their points."),
                link: _t("Open loyalty cards"), tone: "gold",
                icon: "M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2ZM2 9h20M6 15h3M13 15h5",
            },
            {
                key: "programs", action: "programs_action", title: _t("Loyalty programs"),
                description: _t("Manage earning rules and member rewards."),
                link: _t("Open programs"), tone: "violet",
                icon: "M20 12v8H4v-8M2 7h20v5H2zM12 7v13M12 7H7.5A2.5 2.5 0 1 1 10 4.5L12 7ZM12 7h4.5A2.5 2.5 0 1 0 14 4.5L12 7Z",
            },
            {
                key: "messages", action: "message_action", title: _t("Messages"),
                description: _t("Bring a personal touch to the app inbox."),
                link: _t("Open messages"), tone: "green",
                icon: "M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5ZM8 10h8M8 14h5",
            },
            {
                key: "birthday", action: "birthday_customers_action", title: _t("Customer birthdays"),
                description: _t("Upcoming birthdays, native balances and days left to enjoy."),
                link: _t("Manage birthdays"), tone: "gold",
                icon: "M3 8h18v4H3zM5 12v9h14v-9M12 8v13M12 8H8a3 3 0 1 1 3-3zM12 8h4a3 3 0 1 0-3-3z",
            },
            {
                key: "events", action: "announcement_action", title: _t("Event announcements"),
                description: _t("Publish or schedule a little news from Jenny’s."),
                link: _t("Open announcements"), tone: "blue",
                icon: "M3 10h4l12-5v14L7 14H3zM7 14l2 7h3l-2-6",
            },
            {
                key: "gifts", action: "gift_cards_action", title: _t("Gift cards"),
                description: _t("Your existing gift cards, managed in the usual way."),
                link: _t("Open gift cards"), tone: "green",
                icon: "M3 5h18v14H3zM3 10h18M7 15h3M12 5v14",
            },
            {
                key: "sent-gifts", action: "gift_delivery_action", title: _t("Sent gifts"),
                description: _t("Follow recipient details and email delivery."),
                link: _t("View sent gifts"), tone: "gold",
                icon: "M3 5h18v14H3zM3 5l9 7 9-7",
            },
        ];
    }

    async openAction(key, action) {
        if (this.state.opening) {
            return;
        }
        this.state.opening = key;
        try {
            // Native actions retain the current user's model permissions and workflows.
            await this.action.doAction(`spx_loyalty_mobile.${action}`);
        } catch {
            this.notification.add(_t("This screen could not open. Please try again."), {
                type: "danger",
            });
        } finally {
            this.state.opening = null;
        }
    }
}

registry.category("actions").add("spx_loyalty_mobile.home", JennysRewardsHome);
