document.addEventListener('DOMContentLoaded', function () {
    const userSignupsURL = document.getElementById('userSignupsURL').value;

    function fetchData(period) {
        fetch(`${userSignupsURL}?period=${period}`)
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('userSignupsChartOverall').getContext('2d');

                // Destroy existing chart if it exists
                if (window.chartInstance) {
                    window.chartInstance.destroy();
                }

                // Create a new chart with updated data
                window.chartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.labels, // These labels will be the months or weeks, depending on the period
                        datasets: [{
                            label: `${period.charAt(0).toUpperCase() + period.slice(1)} Signups`,
                            data: data.counts, // The total signups for each period (e.g., monthly, weekly, daily)
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
                                    text: 'Sign Up Count'
                                },
                                beginAtZero: true
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
                        },
                    }
                });
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    // Fetch daily data by default
    fetchData('daily');

    // Add event listeners for period selection (you can use a dropdown or buttons)
    const periodSelect = document.getElementById('periodSelect');
    periodSelect.addEventListener('change', function () {
        const selectedPeriod = periodSelect.value;  // Get selected period (daily, weekly, monthly)
        fetchData(selectedPeriod);  // Fetch data for the selected period
    });
});
