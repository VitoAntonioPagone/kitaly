(() => {
    class ThemeManager {
        constructor(options = {}) {
            this.storageKey = options.storageKey || 'theme';
            this.root = document.documentElement;
            this.toggle = null;
            this.boundHandleToggleClick = this.handleToggleClick.bind(this);
            this.boundHandleToggleKeydown = this.handleToggleKeydown.bind(this);
        }

        init() {
            if (window.__kitalyThemeManagerInitialized) {
                return;
            }
            window.__kitalyThemeManagerInitialized = true;

            this.toggle = document.getElementById('theme-toggle');
            this.applyTheme(this.getInitialTheme(), { persist: false, animate: false });
            this.bindToggle();
        }

        getSavedTheme() {
            try {
                const savedTheme = localStorage.getItem(this.storageKey);
                return savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : null;
            } catch (error) {
                return null;
            }
        }

        getInitialTheme() {
            return this.getSavedTheme() || 'light';
        }

        applyTheme(theme, options = {}) {
            const { persist = true, animate = true } = options;
            const normalizedTheme = theme === 'dark' ? 'dark' : 'light';

            if (animate) {
                this.root.classList.add('theme-animating');
                this.root.classList.toggle('theme-switching-to-dark', normalizedTheme === 'dark');
                window.setTimeout(() => {
                    this.root.classList.remove('theme-animating');
                    this.root.classList.remove('theme-switching-to-dark');
                }, 340);
            } else {
                this.root.classList.remove('theme-switching-to-dark');
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

    }

    const manager = new ThemeManager();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => manager.init(), { once: true });
    } else {
        manager.init();
    }
    window.KitalyThemeManager = manager;
})();
