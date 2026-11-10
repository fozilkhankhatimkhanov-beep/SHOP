(function () {
    'use strict';

    var storageKey = 'shop-theme';
    var root = document.documentElement;
    var theme;

    try {
        theme = localStorage.getItem(storageKey);
    } catch (error) {
        theme = null;
    }

    if (theme !== 'day' && theme !== 'night') {
        theme = window.matchMedia &&
            window.matchMedia('(prefers-color-scheme: dark)').matches
            ? 'night'
            : 'day';
    }

    function applyTheme(nextTheme) {
        theme = nextTheme;
        root.setAttribute('data-theme', theme);

        var button = document.getElementById('theme-toggle');
        if (button) {
            button.textContent = theme === 'night' ? '🌙' : '☀️';
            button.setAttribute('aria-pressed', theme === 'night' ? 'true' : 'false');
            button.setAttribute(
                'aria-label',
                theme === 'night' ? 'Kunduzgi rejimni yoqish' : 'Tungi rejimni yoqish'
            );
        }

        try {
            localStorage.setItem(storageKey, theme);
        } catch (error) {
            // The selected theme still applies for this page when storage is unavailable.
        }
    }

    applyTheme(theme);

    document.addEventListener('click', function (event) {
        if (event.target.closest('#theme-toggle')) {
            applyTheme(theme === 'night' ? 'day' : 'night');
        }
    });
})();
