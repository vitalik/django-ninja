# Ask AI

Please feel free to share any questions or describe any problems you're encountering. Simply enter your text in the chat, and I'll be happy to assist you.

<style>
.serenity_chat__powered { display: none !important; }
.md-sidebar--secondary { display: none !important; }
.serenity_widget__container {
    max-width: 1200px !important;
}

.serenity_app {
    --serenity-answer-code-bg: #fafafa;
    --serenity-widget-bg: #ffffff;
}

[data-md-color-scheme="slate"] .serenity_theme-dark {
    --serenity-widget-bg: var(--md-default-bg-color);
    --serenity-answer-code-bg: var(--md-code-bg-color);
    --serenity-widget-text: var(--md-default-fg-color);
    --serenity-widget-primary: var(--serenity-widget-secondary);
    --serenity-widget-placeholder: color-mix(
        in srgb,
        var(--md-default-fg-color) 70%,
        transparent
    );
}

</style>

<div id="serenity"></div>

<script>
var SERENITY_WIDGET = {
    api_url: "https://public.serenitygpt.com/api/v2/",
    api_token: "FqbM1QFShh5mGOD7",
    popup: false,
};
</script>
<script src="https://js.serenitygpt.com/widget.js"></script>
<script>
(function () {
    function serenityShouldBeDark() {
        var schemeEl = document.querySelector('[data-md-color-scheme]');
        return !!schemeEl && schemeEl.getAttribute('data-md-color-scheme') === 'slate';
    }

    function syncSerenityTheme() {
        var widget = document.querySelector('.serenity_app');
        if (!widget) return;
        widget.classList.toggle('serenity_theme-dark', serenityShouldBeDark());
    }

    document.addEventListener('DOMContentLoaded', function () {
        var mountObserver = new MutationObserver(syncSerenityTheme);
        mountObserver.observe(document.body, { childList: true, subtree: true });
        syncSerenityTheme();

        var schemeTarget = document.querySelector('[data-md-color-scheme]') || document.body;
        var schemeObserver = new MutationObserver(syncSerenityTheme);
        schemeObserver.observe(schemeTarget, {
            attributes: true,
            attributeFilter: ['data-md-color-scheme']
        });
    });
})();
</script>
