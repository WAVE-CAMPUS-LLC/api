document.addEventListener("DOMContentLoaded", function () {
    const loginTrendsURL = document.getElementById("userLoginURL").value;

    function fetchTrendData(trend, additionalParams = "") {
        fetch(`${loginTrendsURL}?trend=${trend}${additionalParams}`)
            .then((response) => response.json())
            .then((data) => {
                const ctx = document.getElementById("userLoginsChartOverall").getContext("2d");

                if (window.userLoginsChartOverall && typeof window.userLoginsChartOverall.destroy === "function") {
                    window.userLoginsChartOverall.destroy();
                }

                let chartData, chartType, chartTitle;

                switch (trend) {
                    case "general":
                        chartType = "polarArea";
                        chartData = {
                            labels: ["Total Logins", "Unique Users", "Active Sessions"],
                            datasets: [{
                                data: [
                                    data.total_logins,
                                    data.unique_users,
                                    data.active_sessions,
                                ],
                                backgroundColor: generateColors(3),
                            }],
                        };
                        chartTitle = "General Login Insights";
                        break;

                    case "user_activity":
                        chartType = "bar";
                        chartData = {
                            labels: data.map((item) => item.user__username),
                            datasets: [{
                                label: "Logins",
                                data: data.map((item) => item.count),
                                backgroundColor: generateColors(data.length),
                            }],
                        };
                        chartTitle = "User Activity";
                        break;

                    case "time_trends":
                        chartType = "line";
                        chartData = {
                            labels: data.map((item) => item.time_period),
                            datasets: [{
                                label: "Logins",
                                data: data.map((item) => item.count),
                                borderColor: "rgba(75, 192, 192, 1)",
                                fill: false,
                            }],
                        };
                        chartTitle = "Login Trends Over Time";
                        break;

                    case "ip_insights":
                        chartType = "bar";
                        chartData = {
                            labels: data.map((item) => item.ip_address),
                            datasets: [{
                                label: "Logins",
                                data: data.map((item) => item.count),
                                backgroundColor: generateColors(data.length),
                            }],
                        };
                        chartTitle = "Top IP Addresses";
                        break;

                    case "security":
                        chartType = "bar";

                        // Initialize the chartData object
                        chartData = {
                            labels: ["Failed Logins", "Active Null Role Sessions"],
                            datasets: [{
                                data: [data.failed_login_attempts, data.active_sessions_with_no_groups],
                                backgroundColor: generateColors(2),
                            }],
                        };

                        // Create data for failed login attempts by group
                        if (data.failed_login_attempts_by_group && data.failed_login_attempts_by_group.length > 0) {
                            data.failed_login_attempts_by_group.forEach(group => {
                                chartData.labels.push(`${group.user__groups__name} - Failed Logins`);
                                chartData.datasets[0].data.push(group.failed_attempts);
                            });
                        }

                        // Create data for active sessions by group
                        if (data.active_sessions_by_group && data.active_sessions_by_group.length > 0) {
                            data.active_sessions_by_group.forEach(group => {
                                chartData.labels.push(`${group.user__groups__name} - Active Sessions`);
                                chartData.datasets[0].data.push(group.active_sessions);
                            });
                        }

                        chartTitle = "Security Insights";
                        break;

                    case "retention":
                        chartType = "bar";
                        chartData = {
                            labels: ["Last 7 Days", "Last 30 Days"],
                            datasets: [{
                                data: [data.last_7_days, data.last_30_days],
                                backgroundColor: generateColors(2),
                            }],
                        };
                        chartTitle = "Retention Insights";
                        break;

                    default:
                        console.error("Unknown trend type");
                        return;
                }

                window.userLoginsChartOverall = new Chart(ctx, {
                    type: chartType,
                    data: chartData,
                    options: {
                        responsive: true,
                        plugins: {
                            legend: { display: true },
                            title: { display: true, text: chartTitle },
                        },
                    },
                });
            })
            .catch((error) => console.error("Error:", error));
    }

    const trendSelect = document.getElementById("trendSelect");
    trendSelect.addEventListener("change", function () {
        const selectedTrend = trendSelect.value;
        fetchTrendData(selectedTrend);
    });

    function generateColors(count) {
        return Array.from({ length: count }, () =>
            `rgba(${Math.random() * 255}, ${Math.random() * 255}, ${Math.random() * 255}, 0.6)`
        );
    }

    fetchTrendData(trendSelect.value); // Default fetch
});
