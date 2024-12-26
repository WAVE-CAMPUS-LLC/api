document.addEventListener('DOMContentLoaded', () => {
    const chartContainer = document.getElementById('organizationChart').getContext('2d');
    let chartInstance;
    const url = document.getElementById('organizationOverviewURL').value;

    const typeSelect = document.getElementById('dataTypeSelect'); // Dropdown to select view type

    // Fetch and render data
    const fetchOrganizationData = () => {
        fetch(url)
            .then(response => response.json())
            .then(data => {
                console.log('Organization data:', data);

                if (typeSelect.value === 'college') {
                    renderChartByCollege(data.organizations_by_college_privacy);
                } else if (typeSelect.value === 'privacy') {
                    renderChartByPrivacy(data.organizations_by_privacy);
                }
            })
            .catch(error => console.error('Error fetching organization data:', error));
    };

    // Render chart by college
    const renderChartByCollege = (collegeData) => {
        const colleges = [];
        const publicCounts = [];
        const privateCounts = [];

        // Group data for the chart
        collegeData.forEach(org => {
            if (!colleges.includes(org.college__name)) {
                colleges.push(org.college__name);
                publicCounts.push(0); // Initialize with 0
                privateCounts.push(0); // Initialize with 0
            }

            const index = colleges.indexOf(org.college__name);
            if (org.privacy === "Public") {
                publicCounts[index] = org.org_count;
            } else if (org.privacy === "Private") {
                privateCounts[index] = org.org_count;
            }
        });

        renderChart({
            labels: colleges,
            datasets: [
                {
                    label: 'Public Organizations',
                    data: publicCounts,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                },
                {
                    label: 'Private Organizations',
                    data: privateCounts,
                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1
                }
            ]
        }, 'Colleges', 'Number of Organizations');
    };

    // Render chart by privacy
    const renderChartByPrivacy = (privacyData) => {
        const privacies = [];
        const orgCounts = [];

        // Group data for the chart
        privacyData.forEach(group => {
            privacies.push(group.privacy);
            orgCounts.push(group.org_count);
        });

        renderChart({
            labels: privacies,
            datasets: [
                {
                    label: 'Organizations',
                    data: orgCounts,
                    backgroundColor: ['rgba(54, 162, 235, 0.5)', 'rgba(255, 99, 132, 0.5)'],
                    borderColor: ['rgba(54, 162, 235, 1)', 'rgba(255, 99, 132, 1)'],
                    borderWidth: 1
                }
            ]
        }, 'Privacy Types', 'Number of Organizations');
    };

    // Render chart function
    const renderChart = (data, xAxisTitle, yAxisTitle) => {
        // Destroy previous chart if exists
        if (chartInstance) {
            chartInstance.destroy();
        }

        // Render new chart
        chartInstance = new Chart(chartContainer, {
            type: 'bar',
            data: data,
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: xAxisTitle
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: yAxisTitle
                        },
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        labels: {
                            font: {
                                size: 14
                            }
                        }
                    }
                }
            }
        });
    };

    // Load organization data initially
    fetchOrganizationData();

    // Update chart when type is changed
    typeSelect.addEventListener('change', fetchOrganizationData);
});
