// Audience Analytics JavaScript for Event Host Dashboard
console.log('audienceAnalytics.js executing');

// Function to initialize audience analytics
function initializeAudienceAnalytics() {
    console.log('Initializing audience analytics');
    
    try {
        // Get the audience tab element
        const audienceTab = document.querySelector('.analytics-tab[data-tab="audience"]');
        
        if (!audienceTab) {
            console.error('Audience tab element not found!');
            return;
        }
        
        // Initialize charts when audience tab is clicked
        audienceTab.addEventListener('click', function() {
            renderAgeDistributionChart();
            renderLoginStatusChart();
        });
        
        // Also initialize if audience tab is already active
        if (audienceTab.classList.contains('tab-active')) {
            renderAgeDistributionChart();
            renderLoginStatusChart();
        }
    } catch (e) {
        console.error('Error in initializeAudienceAnalytics:', e);
    }
}

// Function to render age distribution chart
function renderAgeDistributionChart() {
    try {
        console.log('Rendering age distribution chart');
        
        // Get the age distribution data from the hidden input
        const ageDistributionElement = document.getElementById('ageDistributionData');
        if (!ageDistributionElement) {
            console.error('ageDistributionData element not found!');
            return;
        }
        
        const ageDistributionData = JSON.parse(ageDistributionElement.value);
        console.log('Age distribution data:', ageDistributionData);
        
        // Get the canvas element
        const ctx = document.getElementById('ageDistributionChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (window.ageDistributionChartInstance) {
            window.ageDistributionChartInstance.destroy();
        }
        
        // Check if we have any data
        const hasData = Object.values(ageDistributionData).some(value => value > 0);
        
        // Create a new chart with the data
        window.ageDistributionChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(ageDistributionData),
                datasets: [{
                    label: 'Number of Attendees',
                    data: Object.values(ageDistributionData),
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(75, 192, 192, 0.6)',
                        'rgba(153, 102, 255, 0.6)',
                        'rgba(255, 159, 64, 0.6)',
                        'rgba(255, 99, 132, 0.6)',
                        'rgba(255, 205, 86, 0.6)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)',
                        'rgba(255, 159, 64, 1)',
                        'rgba(255, 99, 132, 1)',
                        'rgba(255, 205, 86, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0,
                            stepSize: 1
                        },
                        title: {
                            display: true,
                            text: 'Number of Attendees'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Age Groups'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Attendees: ${context.raw}`;
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Audience Age Distribution',
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
        
        // Display a message if there's no data
        if (!hasData) {
            const container = document.getElementById('age-distribution-container');
            
            // Check if the message already exists
            if (!container.querySelector('.no-data-message')) {
                const noDataMessage = document.createElement('div');
                noDataMessage.className = 'no-data-message text-center mt-4 text-gray-500';
                noDataMessage.textContent = 'No age data available. This may be because all tickets were purchased by guest users.';
                container.appendChild(noDataMessage);
            }
        }
    } catch (e) {
        console.error('Error in renderAgeDistributionChart:', e);
    }
}

// Function to render login status pie chart
function renderLoginStatusChart() {
    try {
        console.log('Rendering login status chart');
        
        // Get the login status data from the hidden input
        const loginStatusElement = document.getElementById('loginStatusData');
        if (!loginStatusElement) {
            console.error('loginStatusData element not found!');
            return;
        }
        
        const loginStatusData = JSON.parse(loginStatusElement.value);
        console.log('Login status data:', loginStatusData);
        
        // Get the canvas element
        const ctx = document.getElementById('loginStatusChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (window.loginStatusChartInstance) {
            window.loginStatusChartInstance.destroy();
        }
        
        // Check if we have any data
        const hasData = Object.values(loginStatusData).some(value => value > 0);
        
        // Create a new chart with the data
        window.loginStatusChartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: Object.keys(loginStatusData),
                datasets: [{
                    data: Object.values(loginStatusData),
                    backgroundColor: [
                        'rgba(54, 162, 235, 0.6)',
                        'rgba(255, 99, 132, 0.6)'
                    ],
                    borderColor: [
                        'rgba(54, 162, 235, 1)',
                        'rgba(255, 99, 132, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: {
                                size: 14
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: 'User Login Status Distribution',
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
        
        // Display a message if there's no data
        if (!hasData) {
            const container = document.getElementById('login-status-container');
            
            // Check if the message already exists
            if (!container.querySelector('.no-data-message')) {
                const noDataMessage = document.createElement('div');
                noDataMessage.className = 'no-data-message text-center mt-4 text-gray-500';
                noDataMessage.textContent = 'No ticket data available for this event.';
                container.appendChild(noDataMessage);
            }
        }
    } catch (e) {
        console.error('Error in renderLoginStatusChart:', e);
    }
}

// Try to initialize immediately
initializeAudienceAnalytics();

// Also initialize on DOMContentLoaded for safety
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired');
    initializeAudienceAnalytics();
});

// Also initialize on window.onload for maximum compatibility
window.onload = function() {
    console.log('window.onload event fired');
    initializeAudienceAnalytics();
};
