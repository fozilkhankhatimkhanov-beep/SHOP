(function () {
    'use strict';

    var navigationInProgress = false;

    function isInternalUrl(url) {
        return url.origin === window.location.origin;
    }

    function navigate(url, options, addHistoryEntry, scrollToTop) {
        if (navigationInProgress) return Promise.resolve();
        navigationInProgress = true;
        document.documentElement.setAttribute('aria-busy', 'true');

        return fetch(url.href, options)
            .then(function (response) {
                if (!response.ok && response.status >= 500) {
                    throw new Error('Sahifani yuklab bo‘lmadi. Qayta urinib ko‘ring.');
                }
                return response.text().then(function (html) {
                    return {
                        html: html,
                        url: response.url,
                        redirected: response.redirected,
                    };
                });
            })
            .then(function (result) {
                var parser = new DOMParser();
                var nextDocument = parser.parseFromString(result.html, 'text/html');
                var nextMain = nextDocument.querySelector('main');
                var nextHeader = nextDocument.querySelector('.site-header');
                var currentMain = document.querySelector('main');
                var currentHeader = document.querySelector('.site-header');

                if (!nextMain || !nextHeader || !currentMain || !currentHeader) {
                    window.location.assign(result.url);
                    return;
                }

                currentHeader.replaceWith(nextHeader);
                currentMain.replaceWith(nextMain);

                var nextFooter = nextDocument.querySelector('.site-footer');
                var currentFooter = document.querySelector('.site-footer');
                if (nextFooter && currentFooter) currentFooter.replaceWith(nextFooter);

                var nextCsrfToken = nextDocument.querySelector('meta[name="csrf-token"]');
                var currentCsrfToken = document.querySelector('meta[name="csrf-token"]');
                if (nextCsrfToken && currentCsrfToken) {
                    currentCsrfToken.content = nextCsrfToken.content;
                }

                document.title = nextDocument.title;

                var finalUrl = new URL(result.url, window.location.href);
                if (addHistoryEntry || result.redirected) {
                    window.history.pushState({}, '', finalUrl.href);
                } else if (finalUrl.href !== window.location.href) {
                    window.history.replaceState({}, '', finalUrl.href);
                }

                document.documentElement.removeAttribute('aria-busy');
                navigationInProgress = false;
                document.dispatchEvent(new CustomEvent('site:page-loaded'));

                if (scrollToTop) window.scrollTo(0, 0);
            })
            .catch(function (error) {
                document.documentElement.removeAttribute('aria-busy');
                navigationInProgress = false;
                if (typeof showMessage === 'function') {
                    showMessage(error.message || 'Sahifani yuklashda xatolik yuz berdi.');
                } else {
                    window.alert(error.message || 'Sahifani yuklashda xatolik yuz berdi.');
                }
            });
    }

    document.addEventListener('click', function (event) {
        if (event.defaultPrevented || event.button !== 0 ||
            event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

        var link = event.target.closest('a[href]');
        if (!link || link.target || link.hasAttribute('download')) return;

        var url = new URL(link.href, window.location.href);
        if (!isInternalUrl(url) || url.hash && url.pathname === window.location.pathname &&
            url.search === window.location.search) return;

        event.preventDefault();
        navigate(url, {
            headers: {'X-Requested-With': 'XMLHttpRequest'},
        }, true, true);
    });

    document.addEventListener('submit', function (event) {
        var form = event.target;
        if (!(form instanceof HTMLFormElement) || form.dataset.noAjax === 'true') return;

        var method = (form.method || 'get').toUpperCase();
        if (method !== 'GET' && method !== 'POST') return;

        var action = new URL(form.action || window.location.href, window.location.href);
        if (!isInternalUrl(action)) return;

        event.preventDefault();
        var options = {
            method: method,
            headers: {'X-Requested-With': 'XMLHttpRequest'},
        };

        if (method === 'GET') {
            new FormData(form).forEach(function (value, key) {
                action.searchParams.set(key, value);
            });
        } else {
            options.body = new FormData(form);
        }

        navigate(action, options, method === 'GET', true);
    });

    window.addEventListener('popstate', function () {
        navigate(new URL(window.location.href), {
            headers: {'X-Requested-With': 'XMLHttpRequest'},
        }, false, false);
    });

    document.addEventListener('DOMContentLoaded', function () {
        document.dispatchEvent(new CustomEvent('site:page-loaded'));
    });
})();
