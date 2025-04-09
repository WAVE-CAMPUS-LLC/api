/**
 * Pagination functionality for the Profile Overview page
 * Handles both Tickets and Transactions sections
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize pagination for tickets section when it becomes visible
    document.querySelectorAll('.profile-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            if (targetTab === 'myTickets-information') {
                initTicketsPagination();
            } else if (targetTab === 'myPurchases-information') {
                initTransactionsPagination();
            }
        });
    });

    // Initialize pagination if the respective tab is active on page load
    if (document.querySelector('[data-tab="myTickets-information"].tab-active')) {
        initTicketsPagination();
    }
    if (document.querySelector('[data-tab="myPurchases-information"].tab-active')) {
        initTransactionsPagination();
    }
});

/**
 * Initialize pagination for the tickets section
 */
function initTicketsPagination() {
    const ticketsContainer = document.querySelector('#myTickets-information .tickets-container');
    if (!ticketsContainer) return;

    const ticketCards = Array.from(ticketsContainer.querySelectorAll('.ticket-card'));
    if (ticketCards.length === 0) return;

    setupPagination(ticketCards, ticketsContainer, 'tickets');
}

/**
 * Initialize pagination for the transactions section
 */
function initTransactionsPagination() {
    const transactionsContainer = document.querySelector('#myPurchases .grid');
    if (!transactionsContainer) return;

    const transactionCards = Array.from(transactionsContainer.querySelectorAll('div[class^="bg-gradient-to-b"]'));
    if (transactionCards.length === 0) return;

    setupPagination(transactionCards, transactionsContainer, 'transactions');
}

/**
 * Set up pagination for a container with items
 * @param {Array} items - Array of DOM elements to paginate
 * @param {Element} container - Container element
 * @param {string} sectionId - Identifier for the section ('tickets' or 'transactions')
 */
function setupPagination(items, container, sectionId) {
    // Get or create pagination controls container
    let paginationControls = document.getElementById(`${sectionId}-pagination-controls`);
    if (!paginationControls) {
        paginationControls = document.createElement('div');
        paginationControls.id = `${sectionId}-pagination-controls`;
        paginationControls.className = 'pagination-controls flex flex-col sm:flex-row justify-between items-center gap-3 mt-4 border-t border-gray-100 pt-4';
        container.parentNode.insertBefore(paginationControls, container.nextSibling);
    }

    // Get or create pagination info container
    let paginationInfo = document.getElementById(`${sectionId}-pagination-info`);
    if (!paginationInfo) {
        paginationInfo = document.createElement('div');
        paginationInfo.id = `${sectionId}-pagination-info`;
        paginationInfo.className = 'pagination-info flex items-center gap-2 text-sm text-gray-600';
        paginationControls.appendChild(paginationInfo);
    }

    // Get or create pagination navigation container
    let paginationNav = document.getElementById(`${sectionId}-pagination-nav`);
    if (!paginationNav) {
        paginationNav = document.createElement('div');
        paginationNav.id = `${sectionId}-pagination-nav`;
        paginationNav.className = 'pagination-nav flex items-center gap-1';
        paginationControls.appendChild(paginationNav);
    }

    // Create entries per page selector if it doesn't exist
    let entriesSelector = document.getElementById(`${sectionId}-entries-selector`);
    if (!entriesSelector) {
        const selectorContainer = document.createElement('div');
        selectorContainer.className = 'entries-selector-container flex items-center gap-2 text-sm';
        
        const label = document.createElement('label');
        label.textContent = 'Show:';
        label.htmlFor = `${sectionId}-entries-selector`;
        
        entriesSelector = document.createElement('select');
        entriesSelector.id = `${sectionId}-entries-selector`;
        entriesSelector.className = 'border border-gray-200 rounded px-2 py-1 text-sm';
        
        [10, 25, 50, 100].forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            entriesSelector.appendChild(option);
        });
        
        selectorContainer.appendChild(label);
        selectorContainer.appendChild(entriesSelector);
        paginationInfo.appendChild(selectorContainer);
    }

    // Store pagination state
    const state = {
        items: items,
        currentPage: 1,
        itemsPerPage: parseInt(entriesSelector.value) || 10,
        totalItems: items.length,
        totalPages: Math.ceil(items.length / (parseInt(entriesSelector.value) || 10))
    };

    // Update pagination when entries per page changes
    entriesSelector.addEventListener('change', function() {
        state.itemsPerPage = parseInt(this.value);
        state.totalPages = Math.ceil(state.totalItems / state.itemsPerPage);
        state.currentPage = 1; // Reset to first page when changing items per page
        updatePagination(state, container, sectionId);
    });

    // Initial pagination setup
    updatePagination(state, container, sectionId);
}

/**
 * Update pagination display and controls
 * @param {Object} state - Pagination state object
 * @param {Element} container - Container element
 * @param {string} sectionId - Identifier for the section
 */
function updatePagination(state, container, sectionId) {
    // Calculate start and end indices
    const startIndex = (state.currentPage - 1) * state.itemsPerPage;
    const endIndex = Math.min(startIndex + state.itemsPerPage, state.totalItems);
    
    // Hide all items
    state.items.forEach(item => {
        item.style.display = 'none';
    });
    
    // Show only items for current page
    for (let i = startIndex; i < endIndex; i++) {
        state.items[i].style.display = '';
    }
    
    // Update pagination info
    const paginationInfo = document.getElementById(`${sectionId}-pagination-info`);
    const infoText = document.createElement('span');
    infoText.textContent = `Showing ${startIndex + 1} to ${endIndex} of ${state.totalItems} entries`;
    
    // Clear previous info text
    Array.from(paginationInfo.querySelectorAll('span')).forEach(span => {
        if (span !== paginationInfo.querySelector('.entries-selector-container')) {
            span.remove();
        }
    });
    
    paginationInfo.appendChild(infoText);
    
    // Update pagination navigation
    updatePaginationNav(state, sectionId);
}

/**
 * Update pagination navigation controls
 * @param {Object} state - Pagination state object
 * @param {string} sectionId - Identifier for the section
 */
function updatePaginationNav(state, sectionId) {
    const paginationNav = document.getElementById(`${sectionId}-pagination-nav`);
    paginationNav.innerHTML = '';
    
    // Previous button
    const prevButton = createPaginationButton('Previous', state.currentPage > 1);
    prevButton.addEventListener('click', function() {
        if (state.currentPage > 1) {
            state.currentPage--;
            updatePagination(state, document.querySelector(`#${sectionId === 'tickets' ? 'myTickets-information .tickets-container' : 'myPurchases .grid'}`), sectionId);
        }
    });
    paginationNav.appendChild(prevButton);
    
    // Page numbers
    const pageNumbers = getPageNumbersToShow(state.currentPage, state.totalPages);
    pageNumbers.forEach(pageNum => {
        if (pageNum === '...') {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'px-2 py-1 text-gray-500';
            paginationNav.appendChild(ellipsis);
        } else {
            const pageButton = createPaginationButton(pageNum, true, pageNum === state.currentPage);
            pageButton.addEventListener('click', function() {
                state.currentPage = pageNum;
                updatePagination(state, document.querySelector(`#${sectionId === 'tickets' ? 'myTickets-information .tickets-container' : 'myPurchases .grid'}`), sectionId);
            });
            paginationNav.appendChild(pageButton);
        }
    });
    
    // Next button
    const nextButton = createPaginationButton('Next', state.currentPage < state.totalPages);
    nextButton.addEventListener('click', function() {
        if (state.currentPage < state.totalPages) {
            state.currentPage++;
            updatePagination(state, document.querySelector(`#${sectionId === 'tickets' ? 'myTickets-information .tickets-container' : 'myPurchases .grid'}`), sectionId);
        }
    });
    paginationNav.appendChild(nextButton);
}

/**
 * Create a pagination button element
 * @param {string|number} text - Button text
 * @param {boolean} enabled - Whether the button is enabled
 * @param {boolean} active - Whether the button is active (current page)
 * @returns {Element} - Button element
 */
function createPaginationButton(text, enabled = true, active = false) {
    const button = document.createElement('button');
    button.textContent = text;
    
    if (active) {
        button.className = 'px-3 py-1 bg-green text-white rounded font-Wanted-Medium';
    } else if (enabled) {
        button.className = 'px-3 py-1 bg-white border border-gray-200 rounded hover:bg-gray-50 font-Wanted-Medium';
    } else {
        button.className = 'px-3 py-1 bg-gray-100 text-gray-400 rounded cursor-not-allowed font-Wanted-Medium';
        button.disabled = true;
    }
    
    return button;
}

/**
 * Get array of page numbers to display in pagination
 * @param {number} currentPage - Current page number
 * @param {number} totalPages - Total number of pages
 * @returns {Array} - Array of page numbers to display
 */
function getPageNumbersToShow(currentPage, totalPages) {
    if (totalPages <= 7) {
        // If 7 or fewer pages, show all page numbers
        return Array.from({length: totalPages}, (_, i) => i + 1);
    } else {
        // Otherwise show a subset with ellipses
        const pages = [];
        
        // Always include first page
        pages.push(1);
        
        // Add ellipsis if current page is more than 3
        if (currentPage > 3) {
            pages.push('...');
        }
        
        // Add page numbers around current page
        const rangeStart = Math.max(2, currentPage - 1);
        const rangeEnd = Math.min(totalPages - 1, currentPage + 1);
        
        for (let i = rangeStart; i <= rangeEnd; i++) {
            pages.push(i);
        }
        
        // Add ellipsis if current page is less than totalPages - 2
        if (currentPage < totalPages - 2) {
            pages.push('...');
        }
        
        // Always include last page
        pages.push(totalPages);
        
        return pages;
    }
}
