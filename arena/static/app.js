const state = {
    ws: null,
    defense: {
        input_guard: true,
        output_guard: true,
        isolation: true,
        hardened_butler: false,
    },
    round: { started: false, remaining: 600, duration: 600 },
    stats: { total: 0, blocked: 0, breached: 0, block_rate: 0 },
};

const $ = (id) => document.getElementById(id);

// --- WebSocket ---

function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/ws`;
    state.ws = new WebSocket(url);

    state.ws.onopen = () => {
        setConnectionStatus(true);
    };

    state.ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleMessage(msg);
        } catch (e) {
            console.error('ws parse error', e);
        }
    };

    state.ws.onclose = () => {
        setConnectionStatus(false);
        setTimeout(connectWS, 2000);
    };

    state.ws.onerror = () => state.ws.close();
}

function setConnectionStatus(connected) {
    const el = $('connection-status');
    if (!el) return;
    el.textContent = connected ? 'live' : 'offline';
    el.classList.toggle('connected', connected);
}

// --- Message handling ---

function handleMessage(msg) {
    switch (msg.type) {
        case 'initial_state':
            state.defense = msg.defense;
            state.round = msg.round;
            state.stats = msg.stats;
            renderDefense();
            renderTimer();
            renderStats();
            break;

        case 'tick':
            state.round = msg.round;
            state.stats = msg.stats;
            renderTimer();
            renderStats();
            break;

        case 'defense_updated':
            state.defense = msg.defense;
            renderDefense();
            addResult('defense-status', 'info', 'Defense updated', 'applies to next attack', null);
            break;

        case 'attack_result':
            addAttackResult(msg.attack);
            state.stats = msg.stats;
            renderStats();
            break;

        case 'round_started':
            state.round = msg.round;
            renderTimer();
            addResult('defense-status', 'info', 'Round started', '10-minute countdown running', null);
            break;

        case 'round_reset':
            state.round = msg.round;
            state.stats = msg.stats;
            $('attack-results').innerHTML = '';
            $('defense-status').innerHTML = '';
            renderTimer();
            renderStats();
            updateCounts();
            break;
    }
}

// --- Rendering ---

function renderDefense() {
    $('def-input-guard').checked = state.defense.input_guard;
    $('def-output-guard').checked = state.defense.output_guard;
    $('def-isolation').checked = state.defense.isolation;
    $('def-hardened').checked = state.defense.hardened_butler;
}

function renderTimer() {
    const remaining = Math.max(0, state.round.remaining || 0);
    const min = Math.floor(remaining / 60);
    const sec = remaining % 60;
    const text = `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;

    const timer = $('timer');
    if (!timer) return;
    timer.textContent = text;

    timer.classList.remove('warning', 'danger');
    if (remaining <= 60 && remaining > 0) timer.classList.add('danger');
    else if (remaining <= 180 && remaining > 0) timer.classList.add('warning');
}

function renderStats() {
    $('stat-total').textContent = state.stats.total ?? 0;
    $('stat-blocked').textContent = state.stats.blocked ?? 0;
    $('stat-breached').textContent = state.stats.breached ?? 0;

    const rate = state.stats.block_rate ?? 0;
    $('stat-rate').textContent = state.stats.total > 0 ? `${(rate * 100).toFixed(0)}%` : '—';
}

function updateCounts() {
    const attackItems = $('attack-results').children.length;
    const defenseItems = $('defense-status').children.length;
    $('attack-count').textContent = `${attackItems} ${attackItems === 1 ? 'attack' : 'attacks'}`;
    $('defense-count').textContent = `${defenseItems} ${defenseItems === 1 ? 'event' : 'events'}`;
}

// --- Result rendering ---

function buildResultItem(variant, badgeText, payloadText, reasonText, techText) {
    const item = document.createElement('div');
    item.className = `result-item ${variant}`;

    const top = document.createElement('div');
    top.className = 'result-top';

    const badge = document.createElement('span');
    badge.className = `result-badge badge-${variant}`;
    badge.textContent = badgeText;
    top.appendChild(badge);

    if (techText) {
        const tech = document.createElement('span');
        tech.className = 'result-tech';
        tech.textContent = techText;
        top.appendChild(tech);
    }

    item.appendChild(top);

    if (payloadText) {
        const p = document.createElement('div');
        p.className = 'result-payload';
        p.textContent = payloadText;
        item.appendChild(p);
    }

    if (reasonText) {
        const r = document.createElement('div');
        r.className = 'result-reason';
        r.textContent = reasonText;
        item.appendChild(r);
    }

    return item;
}

function addResult(containerId, variant, badgeText, payloadText, reasonText) {
    const container = $(containerId);
    if (!container) return;
    const item = buildResultItem(variant, badgeText, payloadText, reasonText, null);
    container.insertBefore(item, container.firstChild);

    while (container.children.length > 30) {
        container.removeChild(container.lastChild);
    }
    updateCounts();
}

function addAttackResult(attack) {
    const variant = attack.blocked ? 'blocked' : 'breached';
    const badgeText = attack.blocked
        ? `Blocked · ${attack.block_layer || '?'}`
        : 'Breached';
    const payloadText = attack.payload.length > 140
        ? attack.payload.slice(0, 140) + '…'
        : attack.payload;
    const reasonText = attack.blocked
        ? attack.reason
        : (attack.response_snippet || 'butler responded');

    const attackItem = buildResultItem(variant, badgeText, payloadText, reasonText, attack.technique);
    const defenseItem = buildResultItem(variant, badgeText, payloadText, reasonText, attack.technique);

    const attackContainer = $('attack-results');
    const defenseContainer = $('defense-status');

    attackContainer.insertBefore(attackItem, attackContainer.firstChild);
    defenseContainer.insertBefore(defenseItem, defenseContainer.firstChild);

    while (attackContainer.children.length > 30) {
        attackContainer.removeChild(attackContainer.lastChild);
    }
    while (defenseContainer.children.length > 30) {
        defenseContainer.removeChild(defenseContainer.lastChild);
    }

    updateCounts();
}

// --- Actions ---

async function sendAttack() {
    const payload = $('attack-payload').value.trim();
    if (!payload) {
        $('attack-payload').focus();
        return;
    }

    const btn = $('send-attack');
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>Running…</span><span class="btn-arrow">↻</span>';

    try {
        const resp = await fetch('/api/attack', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                payload,
                technique: $('attack-technique').value,
            }),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            addResult('attack-results', 'breached', 'Error', payload, JSON.stringify(err));
        }
    } catch (e) {
        addResult('attack-results', 'breached', 'Network error', payload, String(e));
    } finally {
        btn.disabled = false;
        btn.innerHTML = original;
    }
}

async function updateDefense() {
    const newDefense = {
        input_guard: $('def-input-guard').checked,
        output_guard: $('def-output-guard').checked,
        isolation: $('def-isolation').checked,
        hardened_butler: $('def-hardened').checked,
        extra_patterns: [],
    };

    const btn = $('update-defense');
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>Saving…</span><span class="btn-arrow">↻</span>';

    try {
        const resp = await fetch('/api/defense', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newDefense),
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            addResult('defense-status', 'breached', 'Error', 'defense update failed', JSON.stringify(err));
        }
    } catch (e) {
        addResult('defense-status', 'breached', 'Network error', 'defense update failed', String(e));
    } finally {
        btn.disabled = false;
        btn.innerHTML = original;
    }
}

async function startRound() {
    try {
        await fetch('/api/round/start', { method: 'POST' });
    } catch (e) {
        console.error(e);
    }
}

async function resetRound() {
    if (!confirm('Reset round timer and clear all results?')) return;
    try {
        await fetch('/api/round/reset', { method: 'POST' });
    } catch (e) {
        console.error(e);
    }
}

// --- Bindings ---

document.addEventListener('DOMContentLoaded', () => {
    $('send-attack').addEventListener('click', sendAttack);
    $('update-defense').addEventListener('click', updateDefense);
    $('start-round').addEventListener('click', startRound);
    $('reset-round').addEventListener('click', resetRound);

    $('attack-payload').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            sendAttack();
        }
    });

    connectWS();
    updateCounts();
});
