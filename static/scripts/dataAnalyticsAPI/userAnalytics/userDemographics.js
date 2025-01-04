document.addEventListener('DOMContentLoaded', function () {
    const userDemographicsURL = document.getElementById('userDemographicsURL').value;

    function fetchData(groupBy) {
        fetch(`${userDemographicsURL}?group_by=${groupBy}`)
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('userDemographicsChart').getContext('2d');

                // Check if the chart instance exists before attempting to destroy it
                if (window.userDemographicsChart && typeof window.userDemographicsChart.destroy === 'function') {
                    window.userDemographicsChart.destroy();
                }

                // Create a new chart
                window.userDemographicsChart = new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: `User Demographics by ${capitalize(groupBy)}`,
                            data: data.counts,
                            backgroundColor: generateColors(data.labels.length),
                            borderWidth: 1,
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                display: true,
                                labels: {
                                    font: {
                                        size: 14
                                    },
                                }
                            },
                            title: {
                                display: true,
                                text: `User Demographics by ${capitalize(groupBy)}`,
                                font: {
                                    size: 18
                                }
                            }
                        },
                    }
                });
            })
            .catch(error => console.error('Error:', error));
    }

    // Add event listeners for group selection (dropdown or buttons)
    const groupBySelect = document.getElementById('groupBySelect');
    groupBySelect.addEventListener('change', function () {
        const selectedGroup = groupBySelect.value; // Get the selected demographic group (e.g., home_state, gender)
        fetchData(selectedGroup); // Fetch data for the selected group
    });

    // Helper function to generate dynamic colors for the chart
    function generateColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const r = Math.floor(Math.random() * 256);
            const g = Math.floor(Math.random() * 256);
            const b = Math.floor(Math.random() * 256);
            colors.push(`rgba(${r}, ${g}, ${b}, 0.6)`);
        }
        return colors;
    }

    // Helper function to capitalize the first letter of a string
    function capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    // Fetch data for the default group on page load
    fetchData(groupBySelect.value);
});
