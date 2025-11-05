// Add "Ask AI" button to the Material for MkDocs navbar
document.addEventListener('DOMContentLoaded', function() {
    // Find the header navigation actions (right side of navbar)
    const headerActions = document.querySelector('.md-header__topic + .md-header__option');
    const headerTitle = document.querySelector('.md-header__title');

    if (headerTitle) {
        // Create the Ask AI button
        const askAiButton = document.createElement('a');
        askAiButton.href = '/chat';  // Update this URL to your desired destination
        askAiButton.className = 'md-button ask-ai-button';
        askAiButton.textContent = 'Ask AI';
        askAiButton.title = 'Ask AI about Django Ninja';

        // Create a container for the button
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'ask-ai-button-container';
        buttonContainer.appendChild(askAiButton);

        // Insert the button after the header title
        const header = document.querySelector('.md-header__inner');
        if (header) {
            // Find the right spot - after title, before search/repo buttons
            const source = document.querySelector('.md-header__source');
            if (source) {
                header.insertBefore(buttonContainer, source);
            } else {
                header.appendChild(buttonContainer);
            }
        }
    }
});
