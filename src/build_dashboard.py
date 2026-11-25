"""Build static entertainment dashboard HTML from data/reviews.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Guardian Film &amp; TV Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {
      --background: #120b14;
      --card: #1c1120;
      --border: #36203d;
      --foreground: #f8f4fa;
      --muted-foreground: #b8a3c2;
      --primary: #e11d48;
      --primary-foreground: #ffffff;
      --secondary: #2a1830;
      --secondary-foreground: #f3e8f7;
      --warning: #fbbf24;
      --success: #34d399;
      --error: #f87171;
      --link: #fbbf24;
    }
    html.light {
      --background: #fdf8f6;
      --card: #ffffff;
      --border: #e7d8d3;
      --foreground: #1f1219;
      --muted-foreground: #6e5863;
      --primary: #be123c;
      --primary-foreground: #ffffff;
      --secondary: #f5ebe8;
      --secondary-foreground: #2b1821;
      --warning: #d97706;
      --success: #059669;
      --error: #dc2626;
      --link: #be123c;
    }
    .line-clamp-2 {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .star-filled { color: var(--warning); }
    .star-empty { color: var(--muted-foreground); opacity: 0.35; }
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased min-h-screen">
  <div class="h-1.5 w-full bg-gradient-to-r from-[#e11d48] via-[#fbbf24] to-[#9333ea]"></div>
  <div class="max-w-7xl mx-auto space-y-5 p-4 md:p-6">

    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-[var(--border)]">
      <div>
        <div class="flex flex-wrap items-center gap-2.5">
          <span class="text-xl" aria-hidden="true">🎬</span>
          <span id="mode-badge" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">
            __MODE_BADGE__
          </span>
          <h1 class="text-xl font-bold tracking-tight">Guardian Film &amp; TV Dashboard</h1>
        </div>
        <p class="text-xs text-[var(--muted-foreground)] mt-1">
          Last __LOOKBACK_DAYS__ days (6-month window) • Updated __GENERATED_AT__ • Star ratings, platforms, Google Calendar reminders &amp; watchlist.
        </p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button onclick="toggleTheme()" class="px-3 py-1.5 rounded-md text-xs font-medium bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          Toggle Theme
        </button>
        <button onclick="exportState()" class="px-3 py-1.5 rounded-md text-xs font-medium bg-[var(--card)] border border-[var(--border)] hover:border-[var(--primary)] transition">
          Export Watchlist JSON
        </button>
      </div>
    </header>

    <!-- Summary Stats -->
    <section id="stats-bar" class="grid grid-cols-2 md:grid-cols-4 gap-3"></section>

    <!-- Navigation Tabs -->
    <nav class="flex flex-wrap items-center gap-2 border-b border-[var(--border)] pb-3">
      <button data-tab="reviews" onclick="setTab('reviews')" class="tab-btn px-3.5 py-1.5 rounded-md text-xs font-semibold transition">
        Latest Reviews
      </button>
      <button data-tab="top-rated" onclick="setTab('top-rated')" class="tab-btn px-3.5 py-1.5 rounded-md text-xs font-semibold transition">
        Best Rated (Date Order)
      </button>
      <button data-tab="reminders" onclick="setTab('reminders')" class="tab-btn px-3.5 py-1.5 rounded-md text-xs font-semibold transition">
        Reminders &amp; Ticket Drops
      </button>
      <button data-tab="watchlist" onclick="setTab('watchlist')" class="tab-btn px-3.5 py-1.5 rounded-md text-xs font-semibold transition">
        My Watchlist &amp; Archive
      </button>
    </nav>

    <!-- Filters Bar -->
    <section id="filters-bar" class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-3 flex flex-wrap items-center gap-3">
      <input
        id="search-input"
        type="text"
        placeholder="Search title, critic, genre, platform..."
        oninput="render()"
        class="flex-1 min-w-[200px] px-3 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] focus:outline-none focus:border-[var(--primary)]"
      />
      <select id="type-filter" onchange="render()" class="px-2.5 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)]">
        <option value="all">All Types (Film &amp; TV)</option>
        <option value="Movie">Movies Only</option>
        <option value="TV">TV Only</option>
      </select>
      <select id="rating-filter" onchange="render()" class="px-2.5 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)]">
        <option value="0">All Ratings</option>
        <option value="5">5★ Only</option>
        <option value="4">4★ &amp; Above</option>
        <option value="3">3★ &amp; Above</option>
      </select>
      <select id="platform-filter" onchange="render()" class="px-2.5 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)]">
        <option value="all">All Platforms</option>
      </select>
      <select id="period-filter" onchange="render()" class="px-2.5 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)]">
        <option value="all">Last 6 months (All)</option>
        <option value="7">Last 7 days</option>
        <option value="30">Last 30 days</option>
        <option value="90">Last 3 months</option>
      </select>
    </section>

    <!-- Main Content -->
    <main id="main-content" class="space-y-4"></main>
  </div>

  <!-- Review / Note Modal -->
  <div id="note-modal" class="fixed inset-0 bg-black/60 hidden items-center justify-center p-4 z-50">
    <div class="bg-[var(--card)] border border-[var(--border)] rounded-xl max-w-md w-full p-5 space-y-4 shadow-xl">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h3 id="modal-title" class="text-sm font-bold"></h3>
          <p id="modal-subtitle" class="text-xs text-[var(--muted-foreground)] mt-0.5"></p>
        </div>
        <button onclick="closeModal()" class="text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)]">✕</button>
      </div>

      <div class="space-y-3">
        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Status</label>
          <select id="modal-status" class="w-full px-2.5 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)]">
            <option value="watchlist">To Watch</option>
            <option value="seen">Seen</option>
            <option value="archived">Archived</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">My Rating</label>
          <div id="modal-stars" class="flex items-center gap-1.5 text-lg cursor-pointer"></div>
        </div>

        <div>
          <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Short Personal Review / Notes</label>
          <textarea id="modal-note" rows="3" placeholder="e.g., Loved the cinematography, watch with friends..." class="w-full px-2.5 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] focus:outline-none focus:border-[var(--primary)]"></textarea>
        </div>

        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Custom Reminder Date</label>
            <input id="modal-reminder-date" type="date" class="w-full px-2.5 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)]" />
          </div>
          <div>
            <label class="block text-xs font-medium text-[var(--muted-foreground)] mb-1">Reminder Label</label>
            <input id="modal-reminder-label" type="text" placeholder="e.g., BFI Presale / Stream" class="w-full px-2.5 py-1.5 rounded-md text-xs bg-[var(--background)] border border-[var(--border)]" />
          </div>
        </div>
      </div>

      <div class="flex items-center justify-between pt-2 border-t border-[var(--border)]">
        <button onclick="removeFromWatchlist()" class="text-xs text-[var(--error)] hover:underline">
          Remove from Watchlist
        </button>
        <div class="flex items-center gap-2">
          <button onclick="closeModal()" class="px-3 py-1.5 rounded-md text-xs border border-[var(--border)]">Cancel</button>
          <button onclick="saveModal()" class="px-3 py-1.5 rounded-md text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">Save</button>
        </div>
      </div>
    </div>
  </div>

  <script>
    const STORAGE_KEY = 'guardian_entertainment_dashboard_v1';
    const GENERATED_AT = '__GENERATED_AT__';
    const REVIEWS_DATA = __REVIEWS_JSON__;

    let state = loadState();
    let editingId = null;
    let modalRating = 0;

    function loadState() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) return JSON.parse(raw);
      } catch (e) {}
      return { activeTab: 'reviews', watchlistFilter: 'all', items: {} };
    }

    function saveState() {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
    }

    function toggleTheme() {
      document.documentElement.classList.toggle('light');
    }

    function setTab(tab) { state.activeTab = tab; saveState(); render(); }
    function setWatchlistFilter(f) { state.watchlistFilter = f; saveState(); render(); }

    function renderStars(count, max = 5) {
      let html = '<span class="inline-flex items-center tracking-tight" aria-label="' + count + ' out of 5 stars">';
      for (let i = 1; i <= max; i++) {
        html += `<span class="${i <= count ? 'star-filled' : 'star-empty'}">★</span>`;
      }
      return html + '</span>';
    }

    function daysUntil(dateStr) {
      const today = new Date(GENERATED_AT + 'T00:00:00');
      const target = new Date(dateStr + 'T00:00:00');
      return Math.round((target - today) / (1000 * 60 * 60 * 24));
    }

    function formatBadgeDate(dateStr) {
      const diff = daysUntil(dateStr);
      if (diff === 0) return { text: 'Today', cls: 'bg-[var(--success)]/15 text-[var(--success)] border-[var(--success)]/30' };
      if (diff === 1) return { text: 'Tomorrow', cls: 'bg-[var(--warning)]/15 text-[var(--warning)] border-[var(--warning)]/30' };
      if (diff > 1 && diff <= 7) return { text: `In ${diff} days`, cls: 'bg-[var(--primary)]/15 text-[var(--primary)] border-[var(--primary)]/30' };
      if (diff > 7) return { text: dateStr, cls: 'bg-[var(--secondary)] text-[var(--secondary-foreground)] border-[var(--border)]' };
      return { text: 'Released', cls: 'bg-[var(--secondary)] text-[var(--muted-foreground)] border-[var(--border)]' };
    }

    function populatePlatformFilter() {
      const select = document.getElementById('platform-filter');
      const current = select.value;
      const platforms = [...new Set(REVIEWS_DATA.map(r => r.platform))].sort();
      select.innerHTML = '<option value="all">All Platforms</option>' +
        platforms.map(p => `<option value="${p}">${p}</option>`).join('');
      if (platforms.includes(current)) select.value = current;
    }

    function getFilteredReviews() {
      const q = (document.getElementById('search-input')?.value || '').toLowerCase().trim();
      const type = document.getElementById('type-filter')?.value || 'all';
      const minRating = parseInt(document.getElementById('rating-filter')?.value || '0', 10);
      const platform = document.getElementById('platform-filter')?.value || 'all';
      const period = document.getElementById('period-filter')?.value || 'all';
      const today = new Date(GENERATED_AT + 'T23:59:59');

      return REVIEWS_DATA.filter(r => {
        if (type !== 'all' && r.type !== type) return false;
        if (r.stars < minRating) return false;
        if (platform !== 'all' && r.platform !== platform) return false;
        if (period !== 'all') {
          const days = parseInt(period, 10);
          const reviewDt = new Date(r.reviewDate + 'T00:00:00');
          if ((today - reviewDt) / (1000 * 60 * 60 * 24) > days) return false;
        }
        if (q) {
          const hay = `${r.title} ${r.critic} ${r.genre} ${r.platform} ${r.verdict}`.toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      });
    }

    function googleCalendarUrl(title, dateStr, description) {
      const start = dateStr.replace(/-/g, '');
      const endDt = new Date(dateStr + 'T00:00:00');
      endDt.setDate(endDt.getDate() + 1);
      const end = endDt.toISOString().slice(0, 10).replace(/-/g, '');
      const params = new URLSearchParams({
        action: 'TEMPLATE',
        text: title,
        dates: `${start}/${end}`,
        details: description
      });
      return `https://calendar.google.com/calendar/render?${params.toString()}`;
    }

    function downloadICS(title, dateStr, description) {
      const cleanDate = dateStr.replace(/-/g, '');
      const ics = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Guardian Entertainment Tracker//EN',
        'BEGIN:VEVENT', `UID:${Date.now()}@guardian-tracker`, `DTSTAMP:${cleanDate}T090000Z`,
        `DTSTART;VALUE=DATE:${cleanDate}`, `SUMMARY:${title}`, `DESCRIPTION:${description.replace(/\n/g, ' ')}`,
        'END:VEVENT', 'END:VCALENDAR'
      ].join('\r\n');
      const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.ics`;
      a.click();
      URL.revokeObjectURL(url);
    }

    function quickToggleWatchlist(id) {
      if (state.items[id]) { openModal(id); return; }
      const item = REVIEWS_DATA.find(r => r.id === id);
      state.items[id] = {
        status: 'watchlist', myRating: 0, note: '',
        reminderDate: item?.ticketEvent?.date || item?.releaseDate || '',
        reminderLabel: item?.ticketEvent ? `${item.ticketEvent.type} (${item.ticketEvent.venue})` : 'Release Date'
      };
      saveState(); render();
    }

    function quickMarkSeen(id) {
      if (!state.items[id]) state.items[id] = { status: 'seen', myRating: 0, note: '', reminderDate: '', reminderLabel: '' };
      else state.items[id].status = state.items[id].status === 'seen' ? 'watchlist' : 'seen';
      saveState(); render();
    }

    function quickArchive(id) {
      if (!state.items[id]) state.items[id] = { status: 'archived', myRating: 0, note: '', reminderDate: '', reminderLabel: '' };
      else state.items[id].status = state.items[id].status === 'archived' ? 'watchlist' : 'archived';
      saveState(); render();
    }

    function exportState() {
      const payload = {
        exportedAt: new Date().toISOString(),
        watchlist: Object.entries(state.items).map(([id, meta]) => {
          const r = REVIEWS_DATA.find(x => x.id === id);
          return { id, title: r?.title, guardianStars: r?.stars, ...meta };
        })
      };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'guardian-watchlist-export.json'; a.click();
      URL.revokeObjectURL(url);
    }

    function openModal(id) {
      editingId = id;
      const review = REVIEWS_DATA.find(r => r.id === id);
      const userMeta = state.items[id] || {
        status: 'watchlist', myRating: 0, note: '',
        reminderDate: review.ticketEvent?.date || review.releaseDate || '',
        reminderLabel: review.ticketEvent?.type || 'Release'
      };
      document.getElementById('modal-title').textContent = review.title;
      document.getElementById('modal-subtitle').textContent = `${review.type} • Guardian ${review.stars}★ • ${review.platform}`;
      document.getElementById('modal-status').value = userMeta.status;
      document.getElementById('modal-note').value = userMeta.note || '';
      document.getElementById('modal-reminder-date').value = userMeta.reminderDate || '';
      document.getElementById('modal-reminder-label').value = userMeta.reminderLabel || '';
      modalRating = userMeta.myRating || 0;
      renderModalStars();
      const modal = document.getElementById('note-modal');
      modal.classList.remove('hidden'); modal.classList.add('flex');
    }

    function renderModalStars() {
      document.getElementById('modal-stars').innerHTML = [1, 2, 3, 4, 5].map(n =>
        `<span onclick="setModalRating(${n})" class="${n <= modalRating ? 'star-filled' : 'star-empty'} hover:scale-110 transition">★</span>`
      ).join('') + `<span class="text-xs text-[var(--muted-foreground)] ml-2">${modalRating ? modalRating + '/5' : 'Unrated'}</span>`;
    }

    function setModalRating(n) { modalRating = n; renderModalStars(); }

    function saveModal() {
      if (!editingId) return;
      state.items[editingId] = {
        status: document.getElementById('modal-status').value,
        myRating: modalRating,
        note: document.getElementById('modal-note').value.trim(),
        reminderDate: document.getElementById('modal-reminder-date').value,
        reminderLabel: document.getElementById('modal-reminder-label').value.trim()
      };
      saveState(); closeModal(); render();
    }

    function removeFromWatchlist() {
      if (editingId && state.items[editingId]) { delete state.items[editingId]; saveState(); }
      closeModal(); render();
    }

    function closeModal() {
      const modal = document.getElementById('note-modal');
      modal.classList.add('hidden'); modal.classList.remove('flex'); editingId = null;
    }

    function renderStats() {
      const fiveStarCount = REVIEWS_DATA.filter(r => r.stars === 5).length;
      const entries = Object.values(state.items);
      const stats = [
        { label: 'Reviews (6-Mo Window)', value: REVIEWS_DATA.length, sub: `${fiveStarCount} rated 5★` },
        { label: 'On Watchlist', value: entries.filter(i => i.status === 'watchlist').length, sub: 'To watch' },
        { label: 'Seen & Rated', value: entries.filter(i => i.status === 'seen').length, sub: 'Completed' },
        { label: 'Ticket / Presale Drops', value: REVIEWS_DATA.filter(r => r.ticketEvent && daysUntil(r.ticketEvent.date) >= 0).length, sub: 'Upcoming alerts' }
      ];
      document.getElementById('stats-bar').innerHTML = stats.map(s => `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-3">
          <div class="text-xs text-[var(--muted-foreground)]">${s.label}</div>
          <div class="text-xl font-bold mt-0.5 tabular-nums">${s.value}</div>
          <div class="text-xs text-[var(--muted-foreground)] mt-0.5">${s.sub}</div>
        </div>
      `).join('');
    }

    function renderReviewCard(r) {
      const userItem = state.items[r.id];
      const badge = formatBadgeDate(r.releaseDate);
      const statusPill = userItem
        ? userItem.status === 'seen' ? '<span class="px-2 py-0.5 rounded text-xs font-medium bg-[var(--success)]/15 text-[var(--success)]">Seen</span>'
          : userItem.status === 'archived' ? '<span class="px-2 py-0.5 rounded text-xs font-medium bg-[var(--secondary)] text-[var(--muted-foreground)]">Archived</span>'
          : '<span class="px-2 py-0.5 rounded text-xs font-medium bg-[var(--primary)]/15 text-[var(--primary)]">In Watchlist</span>'
        : '';

      return `
        <article class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-4 flex flex-col justify-between gap-3 hover:border-[var(--primary)]/60 transition">
          <div class="space-y-2">
            <div class="flex items-start justify-between gap-2">
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="px-2 py-0.5 rounded text-xs font-semibold bg-[var(--secondary)] text-[var(--secondary-foreground)]">${r.type}</span>
                <span class="px-2 py-0.5 rounded text-xs border ${badge.cls}">${badge.text}</span>
                ${statusPill}
              </div>
              <div class="text-sm leading-none shrink-0">${renderStars(r.stars)}</div>
            </div>
            <div>
              <h3 class="text-sm font-bold leading-snug"><a href="${r.guardianUrl}" target="_blank" rel="noopener noreferrer" class="hover:underline">${r.title}</a></h3>
              <p class="text-xs text-[var(--muted-foreground)] mt-0.5">${r.genre} • By ${r.critic} (${r.reviewDate})</p>
            </div>
            <p class="text-xs text-[var(--foreground)]/90 line-clamp-2">${r.verdict}</p>
            <div class="text-xs text-[var(--muted-foreground)] space-y-1 pt-1">
              <div><strong class="text-[var(--foreground)]">Platform:</strong> ${r.platform}</div>
              <div><strong class="text-[var(--foreground)]">Release:</strong> ${r.releaseDate}</div>
              <div><a href="${r.guardianUrl}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 font-medium text-[var(--link)] hover:underline">Read Guardian Review ↗</a></div>
              ${r.ticketEvent ? `<div class="mt-1.5 px-2.5 py-1.5 rounded bg-[var(--warning)]/10 border border-[var(--warning)]/30 text-xs"><span class="font-semibold text-[var(--warning)]">${r.ticketEvent.type}:</span> ${r.ticketEvent.date} — ${r.ticketEvent.venue}</div>` : ''}
              ${userItem?.note ? `<div class="mt-1.5 px-2.5 py-1.5 rounded bg-[var(--background)] border border-[var(--border)] text-xs italic">"${userItem.note}" ${userItem.myRating ? `(${userItem.myRating}★)` : ''}</div>` : ''}
            </div>
          </div>
          <div class="flex flex-wrap items-center justify-between gap-2 pt-2.5 border-t border-[var(--border)]">
            <div class="flex items-center gap-1.5">
              <button onclick="quickToggleWatchlist('${r.id}')" class="px-2.5 py-1 rounded text-xs font-medium ${userItem ? 'bg-[var(--secondary)] text-[var(--foreground)]' : 'bg-[var(--primary)] text-[var(--primary-foreground)]'}">${userItem ? 'Edit / Notes' : '+ Watchlist'}</button>
              <button onclick="quickMarkSeen('${r.id}')" class="px-2.5 py-1 rounded text-xs border border-[var(--border)] hover:border-[var(--success)]">${userItem?.status === 'seen' ? '✓ Seen' : 'Mark Seen'}</button>
            </div>
            <div class="flex items-center gap-2">
              <a href="${googleCalendarUrl(r.title, r.ticketEvent?.date || r.releaseDate, `${r.platform} — Guardian ${r.stars}★`)}" target="_blank" rel="noopener noreferrer" class="text-xs font-medium text-[var(--link)] hover:underline">+ Google Calendar</a>
              <button onclick="downloadICS('${r.title.replace(/'/g, "\\'")}', '${r.ticketEvent?.date || r.releaseDate}', '${r.platform} — Guardian ${r.stars}★')" class="text-xs text-[var(--muted-foreground)] hover:text-[var(--foreground)]">(.ics)</button>
            </div>
          </div>
        </article>
      `;
    }

    function renderReviewsTab() {
      const list = getFilteredReviews();
      if (!list.length) return `<div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-8 text-center text-xs text-[var(--muted-foreground)]">No reviews match your current filters.</div>`;
      return `<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">${list.map(renderReviewCard).join('')}</div>`;
    }

    function renderTopRatedTab() {
      const list = getFilteredReviews().filter(r => r.stars >= 4).sort((a, b) => a.releaseDate.localeCompare(b.releaseDate));
      if (!list.length) return `<div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-8 text-center text-xs text-[var(--muted-foreground)]">No 4★/5★ items match your filters.</div>`;
      return `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg overflow-hidden">
          <div class="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between">
            <h2 class="text-sm font-bold">Best Rated (4★ &amp; 5★) — Chronological Release Order</h2>
            <span class="text-xs text-[var(--muted-foreground)]">${list.length} picks</span>
          </div>
          <div class="divide-y divide-[var(--border)]">
            ${list.map(r => {
              const userItem = state.items[r.id];
              const badge = formatBadgeDate(r.releaseDate);
              return `
                <div class="p-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div class="flex items-start md:items-center gap-3">
                    <div class="w-24 shrink-0">
                      <div class="text-xs font-mono font-semibold">${r.releaseDate}</div>
                      <span class="inline-block mt-0.5 px-1.5 py-0.5 rounded text-[11px] border ${badge.cls}">${badge.text}</span>
                    </div>
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="text-sm">${renderStars(r.stars)}</span>
                        <a href="${r.guardianUrl}" target="_blank" rel="noopener noreferrer" class="text-sm font-bold hover:underline">${r.title}</a>
                        <span class="px-1.5 py-0.5 rounded text-xs bg-[var(--secondary)]">${r.type}</span>
                      </div>
                      <div class="text-xs text-[var(--muted-foreground)] mt-0.5">
                        ${r.platform} • ${r.critic} • <a href="${r.guardianUrl}" target="_blank" rel="noopener noreferrer" class="text-[var(--link)] hover:underline">Read Review ↗</a>
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2 shrink-0">
                    <button onclick="quickToggleWatchlist('${r.id}')" class="px-2.5 py-1 rounded text-xs font-medium ${userItem ? 'bg-[var(--secondary)]' : 'bg-[var(--primary)] text-[var(--primary-foreground)]'}">${userItem ? 'Edit / Notes' : '+ Watchlist'}</button>
                    <a href="${googleCalendarUrl(r.title, r.releaseDate, `${r.platform} — Guardian ${r.stars}★`)}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 rounded text-xs font-medium border border-[var(--border)] text-[var(--link)]">+ Google Calendar</a>
                    <button onclick="downloadICS('${r.title.replace(/'/g, "\\'")}', '${r.releaseDate}', '${r.platform}')" class="px-2 py-1 rounded text-xs border border-[var(--border)] text-[var(--muted-foreground)]">.ics</button>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    function renderRemindersTab() {
      const reminders = [];
      REVIEWS_DATA.forEach(r => {
        if (r.ticketEvent) reminders.push({ id: r.id, title: r.title, stars: r.stars, date: r.ticketEvent.date, kind: r.ticketEvent.type, detail: `${r.ticketEvent.venue} — ${r.ticketEvent.note}`, source: 'Ticket / Presale' });
        const u = state.items[r.id];
        if (u?.reminderDate) reminders.push({ id: r.id, title: r.title, stars: r.stars, date: u.reminderDate, kind: u.reminderLabel || 'Personal Reminder', detail: `${r.platform}${u.note ? ' — ' + u.note : ''}`, source: 'My Reminder' });
      });
      reminders.sort((a, b) => a.date.localeCompare(b.date));
      return `
        <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg overflow-hidden">
          <div class="px-4 py-3 border-b border-[var(--border)]">
            <h2 class="text-sm font-bold">Upcoming Ticket Drops, Presales &amp; Release Reminders</h2>
            <p class="text-xs text-[var(--muted-foreground)]">Click "+ Google Calendar" to open a pre-filled event directly in Google Calendar.</p>
          </div>
          <div class="divide-y divide-[var(--border)]">
            ${reminders.length ? reminders.map(rem => {
              const badge = formatBadgeDate(rem.date);
              return `
                <div class="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div class="space-y-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="px-2 py-0.5 rounded text-xs border ${badge.cls}">${badge.text}</span>
                      <span class="px-2 py-0.5 rounded text-xs font-semibold bg-[var(--warning)]/15 text-[var(--warning)]">${rem.kind}</span>
                      <span class="text-xs text-[var(--muted-foreground)]">${rem.source}</span>
                    </div>
                    <div class="text-sm font-bold">${rem.title} <span class="text-xs font-normal ml-1">${renderStars(rem.stars)}</span></div>
                    <div class="text-xs text-[var(--muted-foreground)]">${rem.date} • ${rem.detail}</div>
                  </div>
                  <div class="flex items-center gap-2 shrink-0">
                    <button onclick="openModal('${rem.id}')" class="px-2.5 py-1 rounded text-xs border border-[var(--border)]">Edit</button>
                    <a href="${googleCalendarUrl(`${rem.title} (${rem.kind})`, rem.date, rem.detail)}" target="_blank" rel="noopener noreferrer" class="px-2.5 py-1 rounded text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">+ Google Calendar</a>
                    <button onclick="downloadICS('${rem.title.replace(/'/g, "\\'")} (${rem.kind})', '${rem.date}', '${rem.detail.replace(/'/g, "\\'")}')" class="px-2 py-1 rounded text-xs border border-[var(--border)] text-[var(--muted-foreground)]">.ics</button>
                  </div>
                </div>
              `;
            }).join('') : '<div class="p-8 text-center text-xs text-[var(--muted-foreground)]">No upcoming reminders yet.</div>'}
          </div>
        </div>
      `;
    }

    function renderWatchlistTab() {
      const entries = Object.entries(state.items)
        .map(([id, meta]) => ({ review: REVIEWS_DATA.find(r => r.id === id), meta }))
        .filter(x => x.review)
        .filter(x => state.watchlistFilter === 'all' || x.meta.status === state.watchlistFilter);
      const filterBtns = [
        { key: 'all', label: 'All Saved' }, { key: 'watchlist', label: 'To Watch' },
        { key: 'seen', label: 'Seen' }, { key: 'archived', label: 'Archived' }
      ];
      return `
        <div class="space-y-3">
          <div class="flex flex-wrap items-center gap-2">
            ${filterBtns.map(b => `<button onclick="setWatchlistFilter('${b.key}')" class="px-3 py-1 rounded-md text-xs font-medium border ${state.watchlistFilter === b.key ? 'bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)]' : 'bg-[var(--card)] border-[var(--border)]'}">${b.label}</button>`).join('')}
          </div>
          ${entries.length === 0 ? `<div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-8 text-center text-xs text-[var(--muted-foreground)]">No items in this view yet. Add reviews from the Latest Reviews tab!</div>` : `
            <div class="space-y-2.5">
              ${entries.map(({ review, meta }) => `
                <div class="bg-[var(--card)] border border-[var(--border)] rounded-lg p-4 flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div class="space-y-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <a href="${review.guardianUrl}" target="_blank" rel="noopener noreferrer" class="text-sm font-bold hover:underline">${review.title}</a>
                      <span class="px-2 py-0.5 rounded text-xs bg-[var(--secondary)]">${review.type}</span>
                      <span class="text-xs text-[var(--muted-foreground)]">Guardian: ${renderStars(review.stars)}</span>
                      ${meta.myRating ? `<span class="text-xs text-[var(--foreground)]">• Mine: ${renderStars(meta.myRating)}</span>` : ''}
                    </div>
                    <div class="text-xs text-[var(--muted-foreground)]">${review.platform} • Release: ${review.releaseDate} • <a href="${review.guardianUrl}" target="_blank" rel="noopener noreferrer" class="text-[var(--link)] hover:underline">Read Review ↗</a></div>
                    ${meta.note ? `<p class="text-xs italic pt-1">"${meta.note}"</p>` : ''}
                  </div>
                  <div class="flex flex-wrap items-center gap-2 shrink-0">
                    <button onclick="quickMarkSeen('${review.id}')" class="px-2.5 py-1 rounded text-xs border border-[var(--border)]">${meta.status === 'seen' ? '✓ Seen' : 'Mark Seen'}</button>
                    <button onclick="quickArchive('${review.id}')" class="px-2.5 py-1 rounded text-xs border border-[var(--border)]">${meta.status === 'archived' ? 'Unarchive' : 'Archive'}</button>
                    <button onclick="openModal('${review.id}')" class="px-2.5 py-1 rounded text-xs font-semibold bg-[var(--primary)] text-[var(--primary-foreground)]">Edit Note / Rating</button>
                  </div>
                </div>
              `).join('')}
            </div>
          `}
        </div>
      `;
    }

    function render() {
      populatePlatformFilter();
      renderStats();
      document.querySelectorAll('.tab-btn').forEach(btn => {
        const active = btn.dataset.tab === state.activeTab;
        btn.className = `tab-btn px-3.5 py-1.5 rounded-md text-xs font-semibold transition ${active ? 'bg-[var(--primary)] text-[var(--primary-foreground)]' : 'bg-[var(--card)] border border-[var(--border)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]'}`;
      });
      const showFilters = state.activeTab === 'reviews' || state.activeTab === 'top-rated';
      document.getElementById('filters-bar').style.display = showFilters ? 'flex' : 'none';
      const main = document.getElementById('main-content');
      if (state.activeTab === 'reviews') main.innerHTML = renderReviewsTab();
      else if (state.activeTab === 'top-rated') main.innerHTML = renderTopRatedTab();
      else if (state.activeTab === 'reminders') main.innerHTML = renderRemindersTab();
      else if (state.activeTab === 'watchlist') main.innerHTML = renderWatchlistTab();
    }

    render();
  </script>
</body>
</html>
"""


def build_dashboard(data_path: Path, out_path: Path) -> Path:
    """Render static HTML dashboard from reviews JSON."""
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    reviews = payload.get("reviews") or []
    generated_at = payload.get("generatedAt") or "2026-11-25"
    lookback_days = str(payload.get("lookbackDays") or 180)
    mode = (payload.get("mode") or "demo").upper()
    mode_badge = "LIVE GUARDIAN API" if mode == "LIVE" else "DEMO DATA (SET GUARDIAN_API_KEY)"

    html_out = (
        HTML_TEMPLATE.replace("__REVIEWS_JSON__", json.dumps(reviews))
        .replace("__GENERATED_AT__", generated_at)
        .replace("__LOOKBACK_DAYS__", lookback_days)
        .replace("__MODE_BADGE__", mode_badge)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build entertainment dashboard HTML.")
    parser.add_argument("--data", type=Path, default=Path("data/reviews.json"), help="Input JSON path.")
    parser.add_argument("--out", type=Path, default=Path("dist/index.html"), help="Output HTML path.")
    args = parser.parse_args()
    out = build_dashboard(args.data, args.out)
    print(f"Built dashboard at {out}")


if __name__ == "__main__":
    main()
