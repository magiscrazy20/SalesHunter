// ── Card Detail Popup ──
(function() {
    // Create popup elements once
    const overlay = document.createElement('div');
    overlay.className = 'card-popup-overlay';
    overlay.onclick = closeCardPopup;

    const popup = document.createElement('div');
    popup.className = 'card-popup';
    popup.innerHTML = '<div class="card-popup-header"><h3 id="cardPopupTitle"></h3><button class="card-popup-close" onclick="closeCardPopup()">&times;</button></div><div class="card-popup-body" id="cardPopupBody"></div>';

    document.addEventListener('DOMContentLoaded', function() {
        document.body.appendChild(overlay);
        document.body.appendChild(popup);

        // Attach click to all cards with data-detail
        document.querySelectorAll('[data-detail]').forEach(function(card) {
            card.addEventListener('click', function(e) {
                // Don't trigger if clicking a link or button inside the card
                if (e.target.closest('a[href]:not([href="#"])') || e.target.closest('button')) return;
                e.preventDefault();
                e.stopPropagation();
                var title = card.getAttribute('data-title') || 'Details';
                var detail = card.getAttribute('data-detail');
                try {
                    var data = JSON.parse(detail);
                    showCardPopup(title, data);
                } catch(err) {
                    showCardPopup(title, [['Info', detail]]);
                }
            });
        });
    });
})();

function showCardPopup(title, rows) {
    document.getElementById('cardPopupTitle').textContent = title;
    var html = '<table>';
    rows.forEach(function(r) { html += '<tr><td>' + esc(r[0]) + '</td><td>' + esc(String(r[1])) + '</td></tr>'; });
    html += '</table>';
    document.getElementById('cardPopupBody').innerHTML = html;
    document.querySelector('.card-popup-overlay').style.display = 'block';
    document.querySelector('.card-popup').style.display = 'block';
}

function closeCardPopup() {
    document.querySelector('.card-popup-overlay').style.display = 'none';
    document.querySelector('.card-popup').style.display = 'none';
}

// Close on Escape key
document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeCardPopup(); });

// ── HTML escaping ──
function esc(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

// ── Error helpers ──
function showError(msg) { const el = document.getElementById('error'); if (el) { el.textContent = msg; el.style.display = 'block'; } }
function hideError() { const el = document.getElementById('error'); if (el) el.style.display = 'none'; }

// ── Copy to clipboard ──
function copyText(text, el) {
    navigator.clipboard.writeText(text);
    el.textContent = '\u2713';
    setTimeout(() => el.innerHTML = '&#128203;', 1500);
}

// ── Sleep ──
function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── CSRF token from cookie ──
function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (const c of cookies) {
        const [name, val] = c.trim().split('=');
        if (name === 'csrftoken') return val;
    }
    return '';
}

// ── POST helper with CSRF ──
async function postJSON(url, data) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify(data),
    });
}

// ── Manual email add ──
function manualEmail(el) {
    const leadId = el.dataset.id;
    const cell = document.getElementById(`email-cell-${leadId}`);
    // Collect existing emails
    const existingEmails = [];
    cell.querySelectorAll('.email-list a').forEach(a => existingEmails.push(a.textContent.trim()));

    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'Enter email...';
    input.style.cssText = 'background:#0f172a;border:1px solid #6366f1;border-radius:4px;padding:4px 8px;color:#e2e8f0;font-size:12px;width:100%;outline:none;margin-top:4px;';

    // Replace the "+ Add" span with input, keep existing emails
    el.replaceWith(input);
    input.focus();

    async function saveEmail() {
        const email = input.value.trim();
        if (!email || !email.includes('@')) {
            input.replaceWith(createAddSpan(leadId));
            return;
        }
        try {
            const allEmails = [...existingEmails, email];
            await postJSON(`/form/master/api/lead/${leadId}/edit/`, { emails: allEmails });
            // Rebuild the cell
            let html = '<ul class="email-list">';
            allEmails.forEach(e => { html += `<li><a href="mailto:${esc(e)}">${esc(e)}</a></li>`; });
            html += '</ul>';
            html += `<span class="editable-email" data-id="${leadId}" onclick="manualEmail(this)" style="color:#475569;cursor:pointer;font-size:10px;">&#43; Add more</span>`;
            cell.innerHTML = html;
            showToast('Email saved');
        } catch (e) {
            input.replaceWith(createAddSpan(leadId));
        }
    }

    input.addEventListener('blur', saveEmail);
    input.addEventListener('keydown', e => {
        if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
        if (e.key === 'Escape') { input.replaceWith(createAddSpan(leadId)); }
    });
}

function createAddSpan(leadId) {
    const span = document.createElement('span');
    span.className = 'editable-email';
    span.dataset.id = leadId;
    span.onclick = function() { manualEmail(this); };
    span.style.cssText = 'color:#475569;cursor:pointer;font-size:11px;';
    span.innerHTML = '&#43; Add';
    return span;
}

// ── Progress updater ──
function updateProgressBar(barId, labelId, pctId, done, total) {
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    const pctEl = document.getElementById(pctId);
    const labelEl = document.getElementById(labelId);
    const barEl = document.getElementById(barId);
    if (pctEl) pctEl.textContent = pct + '%';
    if (labelEl) labelEl.textContent = done === total ? `Completed ${done} / ${total}` : `Scanning ${done} / ${total}`;
    if (barEl) {
        barEl.style.width = pct + '%';
        barEl.style.background = (done === total && total > 0) ? '#059669' : '#6366f1';
    }
    if (pctEl && done === total && total > 0) pctEl.style.color = '#4ade80';
    else if (pctEl) pctEl.style.color = '#6366f1';
}

// ── Email finder for a single company ──
async function findEmailForRow(idx, website, domain, scrapedEmails, totalEmailsFoundRef) {
    if (!website && !domain) return;
    const cell = document.getElementById(`email-cell-${idx}`);
    if (!cell) return;
    cell.innerHTML = '<span class="email-scanning"><span class="mini-spinner"></span> Scanning...</span>';

    try {
        const resp = await postJSON('/form/master/api/find-emails/', { website, domain });
        const data = await resp.json();
        const emails = data.emails || [];
        scrapedEmails[idx] = emails;

        if (emails.length > 0) {
            totalEmailsFoundRef.count += emails.length;
            const counterEl = document.getElementById('emailsFound');
            if (counterEl) counterEl.textContent = totalEmailsFoundRef.count;
            cell.innerHTML = `<ul class="email-list">${emails.map(e =>
                `<li><a href="mailto:${esc(e)}">${esc(e)}</a><span class="email-copy" onclick="copyText('${esc(e)}', this)">&#128203;</span></li>`
            ).join('')}</ul>`;
        } else {
            cell.innerHTML = '<span style="color:#475569; font-size:12px;">No emails found</span>';
        }
    } catch (err) {
        cell.innerHTML = '<span style="color:#ef4444; font-size:12px;">Scan failed</span>';
    }
}

// ── Batch email finder ──
async function autoFindAllEmails(allResults, getWebsite, getDomain, scrapedEmails, totalEmailsFoundRef, progressIds) {
    let done = 0;
    const scannable = allResults.filter((r, i) => getWebsite(r) || getDomain(r));
    const total = scannable.length;
    if (total === 0) return;

    const progressCard = document.getElementById('progressCard');
    if (progressCard) progressCard.style.display = 'block';
    updateProgressBar(progressIds.bar, progressIds.label, progressIds.pct, 0, total);

    for (let i = 0; i < allResults.length; i += 3) {
        const batch = [];
        for (let j = i; j < Math.min(i + 3, allResults.length); j++) {
            const ws = getWebsite(allResults[j]);
            const dm = getDomain(allResults[j]);
            if (!scrapedEmails[j] && (ws || dm)) {
                batch.push(findEmailForRow(j, ws, dm, scrapedEmails, totalEmailsFoundRef).then(() => {
                    done++;
                    updateProgressBar(progressIds.bar, progressIds.label, progressIds.pct, done, total);
                }));
            }
        }
        await Promise.all(batch);
    }
}

// ── CSV export ──
function exportCSVData(headers, rows, filename) {
    let csv = headers.join(',') + '\n';
    rows.forEach(r => { csv += r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',') + '\n'; });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// ── Create session (call at start of search so it appears in sidebar immediately) ──
async function createSession(source, searchParams) {
    try {
        const resp = await postJSON('/form/master/api/create-session/', { source, search_params: searchParams });
        if (resp.ok) {
            const data = await resp.json();
            return data.session_id;
        }
    } catch (e) { console.error('Create session failed:', e); }
    return null;
}

// ── Update session with leads (call after process completes) ──
async function updateSession(sessionId, leads, status = 'completed') {
    if (!sessionId) return;
    try {
        const resp = await postJSON('/form/master/api/update-session/', { session_id: sessionId, leads, status });
        if (resp.ok) showToast(`${leads.length} leads saved`);
    } catch (e) { console.error('Update session failed:', e); }
}

// ── Toast ──
function showToast(msg) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

