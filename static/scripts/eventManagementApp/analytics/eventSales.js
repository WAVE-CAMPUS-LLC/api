// Immediately execute script to avoid DOMContentLoaded issues
console.log('eventSales.js executing immediately');

// Function to initialize everything once the page is ready
function initializeEventSales() {
    console.log('Initializing event sales analytics');
    
    try {
        // Check if the required elements exist
        const eventSalesURLElement = document.getElementById('eventSalesURL');
        
        if (!eventSalesURLElement) {
            console.error('eventSalesURL element not found!');
            return;
        }
        
        const eventSalesURL = eventSalesURLElement.value;
        
        console.log('Event Sales URL:', eventSalesURL);
        
        // Initialize chart with sales data
        initializeChart(eventSalesURL);
        
        // Add event listeners for period selection
        const periodSelect = document.getElementById('periodSelect');
        if (periodSelect) {
            periodSelect.addEventListener('change', function() {
                updateChart(eventSalesURL, this.value);
            });
        }
    } catch (e) {
        console.error('Error in initializeEventSales:', e);
    }
}

// Function to initialize chart
function initializeChart(eventSalesURL) {
    try {
        console.log('Initializing chart with URL:', eventSalesURL);
        
        const chartLastFetchElement = document.getElementById('chart-last-fetch');
        if (chartLastFetchElement) {
            chartLastFetchElement.textContent = new Date().toLocaleTimeString();
        }
        
        // Show loading state
        const salesContent = document.getElementById('sales-content');
        if (!salesContent) {
            console.error('sales-content element not found!');
            return;
        }
        
        salesContent.innerHTML = '<div class="flex justify-center items-center h-[500px]"><p class="text-gray-500">Loading sales data...</p></div>';
        
        // Default to daily period
        const period = 'daily';
        
        const xhr = new XMLHttpRequest();
        xhr.open('GET', `${eventSalesURL}?period=${period}`, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        
        xhr.onreadystatechange = function() {
            console.log(`XHR readyState: ${xhr.readyState}, status: ${xhr.status}`);
            if (xhr.readyState === 4) { // Complete
                if (xhr.status >= 200 && xhr.status < 300) {
                    console.log('XHR response text:', xhr.responseText);
                    try {
                        const data = JSON.parse(xhr.responseText);
                        console.log('Parsed data:', data);
                        
                        // Restore the canvas element
                        salesContent.innerHTML = '<canvas id="eventSalesChartOverall" class="font-Wanted-Bold w-[600px] h-[500px] text-green"></canvas>';
                        const ctx = document.getElementById('eventSalesChartOverall').getContext('2d');

                        // Destroy existing chart if it exists
                        if (window.chartInstance) {
                            window.chartInstance.destroy();
                        }

                        // Check if we have any sales data
                        const hasData = data.counts.some(count => count > 0);
                        
                        // Create a new chart with updated data
                        window.chartInstance = new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: data.labels, // These labels will be the dates or periods
                                datasets: [{
                                    label: `${period.charAt(0).toUpperCase() + period.slice(1)} Sales`,
                                    data: data.counts, // The total sales for each period
                                    borderColor: 'rgba(75, 192, 192, 1)',
                                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                                    borderWidth: 2,
                                    fill: true,
                                }]
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    x: {
                                        title: {
                                            display: true,
                                            text: period.charAt(0).toUpperCase() + period.slice(1) + ' Period'
                                        }
                                    },
                                    y: {
                                        title: {
                                            display: true,
                                            text: 'Sales Count'
                                        },
                                        beginAtZero: true,
                                        ticks: {
                                            precision: 0,
                                            stepSize: 1
                                        }
                                    }
                                },
                                plugins: {
                                    legend: {
                                        display: true,
                                        labels: {
                                            color: '#008d95',
                                            font: {
                                                size: 16
                                            },
                                        }
                                    },
                                    tooltip: {
                                        callbacks: {
                                            label: function(context) {
                                                return `Sales: ${context.raw}`;
                                            }
                                        }
                                    }
                                },
                            }
                        });
                        
                        // Display a message if there's no data
                        if (!hasData) {
                            const noDataMessage = document.createElement('div');
                            noDataMessage.className = 'text-center mt-4 text-gray-500';
                            noDataMessage.textContent = 'No sales data available for this period.';
                            salesContent.appendChild(noDataMessage);
                        }
                        
                        // Add event listeners for period selection
                        const periodSelect = document.getElementById('periodSelect');
                        if (periodSelect) {
                            periodSelect.addEventListener('change', function () {
                                const selectedPeriod = periodSelect.value;  // Get selected period (daily, weekly, monthly)
                                console.log('Period changed to:', selectedPeriod);
                                updateChart(eventSalesURL, selectedPeriod);
                            });
                        } else {
                            console.error('periodSelect element not found!');
                        }
                    } catch (e) {
                        console.error('Error parsing JSON:', e);
                        console.error('Raw response:', xhr.responseText);
                        salesContent.innerHTML = `<div class="flex justify-center items-center h-[500px]">
                            <p class="text-red-500">Error loading sales data. Please try again later.</p>
                        </div>`;
                    }
                } else {
                    console.error('HTTP error:', xhr.status);
                    console.error('Response text:', xhr.responseText);
                    salesContent.innerHTML = `<div class="flex justify-center items-center h-[500px]">
                        <p class="text-red-500">Error loading sales data. Please try again later.</p>
                    </div>`;
                }
            }
        };
        
        xhr.onerror = function(e) {
            console.error('XHR error:', e);
            salesContent.innerHTML = `<div class="flex justify-center items-center h-[500px]">
                <p class="text-red-500">Error loading sales data. Please try again later.</p>
            </div>`;
        };
        
        console.log('Sending XHR request to:', `${eventSalesURL}?period=${period}`);
        xhr.send();
        console.log('XHR request sent');
    } catch (e) {
        console.error('Error in initializeChart:', e);
    }
}

// Function to update chart with new period
function updateChart(eventSalesURL, period) {
    try {
        console.log('Updating chart for period:', period);
        
        const chartLastFetchElement = document.getElementById('chart-last-fetch');
        if (chartLastFetchElement) {
            chartLastFetchElement.textContent = new Date().toLocaleTimeString();
        }
        
        // Show loading state
        const salesContent = document.getElementById('sales-content');
        if (!salesContent) {
            console.error('sales-content element not found!');
            return;
        }
        
        salesContent.innerHTML = '<div class="flex justify-center items-center h-[500px]"><p class="text-gray-500">Loading sales data...</p></div>';
        
        const xhr = new XMLHttpRequest();
        xhr.open('GET', `${eventSalesURL}?period=${period}`, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        
        xhr.onreadystatechange = function() {
            console.log(`XHR readyState: ${xhr.readyState}, status: ${xhr.status}`);
            if (xhr.readyState === 4) { // Complete
                if (xhr.status >= 200 && xhr.status < 300) {
                    console.log('XHR response text:', xhr.responseText);
                    try {
                        const data = JSON.parse(xhr.responseText);
                        console.log('Parsed data:', data);
                        
                        // Restore the canvas element
                        salesContent.innerHTML = '<canvas id="eventSalesChartOverall" class="font-Wanted-Bold w-[600px] h-[500px] text-green"></canvas>';
                        const ctx = document.getElementById('eventSalesChartOverall').getContext('2d');

                        // Destroy existing chart if it exists
                        if (window.chartInstance) {
                            window.chartInstance.destroy();
                        }

                        // Check if we have any sales data
                        const hasData = data.counts.some(count => count > 0);
                        
                        // Create a new chart with updated data
                        window.chartInstance = new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: data.labels, // These labels will be the dates or periods
                                datasets: [{
                                    label: `${period.charAt(0).toUpperCase() + period.slice(1)} Sales`,
                                    data: data.counts, // The total sales for each period
                                    borderColor: 'rgba(75, 192, 192, 1)',
                                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                                    borderWidth: 2,
                                    fill: true,
                                }]
                            },
                            options: {
                                responsive: true,
                                scales: {
                                    x: {
                                        title: {
                                            display: true,
                                            text: period.charAt(0).toUpperCase() + period.slice(1) + ' Period'
                                        }
                                    },
                                    y: {
                                        title: {
                                            display: true,
                                            text: 'Sales Count'
                                        },
                                        beginAtZero: true,
                                        ticks: {
                                            precision: 0,
                                            stepSize: 1
                                        }
                                    }
                                },
                                plugins: {
                                    legend: {
                                        display: true,
                                        labels: {
                                            color: '#008d95',
                                            font: {
                                                size: 16
                                            },
                                        }
                                    },
                                    tooltip: {
                                        callbacks: {
                                            label: function(context) {
                                                return `Sales: ${context.raw}`;
                                            }
                                        }
                                    }
                                },
                            }
                        });
                        
                        // Display a message if there's no data
                        if (!hasData) {
                            const noDataMessage = document.createElement('div');
                            noDataMessage.className = 'text-center mt-4 text-gray-500';
                            noDataMessage.textContent = 'No sales data available for this period.';
                            salesContent.appendChild(noDataMessage);
                        }
                    } catch (e) {
                        console.error('Error parsing JSON:', e);
                        console.error('Raw response:', xhr.responseText);
                        salesContent.innerHTML = `<div class="flex justify-center items-center h-[500px]">
                            <p class="text-red-500">Error loading sales data. Please try again later.</p>
                        </div>`;
                    }
                } else {
                    console.error('HTTP error:', xhr.status);
                    console.error('Response text:', xhr.responseText);
                    salesContent.innerHTML = `<div class="flex justify-center items-center h-[500px]">
                        <p class="text-red-500">Error loading sales data. Please try again later.</p>
                    </div>`;
                }
            }
        };
        
        xhr.onerror = function(e) {
            console.error('XHR error:', e);
            salesContent.innerHTML = `<div class="flex justify-center items-center h-[500px]">
                <p class="text-red-500">Error loading sales data. Please try again later.</p>
            </div>`;
        };
        
        console.log('Sending XHR request to:', `${eventSalesURL}?period=${period}`);
        xhr.send();
        console.log('XHR request sent');
    } catch (e) {
        console.error('Error in updateChart:', e);
    }
}

// Try to initialize immediately
initializeEventSales();

// Also initialize on DOMContentLoaded for safety
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired');
    initializeEventSales();
});

// Also initialize on window.onload for maximum compatibility
window.onload = function() {
    console.log('window.onload event fired');
    initializeEventSales();
};
