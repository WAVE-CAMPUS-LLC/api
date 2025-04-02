// Customer Analytics JavaScript
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing customer analytics');
    
    try {
        // Check if we're on the analytics page with customers tab
        const customersTab = document.querySelector('.analytics-tab[data-tab="customers"]');
        
        if (!customersTab) {
            console.log('Customers tab not found, skipping initialization');
            return;
        }
        
        // Initialize pagination
        initializePagination();
        
        // Add click event to the customers tab to ensure proper data display
        customersTab.addEventListener('click', function() {
            console.log('Customers tab clicked');
            
            // Refresh pagination when tab is clicked
            refreshPagination();
        });
        
        // Add sorting functionality to the customer table headers
        const tableHeaders = document.querySelectorAll('#customers table th');
        if (tableHeaders.length > 0) {
            tableHeaders.forEach(header => {
                header.style.cursor = 'pointer';
                header.addEventListener('click', function() {
                    sortTable(this);
                    refreshPagination(); // Refresh pagination after sorting
                });
            });
        }
        
    } catch (e) {
        console.error('Error initializing customer analytics:', e);
    }
});

// Pagination variables
let currentPage = 1;
let rowsPerPage = 10;
let totalPages = 1;
let allRows = [];

// Initialize pagination
function initializePagination() {
    // Get all customer rows
    const table = document.getElementById('customersTable');
    if (!table) return;
    
    allRows = Array.from(table.querySelectorAll('tbody tr.customer-row'));
    
    // Initial sort by purchase date (descending)
    initialSortByPurchaseDate();
    
    // Set up entries per page dropdown
    const entriesPerPageSelect = document.getElementById('entriesPerPage');
    if (entriesPerPageSelect) {
        entriesPerPageSelect.addEventListener('change', function() {
            rowsPerPage = parseInt(this.value);
            currentPage = 1; // Reset to first page when changing entries per page
            refreshPagination();
        });
    }
    
    // Set up pagination buttons
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');
    
    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', function() {
            if (currentPage > 1) {
                currentPage--;
                refreshPagination();
            }
        });
    }
    
    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', function() {
            if (currentPage < totalPages) {
                currentPage++;
                refreshPagination();
            }
        });
    }
    
    // Initial pagination setup
    refreshPagination();
}

// Function to initially sort by purchase date in descending order
function initialSortByPurchaseDate() {
    if (allRows.length === 0) return;
    
    // Sort by purchase date (column index 4) in descending order
    allRows.sort((a, b) => {
        const aValue = a.children[4].textContent.trim();
        const bValue = b.children[4].textContent.trim();
        
        const aDate = new Date(aValue);
        const bDate = new Date(bValue);
        
        // Sort in descending order (newest first)
        return bDate - aDate;
    });
    
    // Update the header to show sort direction
    const dateHeader = document.querySelector('#customersTable th:nth-child(5)');
    if (dateHeader) {
        // Clear any existing sort indicators
        document.querySelectorAll('#customersTable th').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
        });
        
        // Set the sort direction attribute and add the visual indicator
        dateHeader.setAttribute('data-sort', 'desc');
        dateHeader.classList.add('sort-desc');
    }
}

// Refresh pagination display
function refreshPagination() {
    if (allRows.length === 0) return;
    
    // Calculate total pages
    totalPages = Math.ceil(allRows.length / rowsPerPage);
    
    // Update pagination info
    updatePaginationInfo();
    
    // Show/hide rows based on current page
    showRowsForCurrentPage();
    
    // Update pagination controls
    updatePaginationControls();
}

// Update pagination information text
function updatePaginationInfo() {
    const paginationInfo = document.getElementById('paginationInfo');
    if (!paginationInfo) return;
    
    const startIndex = (currentPage - 1) * rowsPerPage + 1;
    const endIndex = Math.min(currentPage * rowsPerPage, allRows.length);
    
    paginationInfo.textContent = `Showing ${startIndex}-${endIndex} of ${allRows.length}`;
    
    // Update total customers count
    const totalCustomersElement = document.getElementById('totalCustomers');
    if (totalCustomersElement) {
        totalCustomersElement.textContent = `Total customers: ${allRows.length}`;
    }
}

// Show rows for current page
function showRowsForCurrentPage() {
    const tbody = document.querySelector('#customersTable tbody');
    if (!tbody) return;
    
    // Hide all rows
    allRows.forEach(row => {
        row.style.display = 'none';
    });
    
    // Calculate which rows to show
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = Math.min(startIndex + rowsPerPage, allRows.length);
    
    // Show rows for current page
    for (let i = startIndex; i < endIndex; i++) {
        if (allRows[i]) {
            allRows[i].style.display = '';
        }
    }
}

// Update pagination controls (Previous/Next buttons and page numbers)
function updatePaginationControls() {
    const prevPageBtn = document.getElementById('prevPage');
    const nextPageBtn = document.getElementById('nextPage');
    const pageNumbersContainer = document.getElementById('pageNumbers');
    
    if (!prevPageBtn || !nextPageBtn || !pageNumbersContainer) return;
    
    // Enable/disable Previous button
    prevPageBtn.disabled = currentPage <= 1;
    
    // Enable/disable Next button
    nextPageBtn.disabled = currentPage >= totalPages;
    
    // Generate page number buttons
    pageNumbersContainer.innerHTML = '';
    
    // Determine which page numbers to show
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + 4);
    
    // Adjust if we're near the end
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }
    
    // Add first page button if not included in range
    if (startPage > 1) {
        addPageNumberButton(1, pageNumbersContainer);
        
        // Add ellipsis if there's a gap
        if (startPage > 2) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'px-2 py-1 text-gray-500';
            pageNumbersContainer.appendChild(ellipsis);
        }
    }
    
    // Add page number buttons
    for (let i = startPage; i <= endPage; i++) {
        addPageNumberButton(i, pageNumbersContainer);
    }
    
    // Add last page button if not included in range
    if (endPage < totalPages) {
        // Add ellipsis if there's a gap
        if (endPage < totalPages - 1) {
            const ellipsis = document.createElement('span');
            ellipsis.textContent = '...';
            ellipsis.className = 'px-2 py-1 text-gray-500';
            pageNumbersContainer.appendChild(ellipsis);
        }
        
        addPageNumberButton(totalPages, pageNumbersContainer);
    }
}

// Helper function to add a page number button
function addPageNumberButton(pageNum, container) {
    const pageButton = document.createElement('button');
    pageButton.textContent = pageNum;
    pageButton.className = 'px-3 py-1 border border-gray-300 rounded-md font-Wanted-Variable text-sm';
    
    // Highlight current page
    if (pageNum === currentPage) {
        pageButton.classList.add('bg-blue-500', 'text-white');
    } else {
        pageButton.classList.add('bg-white', 'text-gray-700', 'hover:bg-gray-50');
    }
    
    pageButton.addEventListener('click', function() {
        currentPage = pageNum;
        refreshPagination();
    });
    
    container.appendChild(pageButton);
}

// Function to sort the table when a header is clicked
function sortTable(header) {
    const table = header.closest('table');
    const tbody = table.querySelector('tbody');
    
    // Get the index of the clicked header
    const headerIndex = Array.from(header.parentNode.children).indexOf(header);
    
    // Determine sort direction
    const currentDir = header.getAttribute('data-sort') || 'asc';
    const newDir = currentDir === 'asc' ? 'desc' : 'asc';
    
    // Update sort direction attribute
    header.setAttribute('data-sort', newDir);
    
    // Clear sort indicators from all headers
    table.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Add sort indicator to current header
    header.classList.add(`sort-${newDir}`);
    
    // Sort the rows
    allRows.sort((a, b) => {
        const aValue = a.children[headerIndex].textContent.trim();
        const bValue = b.children[headerIndex].textContent.trim();
        
        // Handle date sorting for purchase date column
        if (headerIndex === 4) { // Date of Purchase column
            const aDate = new Date(aValue);
            const bDate = new Date(bValue);
            return newDir === 'asc' ? aDate - bDate : bDate - aDate;
        }
        
        // Regular string comparison for other columns
        if (newDir === 'asc') {
            return aValue.localeCompare(bValue);
        } else {
            return bValue.localeCompare(aValue);
        }
    });
    
    // Re-append rows in the new order (this is now handled by refreshPagination)
    // We don't need to reappend all rows to the DOM, just update our allRows array
}
