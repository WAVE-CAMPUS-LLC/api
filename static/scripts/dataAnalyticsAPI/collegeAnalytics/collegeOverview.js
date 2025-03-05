document.addEventListener('DOMContentLoaded', () => {
    const dataTypeSelect = document.getElementById('dataTypeSelect');
    const chartContainer = document.getElementById('dataChart').getContext('2d');
    let chartInstance;

    const fetchData = (type) => {
        const url = document.getElementById('collegeOverviewURL').value;

        fetch(`${url}?type=${type}`)
            .then((response) => response.json())
            .then((data) => {

                const labels = [];
                const counts = [];

                if (type === 'state') {
                    data.colleges_by_state.forEach((state) => {
                        labels.push(state.state); // Correctly access "state"
                        counts.push(state.college_count); // Correctly access "college_count"
                    });
                } else if (type === 'city') {
                    data.colleges_by_city.forEach((city) => {
                        labels.push(city.city); // Correctly access "city"
                        counts.push(city.college_count); // Correctly access "college_count"
                    });
                }

                if (chartInstance) {
                    chartInstance.destroy();
                }

                chartInstance = new Chart(chartContainer, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: type === 'state' ? 'Colleges by State' : 'Colleges by City',
                            data: counts, // Use the counts array
                            backgroundColor: 'rgba(75, 192, 192, 0.5)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            x: {
                                title: {
                                    display: true,
                                    text: type === 'state' ? 'States' : 'Cities'
                                }
                            },
                            y: {
                                title: {
                                    display: true,
                                    text: 'Number of Colleges'
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
            .catch((error) => console.error('Error fetching data:', error));
    };

    fetchData('state');

    dataTypeSelect.addEventListener('change', () => {
        const selectedType = dataTypeSelect.value;
        fetchData(selectedType);
    });
});
