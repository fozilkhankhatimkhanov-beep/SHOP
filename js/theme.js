(function () {
    'use strict';

    var STORAGE_KEY = 'theme';
    var html = document.documentElement;

    function getPreferredTheme() {
        var stored = null;
        try {
            stored = localStorage.getItem(STORAGE_KEY);
        } catch (e) { /* ignore */ }
        if (stored === 'night' || stored === 'day') return stored;
        return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'night'
            : 'day';
    }

    function applyTheme(theme) {
        html.setAttribute('data-theme', theme);
        try { localStorage.setItem(STORAGE_KEY, theme); } catch (e) { /* ignore */ }
        var btn = document.getElementById('theme-toggle');
        if (btn) {
            btn.textContent = theme === 'night' ? '🌙' : '☀️';
        }
    }

    var currentTheme = getPreferredTheme();
    applyTheme(currentTheme);

    function initToggle() {
        var btn = document.getElementById('theme-toggle');
        if (!btn) return;
        btn.addEventListener('click', function () {
            var next = html.getAttribute('data-theme') === 'night' ? 'day' : 'night';
            applyTheme(next);
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initToggle);
    } else {
        initToggle();
    }
})();
