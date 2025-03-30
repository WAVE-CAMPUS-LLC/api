// Attendance Analytics JavaScript for Event Host Dashboard
console.log('attendanceAnalytics.js executing');

// Function to initialize attendance analytics
function initializeAttendanceAnalytics() {
    console.log('Initializing attendance analytics');
    
    try {
        // Get the attendance tab element
        const attendanceTab = document.querySelector('.analytics-tab[data-tab="attendance"]');
        
        if (!attendanceTab) {
            console.error('Attendance tab element not found!');
            return;
        }
        
        // Initialize chart when attendance tab is clicked
        attendanceTab.addEventListener('click', function() {
            renderAttendanceChart();
        });
        
        // Also initialize if attendance tab is already active
        if (attendanceTab.classList.contains('tab-active')) {
            renderAttendanceChart();
        }
    } catch (e) {
        console.error('Error in initializeAttendanceAnalytics:', e);
    }
}

// Function to render attendance chart
function renderAttendanceChart() {
    try {
        console.log('Rendering attendance chart');
        
        // Get the attendance data from the hidden input
        const attendanceElement = document.getElementById('attendanceData');
        if (!attendanceElement) {
            console.error('attendanceData element not found!');
            return;
        }
        
        const attendanceData = JSON.parse(attendanceElement.value);
        console.log('Attendance data:', attendanceData);
        
        // Get the canvas element
        const ctx = document.getElementById('attendanceChart').getContext('2d');
        
        // Destroy existing chart if it exists
        if (window.attendanceChartInstance) {
            window.attendanceChartInstance.destroy();
        }
        
        // Check if we have any data
        const totalTickets = Object.values(attendanceData).reduce((sum, value) => sum + value, 0);
        const hasData = totalTickets > 0;
        
        // Calculate attendance rate for display
        const attendanceRate = document.getElementById('attendance-rate');
        if (attendanceRate && totalTickets > 0) {
            const scannedPercentage = Math.round((attendanceData['Attended'] / totalTickets) * 100);
            attendanceRate.textContent = `${scannedPercentage}%`;
        }
        
        // Create a new chart with the data
        window.attendanceChartInstance = new Chart(ctx, {
            type: 'doughnut', // Using doughnut chart for better visualization
            data: {
                labels: Object.keys(attendanceData),
                datasets: [{
                    data: Object.values(attendanceData),
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.7)', // Green for Attended
                        'rgba(255, 99, 132, 0.7)'  // Red for Did Not Attend
                    ],
                    borderColor: [
                        'rgba(75, 192, 192, 1)',
                        'rgba(255, 99, 132, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%', // Makes the doughnut chart have a hole in the middle
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
                                const percentage = totalTickets > 0 ? Math.round((value / totalTickets) * 100) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Attendance Distribution',
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
        
        // Display a message if there's no data
        if (!hasData) {
            const container = document.getElementById('attendance-chart-container');
            
            // Check if the message already exists
            if (!container.querySelector('.no-data-message')) {
                const noDataMessage = document.createElement('div');
                noDataMessage.className = 'no-data-message text-center mt-4 text-gray-500';
                noDataMessage.textContent = 'No ticket data available for this event.';
                container.appendChild(noDataMessage);
            }
        }
    } catch (e) {
        console.error('Error in renderAttendanceChart:', e);
    }
}

// Try to initialize immediately
initializeAttendanceAnalytics();

// Also initialize on DOMContentLoaded for safety
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired');
    initializeAttendanceAnalytics();
});

// Also initialize on window.onload for maximum compatibility
window.onload = function() {
    console.log('window.onload event fired');
    initializeAttendanceAnalytics();
};
