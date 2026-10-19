import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { captureNativeLoyalty } from '../static/src/loyalty_handoff.js';

// Exercise the compiler from the same pinned official Odoo checkout used by
// database CI. Do not duplicate Odoo's points/coupon compilation in a fixture.
const source = readFileSync(`${process.env.ODOO_ROOT}/addons/pos_loyalty/static/src/app/services/pos_store.js`, 'utf8');
const start = source.indexOf('    async postProcessLoyalty(order) {');
assert.ok(start > 0);
const end = source.indexOf('\n    },', start) + 7;
const omit = (obj, ...keys) => Object.fromEntries(Object.entries(obj).filter(([k]) => !keys.includes(k)));
const native = new Function('omit', `return ({${source.slice(start, end)}});`)(omit);

function fixture() {
    const programs = new Map([
        [1, { program_type: 'loyalty', is_nominative: true, applies_on: 'both' }],
        [2, { program_type: 'gift_card', is_nominative: true, applies_on: 'future' }],
    ]);
    const order = {
        id: 15, lines: [], getPartner: () => ({ id: 9 }),
        _getPointsCorrection: () => 0,
        _get_reward_lines: () => [],
        uiState: { couponPointChanges: {} },
    };
    const selected = { id: 99 };
    const calls = [];
    const data = { async call(...args) { calls.push(args); return {}; } };
    const pos = {
        data, models: { 'loyalty.program': programs },
        getOrder: () => selected,
        async orderUpdateLoyaltyPrograms() {
            assert.equal(this.getOrder(), order);
            await this.data.call('loyalty.card', 'search_read', []);
            order.uiState.couponPointChanges = {
                10: { coupon_id: 10, program_id: 1, points: 15, appliedRules: [1] },
                11: { coupon_id: 11, program_id: 2, points: 50 },
            };
        },
        postProcessLoyalty: native.postProcessLoyalty,
        env: { services: { report: { doAction() { assert.fail('No premature report'); } } } },
    };
    return { pos, order, selected, data, calls };
}

test('captures native earned/spent payload without confirmation or changing selection', async () => {
    const { pos, order, selected, data, calls } = fixture();
    order._get_reward_lines = () => [{
        reward_id: { program_id: { id: 1 }, program_type: 'loyalty' },
        coupon_id: { id: 10 }, points_cost: 5, reward_identifier_code: 'native-reward',
    }];
    const payload = await captureNativeLoyalty(pos, order);
    assert.deepEqual(payload, { 10: {
        coupon_id: 10, program_id: 1, points: 10, points_earned: 15,
        points_spent: 5, partner_id: 9, line_codes: ['native-reward'],
    } });
    assert.equal(pos.getOrder(), selected);
    assert.equal(pos.data, data);
    assert.equal(calls.length, 1);
    assert.equal(calls[0][0], 'loyalty.card');
    payload[10].points = 999;
    assert.equal(order.uiState.couponPointChanges[10].points, 15);
});

test('historical recovery uses only server-approved programs', async () => {
    const { pos, order } = fixture();
    assert.deepEqual(await captureNativeLoyalty(pos, order, []), {});
    assert.equal((await captureNativeLoyalty(pos, order, [1]))[10].points, 15);
});

test('wrong-order confirmation cannot escape the scoped compiler', async () => {
    const { pos, order, data } = fixture();
    pos.postProcessLoyalty = async function () {
        await this.data.call('pos.order', 'confirm_coupon_programs', [99, {}]);
    };
    await assert.rejects(captureNativeLoyalty(pos, order), /order mismatch/);
    assert.equal(pos.data, data);
});
