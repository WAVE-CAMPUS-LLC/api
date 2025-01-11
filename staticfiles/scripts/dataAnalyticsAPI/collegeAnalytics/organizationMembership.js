document.addEventListener('DOMContentLoaded', () => {
    const metricsAPI = document.getElementById('organizationMembershipURL').value;

    const dataTypeSelect = document.getElementById("dataTypeSelect");

    // Canvas elements
    const churnRateChartCanvas = document.getElementById("churnRateChart");
    const privacyComparisonChartCanvas = document.getElementById("privacyComparisonChart");
    const collegeComparisonChartCanvas = document.getElementById("collegeComparisonChart");
    const topOrganizationsChartCanvas = document.getElementById("topOrganizationsChart");
    const activeCollegesChartCanvas = document.getElementById("activeCollegesChart");
    const membershipTrendsChartCanvas = document.getElementById("membershipTrendsChart");

    // Chart instances
    let churnRateChart, privacyComparisonChart, collegeComparisonChart, topOrganizationsChart, activeCollegesChart, membershipTrendsChart;

    // Fetch data from the API
    async function fetchMetrics() {
        try {
            const response = await fetch(metricsAPI);
            const data = await response.json();

            // Create charts
            churnRateChart = createChurnRateChart(data.churn_rate);
            privacyComparisonChart = createPrivacyComparisonChart(data.privacy_comparison);
            collegeComparisonChart = createCollegeComparisonChart(data.college_comparison);
            topOrganizationsChart = createTopOrganizationsChart(data.top_organizations);
            activeCollegesChart = createActiveCollegesChart(data.active_colleges);
            membershipTrendsChart = createMembershipTrendsChart(data.membership_trends);

            updateVisibleCharts(dataTypeSelect.value); // Initial display based on default selected value
        } catch (error) {
            console.error("Error fetching metrics:", error);
        }
    }

    // Event listener for data type selector
    dataTypeSelect.addEventListener("change", (event) => {
        const selectedType = event.target.value;
        updateVisibleCharts(selectedType);
    });

    // Update visible charts based on selection
    function updateVisibleCharts(selectedType) {
        // Hide all charts by setting display to none
        const allCharts = [
            churnRateChartCanvas,
            privacyComparisonChartCanvas,
            collegeComparisonChartCanvas,
            topOrganizationsChartCanvas,
            activeCollegesChartCanvas,
            membershipTrendsChartCanvas,
        ];

        allCharts.forEach(chart => {
            chart.style.display = 'none';  // Hide all charts by setting display to 'none'
        });

        // Show the relevant charts based on the selected option
        switch (selectedType) {
            case "churnRate":
                churnRateChartCanvas.style.display = 'block';
                break;
            case "privacy":
                privacyComparisonChartCanvas.style.display = 'block';
                break;
            case "college":
                collegeComparisonChartCanvas.style.display = 'block';
                break;
            case "topOrganizations":
                topOrganizationsChartCanvas.style.display = 'block';
                break;
            case "membershipTrends":
                membershipTrendsChartCanvas.style.display = 'block';
                break;
            case "activeColleges":
                activeCollegesChartCanvas.style.display = 'block';
                break;
            default:
                break;
        }
    }

    // Create charts
    function createChurnRateChart(churnRate) {
        return new Chart(churnRateChartCanvas, {
            type: "doughnut",
            data: {
                labels: ["Churn Rate", "Retention Rate"],
                datasets: [{
                    label: "Churn Rate",
                    data: [churnRate, 100 - churnRate],
                    backgroundColor: ["#FF7043", "#66BB6A"],
                }],
            },
            options: { responsive: true },
        });
    }

    function createPrivacyComparisonChart(data) {
        return new Chart(privacyComparisonChartCanvas, {
            type: "bar",
            data: {
                labels: data.map(item => item.privacy),
                datasets: [{
                    label: "Comparing Organizations by Privacy",
                    data: data.map(item => item.count),
                    backgroundColor: "#42A5F5",
                }],
            },
            options: { responsive: true },
        });
    }

    function createCollegeComparisonChart(data) {
        return new Chart(collegeComparisonChartCanvas, {
            type: "bar",
            data: {
                labels: data.map(item => item.name),
                datasets: [{
                    label: "College Comparison",
                    data: data.map(item => item.count),
                    backgroundColor: "#66BB6A",
                }],
            },
            options: { responsive: true },
        });
    }

    function createTopOrganizationsChart(data) {
        return new Chart(topOrganizationsChartCanvas, {
            type: "bar",
            data: {
                labels: data.map(item => item.name),
                datasets: [{
                    label: "Top Organizations",
                    data: data.map(item => item.member_count),
                    backgroundColor: "#FFA726",
                }],
            },
            options: { responsive: true },
        });
    }

    function createActiveCollegesChart(data) {
        return new Chart(activeCollegesChartCanvas, {
            type: "bar",
            data: {
                labels: data.map(item => item.name),
                datasets: [{
                    label: "Most Active Colleges",
                    data: data.map(item => item.total_memberships),
                    backgroundColor: "#AB47BC",
                }],
            },
            options: { responsive: true },
        });
    }

    function createMembershipTrendsChart(data) {
        return new Chart(membershipTrendsChartCanvas, {
            type: "bar",
            data: {
                labels: data.map(item => item.month),
                datasets: [{
                    label: "Membership Trends",
                    data: data.map(item => item.count),
                    borderColor: "#42A5F5",
                    backgroundColor: "rgba(66, 165, 245, 0.2)",
                    fill: true,
                }],
            },
            options: { responsive: true },
        });
    }

    // Initial data fetch
    fetchMetrics();
});
