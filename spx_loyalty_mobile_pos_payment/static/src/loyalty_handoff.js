/** @odoo-module **/

/**
 * Run the native POS compiler against a scoped view of one order. Capture its
 * confirm payload, without issuing that RPC or changing the cashier's selection.
 * All earning calculations and reward corrections are still Odoo's own code.
 */
export async function captureNativeLoyalty(pos, order, allowedPrograms = null) {
    let couponData = {};
    const scopedData = new Proxy(pos.data, {
        get(target, key) {
            if (key === "call") {
                return async (model, method, args, ...rest) => {
                    if (model === "pos.order" && method === "confirm_coupon_programs") {
                        if (args[0] !== order.id) {
                            throw new Error("Loyalty handoff order mismatch");
                        }
                        couponData = structuredClone(args[1]);
                        return {}; // No updates, reports or communications before payment.
                    }
                    return target.call(model, method, args, ...rest);
                };
            }
            const value = Reflect.get(target, key, target);
            return typeof value === "function" ? value.bind(target) : value;
        },
    });
    const scopedPos = new Proxy(pos, {
        get(target, key, receiver) {
            if (key === "getOrder") {
                return () => order;
            }
            if (key === "data") {
                return scopedData;
            }
            return Reflect.get(target, key, receiver);
        },
    });
    await scopedPos.orderUpdateLoyaltyPrograms();
    await scopedPos.postProcessLoyalty(order);
    return Object.fromEntries(Object.entries(couponData).filter(([, data]) => {
        const program = pos.models["loyalty.program"].get(data.program_id);
        return program?.program_type === "loyalty" &&
            (!allowedPrograms || allowedPrograms.includes(data.program_id));
    }));
}

