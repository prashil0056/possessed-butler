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

// --- DOM helpers ---
const $ = (id) => document.getElementById(id);

// --- WebSocket ---
function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${proto}//${location.host}/ws`;
    state.ws = new WebSocket(url);

    state.ws.onopen = () => {
        setConnectionStatus('connected', '🟢 connected');
    };

    state.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleMessage(msg);
    };

    state.ws.onclose = () => {
        setConnectionStatus('disconnected', '🔴 disconnected — retrying…');
        setTimeout(connectWS, 2000);
    };

    state.ws.onerror = () => {
        state.ws.close();
    };
}

function setConnectionStatus(cls, text) {
    const el = $('connection-status');
    el.className = cls;
    el.textContent = text;
}

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
            addResult('defense-status', 'info', 'Defense updated', 'New config applies to next attack');
            break;
        case 'attack_result':
            addAttackResult(msg.attack);
            state.stats = msg.stats;
            renderStats();
            break;
        case 'round_started':
            state.round = msg.round;
            renderTimer();
            addResult('defense-status', 'info', 'Round started', '10-minute countdown running');
            break;
        case 'round_reset':
            state.round = msg.round;
            state.stats = msg.stats;
            $('attack-results').innerHTML = '';
            $('defense-status').innerHTML = '';
            renderTimer();
            renderStats();
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
    const remaining = state.round.remaining || 0;
    const min = Math.floor(remaining / 60);
    const sec = remaining % 60;
    const text = `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    const timer = $('timer');
    timer.textContent = text;

    timer.classList.remove('warning', 'danger');
    if (remaining <= 60 && remaining > 0) timer.classList.add('danger');
    else if (remaining <= 180 && remaining > 0) timer.classList.add('warning');
}

function renderStats() {
    $('stat-total').textContent = state.stats.total;
    $('stat-blocked').textContent = state.stats.blocked;
    $('stat-breached').textContent = state.stats.breached;
    $('stat-rate').textContent = `${(state.stats.block_rate * 100).toFixed(1)}%`;
}

function addResult(containerId, badgeType, title, detail) {
    const container = $(containerId);
    const item = document.createElement('div');
    item.className = 'result-item';

    const badge = document.createElement('span');
    badge.className = `result-badge badge-${badgeType}`;
    badge.textContent = title;

    item.appendChild(badge);
    if (detail) {
        const d = document.createElement('div');
        d.className = 'result-payload';
        d.textContent = detail;
        item.appendChild(d);
    }

    container.insertBefore(item, container.firstChild);

    // Keep only latest 20
    while (container.children.length > 20) {
        container.removeChild(container.lastChild);
    }
}

function addAttackResult(attack) {
    const container = $('attack-results');
    const item = document.createElement('div');
    item.className = 'result-item';

    const badge = document.createElement('span');
    const status = attack.blocked ? 'blocked' : 'breached';
    badge.className = `result-badge badge-${status}`;
    badge.textContent = attack.blocked ? `BLOCKED (${attack.block_layer || '?'})` : 'BREACHED';

    const payload = document.createElement('div');
    payload.className = 'result-payload';
    payload.textContent = `[${attack.technique}] ${attack.payload.slice(0, 120)}`;

    item.appendChild(badge);
    item.appendChild(payload);

    if (attack.blocked && attack.reason) {
        const reason = document.createElement('div');
        reason.className = 'result-response';
        reason.textContent = `Reason: ${attack.reason}`;
        item.appendChild(reason);
    } else if (attack.response_snippet) {
        const resp = document.createElement('div');
        resp.className = 'result-response';
        resp.textContent = `Response: ${attack.response_snippet}`;
        item.appendChild(resp);
    }

    container.insertBefore(item, container.firstChild);
    while (container.children.length > 20) {
        container.removeChild(container.lastChild);
    }

    // Also show on defense side (they see what's coming)
    const defContainer = $('defense-status');
    const defItem = item.cloneNode(true);
    defContainer.insertBefore(defItem, defContainer.firstChild);
    while (defContainer.children.length > 20) {
        defContainer.removeChild(defContainer.lastChild);
    }
}

// --- Actions ---
async function sendAttack() {
    const payload = $('attack-payload').value.trim();
    if (!payload) {
        alert('Enter a payload first');
        return;
    }

    const btn = $('send-attack');
    btn.disabled = true;
    btn.textContent = 'Running…';

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
            const err = await resp.json();
            addResult('attack-results', 'breached', 'ERROR', JSON.stringify(err));
        }
    } catch (e) {
        addResult('attack-results', 'breached', 'NETWORK ERROR', String(e));
    } finally {
        btn.disabled = false;
        btn.textContent = 'Send Attack';
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
    btn.disabled = true;
    btn.textContent = 'Saving…';

    try {
        const resp = await fetch('/api/defense', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newDefense),
        });
        if (!resp.ok) {
            const err = await resp.json();
            addResult('defense-status', 'breached', 'ERROR', JSON.stringify(err));
        }
    } catch (e) {
        addResult('defense-status', 'breached', 'NETWORK ERROR', String(e));
    } finally {
        btn.disabled = false;
        btn.textContent = 'Update Defense';
    }
}

async function startRound() {
    await fetch('/api/round/start', { method: 'POST' });
}

async function resetRound() {
    if (!confirm('Reset round timer and clear all stats?')) return;
    await fetch('/api/round/reset', { method: 'POST' });
}

// --- Event bindings ---
$('send-attack').addEventListener('click', sendAttack);
$('update-defense').addEventListener('click', updateDefense);
$('start-round').addEventListener('click', startRound);
$('reset-round').addEventListener('click', resetRound);

// Ctrl+Enter in textarea sends attack
$('attack-payload').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        sendAttack();
    }
});

// Boot
connectWS();
