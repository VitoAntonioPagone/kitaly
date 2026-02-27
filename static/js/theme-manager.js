(() => {
    class ThemeManager {
        constructor(options = {}) {
            this.storageKey = options.storageKey || 'theme';
            this.root = document.documentElement;
            this.toggle = null;
            this.mediaQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
            this.boundHandleToggleClick = this.handleToggleClick.bind(this);
            this.boundHandleToggleKeydown = this.handleToggleKeydown.bind(this);
            this.boundHandleSystemThemeChange = this.handleSystemThemeChange.bind(this);
        }

        init() {
            if (window.__kitalyThemeManagerInitialized) {
                return;
            }
            window.__kitalyThemeManagerInitialized = true;

            this.toggle = document.getElementById('theme-toggle');
            this.applyTheme(this.getInitialTheme(), { persist: false, animate: false });
            this.bindToggle();
            this.bindSystemPreference();
        }

        getSavedTheme() {
            try {
                const savedTheme = localStorage.getItem(this.storageKey);
                return savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : null;
            } catch (error) {
                return null;
            }
        }

        getSystemTheme() {
            return this.mediaQuery && this.mediaQuery.matches ? 'dark' : 'light';
        }

        getInitialTheme() {
            return this.getSavedTheme() || this.getSystemTheme();
        }

        applyTheme(theme, options = {}) {
            const { persist = true, animate = true } = options;
            const normalizedTheme = theme === 'dark' ? 'dark' : 'light';

            if (animate) {
                this.root.classList.add('theme-animating');
                window.setTimeout(() => this.root.classList.remove('theme-animating'), 340);
            }

            this.root.classList.toggle('dark', normalizedTheme === 'dark');
            this.root.dataset.theme = normalizedTheme;
            this.root.style.colorScheme = normalizedTheme;

            if (persist) {
                try {
                    localStorage.setItem(this.storageKey, normalizedTheme);
                } catch (error) {
                    // Ignore storage write errors.
                }
            }

            this.syncToggle(normalizedTheme);
        }

        toggleTheme() {
            const nextTheme = this.root.classList.contains('dark') ? 'light' : 'dark';
            this.applyTheme(nextTheme, { persist: true, animate: true });
        }

        syncToggle(theme) {
            if (!this.toggle) {
                return;
            }
            const isDark = theme === 'dark';
            this.toggle.setAttribute('aria-checked', String(isDark));
            this.toggle.dataset.theme = theme;
        }

        bindToggle() {
            if (!this.toggle) {
                return;
            }
            this.toggle.removeEventListener('click', this.boundHandleToggleClick);
            this.toggle.removeEventListener('keydown', this.boundHandleToggleKeydown);
            this.toggle.addEventListener('click', this.boundHandleToggleClick);
            this.toggle.addEventListener('keydown', this.boundHandleToggleKeydown);
        }

        bindSystemPreference() {
            if (!this.mediaQuery) {
                return;
            }
            if (typeof this.mediaQuery.addEventListener === 'function') {
                this.mediaQuery.addEventListener('change', this.boundHandleSystemThemeChange);
            } else if (typeof this.mediaQuery.addListener === 'function') {
                this.mediaQuery.addListener(this.boundHandleSystemThemeChange);
            }
        }

        handleToggleClick() {
            this.toggleTheme();
        }

        handleToggleKeydown(event) {
            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }
            event.preventDefault();
            this.toggleTheme();
        }

        handleSystemThemeChange(event) {
            if (this.getSavedTheme()) {
                return;
            }
            this.applyTheme(event.matches ? 'dark' : 'light', { persist: false, animate: false });
        }
    }

    const manager = new ThemeManager();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => manager.init(), { once: true });
    } else {
        manager.init();
    }
    window.KitalyThemeManager = manager;
})();
