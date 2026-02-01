// Dashboard JavaScript - Fetches and displays portfolio health data

let severityChart, typeChart;

// Fetch and display all dashboard data
async function loadDashboard() {
    try {
        // Load summary stats
        const summary = await fetch('/api/summary').then(r => r.json());
        updateSummaryCards(summary);
        updateCharts(summary);

        // Load open issues
        const openIssues = await fetch('/api/issues/open').then(r => r.json());
        displayOpenIssues(openIssues.issues);

        // Load resolved issues
        const resolvedIssues = await fetch('/api/issues/resolved').then(r => r.json());
        displayResolvedIssues(resolvedIssues.issues);

    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load dashboard data. Please refresh the page.');
    }
}

// Update summary cards
function updateSummaryCards(summary) {
    document.getElementById('total-issues').textContent = summary.total_issues;
    document.getElementById('open-issues').textContent = summary.open_issues;
    document.getElementById('resolved-issues').textContent = summary.resolved_issues;
    document.getElementById('total-threads').textContent = summary.total_threads;

    // Projects
    const projectsText = `${summary.total_projects} project${summary.total_projects !== 1 ? 's' : ''}`;
    document.getElementById('total-projects').textContent = projectsText;

    // Resolution rate
    const resolutionRate = summary.total_issues > 0
        ? ((summary.resolved_issues / summary.total_issues) * 100).toFixed(0)
        : 0;
    document.getElementById('resolution-rate').textContent = `${resolutionRate}% resolution rate`;

    // Emails processed
    if (summary.latest_run) {
        document.getElementById('emails-processed').textContent =
            `${summary.latest_run.total_emails} emails analyzed`;
    }
}

// Update charts
function updateCharts(summary) {
    // Severity Chart
    const severityCtx = document.getElementById('severityChart').getContext('2d');

    if (severityChart) {
        severityChart.destroy();
    }

    severityChart = new Chart(severityCtx, {
        type: 'doughnut',
        data: {
            labels: ['High (7-10)', 'Medium (4-6)', 'Low (1-3)'],
            datasets: [{
                data: [
                    summary.severity_breakdown.high,
                    summary.severity_breakdown.medium,
                    summary.severity_breakdown.low
                ],
                backgroundColor: [
                    '#ff6361', // coral red
                    '#ffa600', // orange
                    '#58508d'  // purple
                ],
                borderWidth: 3,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        }
                    }
                }
            }
        }
    });

    // Type Chart
    const typeCtx = document.getElementById('typeChart').getContext('2d');

    if (typeChart) {
        typeChart.destroy();
    }

    typeChart = new Chart(typeCtx, {
        type: 'bar',
        data: {
            labels: ['Unresolved Actions', 'Emerging Risks'],
            datasets: [{
                label: 'Issues',
                data: [
                    summary.type_breakdown.unresolved_actions,
                    summary.type_breakdown.emerging_risks
                ],
                backgroundColor: [
                    '#003f5c', // dark teal
                    '#bc5090'  // pink/magenta
                ],
                borderWidth: 0,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1,
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                },
                x: {
                    ticks: {
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Display open issues in table
function displayOpenIssues(issues) {
    const tbody = document.getElementById('open-issues-table');
    tbody.innerHTML = '';

    if (issues.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-6 py-8 text-center text-gray-500">
                    <div class="flex flex-col items-center">
                        <svg class="w-12 h-12 text-green-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <p class="text-lg font-medium">No open issues!</p>
                        <p class="text-sm">Portfolio health is excellent.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    issues.forEach(issue => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50 cursor-pointer';
        row.onclick = () => showIssueDetail(issue);

        // Priority badge based on priority_score (not just severity)
        // High priority: score >= 130, Medium: 120-129, Low: < 120
        let priorityBadge;
        if (issue.priority_score >= 130) {
            priorityBadge = `<span class="px-3 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">High</span>`;
        } else if (issue.priority_score >= 120) {
            priorityBadge = `<span class="px-3 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">Medium</span>`;
        } else {
            priorityBadge = `<span class="px-3 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Low</span>`;
        }

        // Type badge
        const typeBadge = issue.issue_type === 'UNRESOLVED_ACTION'
            ? '<span class="px-2 py-1 text-xs font-medium rounded bg-blue-100 text-blue-800">Action</span>'
            : '<span class="px-2 py-1 text-xs font-medium rounded bg-amber-100 text-amber-800">Risk</span>';

        row.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap">${priorityBadge}</td>
            <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900">${escapeHtml(issue.title)}</div>
                <div class="text-xs text-gray-500 mt-1">${escapeHtml(issue.evidence_quote.substring(0, 100))}...</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">${typeBadge}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${escapeHtml(issue.project_name)}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">${escapeHtml(issue.contact_person)}</div>
                <div class="text-xs text-gray-500">${escapeHtml(issue.contact_person_email)}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 py-1 text-xs rounded-full ${issue.days_outstanding > 14 ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}">
                    ${issue.days_outstanding}d
                </span>
            </td>
        `;

        tbody.appendChild(row);
    });
}

// Display resolved issues
function displayResolvedIssues(issues) {
    const tbody = document.getElementById('resolved-issues-table');
    tbody.innerHTML = '';

    if (issues.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-4 text-center text-sm text-gray-500">
                    No resolved issues in this period.
                </td>
            </tr>
        `;
        return;
    }

    issues.forEach(issue => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50';

        row.innerHTML = `
            <td class="px-6 py-4">
                <div class="text-sm font-medium text-gray-900">${escapeHtml(issue.title)}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${escapeHtml(issue.project_name)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">${issue.days_outstanding} days</td>
            <td class="px-6 py-4 text-sm text-gray-600">${escapeHtml(issue.resolution_evidence || 'N/A')}</td>
        `;

        tbody.appendChild(row);
    });
}

// Show issue detail modal
function showIssueDetail(issue) {
    // Set title
    document.getElementById('modal-title').textContent = issue.title;
    
    // Set badges - based on priority_score
    let priorityBadge;
    if (issue.priority_score >= 130) {
        priorityBadge = '<span class="px-3 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">High Priority</span>';
    } else if (issue.priority_score >= 120) {
        priorityBadge = '<span class="px-3 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">Medium Priority</span>';
    } else {
        priorityBadge = '<span class="px-3 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Low Priority</span>';
    }
    
    const typeBadge = issue.issue_type === 'UNRESOLVED_ACTION'
        ? '<span class="px-3 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">Unresolved Action</span>'
        : '<span class="px-3 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">Emerging Risk</span>';
    
    document.getElementById('modal-badges').innerHTML = priorityBadge + typeBadge;
    
    // Set content
    document.getElementById('modal-description').textContent = issue.description;
    document.getElementById('modal-evidence').textContent = issue.evidence_quote;
    document.getElementById('modal-project').textContent = issue.project_name;
    document.getElementById('modal-contact-name').textContent = issue.contact_person;
    document.getElementById('modal-contact-email').textContent = issue.contact_person_email;
    document.getElementById('modal-author').textContent = issue.email_author;
    document.getElementById('modal-date').textContent = new Date(issue.email_date).toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    document.getElementById('modal-subject').textContent = issue.subject;
    
    // Set metrics
    document.getElementById('modal-severity').textContent = `${issue.severity}/10`;
    document.getElementById('modal-confidence').textContent = `${(issue.confidence * 100).toFixed(0)}%`;
    document.getElementById('modal-days').textContent = issue.days_outstanding;
    
    // Show modal
    document.getElementById('issueModal').classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Close modal
function closeModal() {
    document.getElementById('issueModal').classList.remove('active');
    document.body.style.overflow = 'auto';
}

// Close modal on outside click
document.addEventListener('click', function(event) {
    const modal = document.getElementById('issueModal');
    if (event.target === modal) {
        closeModal();
    }
});

// Close modal on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeModal();
    }
});

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show error message
function showError(message) {
    const main = document.querySelector('main');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'bg-red-50 border border-red-200 rounded-lg p-4 mb-6';
    errorDiv.innerHTML = `
        <div class="flex">
            <svg class="w-5 h-5 text-red-400 mr-3" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
            </svg>
            <p class="text-sm text-red-800">${message}</p>
        </div>
    `;
    main.prepend(errorDiv);
}

// Auto-refresh every 30 seconds
setInterval(loadDashboard, 30000);

// Initial load
loadDashboard();
