document.addEventListener("DOMContentLoaded", () => {

    // --- Mock Database (Simulation) ---
    const db = {
        clients: [
            { id: 1, studentId: '23203A0024', device: 'Student Laptop', ip: '192.168.1.10', data: 4.2, activity: 'Studying (Canvas)', blocked: false },
            { id: 2, studentId: '23203A0026', device: 'Smart TV', ip: '192.168.1.12', data: 15.8, activity: 'Streaming (Netflix)', blocked: true }
        ],
        blockedSites: [
            "specific-cheating-site.com",
            "unblock-proxy.net"
        ],
        siteCategories: {
            "Gaming": {
                active: true,
                sites: ["steampowered.com", "twitch.tv", "roblox.com", "discord.gg", "epicgames.com", "ea.com", "playvalorant.com", "minecraft.net", "battle.net", "ubisoft.com"]
            },
            "Social Media": {
                active: false,
                sites: ["tiktok.com", "instagram.com", "facebook.com", "twitter.com", "reddit.com", "snapchat.com", "pinterest.com"]
            },
            "Streaming": {
                active: false,
                sites: ["netflix.com", "hulu.com", "disneyplus.com", "hbomax.com", "primevideo.com", "spotify.com", "peacocktv.com"]
            },
            "File Sharing": {
                active: true,
                sites: ["thepiratebay.org", "1337x.to", "megaupload.com", "wetransfer.com", "mediafire.com", "rarbg.to"]
            },
            "Proxy/VPN": {
                active: true,
                sites: ["nordvpn.com", "expressvpn.com", "hidemyass.com", "proxysite.com", "cyberghostvpn.com", "surfshark.com", "privateinternetaccess.com", "protonvpn.me", "tunnelbear.com"]
            },
            // "Adult Content": { 
            //     active: true, 
            //     sites: ["placeholder-adult-site.com", "generic-tube-site.net", "example-xxx-video.com"] 
            // }
        },
        bandwidthLimits: {
            4: "low",
            6: "low",
            5: 15
        },
        logs: [
            { time: '11:25:01 AM', level: 'warn', user: '23203A0025', action: 'High bandwidth detected (25.4 GB)' },
            { time: '11:24:15 AM', level: 'error', user: 'Unknown (192.168.1.45)', action: 'Failed login attempt (3)' },
            { time: '11:23:00 AM', level: 'info', user: 'ADMIN', action: 'Blocked user S1026' },
            { time: '11:20:11 AM', level: 'info', user: '23203A0024', action: 'Connected to network (Student Laptop)' }
        ],
        guestNetworkEnabled: true,
        totalData: 28.7,
        threatsBlocked: 0,
    };

    // --- Element Selections (Static) ---
    const menuItems = document.querySelectorAll(".menu-item");
    const pageTitle = document.getElementById("page-title");
    const menuToggle = document.getElementById("menu-toggle");
    const sidebar = document.getElementById("sidebar");
    const contentArea = document.getElementById("content-area");
    const profileMenuToggle = document.getElementById("profile-menu-toggle");
    const profileDropdown = document.getElementById("profile-dropdown");
    const notificationBell = document.getElementById("notification-bell");
    const notificationBadge = document.getElementById("notification-badge");
    const notificationTray = document.getElementById("notification-tray");
    const notificationList = document.getElementById("notification-list");
    const modalOverlay = document.getElementById("edit-modal-overlay");
    const editClientForm = document.getElementById("edit-client-form");

    // --- App-Scoped Chart Variables ---
    let myTrafficChart = null;
    let trafficInterval;
    const customBandwidthTimers = {};
    const DEFAULT_BANDWIDTH_PRESETS = {
        low: 2,
        medium: 5,
        high: 20,
    };
    let bandwidthPresets = { ...DEFAULT_BANDWIDTH_PRESETS };

    function getPresetMbps(tier) {
        const fallback = DEFAULT_BANDWIDTH_PRESETS[tier] || DEFAULT_BANDWIDTH_PRESETS.medium;
        const parsed = parseInt(bandwidthPresets[tier], 10);
        if (!Number.isFinite(parsed) || parsed < 1) return fallback;
        return parsed;
    }

    function currentTimeLabel() {
        return new Date().toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    function normalizeTrafficData(rawTrafficData) {
        const labels = Array.isArray(rawTrafficData?.labels) ? rawTrafficData.labels.slice() : [];
        const download = Array.isArray(rawTrafficData?.download)
            ? rawTrafficData.download.map(v => Number(v) || 0)
            : [];
        const upload = Array.isArray(rawTrafficData?.upload)
            ? rawTrafficData.upload.map(v => Number(v) || 0)
            : [];

        const points = Math.max(labels.length, download.length, upload.length, 1);

        while (labels.length < points) labels.push(currentTimeLabel());
        while (download.length < points) download.push(0);
        while (upload.length < points) upload.push(0);

        return { labels, download, upload };
    }

    function updateTrafficChart(rawTrafficData) {
        const chart = myTrafficChart || window.myTrafficChart;
        if (!chart) return;

        const traffic = normalizeTrafficData(rawTrafficData);
        chart.data.labels = traffic.labels;
        chart.data.datasets[0].data = traffic.download;
        chart.data.datasets[1].data = traffic.upload;
        chart.update('none');
    }

    // --- Page Loading Logic ---
    async function loadPage(pageName) {
        if (trafficInterval) clearInterval(trafficInterval);
        if (window.myTrafficChart && typeof window.myTrafficChart.destroy === 'function') {
            window.myTrafficChart.destroy();
        }
        myTrafficChart = null;
        window.myTrafficChart = null;

        // Clean up dashboard refresh interval when leaving dashboard
        if (window.dashboardRefreshInterval) {
            clearInterval(window.dashboardRefreshInterval);
            window.dashboardRefreshInterval = null;
        }

        try {
            contentArea.innerHTML = `<div class="loading-spinner"></div>`;
            const response = await fetch(`pages/${pageName}.html`);
            if (!response.ok) throw new Error(`Could not load page: ${response.status}`);
            const html = await response.text();
            contentArea.innerHTML = html;

            if (pageName === 'dashboard') initDashboard();
            else if (pageName === 'clients') initClients();
            else if (pageName === 'web_filtering') initWebFiltering();
            else if (pageName === 'bandwidth') initBandwidth();
            else if (pageName === 'logs') initLogs();
            else if (pageName === 'settings') initSettings();
            else if (pageName === 'ap_status') initApStatus();
            else if (pageName === 'guest_network') initGuestNetwork();
            else if (pageName === 'reporting') initReporting();

        } catch (error) {
            console.error("Fetch error:", error);
            contentArea.innerHTML = `<div class="card"><p>Error: Could not load page content. Make sure you are running this on a local server (e.g., VS Code Live Server).</p></div>`;
        }
    }

    // --- Notification Functions ---

    async function loadNotifications() {
        const token = localStorage.getItem('admin_token');
        if (!token) return;

        try {
            const response = await fetch('/api/admin/notifications', {
                headers: { 'Authorization': 'Bearer ' + token }
            });

            if (!response.ok) {
                console.error('Failed to fetch notifications');
                return;
            }

            const data = await response.json();
            const notifications = data.notifications || [];

            // Update notification list
            if (notificationList) {
                notificationList.innerHTML = '';

                if (notifications.length === 0) {
                    const li = document.createElement('li');
                    li.textContent = 'No new notifications';
                    li.style.color = '#999';
                    notificationList.appendChild(li);
                } else {
                    notifications.forEach(notif => {
                        const li = document.createElement('li');
                        li.className = 'notification-item';

                        // Determine icon and color based on level
                        let icon = 'fa-circle-info';
                        let levelClass = 'notif-info';

                        if (notif.level === 'warn') {
                            icon = 'fa-triangle-exclamation';
                            levelClass = 'notif-warn';
                        } else if (notif.level === 'error') {
                            icon = 'fa-circle-exclamation';
                            levelClass = 'notif-error';
                        }

                        li.innerHTML = `
                            <div class="notif-content ${levelClass}">
                                <i class="fa-solid ${icon}"></i>
                                <div class="notif-text">
                                    <strong>${notif.level.toUpperCase()}: </strong>${notif.message}
                                    <div class="notif-meta">${notif.timestamp}</div>
                                </div>
                            </div>
                        `;

                        notificationList.appendChild(li);
                    });
                }
            }
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    async function updateNotificationBadge() {
        const token = localStorage.getItem('admin_token');
        if (!token) return;

        try {
            const response = await fetch('/api/admin/notifications/count', {
                headers: { 'Authorization': 'Bearer ' + token }
            });

            if (!response.ok) {
                console.error('Failed to fetch notification count');
                return;
            }

            const data = await response.json();
            const count = data.count || 0;

            // Update badge
            if (notificationBadge) {
                if (count > 0) {
                    notificationBadge.textContent = count > 99 ? '99+' : count;
                    notificationBadge.classList.remove('hidden');
                } else {
                    notificationBadge.classList.add('hidden');
                }
            }
        } catch (error) {
            console.error('Error updating notification badge:', error);
        }
    }

    async function markAllNotificationsRead() {
        const token = localStorage.getItem('admin_token');
        if (!token) return;

        try {
            await fetch('/api/admin/notifications/mark-read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({ all: true })
            });

            // Update badge after marking as read
            updateNotificationBadge();
        } catch (error) {
            console.error('Error marking notifications as read:', error);
        }
    }

    // Initialize notifications on load
    loadNotifications();
    updateNotificationBadge();

    // Set up auto-refresh for notifications (every 30 seconds)
    setInterval(() => {
        // Only refresh if notification tray is NOT open (to avoid UI jarring)
        if (!notificationTray.classList.contains('active')) {
            loadNotifications();
        }
        updateNotificationBadge();
    }, 30000);

    // --- Page Initializers (These run after a page is loaded) ---

    function initDashboard() {
        // Clear any existing refresh interval
        if (window.dashboardRefreshInterval) {
            clearInterval(window.dashboardRefreshInterval);
        }

        // Function to load dashboard data
        async function loadDashboardData() {
            const token = localStorage.getItem('admin_token');
            if (!token) {
                console.error('No admin token found');
                return;
            }

            try {
                // Fetch dashboard statistics from API
                const statsResponse = await fetch('/api/admin/dashboard/stats', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });

                if (!statsResponse.ok) {
                    console.error('Failed to fetch dashboard stats');
                    return;
                }

                const stats = await statsResponse.json();

                // Update Active Students count
                const clientCountElement = document.getElementById("client-count");
                if (clientCountElement) {
                    clientCountElement.textContent = stats.active_students || 0;
                }

                // Update Total Data usage
                const dataCountElement = document.getElementById("data-count");
                if (dataCountElement) {
                    dataCountElement.textContent = `${stats.total_data_gb || 0} GB`;
                }

                // Update Threats Blocked count
                const threatCountElement = document.getElementById("threat-count");
                if (threatCountElement) {
                    threatCountElement.textContent = stats.threats_blocked || 0;
                }

                // Update traffic chart with live backend data
                updateTrafficChart(stats.traffic_data);

            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }

            // Load recent event logs
            try {
                const logsResponse = await fetch('/api/admin/logs', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });

                if (logsResponse.ok) {
                    const logsData = await logsResponse.json();
                    const logBody = document.getElementById("event-log-body");

                    if (logBody && logsData.logs) {
                        logBody.innerHTML = "";
                        logsData.logs.slice(0, 5).forEach(log => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `<td>${log.time}</td><td><span class="log-level-${log.level}">${log.level.toUpperCase()}</span></td><td>${log.user}</td><td>${log.action}</td>`;
                            logBody.appendChild(tr);
                        });
                    }
                }
            } catch (error) {
                console.error('Error loading event logs:', error);
            }
        }

        // Initialize the traffic chart
        const canvas = document.getElementById('traffic-chart-canvas');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            myTrafficChart = renderTrafficChart(ctx);
        }

        // Load initial data
        loadDashboardData();

        // Set up auto-refresh every 5 seconds
        window.dashboardRefreshInterval = setInterval(() => {
            // Only refresh if we're still on the dashboard page
            const dashboardPage = document.getElementById('dashboard-page');
            if (dashboardPage && dashboardPage.parentElement) {
                loadDashboardData();
            } else {
                // Clean up if user navigated away
                if (window.dashboardRefreshInterval) {
                    clearInterval(window.dashboardRefreshInterval);
                    window.dashboardRefreshInterval = null;
                }
            }
        }, 5000); // Refresh every 5 seconds
    }

    function initClients() {
        if (typeof window.loadClientsData === 'function') {
            window.loadClientsData();
            return;
        }
        const tbody = document.getElementById('client-list-body') || document.getElementById('clients-table-body');
        if (!tbody) return;
        const token = localStorage.getItem('admin_token');
        if (!token) return;
        fetch('/api/admin/clients', { headers: { 'Authorization': 'Bearer ' + token } })
            .then(res => res.json())
            .then(({ clients }) => {
                tbody.innerHTML = '';
                (clients || []).forEach(c => {
                    const blocked = c.blocked === true;
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${(c.roll_no || c.name || 'N/A')}</td>
                        <td>${c.ip || 'N/A'}</td>
                        <td>${c.data ? c.data + ' GB' : '0 GB'}</td>
                        <td>${c.activity || 'Idle'}</td>
                        <td>${blocked ? '<span class="status-blocked">Blocked</span>' : '<span class="status-active">Active</span>'}</td>
                        <td class="action-buttons">
                            <button class="btn btn-edit" onclick="editClient('${c._id || c.id}')">Edit</button>
                            <button class="${blocked ? 'btn-unblock' : 'btn-block'} btn" onclick="toggleBlock('${c._id || c.id}', ${blocked})">${blocked ? 'Unblock' : 'Block'}</button>
                        </td>`;
                    tbody.appendChild(tr);
                });
            })
            .catch(err => console.error('initClients fetch error', err));
    }

    async function initWebFiltering() {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            console.error('No admin token found');
            return;
        }

        try {
            const response = await fetch('/api/admin/filtering', {
                headers: { 'Authorization': 'Bearer ' + token }
            });

            if (!response.ok) {
                console.error('Failed to fetch filtering config');
                return;
            }

            const data = await response.json();
            const categories = data.categories || {};
            const manualBlocks = data.manual_blocks || [];

            // Build normalized domain set from stored manual entries
            window._blockedSitesSet = new Set(
                manualBlocks.map(site => normalizeDomain(site)).filter(Boolean)
            );

            // Update local db object for compatibility with existing code
            db.siteCategories = categories;
            db.blockedSites = manualBlocks;

            // Populate blocked sites list
            const blockedSitesList = document.getElementById("blocked-sites-list");
            if (blockedSitesList) {
                blockedSitesList.innerHTML = "";

                if (manualBlocks.length === 0) {
                    blockedSitesList.innerHTML = '<li style="color:var(--text-secondary);font-style:italic;padding:8px 0;">No sites manually blocked yet.</li>';
                } else {
                    manualBlocks.forEach(site => addBlockedSiteToDOM(site));
                }

                // Add category sites (read-only, cannot be individually removed)
                Object.keys(categories).forEach(categoryName => {
                    const cat = categories[categoryName];
                    if (cat.active && Array.isArray(cat.sites)) {
                        cat.sites.forEach(site => {
                            const normalizedSite = normalizeDomain(site);
                            if (!window._blockedSitesSet.has(normalizedSite)) {
                                addBlockedSiteToDOM(site, true, categoryName);
                            }
                        });
                    }
                });
            }

            // Populate category buttons
            const categoriesContainer = document.getElementById("filter-categories");
            if (categoriesContainer) {
                categoriesContainer.innerHTML = "";
                Object.keys(categories).forEach(categoryName => {
                    const cat = categories[categoryName];
                    const btn = document.createElement("button");
                    btn.className = `filter-toggle ${cat.active ? 'active' : ''}`;
                    btn.textContent = categoryName;
                    btn.dataset.category = categoryName;
                    categoriesContainer.appendChild(btn);
                });
            }
        } catch (error) {
            console.error('Error loading filtering config:', error);
        }
    }

    function initBandwidth() {
        const bandwidthListBody = document.getElementById("bandwidth-list-body");
        if (!bandwidthListBody) return;

        // Show loading
        bandwidthListBody.innerHTML = "<tr><td colspan='5'>Loading clients...</td></tr>";

        const token = localStorage.getItem('admin_token');
        if (!token) {
            bandwidthListBody.innerHTML = "<tr><td colspan='5'>Please login as admin</td></tr>";
            return;
        }

        // Fetch clients from API
        fetch('/api/admin/clients', { headers: { 'Authorization': 'Bearer ' + token } })
            .then(async res => {
                const body = await res.json().catch(() => ({}));
                if (!res.ok) {
                    throw new Error(body.message || 'Failed to load clients');
                }
                return body;
            })
            .then(data => {
                const clients = data.clients || [];
                if (data.bandwidth_presets && typeof data.bandwidth_presets === 'object') {
                    bandwidthPresets = {
                        ...DEFAULT_BANDWIDTH_PRESETS,
                        ...data.bandwidth_presets,
                    };
                }
                bandwidthListBody.innerHTML = "";

                if (clients.length === 0) {
                    bandwidthListBody.innerHTML = "<tr><td colspan='5'>No students registered yet</td></tr>";
                    return;
                }

                let renderedClients = 0;

                clients.forEach(client => {
                    if (client.role === 'admin') return;
                    renderedClients += 1;

                    const clientId = client._id || client.id;
                    const rawLimit = client.bandwidth_limit;
                    let limit = 'medium';
                    if (typeof rawLimit === 'number') {
                        limit = 'manual';
                    } else if (typeof rawLimit === 'string') {
                        const normalized = rawLimit.trim().toLowerCase();
                        if (['low', 'medium', 'high', 'manual', 'auto'].includes(normalized)) {
                            limit = normalized;
                        }
                    }

                    const customSource = (client.bandwidth_custom_value !== undefined && client.bandwidth_custom_value !== null)
                        ? client.bandwidth_custom_value
                        : rawLimit;
                    const parsedCustomValue = parseInt(customSource, 10);
                    const customValue = Number.isFinite(parsedCustomValue)
                        ? Math.min(500, Math.max(1, parsedCustomValue))
                        : 50;
                    const dataUsage = client.data_usage || '0';
                    const activity = client.detected_activity || client.activity || 'Idle';
                    const effectiveMbps = client.bandwidth_effective_mbps || (limit === 'manual'
                        ? customValue
                        : getPresetMbps(limit));
                    const effectiveInfoHtml = `<div class="effective-bw-info" style="margin-top: 5px; font-size: 0.82em; color: #4b5563;">Applied: <strong>${effectiveMbps} Mbps</strong></div>`;

                    // Determine status display
                    let statusHtml = '<span class="status-offline">Offline</span>';
                    if (client.status) {
                        if (client.status.includes('Blocked')) {
                            statusHtml = `<span class="status-blocked">${client.status}</span>`;
                        } else if (client.status === 'Online') {
                            statusHtml = '<span class="status-online">Online</span>';
                        } else if (client.status === 'Offline') {
                            statusHtml = '<span class="status-offline">Offline</span>';
                        } else if (client.status === 'Active') {
                            statusHtml = '<span class="status-active">Active</span>';
                        } else {
                            statusHtml = `<span class="status-active">${client.status}</span>`;
                        }
                    } else if (client.blocked) {
                        statusHtml = '<span class="status-blocked">Blocked</span>';
                    }

                    const row = document.createElement("tr");

                    // Determine bandwidth display for AUTO mode
                    let bandwidthDisplayHtml = '';
                    if (limit === 'auto') {
                        const autoAssigned = client.bandwidth_auto_assigned || 'medium';
                        const autoConfidence = client.bandwidth_auto_confidence || 0;
                        const confidencePercent = (autoConfidence * 100).toFixed(0);
                        bandwidthDisplayHtml = `
                        <div class="bandwidth-control-cell">
                            <select class="limit-select" data-id="${clientId}">
                                <option value="low">LOW (${getPresetMbps('low')} Mbps)</option>
                                <option value="medium">MEDIUM (${getPresetMbps('medium')} Mbps)</option>
                                <option value="high">HIGH (${getPresetMbps('high')} Mbps)</option>
                                <option value="manual">MANUAL (Custom)</option>
                                <option value="auto" selected>AUTO (Activity-Based)</option>
                            </select>
                            <span class="custom-bw-group hidden" style="margin-left: 10px;">
                                <input type="number" class="custom-bw-input" data-id="${clientId}" value="${customValue}" min="1" max="500" style="width: 60px;">
                                <span>Mbps</span>
                            </span>
                            <div class="auto-bw-info" style="margin-top: 5px; font-size: 0.85em; color: #666;">
                                Currently: <strong>${autoAssigned.toUpperCase()}</strong> (${confidencePercent}% confidence)
                            </div>
                            ${effectiveInfoHtml}
                        </div>
                    `;
                    } else if (limit === 'manual') {
                        bandwidthDisplayHtml = `
                        <div class="bandwidth-control-cell">
                            <select class="limit-select" data-id="${clientId}">
                                <option value="low">LOW (${getPresetMbps('low')} Mbps)</option>
                                <option value="medium">MEDIUM (${getPresetMbps('medium')} Mbps)</option>
                                <option value="high">HIGH (${getPresetMbps('high')} Mbps)</option>
                                <option value="manual" selected>MANUAL (Custom)</option>
                                <option value="auto">AUTO (Activity-Based)</option>
                            </select>
                            <span class="custom-bw-group" style="margin-left: 10px;">
                                <input type="number" class="custom-bw-input" data-id="${clientId}" value="${customValue}" min="1" max="500" style="width: 60px;">
                                <span>Mbps</span>
                            </span>
                            ${effectiveInfoHtml}
                        </div>
                    `;
                    } else {
                        // Normal preset tiers: low, medium, high
                        const normalizedLimit = limit || 'medium';
                        bandwidthDisplayHtml = `
                        <div class="bandwidth-control-cell">
                            <select class="limit-select" data-id="${clientId}">
                                <option value="low" ${normalizedLimit === 'low' ? 'selected' : ''}>LOW (${getPresetMbps('low')} Mbps)</option>
                                <option value="medium" ${normalizedLimit === 'medium' ? 'selected' : ''}>MEDIUM (${getPresetMbps('medium')} Mbps)</option>
                                <option value="high" ${normalizedLimit === 'high' ? 'selected' : ''}>HIGH (${getPresetMbps('high')} Mbps)</option>
                                <option value="manual">MANUAL (Custom)</option>
                                <option value="auto">AUTO (Activity-Based)</option>
                            </select>
                            <span class="custom-bw-group hidden">
                                <input type="number" class="custom-bw-input" data-id="${clientId}" value="${customValue}" min="1" max="500" style="width: 60px;">
                                <span>Mbps</span>
                            </span>
                            ${effectiveInfoHtml}
                        </div>
                    `;
                    }

                    row.innerHTML = `
                    <td>${client.roll_no || client.name || 'Unknown'}</td>
                    <td>${dataUsage} GB</td>
                    <td>${activity}</td>
                    <td style="text-align: center;">${statusHtml}</td>
                    <td>${bandwidthDisplayHtml}</td>
                `;
                    bandwidthListBody.appendChild(row);
                });

                if (renderedClients === 0) {
                    bandwidthListBody.innerHTML = "<tr><td colspan='5'>No students registered yet</td></tr>";
                }
            })
            .catch(err => {
                console.error('Error fetching clients:', err);
                bandwidthListBody.innerHTML = `<tr><td colspan='5'>${err.message || 'Error loading clients'}</td></tr>`;
            });
    }

    function initLogs() {
        const logBody = document.getElementById("log-body");
        if (!logBody) return;

        // Clear existing logs and show loading
        logBody.innerHTML = "<tr><td colspan='4'>Loading logs...</td></tr>";

        // Fetch real logs from API
        const token = localStorage.getItem('admin_token');
        if (!token) {
            logBody.innerHTML = "<tr><td colspan='4'>Please login as admin to view logs</td></tr>";
            return;
        }

        fetch('/api/admin/logs', {
            headers: { 'Authorization': 'Bearer ' + token }
        })
            .then(res => res.json())
            .then(data => {
                const logs = data.logs || [];
                logBody.innerHTML = "";

                if (logs.length === 0) {
                    logBody.innerHTML = "<tr><td colspan='4'>No network activity logs found. Start monitoring to capture activity.</td></tr>";
                    return;
                }

                logs.forEach(log => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                    <td>${log.time || 'N/A'}</td>
                    <td><span class="log-level-${log.level || 'info'}">${(log.level || 'info').toUpperCase()}</span></td>
                    <td>${log.user || 'Unknown'} / ${log.ip || 'N/A'}</td>
                    <td>${log.action || 'Unknown activity'}</td>
                `;
                    logBody.appendChild(tr);
                });
            })
            .catch(err => {
                console.error('Error fetching logs:', err);
                logBody.innerHTML = "<tr><td colspan='4'>Error loading logs. Please try again.</td></tr>";
            });
    }

    async function initSettings() {
        const token = localStorage.getItem('admin_token');
        if (!token) {
            window.location.href = '/admin/login';
            return;
        }

        function decodeJwtPayload(rawToken) {
            try {
                const payloadPart = rawToken.split('.')[1];
                if (!payloadPart) return null;
                const normalized = payloadPart.replace(/-/g, '+').replace(/_/g, '/');
                const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
                return JSON.parse(atob(padded));
            } catch (_) {
                return null;
            }
        }

        function formatHours(value) {
            const hours = Number(value) || 2;
            return `${hours} hour${hours === 1 ? '' : 's'}`;
        }

        function clampTimeout(value, fallback = 2) {
            const parsed = Number.parseInt(value, 10);
            if (!Number.isFinite(parsed)) return fallback;
            return Math.min(24, Math.max(1, parsed));
        }

        async function readApiPayload(response) {
            const raw = await response.text();
            let data = {};
            if (raw) {
                try {
                    data = JSON.parse(raw);
                } catch (_) {
                    data = {};
                }
            }
            return { data, raw };
        }

        function extractApiMessage(response, payload) {
            const data = payload && payload.data && typeof payload.data === 'object' ? payload.data : {};
            if (typeof data.message === 'string' && data.message.trim()) return data.message;
            if (typeof data.msg === 'string' && data.msg.trim()) return data.msg;

            const raw = payload && typeof payload.raw === 'string' ? payload.raw.trim() : '';
            if (raw && raw[0] !== '<') return raw;

            if (response.status === 404) {
                return 'Password/settings API not found on backend. Restart backend and login again.';
            }
            if (response.status === 401) {
                return 'Session expired. Please login again.';
            }
            return `Request failed (${response.status}).`;
        }

        // --- Show status badge helper ---
        function showBadge(msg, color = '#15803d', bg = '#dcfce7') {
            const badge = document.getElementById('settings-status-badge');
            if (!badge) return;
            badge.textContent = (color === '#15803d' ? '✔ ' : '✖ ') + msg;
            badge.style.background = bg;
            badge.style.color = color;
            badge.style.display = 'inline-block';
            setTimeout(() => { badge.style.display = 'none'; }, 3500);
        }

        const payload = decodeJwtPayload(token) || {};
        const usernameEl = document.getElementById('settings-admin-username');
        if (usernameEl) {
            usernameEl.textContent = `Logged in as: ${payload.username || 'admin'}`;
        }

        const sessionInfoEl = document.getElementById('settings-session-info');
        if (sessionInfoEl) {
            const exp = Number(payload.exp);
            if (Number.isFinite(exp)) {
                const expiryTime = new Date(exp * 1000);
                sessionInfoEl.textContent = `Current session expires: ${expiryTime.toLocaleString()}`;
            } else {
                sessionInfoEl.textContent = 'Current session expiry unavailable.';
            }
        }

        const timeoutInfoEl = document.getElementById('timeout-current-info');
        const timeoutMsgEl = document.getElementById('timeout-msg');
        const adminTimeoutInput = document.getElementById('admin-timeout');
        const studentTimeoutInput = document.getElementById('student-timeout');

        function renderTimeoutInfo(adminHours, studentHours, draft = false) {
            if (!timeoutInfoEl) return;
            timeoutInfoEl.style.borderColor = draft ? '#fcd34d' : '#dbeafe';
            timeoutInfoEl.style.background = draft ? '#fffbeb' : '#eff6ff';
            timeoutInfoEl.style.color = draft ? '#92400e' : '#1e3a8a';
            timeoutInfoEl.textContent = `${draft ? 'Draft policy' : 'Current policy'}: Admin ${formatHours(adminHours)}, Student ${formatHours(studentHours)}. Applies to new logins immediately.`;
        }

        // --- Password strength meter ---
        const newPwInput = document.getElementById('new-password');
        if (newPwInput) {
            newPwInput.addEventListener('input', () => {
                const val = newPwInput.value;
                const wrap = document.getElementById('pw-strength-wrap');
                const bar = document.getElementById('pw-strength-bar');
                const label = document.getElementById('pw-strength-label');
                if (!wrap || !bar || !label) return;
                wrap.style.display = val.length > 0 ? 'block' : 'none';
                let score = 0;
                if (val.length >= 8) score++;
                if (/[A-Z]/.test(val)) score++;
                if (/[0-9]/.test(val)) score++;
                if (/[^A-Za-z0-9]/.test(val)) score++;
                const levels = [
                    { color: '#ef4444', text: 'Weak' },
                    { color: '#f97316', text: 'Fair' },
                    { color: '#eab308', text: 'Good' },
                    { color: '#22c55e', text: 'Strong' },
                ];
                const lvl = levels[Math.min(score, 3)];
                bar.style.background = lvl.color;
                bar.style.width = `${(score / 4) * 100}%`;
                label.textContent = `Strength: ${lvl.text}`;
                label.style.color = lvl.color;
            });
        }

        // --- Eye toggle for password fields ---
        document.querySelectorAll('.toggle-pw').forEach(icon => {
            icon.addEventListener('click', () => {
                const input = document.getElementById(icon.dataset.target);
                if (!input) return;
                const isHidden = input.type === 'password';
                input.type = isHidden ? 'text' : 'password';
                icon.classList.toggle('fa-eye-slash', !isHidden);
                icon.classList.toggle('fa-eye', isHidden);
            });
        });

        // --- Change Password Form ---
        const pwForm = document.getElementById('change-password-form');
        if (pwForm) {
            pwForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const errEl = document.getElementById('pw-error');
                const currentPw = document.getElementById('current-password')?.value || '';
                const newPw = document.getElementById('new-password')?.value || '';
                const confirmPw = document.getElementById('confirm-password')?.value || '';
                const submitBtn = pwForm.querySelector('button[type="submit"]');
                const defaultBtnHtml = submitBtn ? submitBtn.innerHTML : '';

                if (errEl) errEl.style.display = 'none';

                if (!currentPw) {
                    if (errEl) {
                        errEl.textContent = 'Current password is required.';
                        errEl.style.display = 'block';
                    }
                    return;
                }

                if (newPw !== confirmPw) {
                    if (errEl) { errEl.textContent = 'New passwords do not match.'; errEl.style.display = 'block'; }
                    return;
                }
                if (newPw.length < 6) {
                    if (errEl) { errEl.textContent = 'Password must be at least 6 characters.'; errEl.style.display = 'block'; }
                    return;
                }

                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i class="fa-solid fa-key" style="margin-right: 6px"></i> Updating...';
                }

                try {
                    const res = await fetch('/api/admin/change-password', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({ current_password: currentPw, new_password: newPw })
                    });
                    const payload = await readApiPayload(res);
                    const data = payload.data;

                    if (res.status === 401) {
                        window.location.href = '/admin/login';
                        return;
                    }

                    if (res.ok) {
                        pwForm.reset();
                        const wrap = document.getElementById('pw-strength-wrap');
                        if (wrap) wrap.style.display = 'none';
                        showBadge('Password Updated');
                    } else {
                        if (errEl) {
                            errEl.textContent = extractApiMessage(res, payload);
                            errEl.style.display = 'block';
                        }
                    }
                } catch (err) {
                    if (errEl) { errEl.textContent = 'Server error. Please try again.'; errEl.style.display = 'block'; }
                } finally {
                    if (submitBtn) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = defaultBtnHtml;
                    }
                }
            });
        }

        // --- Load existing timeout settings ---
        let currentTimeouts = { admin: 2, student: 2 };

        try {
            const res = await fetch('/api/admin/settings/timeout', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            const payload = await readApiPayload(res);
            const data = payload.data;

            if (res.status === 401) {
                window.location.href = '/admin/login';
                return;
            }

            if (res.ok) {
                currentTimeouts = {
                    admin: clampTimeout(data.admin_timeout_hours, 2),
                    student: clampTimeout(data.student_timeout_hours, 2),
                };
            } else if (timeoutMsgEl) {
                timeoutMsgEl.style.display = 'block';
                timeoutMsgEl.style.color = '#dc2626';
                timeoutMsgEl.textContent = extractApiMessage(res, payload);
            }
        } catch (_) {
            if (timeoutMsgEl) {
                timeoutMsgEl.style.display = 'block';
                timeoutMsgEl.style.color = '#dc2626';
                timeoutMsgEl.textContent = 'Could not reach server to load timeout settings.';
            }
        }

        if (adminTimeoutInput) adminTimeoutInput.value = String(currentTimeouts.admin);
        if (studentTimeoutInput) studentTimeoutInput.value = String(currentTimeouts.student);
        renderTimeoutInfo(currentTimeouts.admin, currentTimeouts.student, false);

        const updateTimeoutDraft = () => {
            const adminHours = clampTimeout(adminTimeoutInput?.value, currentTimeouts.admin);
            const studentHours = clampTimeout(studentTimeoutInput?.value, currentTimeouts.student);
            renderTimeoutInfo(adminHours, studentHours, true);
        };

        if (adminTimeoutInput) {
            adminTimeoutInput.addEventListener('input', updateTimeoutDraft);
            adminTimeoutInput.addEventListener('blur', () => {
                adminTimeoutInput.value = String(clampTimeout(adminTimeoutInput.value, currentTimeouts.admin));
                updateTimeoutDraft();
            });
        }

        if (studentTimeoutInput) {
            studentTimeoutInput.addEventListener('input', updateTimeoutDraft);
            studentTimeoutInput.addEventListener('blur', () => {
                studentTimeoutInput.value = String(clampTimeout(studentTimeoutInput.value, currentTimeouts.student));
                updateTimeoutDraft();
            });
        }

        // --- Save Timeout Button ---
        const saveTimeoutBtn = document.getElementById('save-timeout-btn');
        if (saveTimeoutBtn) {
            saveTimeoutBtn.addEventListener('click', async () => {
                const adminHours = clampTimeout(adminTimeoutInput?.value, currentTimeouts.admin);
                const studentHours = clampTimeout(studentTimeoutInput?.value, currentTimeouts.student);
                const defaultBtnHtml = saveTimeoutBtn.innerHTML;

                if (adminTimeoutInput) adminTimeoutInput.value = String(adminHours);
                if (studentTimeoutInput) studentTimeoutInput.value = String(studentHours);

                saveTimeoutBtn.disabled = true;
                saveTimeoutBtn.innerHTML = '<i class="fa-solid fa-floppy-disk" style="margin-right: 6px"></i> Saving...';
                if (timeoutMsgEl) timeoutMsgEl.style.display = 'none';

                try {
                    const res = await fetch('/api/admin/settings/timeout', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + token
                        },
                        body: JSON.stringify({ admin_timeout_hours: adminHours, student_timeout_hours: studentHours })
                    });
                    const payload = await readApiPayload(res);

                    if (res.status === 401) {
                        window.location.href = '/admin/login';
                        return;
                    }

                    if (res.ok) {
                        currentTimeouts = { admin: adminHours, student: studentHours };
                        showBadge('Timeout Saved');
                        renderTimeoutInfo(currentTimeouts.admin, currentTimeouts.student, false);
                        if (timeoutMsgEl) {
                            timeoutMsgEl.style.display = 'block';
                            timeoutMsgEl.style.color = '#15803d';
                            timeoutMsgEl.textContent = `✔ Settings saved. New login sessions now use Admin ${formatHours(adminHours)} and Student ${formatHours(studentHours)}.`;
                        }
                    } else {
                        if (timeoutMsgEl) {
                            timeoutMsgEl.style.display = 'block';
                            timeoutMsgEl.style.color = '#dc2626';
                            timeoutMsgEl.textContent = extractApiMessage(res, payload);
                        }
                    }
                } catch (err) {
                    if (timeoutMsgEl) {
                        timeoutMsgEl.style.display = 'block';
                        timeoutMsgEl.style.color = '#dc2626';
                        timeoutMsgEl.textContent = 'Server error.';
                    }
                } finally {
                    saveTimeoutBtn.disabled = false;
                    saveTimeoutBtn.innerHTML = defaultBtnHtml;
                }
            });
        }
    }

    function initApStatus() {
        const apListBody = document.getElementById("ap-list-body");
        if (!apListBody) return;
        apListBody.innerHTML = "";
        db.accessPoints.forEach(ap => {
            const statusClass = ap.status === "Online" ? "status-online" : "status-offline";
            const loadClass = ap.load === "High" ? "status-high" : (ap.load === "Medium" ? "status-medium" : "");
            const row = document.createElement("tr");
            row.innerHTML = `<td><strong>${ap.location}</strong> (${ap.id})</td><td class="${statusClass}">${ap.status}</td><td>${ap.clients} Devices</td><td class="${loadClass}">${ap.load}</td><td><button class="btn btn-secondary reboot-ap-btn" data-id="${ap.id}" data-location="${ap.location}"><i class="fa-solid fa-sync"></i> Reboot AP</button></td>`;
            apListBody.appendChild(row);
        });
    }

    function initGuestNetwork() {
        const voucherList = document.getElementById("guest-voucher-list");
        if (!voucherList) return;

        const guestToggle = document.getElementById('guest-toggle-cb');
        const guestStatusText = document.getElementById('guest-status-text');
        if (guestToggle && guestStatusText) {
            guestToggle.checked = db.guestNetworkEnabled;
            guestStatusText.textContent = db.guestNetworkEnabled ? 'Enabled' : 'Disabled';
        }
        voucherList.innerHTML = "";
        db.guestVouchers.forEach(voucher => {
            const statusText = voucher.status;
            const isUnused = statusText === "Unused";
            const statusClass = isUnused ? "status-unused" : "status-claimed";
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${voucher.code}</td>
                <td>${voucher.duration}</td>
                <td class="${statusClass}">
                    ${isUnused ? `<button class="btn-status-unused" data-id="${voucher.id}" title="Click to simulate claiming this voucher">${statusText}</button>` : `<span>${statusText}</span>`}
                </td>
                <td class="action-buttons">
                    <button class="btn-delete-voucher" data-id="${voucher.id}" title="Delete Voucher">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            `;
            voucherList.appendChild(tr);
        });
    }

    function initReporting() {
        handleReportRangeChange(document.getElementById('report-range'));
    }


    // --- Global Event Listeners (using delegation on document.body) ---

    // --- 1. CLICK Listener ---
    document.body.addEventListener('click', (e) => {

        if (e.target.closest('#profile-menu-toggle')) {
            profileDropdown.classList.toggle('active');
            notificationTray.classList.remove('active');
        } else if (!e.target.closest('.profile-dropdown')) {
            profileDropdown.classList.remove('active');
        }

        if (e.target.closest('#notification-bell')) {
            notificationTray.classList.toggle('active');
            notificationBadge.classList.add('hidden');
            profileDropdown.classList.remove('active');
            // Mark all notifications as read when dropdown is opened
            if (notificationTray.classList.contains('active')) {
                markAllNotificationsRead();
            }
        } else if (!e.target.closest('.notification-dropdown')) {
            notificationTray.classList.remove('active');
        }

        const menuItem = e.target.closest('.menu-item');
        if (menuItem) {
            e.preventDefault();
            const pageName = menuItem.getAttribute("data-page");
            menuItems.forEach(i => i.classList.remove("active"));
            menuItem.classList.add("active");
            pageTitle.textContent = menuItem.querySelector("span").textContent;
            loadPage(pageName);
            if (window.innerWidth <= 768) sidebar.classList.remove("open");
        }

        if (e.target.closest('#menu-toggle')) {
            sidebar.classList.toggle("open");
        }

        if (e.target.classList.contains('btn-block') || e.target.classList.contains('btn-unblock')) {
            if (typeof window.toggleBlock === 'function') return;
            handleBlockUnblock(e.target);
        }

        if (e.target.classList.contains('btn-edit')) {
            // If a global editClient is defined (inline onclick), skip the delegate
            if (typeof window.editClient === 'function') return;
            const rawId = e.target.dataset.id || e.target.getAttribute('data-id');
            const id = rawId ? String(rawId) : '';
            if (!id) return;
            openEditModal(id);
        }

        if (e.target.id === 'edit-modal-close-btn' || e.target.id === 'edit-modal-overlay') {
            closeEditModal();
        }

        const removeBtnEl = e.target.closest('.btn-remove');
        if (removeBtnEl) {
            handleRemoveSite(removeBtnEl);
        }

        if (e.target.classList.contains('filter-toggle')) {
            handleCategoryToggle(e.target);
        }

        if (e.target.id === 'reboot-button') {
            handleReboot("Main Router");
        }

        if (e.target.classList.contains('reboot-ap-btn')) {
            const location = e.target.dataset.location;
            handleReboot(location);
        }

        if (e.target.classList.contains('btn-status-unused')) {
            const id = parseInt(e.target.dataset.id);
            const voucher = db.guestVouchers.find(v => v.id === id);
            if (voucher) {
                voucher.status = "Claimed by Guest's Phone";
                addLog('info', 'GUEST', `Voucher ${voucher.code} was claimed.`);
                initGuestNetwork();
            }
        }

        if (e.target.closest('.btn-delete-voucher')) {
            const id = parseInt(e.target.closest('.btn-delete-voucher').dataset.id);
            const voucher = db.guestVouchers.find(v => v.id === id);
            if (voucher && confirm(`Are you sure you want to delete voucher ${voucher.code}?`)) {
                db.guestVouchers = db.guestVouchers.filter(v => v.id !== id);
                addLog('info', 'ADMIN', `Deleted voucher ${voucher.code}`);
                initGuestNetwork();
            }
        }

        // --- MODIFIED: This is the new Download Button handler ---
        if (e.target.classList.contains('btn-download-report')) {
            handleDownloadReport(e.target);
        }
    });

    // --- 2. SUBMIT Listener ---
    document.body.addEventListener('submit', (e) => {
        if (e.target.id === 'add-client-form') {
            e.preventDefault();
            const roll_no = document.getElementById('client-id')?.value.trim();
            const password = document.getElementById('client-password')?.value.trim();
            const activity = document.getElementById('client-activity')?.value?.trim();
            if (!roll_no) return alert('Enter Student ID');
            const token = localStorage.getItem('admin_token');
            if (!token) return alert('Please log in as admin');
            const body = { roll_no };
            if (password) body.password = password;
            if (activity) body.activity = activity;
            fetch('/api/admin/clients', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                body: JSON.stringify(body)
            }).then(async (res) => {
                if (!res.ok) { alert('Failed to add client'); return; }
                e.target.reset();
                if (typeof window.loadClientsData === 'function') window.loadClientsData(); else initClients();
            }).catch(err => { console.error(err); alert('Request error'); });
        }

        if (e.target.id === 'website-block-form') {
            e.preventDefault();
            const websiteInput = document.getElementById("website-input");
            const rawInput = websiteInput.value.trim();
            if (!rawInput) return;

            const domain = normalizeDomain(rawInput);
            if (!domain || !domain.includes('.')) {
                showFilteringError('Invalid URL — could not detect a domain.');
                return;
            }

            // Local duplicate check — no round-trip needed
            if (window._blockedSitesSet && window._blockedSitesSet.has(domain)) {
                showFilteringError(`"${domain}" is already in the block list.`);
                return;
            }

            const token = localStorage.getItem('admin_token');
            if (!token) { alert('Please log in as admin'); return; }

            const submitBtn = e.target.querySelector('button[type="submit"]');
            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Blocking…'; }

            fetch('/api/admin/filtering/sites', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({ url: rawInput })
            })
            .then(async (res) => {
                const result = await res.json().catch(() => ({}));
                if (!res.ok) {
                    showFilteringError(result.message || 'Failed to block site');
                    return;
                }
                // Optimistic UI: add to set and DOM immediately
                websiteInput.value = '';
                addLog('warn', 'ADMIN', `Manually blocked site: ${domain}`);
                if (!window._blockedSitesSet) window._blockedSitesSet = new Set();
                window._blockedSitesSet.add(domain);
                db.blockedSites = [...(db.blockedSites || []), domain];

                // Remove placeholder if present
                const list = document.getElementById('blocked-sites-list');
                if (list) {
                    const placeholder = list.querySelector('li[style]');
                    if (placeholder && placeholder.textContent.includes('No sites')) placeholder.remove();
                }
                addBlockedSiteToDOM(domain, false, false, true /* prepend */);
            })
            .catch(err => {
                console.error('Error blocking site:', err);
                showFilteringError('Request error — please try again.');
            })
            .finally(() => {
                if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Block Website'; }
            });
        }

        if (e.target.id === 'network-settings-form') {
            e.preventDefault();
            addLog('info', 'ADMIN', 'Network settings saved');
            alert('Network settings saved successfully! (Demo)');
        }

        if (e.target.id === 'edit-client-form') {
            e.preventDefault();
            handleEditClient();
        }

        if (e.target.id === 'create-voucher-form') {
            e.preventDefault();
            const code = document.getElementById('voucher-code-input').value;
            const limit = document.getElementById('voucher-limit-select').value;
            if (code && limit) {
                const newVoucher = {
                    id: db.guestVouchers.length + 1, code: code, duration: limit, status: 'Unused'
                };
                db.guestVouchers.push(newVoucher);
                addLog('info', 'ADMIN', `Created new voucher: ${code}`);
                initGuestNetwork();
                e.target.reset();
                alert('Guest voucher created successfully!');
            }
        }

        if (e.target.id === 'reporting-form') {
            e.preventDefault();
            const type = document.getElementById('report-type').value;
            const range = document.getElementById('report-range').value;
            const format = document.getElementById('report-format').value;

            // Show loading state
            const resultsArea = document.getElementById('report-results-area');
            if (resultsArea) {
                resultsArea.innerHTML = '<div class="card"><p>Generating report...</p></div>';
            }

            // Fetch real report data from API
            const token = localStorage.getItem('admin_token');
            if (!token) {
                alert('Please login as admin');
                return;
            }

            fetch('/api/admin/reports', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({ type, range })
            })
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        resultsArea.innerHTML = `<div class="card"><p>Error: ${data.error}</p></div>`;
                        return;
                    }
                    const reportName = data.title || `${range} ${type} Report`;
                    renderReport(reportName, data.headers || [], data.data || [], format);
                    addLog('info', 'ADMIN', `Generated report: ${reportName}`);
                })
                .catch(err => {
                    console.error('Report error:', err);
                    if (resultsArea) {
                        resultsArea.innerHTML = '<div class="card"><p>Error generating report. Please try again.</p></div>';
                    }
                });
        }
    });

    // --- 3. CHANGE Listener ---
    document.body.addEventListener('change', (e) => {
        if (e.target.classList.contains('limit-select')) {
            handleBandwidthChange(e.target);
        }

        if (e.target.id === 'guest-toggle-cb') {
            handleGuestToggle(e.target);
        }

        if (e.target.id === 'report-range') {
            handleReportRangeChange(e.target);
        }
    });

    // --- 4. INPUT Listener ---
    document.body.addEventListener('input', (e) => {
        if (e.target.classList.contains('custom-bw-input')) {
            handleCustomBandwidthInput(e.target);
        }
    });

    // --- Event Handler Functions ---

    function handleBlockUnblock(button) {
        const id = parseInt(button.getAttribute("data-id"));
        const client = db.clients.find(c => c.id === id);
        if (!client) return;
        if (client.blocked) {
            if (confirm(`Are you sure you want to unblock ${client.studentId} (${client.device})?`)) {
                client.blocked = false;
                addLog('info', 'ADMIN', `Unblocked user ${client.studentId}`);
                if (document.getElementById('clients-page')) initClients();
                if (document.getElementById('bandwidth-page')) initBandwidth();
                initDashboard();
            }
        } else {
            if (confirm(`Are you sure you want to block ${client.studentId} (${client.device})?`)) {
                client.blocked = true;
                addLog('warn', 'ADMIN', `Blocked user ${client.studentId}`);
                if (document.getElementById('clients-page')) initClients();
                if (document.getElementById('bandwidth-page')) initBandwidth();
                initDashboard();
            }
        }
    }

    function handleEditClient() {
        const id = document.getElementById('edit-client-id').value;
        const roll_no = document.getElementById('edit-client-id-text').value.trim();
        const password = document.getElementById('edit-client-password').value.trim();
        if (!roll_no || !id) return alert('Missing required fields');
        const token = localStorage.getItem('admin_token');
        if (!token) return alert('Please log in as admin');
        const body = { roll_no };
        if (password) body.password = password;
        fetch(`/api/admin/clients/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(body)
        }).then(async (res) => {
            if (!res.ok) { alert('Failed to update client'); return; }
            closeEditModal();
            if (typeof window.loadClientsData === 'function') window.loadClientsData(); else initClients();
        }).catch(err => { console.error(err); alert('Request error'); });
    }

    async function fetchClientById(id) {
        const token = localStorage.getItem('admin_token');
        if (!token) return null;
        try {
            const resOne = await fetch(`/api/admin/clients/${id}`, { headers: { 'Authorization': 'Bearer ' + token } });
            if (resOne.ok) {
                const data = await resOne.json();
                return data.client || data;
            }
        } catch { }
        try {
            const res = await fetch('/api/admin/clients', { headers: { 'Authorization': 'Bearer ' + token } });
            if (res.ok) {
                const { clients } = await res.json();
                return (clients || []).find(x => String(x._id || x.id) === String(id)) || null;
            }
        } catch { }
        return null;
    }

    function openEditModal(id) {
        document.getElementById('edit-client-id').value = id;
        const pwd = document.getElementById('edit-client-password');
        if (pwd) pwd.value = '';
        fetchClientById(id).then(c => {
            document.getElementById('edit-client-id-text').value = (c && (c.roll_no || c.name)) ? (c.roll_no || c.name) : '';
            modalOverlay.classList.remove('hidden');
        }).catch(() => {
            document.getElementById('edit-client-id-text').value = '';
            modalOverlay.classList.remove('hidden');
        });
    }

    // expose edit modal function globally for inline onclicks
    window.openEditModal = openEditModal;

    // expose block/unblock globally for inline onclicks and call backend
    window.toggleBlock = function (id, isBlocked) {
        const token = localStorage.getItem('admin_token');
        if (!token) return alert('Please log in as admin');
        fetch(`/api/admin/clients/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify({ blocked: !isBlocked })
        }).then(async (res) => {
            if (!res.ok) { alert('Failed to update client'); return; }
            if (typeof window.loadClientsData === 'function') window.loadClientsData(); else initClients();
        }).catch(err => { console.error(err); alert('Request error'); });
    };

    function closeEditModal() {
        modalOverlay.classList.add('hidden');
    }

    function handleRemoveSite(button) {
        const li = button.closest('li');
        if (!li) return;
        // Manual site is stored in data-site by addBlockedSiteToDOM
        const site = li.dataset.site;
        if (!site) { li.remove(); return; }

        const token = localStorage.getItem('admin_token');
        if (!token) { alert('Please log in as admin'); return; }

        // Optimistic removal
        li.style.opacity = '0.4';
        button.disabled = true;

        fetch('/api/admin/filtering/sites', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({ url: site })
        })
        .then(async res => {
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                alert(err.message || 'Failed to remove site');
                li.style.opacity = '1';
                button.disabled = false;
                return;
            }
            // Update in-memory state
            if (window._blockedSitesSet) window._blockedSitesSet.delete(site);
            db.blockedSites = (db.blockedSites || []).filter(b => normalizeDomain(b) !== site);
            addLog('info', 'ADMIN', `Removed manual block: ${site}`);
            li.remove();

            // Show placeholder if list is now empty
            const list = document.getElementById('blocked-sites-list');
            if (list && list.querySelectorAll('li[data-site]').length === 0) {
                // Check if all remaining are category sites
                const allLis = list.querySelectorAll('li');
                const hasManual = [...allLis].some(l => l.dataset.site);
                if (!hasManual) {
                    list.insertAdjacentHTML('afterbegin', '<li style="color:var(--text-secondary);font-style:italic;padding:8px 0;">No sites manually blocked yet.</li>');
                }
            }
        })
        .catch(err => {
            console.error('Error removing site:', err);
            alert('Request error — please try again.');
            li.style.opacity = '1';
            button.disabled = false;
        });
    }

    async function handleCategoryToggle(button) {
        const category = button.dataset.category;
        const token = localStorage.getItem('admin_token');
        if (!token) {
            alert('Please log in as admin');
            return;
        }

        try {
            const response = await fetch('/api/admin/filtering/categories', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({ category })
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                console.error('Failed to toggle category', err);
                alert(err.message || 'Failed to update category');
                return;
            }

            const result = await response.json();
            const isActive = result.active;

            if (isActive) {
                addLog('warn', 'ADMIN', `Enabled category block: ${category}`);
            } else {
                addLog('info', 'ADMIN', `Disabled category block: ${category}`);
            }

            // Reload filtering page to show updated state
            await initWebFiltering();
        } catch (error) {
            console.error('Error toggling category:', error);
            alert('Request error');
        }
    }

    function handleReboot(location) {
        if (confirm(`Are you sure you want to reboot ${location}? This may disconnect users.`)) {
            addLog('error', 'ADMIN', `!!! REBOOT INITIATED: ${location} !!!`);
            alert(`Simulating reboot for ${location}...`);
        }
    }

    function getBandwidthApplyWarning(payload) {
        if (!payload || typeof payload !== 'object') return '';

        if (payload.warning) {
            return String(payload.warning);
        }

        const applyStatus = payload.apply_status;
        if (!applyStatus || typeof applyStatus !== 'object') {
            return '';
        }

        if (applyStatus.success === false && applyStatus.error) {
            return String(applyStatus.error);
        }

        const tcStatus = applyStatus.tc && typeof applyStatus.tc === 'object'
            ? applyStatus.tc
            : applyStatus;

        if ((applyStatus.total_active_users === 0 || applyStatus.total_active_sessions === 0)
            && tcStatus.message) {
            return String(tcStatus.message);
        }

        if (Array.isArray(applyStatus.skipped_sessions) && applyStatus.skipped_sessions.length > 0) {
            const firstSkipped = applyStatus.skipped_sessions[0];
            if (firstSkipped && firstSkipped.reason) {
                return `Active session skipped: ${firstSkipped.reason}`;
            }
            return 'Some active sessions were skipped for shaping';
        }

        if (Array.isArray(tcStatus.warnings) && tcStatus.warnings.length > 0) {
            return tcStatus.warnings.join('; ');
        }

        if (tcStatus.success === false) {
            if (Array.isArray(tcStatus.errors) && tcStatus.errors.length > 0) {
                return tcStatus.errors.join('; ');
            }
            if (tcStatus.error) {
                return String(tcStatus.error);
            }
            return 'Traffic shaping command failed';
        }

        return '';
    }

    function handleBandwidthChange(selectElement) {
        const clientId = selectElement.dataset.id;
        const limit = selectElement.value;
        const bandwidthCell = selectElement.closest('.bandwidth-control-cell');
        if (!bandwidthCell || !clientId) return;

        if (customBandwidthTimers[clientId]) {
            clearTimeout(customBandwidthTimers[clientId]);
            delete customBandwidthTimers[clientId];
        }

        const customInputSpan = bandwidthCell.querySelector('.custom-bw-group');
        const autoInfoDiv = bandwidthCell.querySelector('.auto-bw-info');

        // Handle MANUAL mode
        if (limit === 'manual') {
            let customInput = bandwidthCell.querySelector('.custom-bw-input');

            // If this row came from AUTO mode, create manual input UI on the fly
            if (!customInput) {
                const manualGroup = document.createElement('span');
                manualGroup.className = 'custom-bw-group';
                manualGroup.style.marginLeft = '10px';
                manualGroup.innerHTML = `
                    <input type="number" class="custom-bw-input" data-id="${clientId}" value="50" min="1" max="500" style="width: 60px;">
                    <span>Mbps</span>
                `;
                const effectiveInfo = bandwidthCell.querySelector('.effective-bw-info');
                if (effectiveInfo) {
                    bandwidthCell.insertBefore(manualGroup, effectiveInfo);
                } else {
                    bandwidthCell.appendChild(manualGroup);
                }
                customInput = manualGroup.querySelector('.custom-bw-input');
            }

            // Show custom input field
            if (customInputSpan) {
                customInputSpan.classList.remove('hidden');
            }

            // Hide AUTO info
            if (autoInfoDiv) {
                autoInfoDiv.remove();
            }

            const parsedCustomValue = parseInt(customInput.value, 10);
            const customValue = Number.isFinite(parsedCustomValue)
                ? Math.min(500, Math.max(1, parsedCustomValue))
                : 50;
            customInput.value = customValue;
            saveBandwidthLimit(clientId, 'manual', customValue);
        }
        // Handle AUTO mode
        else if (limit === 'auto') {
            // Hide custom input
            if (customInputSpan) {
                customInputSpan.classList.add('hidden');
            }

            // Show loading state
            const existingAutoInfo = bandwidthCell.querySelector('.auto-bw-info');
            if (existingAutoInfo) {
                existingAutoInfo.innerHTML = 'Analyzing usage patterns...';
            } else {
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'auto-bw-info';
                loadingDiv.style.cssText = 'margin-top: 5px; font-size: 0.85em; color: #666;';
                loadingDiv.innerHTML = 'Analyzing usage patterns...';
                bandwidthCell.appendChild(loadingDiv);
            }

            // Call API to auto-assign bandwidth
            const token = localStorage.getItem('admin_token');
            if (!token) return alert('Please login as admin');

            selectElement.disabled = true;
            fetch(`/api/admin/bandwidth/auto-assign/${clientId}`, {
                method: 'POST',
                headers: { 'Authorization': 'Bearer ' + token }
            })
                .then(async res => {
                    const body = await res.json().catch(() => ({}));
                    if (!res.ok) {
                        throw new Error(body.message || 'Failed to auto-assign bandwidth');
                    }
                    return body;
                })
                .then(data => {
                    if (data.tier && data.confidence !== undefined) {
                        const confidencePercent = (data.confidence * 100).toFixed(0);
                        const recommendedMbps = data.recommended_mbps || getPresetMbps(data.tier);
                        const detectedActivity = data.detected_activity || 'General Browsing';
                        const autoInfo = bandwidthCell.querySelector('.auto-bw-info');
                        if (autoInfo) {
                            autoInfo.innerHTML = `Detected: <strong>${detectedActivity}</strong><br>Currently: <strong>${data.tier.toUpperCase()}</strong> (${recommendedMbps} Mbps, ${confidencePercent}% confidence)`;
                        }
                        console.log(`✅ AUTO bandwidth assigned: ${data.tier.toUpperCase()} (${data.explanation})`);
                        addLog('info', 'ADMIN', `Set bandwidth to AUTO mode - assigned: ${data.tier.toUpperCase()}`);

                        const applyWarning = getBandwidthApplyWarning(data);
                        if (applyWarning) {
                            console.warn('AUTO bandwidth apply warning:', applyWarning);
                            addLog('warn', 'ADMIN', `AUTO mode warning for ${clientId}: ${applyWarning}`);
                            alert(`AUTO assigned, but traffic shaping reported an issue:\n${applyWarning}`);
                        }

                        if (document.getElementById('bandwidth-page')) {
                            initBandwidth();
                        }
                    } else {
                        console.error('Invalid response from auto-assign endpoint');
                        alert('Failed to auto-assign bandwidth');
                    }
                })
                .catch(err => {
                    console.error('Error auto-assigning bandwidth:', err);
                    const autoInfo = bandwidthCell.querySelector('.auto-bw-info');
                    if (autoInfo) {
                        autoInfo.innerHTML = 'Error - fallback to MEDIUM';
                    }
                    alert(err.message || 'Error auto-assigning bandwidth');
                })
                .finally(() => {
                    selectElement.disabled = false;
                });
        }
        // Handle preset tiers (LOW, MEDIUM, HIGH)
        else {
            // Hide custom input
            if (customInputSpan) {
                customInputSpan.classList.add('hidden');
            }
            // Remove AUTO info if switching away from AUTO
            if (autoInfoDiv) {
                autoInfoDiv.remove();
            }

            saveBandwidthLimit(clientId, limit);
        }
    }

    // Save bandwidth limit to database
    function saveBandwidthLimit(clientId, limit, customValue = null) {
        const token = localStorage.getItem('admin_token');
        if (!token) return alert('Please login as admin');

        const payload = { bandwidth_limit: limit };

        // If manual mode, include custom value
        if (limit === 'manual') {
            const parsedCustomValue = parseInt(customValue, 10);
            payload.bandwidth_custom_value = Number.isFinite(parsedCustomValue)
                ? Math.min(500, Math.max(1, parsedCustomValue))
                : 50;
        }

        fetch(`/api/admin/clients/${clientId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify(payload)
        })
            .then(async res => {
                const responseData = await res.json().catch(() => ({}));
                if (res.ok) {
                    const displayValue = limit === 'manual' ? `${payload.bandwidth_custom_value} Mbps` : limit.toUpperCase();
                    console.log(`✅ Bandwidth limit saved: ${displayValue}`);
                    addLog('info', 'ADMIN', `Set bandwidth limit to ${displayValue}`);

                    const applyWarning = getBandwidthApplyWarning(responseData);
                    if (applyWarning) {
                        console.warn('Bandwidth apply warning:', applyWarning);
                        addLog('warn', 'ADMIN', `Bandwidth apply warning for ${clientId}: ${applyWarning}`);
                        alert(`Bandwidth was saved, but traffic shaping reported an issue:\n${applyWarning}`);
                    }

                    if (document.getElementById('bandwidth-page')) {
                        initBandwidth();
                    }
                } else {
                    console.error('Failed to save bandwidth limit', responseData);
                    alert(responseData.message || 'Failed to save bandwidth limit');
                }
            })
            .catch(err => {
                console.error('Error saving bandwidth:', err);
                alert('Error saving bandwidth limit');
            });
    }

    function handleCustomBandwidthInput(inputElement) {
        const clientId = inputElement.dataset.id;
        if (!clientId) return;

        if (customBandwidthTimers[clientId]) {
            clearTimeout(customBandwidthTimers[clientId]);
            delete customBandwidthTimers[clientId];
        }

        const customValue = parseInt(inputElement.value, 10);
        if (!Number.isFinite(customValue)) return;

        const normalizedValue = Math.min(500, Math.max(1, customValue));
        if (normalizedValue !== customValue) {
            inputElement.value = normalizedValue;
        }
        
        db.bandwidthLimits[clientId] = normalizedValue;

        customBandwidthTimers[clientId] = setTimeout(() => {
            saveBandwidthLimit(clientId, 'manual', normalizedValue);
        }, 700);
    }

    function handleGenerateVouchers() {
        let newVouchers = [];
        for (let i = 0; i < 5; i++) {
            const code = `GUEST-${Math.random().toString(36).substr(2, 4).toUpperCase()}`;
            newVouchers.push({ id: db.guestVouchers.length + i + 1, code: code, duration: "24 hours", status: "Unused" });
        }
        db.guestVouchers = [...newVouchers, ...db.guestVouchers];
        initGuestNetwork();
        addLog('info', 'ADMIN', 'Generated 5 new guest vouchers');
    }

    function handleGuestToggle(checkbox) {
        const isChecked = checkbox.checked;
        db.guestNetworkEnabled = isChecked;
        const statusText = document.getElementById('guest-status-text');
        if (statusText) {
            statusText.textContent = isChecked ? 'Enabled' : 'Disabled';
        }
        if (isChecked) {
            addLog('info', 'ADMIN', 'Guest Network Enabled');
        } else {
            addLog('warn', 'ADMIN', 'Guest Network Disabled');
        }
    }

    function handleReportRangeChange(selectElement) {
        if (!selectElement) return;
        const value = selectElement.value;
        const dateGroup = document.getElementById('date-picker-group');
        const dateLabel = document.getElementById('date-picker-label');
        const dateDaily = document.getElementById('report-date-daily');
        const dateWeekly = document.getElementById('report-date-weekly');
        const dateMonthly = document.getElementById('report-date-monthly');

        if (!dateGroup || !dateLabel || !dateDaily || !dateWeekly || !dateMonthly) return;

        if (value === 'daily') {
            dateGroup.classList.remove('hidden');
            dateLabel.textContent = 'Select Date';
            dateDaily.classList.remove('hidden');
            dateWeekly.classList.add('hidden');
            dateMonthly.classList.add('hidden');
        } else if (value === 'weekly') {
            dateGroup.classList.remove('hidden');
            dateLabel.textContent = 'Select Week';
            dateDaily.classList.add('hidden');
            dateWeekly.classList.remove('hidden');
            dateMonthly.classList.add('hidden');
        } else { // monthly
            dateGroup.classList.remove('hidden');
            dateLabel.textContent = 'Select Month';
            dateDaily.classList.add('hidden');
            dateWeekly.classList.add('hidden');
            dateMonthly.classList.remove('hidden');
        }
    }

    // --- NEW: Download Report Function ---
    function handleDownloadReport(button) {
        const format = button.dataset.format;
        const title = button.dataset.title;
        const filename = title.replace(/ /g, '_');

        const table = button.closest('.report-result-card').querySelector('table');

        const headers = [...table.querySelectorAll('thead th')].map(th => th.textContent);
        const data = [...table.querySelectorAll('tbody tr')].map(tr => {
            return [...tr.querySelectorAll('td')].map(td => td.textContent);
        });

        if (format === 'PDF') {
            downloadPDF(filename, title, headers, data);
        } else { // CSV
            downloadCSV(filename, headers, data);
        }
    }

    // ─── URL / Domain Utility Functions ────────────────────────────────────────

    function normalizeDomain(url) {
        let value = (url || '').trim().toLowerCase();
        if (!value) return '';

        if (value.includes('://')) {
            value = value.split('://', 2)[1];
        }
        if (value.startsWith('//')) {
            value = value.slice(2);
        }

        value = value.split('/')[0].split('?')[0].split('#')[0];

        if (value.includes('@')) {
            value = value.split('@').pop();
        }

        const colonIndex = value.lastIndexOf(':');
        if (colonIndex > -1) {
            const maybePort = value.slice(colonIndex + 1);
            if (/^[0-9]+$/.test(maybePort)) {
                value = value.slice(0, colonIndex);
            }
        }

        if (value.startsWith('www.')) {
            value = value.slice(4);
        }

        return value.replace(/^\.+|\.+$/g, '');
    }

    function isSiteBlocked(testUrl, blockedSitesSet) {
        const domain = normalizeDomain(testUrl);
        if (!blockedSitesSet || blockedSitesSet.size === 0 || !domain) return false;
        if (blockedSitesSet.has(domain)) return true;
        return [...blockedSitesSet].some(stored => domain.endsWith('.' + stored));
    }

    /**
     * Show an inline error message under the block-site form.
     */
    function showFilteringError(msg) {
        let errEl = document.getElementById('filtering-error-msg');
        if (!errEl) {
            const form = document.getElementById('website-block-form');
            if (!form) return;
            errEl = document.createElement('p');
            errEl.id = 'filtering-error-msg';
            errEl.style.cssText = 'color:#ef4444;margin:6px 0 0;font-size:0.88em;';
            form.after(errEl);
        }
        errEl.textContent = msg;
        errEl.style.display = 'block';
        clearTimeout(errEl._hideTimer);
        errEl._hideTimer = setTimeout(() => { errEl.style.display = 'none'; }, 4000);
    }

    // ─── Utility Functions ──────────────────────────────────────────────────────

    /**
     * Add a blocked entry to the UI list.
     * @param {string} siteOrUrl  - The domain stored in DB or a category site URL
     * @param {boolean} isCategorySite - If true, this is a read-only category-controlled entry
     * @param {string|false} categoryName - Name of the category if isCategorySite
     * @param {boolean} prepend - Insert at top of list instead of bottom
     */
    function addBlockedSiteToDOM(siteOrUrl, isCategorySite = false, categoryName = false, prepend = false) {
        const blockedSitesList = document.getElementById('blocked-sites-list');
        if (!blockedSitesList) return;

        const li = document.createElement('li');
        li.style.cssText = 'display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 4px;border-bottom:1px solid var(--border,#e5e7eb);transition:opacity 0.2s;';

        const display = normalizeDomain(siteOrUrl) || String(siteOrUrl || '').trim().toLowerCase();

        if (isCategorySite) {
            // Category-controlled site — display-only
            li.innerHTML = `
                <span style="flex:1;">
                    <strong>${display}</strong>
                    <small style="margin-left:6px;color:var(--text-secondary);">📂 ${categoryName || 'Category'}</small>
                </span>`;
        } else {
            // Manually added domain — store in data attribute for removal
            li.dataset.site = display;
            li.innerHTML = `
                <span style="flex:1;">
                    <strong style="font-family:monospace;">${display}</strong>
                    <small style="margin-left:8px;color:var(--text-secondary);font-size:0.8em;">🔒 Blocks ${display} and subdomains</small>
                </span>
                <button class="btn btn-remove" title="Remove block" style="flex-shrink:0;">
                    <i class="fa-solid fa-trash"></i>
                </button>`;
        }

        if (prepend) {
            blockedSitesList.prepend(li);
        } else {
            blockedSitesList.appendChild(li);
        }
    }

    function addLog(level, user, action) {
        const time = new Date().toLocaleTimeString('en-US', { hour12: true });
        const ip = db.clients.find(c => c.studentId === user)?.ip;
        db.logs.unshift({ time, level, user, ip, action });
        if (db.logs.length > 100) db.logs.pop();
        if (level === 'warn' || level === 'error') {
            addNotification(level, `${user}: ${action}`);
        }
        if (document.getElementById('log-page')) initLogs();
        if (document.getElementById('dashboard-page')) initDashboard();
    }

    function addNotification(level, message) {
        notificationBadge.classList.remove('hidden');
        if (notificationList.querySelector('.empty-state')) {
            notificationList.innerHTML = '';
        }
        const li = document.createElement('li');
        li.innerHTML = `<strong class="level-${level}">${level.toUpperCase()}</strong>: ${message}`;
        notificationList.prepend(li);
        if (notificationList.children.length > 5) {
            notificationList.removeChild(notificationList.lastChild);
        }
    }

    function initNotificationTray() {
        notificationList.innerHTML = '';
        const importantLogs = db.logs.filter(log => log.level === 'warn' || log.level === 'error').slice(0, 5);
        if (importantLogs.length === 0) {
            notificationList.innerHTML = '<li class="empty-state">No new notifications</li>';
        } else {
            importantLogs.forEach(log => {
                const li = document.createElement('li');
                li.innerHTML = `<strong class="level-${log.level}">${log.level.toUpperCase()}</strong>: ${log.user}: ${log.action}`;
                notificationList.appendChild(li);
            });
        }
    }

    function generateReportData(type, range) {
        let headers = [];
        let data = [];

        switch (type) {
            case 'Top Bandwidth Users':
                headers = ['Rank', 'Student ID', 'Device', 'Data Used (GB)'];
                data = [...db.clients]
                    .filter(c => c.studentId !== 'ADMIN')
                    .sort((a, b) => b.data - a.data)
                    .slice(0, 5)
                    .map((client, index) => [
                        `#${index + 1}`,
                        client.studentId,
                        client.device,
                        `${client.data} GB`
                    ]);
                break;
            case 'Blocked Site Activity':
                headers = ['Website', 'Category', 'Attempts (Simulated)'];
                let allBlocked = [...db.blockedSites];
                Object.keys(db.siteCategories).forEach(key => {
                    if (db.siteCategories[key].active) {
                        db.siteCategories[key].sites.forEach(site => {
                            if (!allBlocked.includes(site)) allBlocked.push(site);
                        });
                    }
                });
                data = allBlocked.map(site => [
                    site,
                    Object.keys(db.siteCategories).find(key => db.siteCategories[key].sites.includes(site)) || 'Manual',
                    Math.floor(Math.random() * 500) + 50
                ]).sort((a, b) => b[2] - a[2]);
                break;
            case 'Full Network Audit':
                headers = ['Time', 'Level', 'User', 'Action'];
                data = db.logs.slice(0, 20).map(log => [
                    log.time,
                    log.level.toUpperCase(),
                    log.user,
                    log.action
                ]);
                break;
        }
        return { headers, data };
    }

    function renderReport(title, headers, data, format) {
        const resultsArea = document.getElementById('report-results-area');
        if (!resultsArea) return;

        let tableHTML = `<table class="client-table"><thead><tr>`;
        headers.forEach(h => tableHTML += `<th>${h}</th>`);
        tableHTML += `</tr></thead><tbody>`;

        data.forEach(row => {
            tableHTML += `<tr>`;
            row.forEach(cell => tableHTML += `<td>${cell}</td>`);
            tableHTML += `</tr>`;
        });
        tableHTML += `</tbody></table></div>`;

        const card = document.createElement('div');
        card.className = 'card report-result-card';
        card.innerHTML = `
            <div class="report-result-header">
                <h3>${title}</h3>
                <button class="btn btn-success btn-download-report" data-format="${format}" data-title="${title.replace(/ /g, '_')}">
                    <i class="fa-solid fa-download"></i> Download ${format === 'CSV' ? 'Excel (.csv)' : 'PDF'}
                </button>
            </div>
            <div style="overflow-x: auto;">
                ${tableHTML}
            </div>
        `;

        resultsArea.prepend(card);
    }

    // --- MODIFIED: This function is now fixed ---
    function downloadCSV(filename, headers, data) {
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += headers.map(cell => `"${cell.replace(/"/g, '""')}"`).join(",") + "\r\n";
        data.forEach(rowArray => {
            let row = rowArray.map(cell => `"${cell.toString().replace(/"/g, '""')}"`).join(",");
            csvContent += row + "\r\n";
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `${filename}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function downloadPDF(filename, title, headers, data) {
        try {
            const { jsPDF } = window.jspdf;
            const doc = new jsPDF();

            doc.text(title.replace(/_/g, ' '), 14, 20);
            doc.autoTable({
                head: [headers],
                body: data,
                startY: 25,
            });

            doc.save(`${filename}.pdf`);
        } catch (e) {
            console.error(e);
            alert("Error: Could not generate PDF. jsPDF library may not be loaded.");
        }
    }

    /**
     * Ensure the clients table exists inside the clients page fragment.
     * Returns the <tbody> element to populate.
     * Only works on the clients page, returns null for other pages.
     */
    function ensureClientsTableBody() {
        // Try common ids first
        let tbody = document.getElementById('clients-table-body') || document.getElementById('client-list-body');
        if (tbody) return tbody;

        // Find the clients page container in the DOM - ONLY create on clients page
        const clientsSection = document.getElementById('clients-page') || document.querySelector('.page#clients-page');
        if (!clientsSection) return null;  // Don't create table on non-clients pages

        const container = clientsSection;

        // Create table markup and append
        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
          <h3>All Connected Clients</h3>
          <div class="table-responsive">
            <table class="clients-table">
              <thead>
                <tr>
                  <th>STUDENT / DEVICE</th>
                  <th>IP ADDRESS</th>
                  <th>DATA USAGE (24H)</th>
                  <th>CURRENT ACTIVITY (SIMULATED)</th>
                  <th>STATUS</th>
                  <th>ACTION</th>
                </tr>
              </thead>
              <tbody id="clients-table-body"></tbody>
            </table>
          </div>
        `;
        container.appendChild(wrapper);
        return document.getElementById('clients-table-body');
    }

    // make function global (existing loadClientsData implementation may be present)
    window.loadClientsData = async function loadClientsData() {
        const tbody = ensureClientsTableBody();
        if (!tbody) return console.warn('unable to create/find clients table body');

        const token = localStorage.getItem('admin_token');
        if (!token) {
            console.warn('No admin token found; will retry in 2s');
            setTimeout(loadClientsData, 2000);
            return;
        }

        try {
            const res = await fetch('/api/admin/clients', {
                headers: { 'Authorization': 'Bearer ' + token }
            });
            if (!res.ok) return console.error('Failed to fetch clients', res.status);
            const { clients } = await res.json();
            if (!Array.isArray(clients)) return console.warn('Invalid clients response', clients);

            tbody.innerHTML = '';
            clients.forEach(c => {
                const tr = document.createElement('tr');

                // Determine status display
                let statusHtml = '<span class="status-offline">Offline</span>';
                if (c.status) {
                    if (c.status.includes('Blocked')) {
                        statusHtml = `<span class="status-blocked">${c.status}</span>`;
                    } else if (c.status === 'Online') {
                        statusHtml = '<span class="status-online">Online</span>';
                    } else if (c.status === 'Offline') {
                        statusHtml = '<span class="status-offline">Offline</span>';
                    } else if (c.status === 'Active') {
                        statusHtml = '<span class="status-active">Active</span>';
                    } else {
                        statusHtml = `<span class="status-active">${c.status}</span>`;
                    }
                } else if (c.blocked) {
                    statusHtml = '<span class="status-blocked">Blocked</span>';
                }

                tr.innerHTML = `
                    <td>${(c.roll_no || c.name || 'N/A')}</td>
                    <td>${c.ip_address || c.ip || 'N/A'}</td>
                    <td>${c.data_usage || c.data ? (c.data_usage || c.data) + ' GB' : '0 GB'}</td>
                    <td>${c.activity || 'Idle'}</td>
                    <td>${statusHtml}</td>
                    <td>
                        <button class="btn-edit" onclick="editClient('${c._id}')">Edit</button>
                        <button onclick="toggleBlock('${c._id}', ${c.blocked === true})">${c.blocked ? 'Unblock' : 'Block'}</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            console.log('Table populated with', clients.length, 'clients');
        } catch (err) {
            console.error('Error loading clients:', err);
        }
    };

    // --- Initial Load ---
    loadPage('dashboard');
    initNotificationTray();

    // Fetch real admin stats & clients/logs from backend if admin token is present
    fetchAndApplyAdminData().catch(err => console.warn("Admin fetch failed:", err));
});

async function fetchAndApplyAdminData() {
    const token = localStorage.getItem("admin_token");
    if (!token) return; // not logged in as admin

    const headers = { "Authorization": "Bearer " + token };

    try {
        const [statsRes, clientsRes, logsRes] = await Promise.all([
            fetch("/api/admin/stats", { headers }),
            fetch("/api/admin/clients", { headers }),
            fetch("/api/admin/logs", { headers })
        ]);

        if (statsRes.ok) {
            const stats = await statsRes.json();
            const clientCountElement = document.getElementById("client-count");
            if (clientCountElement && typeof stats.client_count !== 'undefined') {
                clientCountElement.textContent = stats.client_count;
            }
            const dataCountElement = document.getElementById("data-count");
            if (dataCountElement && typeof stats.total_data !== 'undefined') {
                dataCountElement.textContent = `${stats.total_data} GB`;
            }
            const threatCountElement = document.getElementById("threat-count");
            if (threatCountElement && typeof stats.threats_blocked !== 'undefined') {
                threatCountElement.textContent = stats.threats_blocked;
            }
        }

        if (clientsRes.ok) {
            const clientsJson = await clientsRes.json();
            const clients = Array.isArray(clientsJson.clients) ? clientsJson.clients : clientsJson;
            const tbody = document.getElementById('clients-table-body') || document.getElementById('client-list-body');
            if (tbody) {
                tbody.innerHTML = '';
                clients.forEach(c => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${(c.roll_no || c.name || 'N/A')}</td>
                        <td>${c.ip || 'N/A'}</td>
                        <td>${c.data ? c.data + ' GB' : '0 GB'}</td>
                        <td>${c.activity || 'Idle'}</td>
                        <td>${c.blocked ? '<span class="status-blocked">Blocked</span>' : '<span class="status-active">Active</span>'}</td>
                        <td>
                            <button class="btn-edit" onclick="editClient('${c._id || c.id}')">Edit</button>
                            <button onclick="toggleBlock('${c._id || c.id}', ${c.blocked === true})">${c.blocked ? 'Unblock' : 'Block'}</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }

        if (logsRes.ok) {
            const logsJson = await logsRes.json();
            const logs = Array.isArray(logsJson.logs) ? logsJson.logs : logsJson;
            const logBody = document.getElementById('log-body') || document.getElementById('event-log-body');
            if (logBody) {
                logBody.innerHTML = '';
                logs.slice(0, 50).forEach(log => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `<td>${log.time || ''}</td><td><span class="log-level-${log.level || 'info'}">${(log.level || '').toUpperCase()}</span></td><td>${log.user || ''}</td><td>${log.action || ''}</td>`;
                    logBody.appendChild(tr);
                });
            }
        }
    } catch (err) {
        console.warn("fetchAndApplyAdminData error:", err);
    }
}

/**
 * Safely load an HTML fragment into container. Tries two relative paths and never leaves a visible error box.
 * Usage: safeLoadFragment('pages/clients.html', '#page-content')
 */
async function safeLoadFragment(fragmentPath, containerSelector) {
    const container = document.querySelector(containerSelector || '#content-area') || document.getElementById('content-area') || document.body;
    // hide any visible error card
    const errEl = document.querySelector('.page-load-error, .fragment-error');
    if (errEl) errEl.style.display = 'none';

    // Try a few sensible relative paths (most robust)
    const candidates = [
        fragmentPath,
        './' + fragmentPath,
        fragmentPath.replace(/^\.\//, ''),
        (fragmentPath.startsWith('pages/') ? fragmentPath : 'pages/' + fragmentPath),
        './pages/' + fragmentPath.replace(/^pages\//, '')
    ].map(p => p.replace(/\/+/g, '/')); // normalize

    for (const p of candidates) {
        try {
            console.debug('safeLoadFragment: trying', p);
            const r = await fetch(p, { cache: 'no-store' });
            if (!r.ok) {
                console.debug(`safeLoadFragment: ${p} returned ${r.status}`);
                continue;
            }
            const html = await r.text();
            container.innerHTML = html;

            // Execute inline scripts inside the fetched HTML (best-effort)
            const tmp = document.createElement('div');
            tmp.innerHTML = html;
            tmp.querySelectorAll('script').forEach(s => {
                if (!s.src) {
                    try { new Function(s.textContent)(); } catch (e) { console.error('fragment inline script error', e); }
                } else {
                    // Optionally load external scripts if necessary
                    const ext = document.createElement('script');
                    ext.src = s.src;
                    document.head.appendChild(ext);
                }
            });

            console.info('safeLoadFragment: loaded', p);
            return true;
        } catch (err) {
            console.warn('safeLoadFragment fetch error for', p, err);
        }
    }

    console.warn('safeLoadFragment: could not load any candidate for', fragmentPath, 'tried', candidates);
    return false;
}

// Example: replace direct fragment loads with safeLoadFragment calls
document.addEventListener('DOMContentLoaded', () => {
    // ...existing init...
    // when loading the clients/dashboard fragments use:
    // safeLoadFragment('pages/clients.html', '#page-content');
    // safeLoadFragment('pages/dashboard.html', '#page-content');
});

// Ensure global editClient exists for inline onclick usage
window.editClient = function (id) {
    openEditModal(String(id));
};

// Add this near the top of admin.js (before initDashboard uses it)
function renderTrafficChart(ctx, chartData) {
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded.');
        return null;
    }

    // destroy previous chart if present
    if (window.myTrafficChart && typeof window.myTrafficChart.destroy === 'function') {
        window.myTrafficChart.destroy();
    }

    // If caller did not pass chartData, make a small fallback dataset
    if (!chartData) {
        const labels = Array.from({ length: 8 }, (_, i) => {
            const d = new Date(Date.now() - (7 - i) * 2000);
            return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
        });
        chartData = {
            labels,
            datasets: [
                {
                    label: 'Download (KB/s)',
                    backgroundColor: 'rgba(54,162,235,0.2)',
                    borderColor: 'rgba(54,162,235,1)',
                    data: labels.map(() => 0),
                    fill: true
                },
                {
                    label: 'Upload (KB/s)',
                    backgroundColor: 'rgba(255,99,132,0.1)',
                    borderColor: 'rgba(255,99,132,1)',
                    data: labels.map(() => 0),
                    fill: true
                }
            ]
        };
    }

    const chartInstance = new Chart(ctx, {
        type: 'line',
        data: chartData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            stacked: false,
            plugins: {
                legend: { position: 'top' }
            },
            scales: {
                x: { display: true },
                y: { display: true, beginAtZero: true }
            }
        }
    });

    window.myTrafficChart = chartInstance;
    return chartInstance;
}

// ========== CSV UPLOAD FUNCTIONALITY - SIMPLE VERSION ==========
window.csvInitialized = false;

function initCSVUpload() {
    console.log('CSV Upload: Initializing...');

    const csvModal = document.getElementById('csv-modal');
    const openModalBtn = document.getElementById('open-csv-modal');

    console.log('CSV Elements:', {
        modal: !!csvModal,
        button: !!openModalBtn
    });

    if (!csvModal || !openModalBtn) {
        console.log('CSV elements not found yet');
        return false;
    }

    // Check if already initialized
    if (window.csvInitialized) {
        console.log('CSV already initialized, skipping...');
        return true;
    }

    console.log('CSV elements found! Setting up...');

    const closeModalBtn = document.getElementById('close-csv-modal');
    const cancelBtn = document.getElementById('cancel-upload');
    const submitBtn = document.getElementById('submit-upload');
    const fileInput = document.getElementById('csv-file-input');
    const browseBtn = document.getElementById('browse-btn');
    const dropArea = document.getElementById('drop-area');
    const fileName = document.getElementById('file-name');
    const resultMessage = document.getElementById('result-message');
    const uploadLoading = document.getElementById('upload-loading');
    const downloadTemplate = document.getElementById('download-template');

    let selectedFile = null;

    // IMPORTANT: Use onclick instead of addEventListener
    openModalBtn.onclick = function (e) {
        console.log('===== CSV BUTTON CLICKED! =====');
        e.preventDefault();
        e.stopPropagation();
        csvModal.style.display = 'flex';
        resetUploadForm();
        console.log('Modal should be visible now');
    };

    console.log('Button onclick handler attached');

    // Close modal handlers
    if (closeModalBtn) {
        closeModalBtn.onclick = function () {
            console.log('Close button clicked');
            csvModal.style.display = 'none';
        };
    }

    if (cancelBtn) {
        cancelBtn.onclick = function () {
            console.log('Cancel button clicked');
            csvModal.style.display = 'none';
        };
    }

    csvModal.onclick = function (e) {
        if (e.target === csvModal) {
            console.log('Modal overlay clicked');
            csvModal.style.display = 'none';
        }
    };

    // Browse button
    if (browseBtn && fileInput) {
        browseBtn.onclick = function () {
            console.log('Browse button clicked');
            fileInput.click();
        };
    }

    // File input change
    if (fileInput) {
        fileInput.onchange = function (e) {
            console.log('File selected:', e.target.files[0]);
            handleFileSelect(e.target.files[0]);
        };
    }

    // Drag and drop
    if (dropArea) {
        dropArea.ondragover = function (e) {
            e.preventDefault();
            dropArea.style.borderColor = '#007bff';
            dropArea.style.backgroundColor = '#e7f3ff';
        };

        dropArea.ondragleave = function () {
            dropArea.style.borderColor = '#007bff';
            dropArea.style.backgroundColor = 'transparent';
        };

        dropArea.ondrop = function (e) {
            e.preventDefault();
            console.log('File dropped');
            dropArea.style.borderColor = '#007bff';
            dropArea.style.backgroundColor = 'transparent';
            handleFileSelect(e.dataTransfer.files[0]);
        };
    }

    function handleFileSelect(file) {
        console.log('Handling file:', file);
        if (!file) return;

        const validTypes = ['.csv', '.xlsx', '.xls'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();

        if (!validTypes.includes(fileExtension)) {
            showResult('error', '❌ Invalid file format. Please upload CSV or Excel file.');
            return;
        }

        selectedFile = file;
        if (fileName) {
            fileName.textContent = `✅ Selected: ${file.name}`;
            fileName.style.color = '#28a745';
        }
        if (submitBtn) submitBtn.disabled = false;
        if (resultMessage) resultMessage.style.display = 'none';
        console.log('File ready:', file.name);
    }

    // Submit upload
    if (submitBtn) {
        submitBtn.onclick = async function () {
            console.log('Submit button clicked');
            if (!selectedFile) {
                console.log('No file selected');
                return;
            }

            const token = localStorage.getItem('admin_token');
            if (!token) {
                alert('Please log in as admin');
                return;
            }

            const formData = new FormData();
            formData.append('file', selectedFile);

            if (uploadLoading) uploadLoading.style.display = 'block';
            submitBtn.disabled = true;
            if (resultMessage) resultMessage.style.display = 'none';

            try {
                console.log('Sending upload request...');
                const response = await fetch('/api/admin/bulk-upload', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + token
                    },
                    body: formData
                });

                const data = await response.json();
                console.log('Upload response:', data);

                if (response.ok) {
                    let message = `✅ Upload completed!\n\n`;
                    message += `• Added: ${data.added} students\n`;
                    message += `• Skipped: ${data.skipped} students\n`;

                    if (data.errors && data.errors.length > 0) {
                        message += `\n⚠️ Errors:\n${data.errors.join('\n')}`;
                    }

                    showResult('success', message);

                    setTimeout(() => {
                        if (typeof loadClientsData === 'function') {
                            loadClientsData();
                        }
                    }, 2000);
                } else {
                    showResult('error', `❌ ${data.error || 'Upload failed'}`);
                }
            } catch (error) {
                console.error('Upload error:', error);
                showResult('error', '❌ Network error: ' + error.message);
            } finally {
                if (uploadLoading) uploadLoading.style.display = 'none';
                submitBtn.disabled = false;
            }
        };
    }

    function showResult(type, message) {
        if (!resultMessage) return;

        resultMessage.className = `result-message ${type}`;
        resultMessage.textContent = message;
        resultMessage.style.display = 'block';
        resultMessage.style.padding = '15px';
        resultMessage.style.borderRadius = '6px';
        resultMessage.style.marginTop = '15px';
        resultMessage.style.whiteSpace = 'pre-line';

        if (type === 'success') {
            resultMessage.style.backgroundColor = '#d4edda';
            resultMessage.style.color = '#155724';
            resultMessage.style.border = '1px solid #c3e6cb';
        } else {
            resultMessage.style.backgroundColor = '#f8d7da';
            resultMessage.style.color = '#721c24';
            resultMessage.style.border = '1px solid #f5c6cb';
        }
    }

    function resetUploadForm() {
        console.log('Resetting form');
        selectedFile = null;
        if (fileInput) fileInput.value = '';
        if (fileName) fileName.textContent = '';
        if (submitBtn) submitBtn.disabled = true;
        if (resultMessage) resultMessage.style.display = 'none';
        if (uploadLoading) uploadLoading.style.display = 'none';
    }

    // Download template
    if (downloadTemplate) {
        downloadTemplate.onclick = function (e) {
            e.preventDefault();
            console.log('Downloading template');
            const csvContent = "roll_number,password\n23203A0027,password123\n23203A0038,password456\n23203A0045,password789";
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'student_template.csv';
            a.click();
            window.URL.revokeObjectURL(url);
        };
    }

    window.csvInitialized = true;
    console.log('✅ CSV Upload initialized successfully!');
    return true;
}

// Retry mechanism
let csvRetries = 0;
function tryInitCSV() {
    if (initCSVUpload()) {
        console.log('✅ CSV Upload ready!');
        return;
    }

    csvRetries++;
    if (csvRetries < 15) {
        setTimeout(tryInitCSV, 500);
    }
}

// Try on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', tryInitCSV);
} else {
    tryInitCSV();
}

// Watch for clients page
const csvObserver = new MutationObserver(function (mutations) {
    const clientsPage = document.getElementById('clients-page');
    if (clientsPage && !window.csvInitialized) {
        console.log('📄 Clients page detected');
        setTimeout(tryInitCSV, 200);
    }
});

csvObserver.observe(document.body, {
    childList: true,
    subtree: true
});

console.log('🔄 CSV Upload module loaded');
