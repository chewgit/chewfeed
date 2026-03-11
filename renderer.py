import base64
import os
import sys
from datetime import datetime


CSS = """
:root {
    --reader-font-size: 16px;
    --reader-width: min(48vw, 680px);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: #f5f5f3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    color: #2c3e50;
    height: 100vh;
    overflow: hidden;
}
.main-page {
    height: 100vh;
    width: 100%;
    overflow-y: auto;
    overflow-x: hidden;
    transition: width 0.18s ease-out;
}

/* â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.header {
    background: #1a1a1a;
    color: #fff;
    padding: 24px 32px 20px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 30;
}
.header-left {
    display: flex;
    align-items: center;
    gap: 12px;
}
.header-refresh {
    border: none;
    background: transparent;
    color: #bfc4cb;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-left: 10px;
    padding: 0;
    transition: color 0.18s;
}
.header-refresh:hover {
    color: #ffffff;
}
.header-refresh:disabled {
    opacity: 0.7;
    cursor: not-allowed;
}
.header-refresh-icon {
    display: inline-block;
    transform-origin: center center;
    width: 16px;
    height: 16px;
}
.header-refresh.refreshing .header-refresh-icon {
    animation: spin 1.8s linear infinite;
}
.app-logo {
    width: 42px;
    height: 42px;
    object-fit: contain;
    border-radius: 10px;
    background: #fff;
    padding: 4px;
}
.brand-title-row {
    display: flex;
    align-items: center;
}
.brand-text h1 {
    font-size: 22px;
    font-weight: 600;
    margin: 0;
}
.brand-text .subtitle {
    font-size: 13px;
    color: #999;
    font-weight: 400;
    margin-top: 4px;
}
.brand-text .subtitle .subtitle-date {
    display: inline;
}
.brand-text .subtitle .subtitle-time {
    display: inline;
}

/* â”€â”€ Add-source form â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.add-form {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}
.add-form input {
    background: #2a2a2a;
    border: 1px solid #444;
    border-radius: 6px;
    color: #eee;
    padding: 7px 12px;
    font-size: 13px;
    font-family: inherit;
    outline: none;
    transition: border-color 0.2s;
}
.add-form input:focus { border-color: #888; }
.add-form input::placeholder { color: #777; }
.add-form input.title-input { width: 140px; }
.add-form input.url-input { width: 240px; }
.add-btn {
    background: #444;
    color: #eee;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-family: inherit;
    cursor: pointer;
    transition: background 0.2s;
    white-space: nowrap;
}
.add-btn:hover { background: #555; }
.add-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.add-btn .btn-spinner {
    display: inline-block;
    width: 12px; height: 12px;
    border: 2px solid #888;
    border-top-color: #eee;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
    vertical-align: middle;
    margin-right: 4px;
}

body.compact .header {
    flex-wrap: wrap;
    gap: 12px;
}
body.compact .add-form {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    width: 100%;
}
body.compact .add-form input.title-input,
body.compact .add-form input.url-input {
    width: min(100%, 360px);
}
body.compact .add-btn {
    align-self: flex-start;
}
body.compact .brand-text .subtitle .subtitle-time {
    display: none;
}
body.compact .brand-text .subtitle .subtitle-date::after {
    content: "";
}

/* â”€â”€ Card grid â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.content {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    padding: 16px 24px 32px;
    margin: 0 auto;
}
.card {
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    overflow: visible;
    min-width: 340px;
    max-width: 340px;
    width: 340px;
    flex: 0 0 340px;
    display: flex;
    flex-direction: column;
    position: relative;
}
.card.favourites-card {
    border: 2px solid #f5b041;
    box-shadow: 0 4px 14px rgba(245, 176, 65, 0.25);
}

/* â”€â”€ Card header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.card-header {
    display: flex;
    align-items: center;
    flex-wrap: nowrap;
    padding: 12px 14px;
    border-bottom: 1px solid #f0f0ee;
}
.card-star {
    border: none;
    background: none;
    color: #c7c7c7;
    cursor: pointer;
    font-size: 17px;
    line-height: 1;
    margin-right: 10px;
    padding: 0;
    transition: color 0.15s ease, transform 0.15s ease;
}
.card-star:hover {
    color: #f5b041;
    transform: scale(1.08);
}
.card-star.active {
    color: #f5b041;
}
.card-star:disabled {
    cursor: default;
    transform: none;
}
.source-name {
    font-weight: 600;
    font-size: 15px;
    flex-grow: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.paywall-badge {
    background: #fff3cd;
    color: #856404;
    padding: 3px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    margin-right: 8px;
    white-space: nowrap;
}

/* â”€â”€ Triple-dot menu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.menu-wrapper {
    position: relative;
    flex-shrink: 0;
    margin-left: 6px;
}
.menu-trigger {
    background: none;
    border: none;
    color: #bbb;
    font-size: 18px;
    cursor: pointer;
    padding: 2px 4px;
    line-height: 1;
    border-radius: 4px;
    transition: background 0.15s, color 0.15s;
    letter-spacing: 1px;
}
.menu-trigger:hover {
    background: #f0f0ee;
    color: #666;
}
.menu-dropdown {
    display: none;
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 4px;
    background: #fff;
    border: 1px solid #e8e8e6;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    min-width: 140px;
    z-index: 100;
    overflow: hidden;
}
.menu-dropdown.open { display: block; }
.menu-item {
    display: block;
    width: 100%;
    padding: 9px 16px;
    font-size: 13px;
    font-family: inherit;
    color: #333;
    background: none;
    border: none;
    text-align: left;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.12s;
}
.menu-item:hover { background: #f5f5f3; }
.menu-item.danger { color: #333; }
.menu-item.danger:hover {
    background: #fdf0f0;
    color: #d63031;
}
.menu-separator {
    height: 1px;
    background: #f0f0ee;
    margin: 0;
}

/* â”€â”€ Card body / articles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.card-body {
    flex: 1;
    overflow-y: auto;
    max-height: 420px;
}
.article-row {
    display: flex;
    align-items: baseline;
    padding: 8px 14px;
    border-bottom: 1px solid #f7f7f5;
    transition: background 0.15s;
}
.article-row:last-child { border-bottom: none; }
.article-row:hover { background: #fafaf8; }
.article-title {
    flex: 1;
    min-width: 0;
}
.article-title a {
    color: #2c3e50;
    text-decoration: none;
    font-weight: 500;
    font-size: 13px;
    line-height: 1.4;
}
.article-title a:hover { text-decoration: underline; }
.article-source {
    color: #7f8c8d;
    font-size: 11px;
    font-style: italic;
    margin-top: 2px;
}
.article-date {
    color: #aaa;
    font-size: 11px;
    text-align: right;
    width: 110px;
    flex-shrink: 0;
    padding-left: 8px;
    white-space: nowrap;
}
.error-msg {
    color: #999;
    font-style: italic;
    padding: 16px 20px;
    font-size: 13px;
}
.paywalled-icon {
    color: #ccc;
    font-size: 11px;
    margin-left: 6px;
}

/* â”€â”€ Loading state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: calc(100vh - 100px);
}
.spinner {
    width: 36px; height: 36px;
    border: 3px solid #e0e0e0;
    border-top-color: #555;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text {
    color: #888;
    font-size: 14px;
}

/* Reader sidebar */
.reader-overlay {
    position: fixed;
    top: 0;
    right: 0;
    width: var(--reader-width);
    height: 100%;
    transform: translateX(100%);
    transition: transform 0.18s ease-out;
    pointer-events: none;
    z-index: 1000;
}
.reader-overlay.open {
    transform: translateX(0);
    pointer-events: auto;
}
.reader-panel {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: #f5f5f3;
    border-left: 1px solid #e8e8e6;
    box-shadow: -8px 0 30px rgba(0, 0, 0, 0.12);
    display: flex;
    flex-direction: column;
}
.reader-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid #f0f0ee;
    background: #fff;
}
.reader-zoom {
    display: flex;
    align-items: center;
    gap: 6px;
}
.reader-actions {
    display: flex;
    align-items: center;
    gap: 6px;
}
.zoom-btn, .reader-open-url, .reader-close {
    border: 1px solid #ddd;
    background: #fafafa;
    color: #444;
    border-radius: 6px;
    padding: 4px 8px;
    cursor: pointer;
    font-size: 12px;
}
.zoom-btn:hover, .reader-open-url:hover, .reader-close:hover { background: #f1f1f1; }
.reader-body {
    padding: 18px 20px 24px;
    overflow-y: auto;
    height: 100%;
}
.reader-source {
    font-weight: 700;
    color: #2b2b2b;
    margin-bottom: 6px;
    font-size: 18px;
}
.reader-title {
    font-weight: 700;
    color: #1f1f1f;
    font-size: 15px;
    margin-bottom: 4px;
}
.reader-date {
    color: #8a8a8a;
    font-style: italic;
    font-size: 12px;
    margin-bottom: 14px;
}
.reader-content {
    color: #1f1f1f;
    line-height: 1.35;
    font-size: var(--reader-font-size);
    overflow-wrap: anywhere;
    white-space: pre-wrap;
    -webkit-user-select: text;
    -ms-user-select: text;
    user-select: text;
    cursor: text;
}
.reader-content strong {
    font-weight: 700;
}
.reader-loading {
    color: #777;
    font-style: italic;
}
body.reader-open .main-page {
    width: calc(100% - var(--reader-width));
}
"""

JS = """
/* â”€â”€ Wait for pywebview API to be injected â”€â”€â”€â”€â”€â”€â”€â”€ */
function _getPywebviewApi() {
    if (window.pywebview && window.pywebview.api) return window.pywebview.api;
    if (window.pywebviewApi) return window.pywebviewApi;
    return null;
}

var _apiReady = new Promise(function(resolve) {
    var api = _getPywebviewApi();
    if (api) {
        resolve(api);
    } else {
        window.addEventListener('pywebviewready', function() {
            resolve(_getPywebviewApi());
        }, { once: true });
    }
});
var _currentReaderUrl = '';

/* â”€â”€ Add source â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
async function addSource() {
    var api = await _apiReady;
    var titleEl = document.getElementById('add-title');
    var urlEl   = document.getElementById('add-url');
    var btn     = document.getElementById('add-btn');
    var title   = titleEl.value.trim();
    var url     = urlEl.value.trim();
    if (!title || !url) return;

    btn.disabled  = true;
    btn.innerHTML = '<span class="btn-spinner"></span>Adding\\u2026';
    try {
        if (!api || !api.add_source) {
            throw new Error('Python API bridge not available');
        }
        await api.add_source(title, url);
    } catch(e) {
        alert('Failed to add source: ' + e);
        btn.disabled  = false;
        btn.textContent = '+ Add';
    }
}

/* â”€â”€ Remove source â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
async function refreshFeeds(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    var btn = document.getElementById('refresh-btn');
    if (btn) {
        btn.disabled = true;
        btn.classList.add('refreshing');
    }
    var api = await _apiReady;
    try {
        if (!api || !api.refresh_all) {
            throw new Error('Python API bridge not available');
        }
        await api.refresh_all();
    } catch (e) {
        if (btn) {
            btn.disabled = false;
            btn.classList.remove('refreshing');
        }
        alert('Failed to refresh feeds: ' + e);
    }
}
async function removeSource(key) {
    var api = await _apiReady;
    closeAllMenus();
    try {
        if (!api || !api.remove_source) {
            throw new Error('Python API bridge not available');
        }
        await api.remove_source(key);
    } catch(e) {
        alert('Failed to remove: ' + e);
    }
}

/* â”€â”€ Triple-dot menu â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function toggleMenu(event, menuId) {
    event.stopPropagation();
    var menu = document.getElementById(menuId);
    var wasOpen = menu.classList.contains('open');
    closeAllMenus();
    if (!wasOpen) menu.classList.add('open');
}

function closeAllMenus() {
    document.querySelectorAll('.menu-dropdown.open').forEach(function(m) {
        m.classList.remove('open');
    });
}

function _parseCardDate(dateText) {
    var text = (dateText || '').trim();
    if (!text) return 0;
    var parsed = Date.parse(text);
    return Number.isNaN(parsed) ? 0 : parsed;
}

function _refreshFavouritesCardFromDom() {
    var favCard = document.querySelector('.favourites-card');
    if (!favCard) return;
    var favBody = favCard.querySelector('.card-body');
    if (!favBody) return;

    var items = [];
    var cards = Array.from(document.querySelectorAll('.card')).filter(function(card) {
        return !card.classList.contains('favourites-card');
    });

    cards.forEach(function(card) {
        var star = card.querySelector('.card-star');
        if (!star || !star.classList.contains('active')) return;
        var sourceNameEl = card.querySelector('.source-name');
        var sourceName = sourceNameEl ? sourceNameEl.textContent.trim() : '';
        card.querySelectorAll('.article-row').forEach(function(row) {
            var link = row.querySelector('.reader-link');
            if (!link) return;
            var dateEl = row.querySelector('.article-date');
            var dateText = dateEl ? dateEl.textContent.trim() : '';
            items.push({
                title: link.textContent || '',
                url: link.dataset.url || '',
                source: sourceName,
                dateText: dateText,
                sortValue: _parseCardDate(dateText)
            });
        });
    });

    if (!items.length) {
        favBody.innerHTML = '<div class="error-msg">Star cards to add them to My Favourites.</div>';
        return;
    }

    items.sort(function(a, b) {
        return (b.sortValue || 0) - (a.sortValue || 0);
    });

    var html = '';
    items.slice(0, 300).forEach(function(item) {
        var safeTitle = _escapeHtml(item.title);
        var safeUrl = _escapeHtml(item.url);
        var safeSource = _escapeHtml(item.source);
        var safeDate = _escapeHtml(item.dateText || '');
        html += '<div class="article-row">' +
            '<div class="article-title">' +
            '<a href="#" class="reader-link" data-url="' + safeUrl + '" data-source="' + safeSource + '" data-title="' + safeTitle + '">' + safeTitle + '</a>' +
            '<div class="article-source">' + safeSource + '</div>' +
            '</div>' +
            '<div class="article-date">' + safeDate + '</div>' +
            '</div>';
    });
    favBody.innerHTML = html;
}

function _escapeHtml(text) {
    return String(text || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

async function toggleFavourite(event, key) {
    var btn = event && event.currentTarget ? event.currentTarget : null;
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    if (btn) {
        btn.classList.toggle('active');
        _refreshFavouritesCardFromDom();
    }
    var api = await _apiReady;
    try {
        if (!api || !api.toggle_favourite) {
            throw new Error('Python API bridge not available');
        }
        var result = await api.toggle_favourite(key);
        if (btn && result && typeof result.favourited === 'boolean') {
            btn.classList.toggle('active', !!result.favourited);
            _refreshFavouritesCardFromDom();
        }
    } catch (e) {
        if (btn) {
            btn.classList.toggle('active');
            _refreshFavouritesCardFromDom();
        }
        alert('Failed to update favourites: ' + e);
    }
}

function closeReader() {
    var overlay = document.getElementById('reader-overlay');
    if (overlay) overlay.classList.remove('open');
    document.body.classList.remove('reader-open');
}

async function openReaderUrl() {
    if (!_currentReaderUrl) return;
    var api = await _apiReady;
    try {
        if (api && api.open_external) {
            await api.open_external(_currentReaderUrl);
            return;
        }
    } catch (e) {}
    window.open(_currentReaderUrl, '_blank', 'noopener');
}

function _setReaderFont(delta) {
    var root = document.documentElement;
    var raw = getComputedStyle(root).getPropertyValue('--reader-font-size').trim();
    var current = parseInt(raw, 10);
    if (isNaN(current)) current = 16;
    var next = Math.max(12, Math.min(26, current + delta));
    root.style.setProperty('--reader-font-size', next + 'px');
}

function _applyResponsiveLayout() {
    var mainPage = document.querySelector('.main-page');
    if (!mainPage) return;
    // Force compact mode when window is visually constrained.
    var compact = mainPage.clientWidth <= 980;
    document.body.classList.toggle('compact', compact);
}

async function openArticle(event, articleUrl, sourceName, fallbackTitle) {
    var clickedCard = null;
    if (event) {
        clickedCard = event.target && event.target.closest ? event.target.closest('.card') : null;
        event.preventDefault();
        event.stopPropagation();
    }
    if (clickedCard) {
        var mainPage = document.querySelector('.main-page');
        var header = document.querySelector('.header');
        if (mainPage) {
            var cardTop = clickedCard.getBoundingClientRect().top - mainPage.getBoundingClientRect().top + mainPage.scrollTop;
            var headerHeight = header ? header.getBoundingClientRect().height : 0;
            mainPage.scrollTo({
                top: Math.max(cardTop - headerHeight - 8, 0),
                behavior: 'smooth'
            });
        } else {
            clickedCard.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
        }
    }
    closeAllMenus();
    var overlay = document.getElementById('reader-overlay');
    var sourceEl = document.getElementById('reader-source');
    var titleEl = document.getElementById('reader-title');
    var dateEl = document.getElementById('reader-date');
    var contentEl = document.getElementById('reader-content');

    overlay.classList.add('open');
    document.body.classList.add('reader-open');
    sourceEl.textContent = sourceName || '';
    titleEl.textContent = fallbackTitle || 'Loading...';
    dateEl.textContent = '';
    contentEl.textContent = 'Loading article...';
    _currentReaderUrl = articleUrl || '';

    try {
        var api = await _apiReady;
        if (!api || !api.get_article) {
            throw new Error('Reader API is not available');
        }
        var result = await api.get_article(articleUrl, sourceName, fallbackTitle);
        sourceEl.textContent = result.source_name || sourceName || '';
        titleEl.textContent = result.title || fallbackTitle || 'Untitled';
        dateEl.textContent = result.date || '';
        if (result.content_html) {
            contentEl.innerHTML = result.content_html;
        } else {
            contentEl.textContent = result.content_text || 'No content found.';
        }
        _currentReaderUrl = result.url || articleUrl || '';
        contentEl.scrollTop = 0;
    } catch (e) {
        contentEl.textContent = 'Unable to load this article in-app.';
    }
}

/* Close menus on any click outside */
document.addEventListener('click', closeAllMenus);
document.addEventListener('click', function(e) {
    var link = e.target.closest('.reader-link');
    if (!link) return;
    openArticle(
        e,
        link.dataset.url || '',
        link.dataset.source || '',
        link.dataset.title || ''
    );
});

/* Enter key in form inputs */
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && (e.target.id === 'add-title' || e.target.id === 'add-url')) {
        addSource();
    }
    if (e.key === 'Escape') {
        closeReader();
    }
});
window.addEventListener('resize', _applyResponsiveLayout);
document.addEventListener('DOMContentLoaded', _applyResponsiveLayout);
setTimeout(_applyResponsiveLayout, 0);
"""


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )



def _asset_path(filename: str) -> str:
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "assets", filename)

def _load_logo_data_uri() -> str:
    try:
        with open(_asset_path("logo.png"), "rb") as f:
            encoded = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return ""

def _render_brand(date_text: str, time_text: str = "") -> str:
    logo_data_uri = _load_logo_data_uri()
    logo_html = (
        f'<img class="app-logo" src="{logo_data_uri}" alt="ChewFeed logo">'
        if logo_data_uri else ""
    )
    subtitle = (
        f'<span class="subtitle-date">{_escape(date_text)}</span>'
        f'<span class="subtitle-time"> \u2014 {_escape(time_text)}</span>'
        if time_text
        else f'<span class="subtitle-date">{_escape(date_text)}</span>'
    )
    return (
        '<div class="header-left">'
        f'{logo_html}'
        '<div class="brand-text">'
        '<div class="brand-title-row">'
        '<h1>ChewFeed</h1>'
        '<button id="refresh-btn" class="header-refresh" onclick="refreshFeeds(event)" title="Refresh all feeds" aria-label="Refresh all feeds">'
        '<svg class="header-refresh-icon" viewBox="0 0 16 16" fill="currentColor" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        '<path d="M11.534 7h3.932a.25.25 0 0 1 .192.41l-1.966 2.36a.25.25 0 0 1-.384 0l-1.966-2.36a.25.25 0 0 1 .192-.41m-11 2h3.932a.25.25 0 0 0 .192-.41L2.692 6.23a.25.25 0 0 0-.384 0L.342 8.59A.25.25 0 0 0 .534 9"/>'
        '<path fill-rule="evenodd" d="M8 3c-1.552 0-2.94.707-3.857 1.818a.5.5 0 1 1-.771-.636A6.002 6.002 0 0 1 13.917 7H12.9A5 5 0 0 0 8 3M3.1 9a5.002 5.002 0 0 0 8.757 2.182.5.5 0 1 1 .771.636A6.002 6.002 0 0 1 2.083 9z"/>'
        '</svg>'
        '</button>'
        '</div>'
        f'<div class="subtitle">{subtitle}</div>'
        '</div>'
        '</div>'
    )

def render_loading() -> str:
    now = datetime.now().strftime("%A, %B %d, %Y")
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="main-page">
    <div class="header">
        {_render_brand(now)}
    </div>
    <div class="loading-container">
        <div class="spinner"></div>
        <div class="loading-text">Fetching articles\u2026</div>
    </div>
</div>
</body></html>"""


def _render_card(source: dict) -> str:
    key = _escape(source["key"])
    name = _escape(source["name"])
    url = _escape(source["url"])
    menu_id = f"menu-{key}"
    is_favourites = bool(source.get("is_favourites"))
    favourited = bool(source.get("favourited"))
    favoritable = bool(source.get("favoritable"))

    badge = ""
    if source.get("badge"):
        badge = '<span class="paywall-badge">\u26a0 Subscription required</span>'

    # Build menu items
    visit_item = ""
    if url:
        visit_item = (
            f'<a class="menu-item" href="{url}" target="_blank">'
            f'\U0001f517  Visit source</a>'
        )

    delete_item = ""
    if source.get("removable"):
        delete_item = (
            f'<div class="menu-separator"></div>'
            f'<button class="menu-item danger" '
            f"onclick=\"removeSource('{key}')\">"
            f'\U0001f5d1  Delete card</button>'
        )

    menu_html = ""
    menu_content = f"{visit_item}{delete_item}".strip()
    if menu_content:
        menu_html = (
            f'<div class="menu-wrapper">'
            f'<button class="menu-trigger" onclick="toggleMenu(event, \'{menu_id}\')" '
            f'title="Options">\u22ee</button>'
            f'<div class="menu-dropdown" id="{menu_id}">{menu_content}</div>'
            f'</div>'
        )

    star_html = ""
    if is_favourites:
        star_html = '<button class="card-star active" title="My Favourites" disabled>\u2605</button>'
    elif favoritable:
        star_class = "card-star active" if favourited else "card-star"
        star_html = (
            f'<button class="{star_class}" '
            f'onclick="toggleFavourite(event, \'{key}\')" '
            f'title="Toggle favourite">\u2605</button>'
        )

    # Article rows
    rows = ""
    error = source.get("error")
    articles = source.get("articles", [])
    if error and not articles:
        rows = f'<div class="error-msg">{_escape(error)}</div>'
    else:
        for a in articles:
            row_source = getattr(a, "source_name", None) or source["name"]
            date_cell = (
                f'<div class="article-date">{_escape(a.date)}</div>'
                if a.date else '<div class="article-date"></div>'
            )
            source_label = ""
            if source.get("show_source_name") and getattr(a, "source_name", None):
                source_label = f'<div class="article-source">{_escape(a.source_name)}</div>'
            lock = (
                '<span class="paywalled-icon">\U0001f512</span>'
                if a.paywalled else ""
            )
            rows += (
                f'<div class="article-row">'
                f'<div class="article-title">'
                f'<a href="#" class="reader-link" '
                f'data-url="{_escape(a.url)}" '
                f'data-source="{_escape(row_source)}" '
                f'data-title="{_escape(a.title)}">{_escape(a.title)}</a>'
                f'{lock}{source_label}</div>'
                f'{date_cell}'
                f'</div>\n'
            )

    card_class = "card favourites-card" if is_favourites else "card"
    return f"""<div class="{card_class}">
    <div class="card-header">
        {star_html}
        <span class="source-name">{name}</span>
        {badge}
        {menu_html}
    </div>
    <div class="card-body">
        {rows}
    </div>
</div>"""


def render_html(sources: list[dict]) -> str:
    now_date = datetime.now().strftime("%A, %B %d, %Y")
    now_time = datetime.now().strftime("%I:%M %p")

    cards = "\n".join(_render_card(s) for s in sources)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><style>{CSS}</style></head>
<body>
<div class="main-page">
    <div class="header">
        {_render_brand(now_date, now_time)}
        <div class="add-form">
            <input type="text" id="add-title" class="title-input" placeholder="Add blog title">
            <input type="text" id="add-url" class="url-input" placeholder="Add website URL">
            <button id="add-btn" class="add-btn" onclick="addSource()">+ Add</button>
        </div>
    </div>
    <div class="content">
        {cards}
    </div>
</div>
<div id="reader-overlay" class="reader-overlay">
    <div class="reader-panel">
        <div class="reader-topbar">
            <div class="reader-zoom">
                <button class="zoom-btn" onclick="_setReaderFont(-1)" title="Decrease text size">A-</button>
                <button class="zoom-btn" onclick="_setReaderFont(1)" title="Increase text size">A+</button>
            </div>
            <div class="reader-actions">
                <button class="reader-open-url" onclick="openReaderUrl()">Open URL</button>
                <button class="reader-close" onclick="closeReader()">Close</button>
            </div>
        </div>
        <div class="reader-body">
            <div id="reader-source" class="reader-source"></div>
            <div id="reader-title" class="reader-title"></div>
            <div id="reader-date" class="reader-date"></div>
            <div id="reader-content" class="reader-content"></div>
        </div>
    </div>
</div>
<script>{JS}</script>
</body></html>"""















