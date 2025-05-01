/**
 * Font Loader Script for FoglioAI
 * Handles font loading strategy for Old Standard TT font
 */

// Mark JS as available
document.documentElement.classList.remove('no-js');

// Check for FontFaceSet API support
if ('fonts' in document) {
    // Setup font loading promises
    Promise.all([
        document.fonts.load('400 1em "Old Standard TT"'),
        document.fonts.load('700 1em "Old Standard TT"'),
        document.fonts.load('italic 400 1em "Old Standard TT"')
    ]).then(function() {
        // Fonts loaded - mark as ready
        document.documentElement.classList.add('fonts-loaded');
        
        // Store in localStorage for future visits
        try {
            localStorage.setItem('fonts-loaded', 'true');
        } catch (e) {
            // localStorage might be unavailable in some contexts
            console.warn('Could not save font loading state to localStorage');
        }
    }).catch(function(err) {
        console.warn('Font loading failed:', err);
        // Fallback - mark as loaded anyway to use system fonts
        document.documentElement.classList.add('fonts-loaded');
    });
} else {
    // No font loading API support - mark as loaded to use system fonts
    document.documentElement.classList.add('fonts-loaded');
}

// Check for cached font loading state
try {
    if (localStorage.getItem('fonts-loaded')) {
        // Immediately apply loaded fonts if previously cached
        document.documentElement.classList.add('fonts-loaded');
    }
} catch (e) {
    // localStorage might be unavailable
    console.warn('Could not access localStorage for font loading state');
}

// Set a timeout as a fallback
setTimeout(function() {
    if (!document.documentElement.classList.contains('fonts-loaded')) {
        document.documentElement.classList.add('fonts-loaded');
        console.warn('Font loading timed out, using fallback fonts');
    }
}, 3000); // 3 seconds timeout 