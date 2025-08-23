document.addEventListener('DOMContentLoaded', function() {
    // make rows clickable
    const rows = document.querySelectorAll('.clickable-row');
    if (rows.length > 0) {
        rows.forEach(row => {
            row.addEventListener('click', (e) => {
                // only go to link if you didnt click on another link
                if (e.target.tagName !== 'A') {
                    window.location.href = row.dataset.href;
                }
            });
        });
    }

    // Code for handling user deletion with Optimistic UI
    const usersTable = document.getElementById('users-table');
    if (usersTable) {
        usersTable.addEventListener('click', function(e) {
            if (e.target && e.target.classList.contains('js-delete-user')) {
                const button = e.target;
                const deleteUrl = button.dataset.deleteUrl;
                const row = button.closest('tr');
                const parentTbody = row.parentElement;
                const originalIndex = Array.from(parentTbody.children).indexOf(row);

                if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
                    // Optimistically remove from the UI
                    row.remove();

                    fetch(deleteUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(err => Promise.reject(err));
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (!data.success) {
                            throw new Error(data.message);
                        }
                        // On success, do nothing. The row is already gone.
                        console.log(data.message);
                    })
                    .catch(error => {
                        // This block handles network errors and server errors.
                        console.error('Deletion failed:', error);
                        // Put the row back in its original position
                        parentTbody.insertBefore(row, parentTbody.children[originalIndex]);
                        // Show an alert with the error message.
                        alert(`Could not delete user: ${error.message || 'A network error occurred.'}`);
                    });
                }
            }
        });
    }

    // code for the score graph
    const chartContainer = document.getElementById('scoreChart')?.parentElement;
    const ctx = document.getElementById('scoreChart');

    if (chartContainer && ctx) {
        try {
            fetch('/api/graph_data')
                .then(response => response.json())
                .then(data => {
                    // if no data, hide the chart
                    if (!data || !data.labels || data.labels.length === 0) {
                        chartContainer.style.display = 'none';
                        return;
                    }

                    const myChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.labels,
                            datasets: data.datasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false, // so it fits on mobile
                            plugins: {
                                legend: {
                                    position: 'top',
                                    align: 'center',
                                    labels: {
                                        color: '#e0e0e0',
                                        font: { size: 10 },
                                        boxWidth: 20,
                                        padding: 20
                                    }
                                },
                                tooltip: {
                                    callbacks: {
                                        title: function(context) {
                                            return context[0].label;
                                        },
                                        label: function(context) {
                                            let label = context.dataset.label || '';
                                            if (label) {
                                                label += ': ';
                                            }
                                            label += context.raw + ' points';
                                            return label;
                                        }
                                    }
                                },
                                title: {
                                    display: true,
                                    text: 'Score Progression by Event',
                                    color: '#e0e0e0',
                                    font: { size: 16 }
                                }
                            },
                            scales: {
                                x: {
                                    title: { display: true, text: 'Events', color: '#e0e0e0' },
                                    ticks: { color: '#e0e0e0' },
                                    grid: { color: '#444' }
                                },
                                y: {
                                    title: { display: true, text: 'Total Score', color: '#e0e0e0' },
                                    ticks: { color: '#e0e0e0' },
                                    grid: { color: '#444' },
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                })
                .catch(error => {
                    // if something goes wrong, hide the chart
                    console.error('Error getting graph data:', error);
                    chartContainer.style.display = 'none';
                });
        } catch (error) {
            console.error('Error making chart:', error);
            chartContainer.style.display = 'none';
        }
    }

    // Code for handling school deletion with Optimistic UI
    const schoolsTable = document.getElementById('schools-table');
    if (schoolsTable) {
        schoolsTable.addEventListener('click', function(e) {
            if (e.target && e.target.classList.contains('js-delete-school')) {
                const button = e.target;
                const deleteUrl = button.dataset.deleteUrl;
                const row = button.closest('tr');
                const parentTbody = row.parentElement;
                const originalIndex = Array.from(parentTbody.children).indexOf(row);

                if (confirm('Are you sure you want to delete this school? This action cannot be undone.')) {
                    // Optimistically remove from the UI
                    row.remove();

                    fetch(deleteUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    })
                    .then(response => {
                        if (!response.ok) {
                            return response.json().then(err => Promise.reject(err));
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (!data.success) {
                            throw new Error(data.message);
                        }
                        // On success, do nothing. The row is already gone.
                        console.log(data.message);
                    })
                    .catch(error => {
                        // This block handles network errors and server errors.
                        console.error('Deletion failed:', error);
                        // Put the row back in its original position
                        parentTbody.insertBefore(row, parentTbody.children[originalIndex]);
                        // Show an alert with the error message.
                        alert(`Could not delete school: ${error.message || 'A network error occurred.'}`);
                    });
                }
            }
        });
    }

    // Celebration pop-up logic
    const leaderboardTable = document.getElementById('leaderboard-table');
    if (leaderboardTable) {
        leaderboardTable.addEventListener('click', function(e) {
            const triggerRow = e.target.closest('.js-celebration-trigger');
            if (!triggerRow) return;

            // Prevent default navigation to happen instantly
            e.preventDefault();

            const rank = triggerRow.dataset.rank;
            const destinationUrl = triggerRow.dataset.href;

            const popup = document.getElementById('celebration-popup');
            const rankDisplay = document.getElementById('celebration-rank');

            if (!popup || !rankDisplay) return;

            // Set the rank text and color class
            rankDisplay.textContent = `#${rank}`;
            rankDisplay.className = ''; // Clear previous classes
            rankDisplay.classList.add(`rank-${rank}`);

            // Create confetti and show the pop-up
            createConfetti();
            popup.style.display = 'flex';
            setTimeout(() => {
                popup.style.opacity = '1';
                popup.style.pointerEvents = 'auto';
            }, 10); // Small delay to allow transition to work

            // Wait for the celebration and then redirect
            setTimeout(() => {
                window.location.href = destinationUrl;
            }, 4000); // 5-second celebration
        });
    }

    // Ensure celebration popup is hidden on page back/forward navigation
    window.addEventListener('pageshow', function(event) {
        const popup = document.getElementById('celebration-popup');
        if (popup && event.persisted) {
            popup.style.display = 'none';
            popup.style.opacity = '0';
            popup.style.pointerEvents = 'none';
        }
    });
});
