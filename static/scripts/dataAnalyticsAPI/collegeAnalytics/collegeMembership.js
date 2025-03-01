document.addEventListener('DOMContentLoaded', () => {
    const chartContainer = document.getElementById('membershipChart').getContext('2d');
    let chartInstance;
    const collegeMembershipURL = document.getElementById('collegeMembershipURL').value;


    // Fetch and render data
    const fetchMembershipData = () => {

        fetch(collegeMembershipURL)
            .then(response => response.json())
            .then(data => {

                const labels = [];
                const counts = [];

                data.members_by_college.forEach(college => {
                    labels.push(college.college__name);
                    counts.push(college.member_count);
                });

                // Destroy previous chart if exists
                if (chartInstance) {
                    chartInstance.destroy();
                }

                // Render new chart
                chartInstance = new Chart(chartContainer, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Members by College',
                            data: counts,
                            backgroundColor: 'rgba(153, 102, 255, 0.5)',
                            borderColor: 'rgba(153, 102, 255, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: 'Colleges'
                                }
                            },
                            y: {
                                title: {
                                    display: true,
                                    text: 'Number of Members'
                                },
                                beginAtZero: true
                            }
                        },
                        plugins: {
                            legend: {
                                display: true,
                                labels: {
                                    color: '#000',
                                    font: {
                                        size: 16
                                    },
                                }
                            },
                        },
                    }
                });
            })
            .catch(error => console.error('Error fetching membership data:', error));
    };

    // Load membership data initially
    fetchMembershipData();
});
