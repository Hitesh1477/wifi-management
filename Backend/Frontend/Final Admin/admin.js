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
    let myTrafficChart;
    let trafficInterval;

    // --- Page Loading Logic ---
    async function loadPage(pageName) {
        if (trafficInterval) clearInterval(trafficInterval);
        if (myTrafficChart) myTrafficChart.destroy();

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

    // --- Page Initializers (These run after a page is loaded) ---

    function initDashboard() {
        const clientCountElement = document.getElementById("client-count");
        if (clientCountElement) {
            clientCountElement.textContent = db.clients.filter(c => !c.blocked).length;
        }
        const dataCountElement = document.getElementById("data-count");
        if (dataCountElement) {
            dataCountElement.textContent = `${db.totalData.toFixed(1)} GB`;
        }
        const threatCountElement = document.getElementById("threat-count");
        if (threatCountElement) {
            threatCountElement.textContent = db.threatsBlocked;
        }

        const logBody = document.getElementById("event-log-body");
        if (logBody) {
            logBody.innerHTML = "";
            db.logs.slice(0, 5).forEach(log => {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td>${log.time}</td><td><span class="log-level-${log.level}">${log.level.toUpperCase()}</span></td><td>${log.user}</td><td>${log.action}</td>`;
                logBody.appendChild(tr);
            });
        }

        const canvas = document.getElementById('traffic-chart-canvas');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            renderTrafficChart(ctx, /* your chartData */);
        }

        trafficInterval = setInterval(() => {
            const newDownload = Math.floor(Math.random() * 400) + 100;
            const newUpload = Math.floor(Math.random() * 50) + 30;
            const newLabel = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            if (myTrafficChart) {
                myTrafficChart.data.labels.push(newLabel);
                myTrafficChart.data.datasets[0].data.push(newDownload);
                myTrafficChart.data.datasets[1].data.push(newUpload);
                myTrafficChart.data.labels.shift();
                myTrafficChart.data.datasets[0].data.shift();
                myTrafficChart.data.datasets[1].data.shift();
                myTrafficChart.update();
            }

            db.totalData += Math.random() * 0.5;
            if (dataCountElement) {
                dataCountElement.textContent = `${db.totalData.toFixed(1)} GB`;
            }

            if (Math.random() < 0.3) {
                db.threatsBlocked++;
                if (threatCountElement) {
                    threatCountElement.textContent = db.threatsBlocked;
                }
                const randomUser = db.clients[Math.floor(Math.random() * db.clients.length)];
                addLog('error', randomUser.studentId, 'Blocked access to Proxy/VPN');
            }
        }, 2000);
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

    function initWebFiltering() {
        const blockedSitesList = document.getElementById("blocked-sites-list");
        if (!blockedSitesList) return;

        blockedSitesList.innerHTML = "<li>Loading...</li>";
        const categories = document.getElementById("filter-categories");
        categories.innerHTML = "Loading...";

        const token = localStorage.getItem('admin_token');
        if (!token) return;

        fetch('/api/admin/filtering', { headers: { 'Authorization': 'Bearer ' + token } })
            .then(res => res.json())
            .then(data => {
                // 1. Manual Blocks
                db.blockedSites = data.manual_blocks || [];
                blockedSitesList.innerHTML = "";
                db.blockedSites.forEach(url => addBlockedSiteToDOM(url, false));

                // 2. Categories
                db.siteCategories = data.categories || {};

                // Show category sites if active (optional visualization)
                Object.keys(db.siteCategories).forEach(key => {
                    if (db.siteCategories[key].active) {
                        db.siteCategories[key].sites.forEach(site => {
                            if (!db.blockedSites.includes(site)) addBlockedSiteToDOM(site, true);
                        });
                    }
                });

                categories.innerHTML = "";
                Object.keys(db.siteCategories).forEach(key => {
                    const btn = document.createElement("button");
                    btn.className = `filter-toggle ${db.siteCategories[key].active ? 'active' : ''}`;
                    btn.textContent = key;
                    btn.dataset.category = key;
                    categories.appendChild(btn);
                });
            })
            .catch(err => {
                console.error("Error loading filtering:", err);
                blockedSitesList.innerHTML = "<li>Error loading data</li>";
            });
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
            .then(res => res.json())
            .then(data => {
                const clients = data.clients || [];
                bandwidthListBody.innerHTML = "";

                if (clients.length === 0) {
                    bandwidthListBody.innerHTML = "<tr><td colspan='5'>No students registered yet</td></tr>";
                    return;
                }

                clients.forEach(client => {
                    if (client.role === 'admin') return;

                    const clientId = client._id || client.id;
                    const limit = client.bandwidth_limit || 'standard';
                    const isCustom = typeof limit === 'number';
                    const dataUsage = client.data_usage || '0';
                    const activity = client.activity || 'Idle';

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
                    row.innerHTML = `
                    <td>${client.roll_no || client.name || 'Unknown'}</td>
                    <td>${dataUsage} GB</td>
                    <td>${activity}</td>
                    <td style="text-align: center;">${statusHtml}</td>
                    <td>
                        <div class="bandwidth-control-cell">
                            <select class="limit-select" data-id="${clientId}">
                                <option value="vlow" ${limit === 'vlow' ? 'selected' : ''}>Very Low (2 Mbps)</option>
                                <option value="low" ${limit === 'low' ? 'selected' : ''}>Low (10 Mbps)</option>
                                <option value="standard" ${!limit || limit === 'standard' ? 'selected' : ''}>Standard (25 Mbps)</option>
                                <option value="high" ${limit === 'high' ? 'selected' : ''}>High (100 Mbps)</option>
                                <option value="unlimited" ${limit === 'unlimited' ? 'selected' : ''}>Unlimited</option>
                                <option value="custom" ${isCustom ? 'selected' : ''}>Manual...</option>
                            </select>
                            <span class="custom-bw-group ${isCustom ? '' : 'hidden'}">
                                <input type="number" class="custom-bw-input" data-id="${clientId}" value="${isCustom ? limit : '50'}" min="1">
                                <span>Mbps</span>
                            </span>
                        </div>
                    </td>
                `;
                    bandwidthListBody.appendChild(row);
                });
            })
            .catch(err => {
                console.error('Error fetching clients:', err);
                bandwidthListBody.innerHTML = "<tr><td colspan='5'>Error loading clients</td></tr>";
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

    function initSettings() {
        // Placeholder
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

        if (e.target.closest('.btn-remove')) {
            handleRemoveSite(e.target);
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
            const url = websiteInput.value.trim();
            const token = localStorage.getItem('admin_token');

            if (url && token) {
                fetch('/api/admin/filtering/sites', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                    body: JSON.stringify({ url })
                })
                    .then(async res => {
                        const data = await res.json();
                        if (res.ok) {
                            addLog('warn', 'ADMIN', `Manually blocked site: ${url}`);
                            websiteInput.value = "";
                            initWebFiltering(); // Reload to show update
                        } else if (res.status === 409) {
                            alert('This site is already in the manual block list.');
                        } else {
                            alert(data.message || 'Error blocking site');
                        }
                    })
                    .catch(err => console.error(err));
            }
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
        const li = button.closest("li");
        const url = li.querySelector("span").textContent;
        const token = localStorage.getItem('admin_token');

        let isInCategory = false;
        if (db.siteCategories) {
            Object.keys(db.siteCategories).forEach(key => {
                if (db.siteCategories[key].active && db.siteCategories[key].sites.includes(url)) isInCategory = true;
            });
        }

        if (isInCategory) {
            alert(`Cannot manually remove ${url}. It is part of an active blocked category. Disable the category first.`);
            return;
        }

        if (token) {
            fetch('/api/admin/filtering/sites', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                body: JSON.stringify({ url })
            })
                .then(res => {
                    if (res.ok) {
                        addLog('info', 'ADMIN', `Removed ${url} from block list`);
                        initWebFiltering(); // Reload
                    } else {
                        alert('Failed to remove block');
                    }
                })
                .catch(err => console.error(err));
        }
    }

    function handleCategoryToggle(button) {
        const category = button.dataset.category;
        const token = localStorage.getItem('admin_token');

        if (token) {
            fetch('/api/admin/filtering/categories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
                body: JSON.stringify({ category })
            })
                .then(async res => {
                    const data = await res.json();
                    if (res.ok) {
                        if (data.active) {
                            addLog('warn', 'ADMIN', `Enabled category block: ${category}`);
                        } else {
                            addLog('info', 'ADMIN', `Disabled category block: ${category}`);
                        }
                        initWebFiltering(); // Reload
                    }
                })
                .catch(err => console.error(err));
        }
    }

    function handleReboot(location) {
        if (confirm(`Are you sure you want to reboot ${location}? This may disconnect users.`)) {
            addLog('error', 'ADMIN', `!!! REBOOT INITIATED: ${location} !!!`);
            alert(`Simulating reboot for ${location}...`);
        }
    }

    function handleBandwidthChange(selectElement) {
        const clientId = selectElement.dataset.id;
        const limit = selectElement.value;
        const customInputSpan = selectElement.closest('.bandwidth-control-cell').querySelector('.custom-bw-group');

        if (limit === 'custom') {
            customInputSpan.classList.remove('hidden');
            const customValue = parseInt(customInputSpan.querySelector('.custom-bw-input').value, 10);
            saveBandwidthLimit(clientId, customValue);
        } else {
            customInputSpan.classList.add('hidden');
            saveBandwidthLimit(clientId, limit);
        }
    }

    // Save bandwidth limit to database
    function saveBandwidthLimit(clientId, limit) {
        const token = localStorage.getItem('admin_token');
        if (!token) return alert('Please login as admin');

        fetch(`/api/admin/clients/${clientId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({ bandwidth_limit: limit })
        })
            .then(res => {
                if (res.ok) {
                    console.log(`✅ Bandwidth limit saved: ${limit}`);
                    addLog('info', 'ADMIN', `Set bandwidth limit to ${limit}`);
                } else {
                    console.error('Failed to save bandwidth limit');
                    alert('Failed to save bandwidth limit');
                }
            })
            .catch(err => {
                console.error('Error saving bandwidth:', err);
                alert('Error saving bandwidth limit');
            });
    }

    function handleCustomBandwidthInput(inputElement) {
        const id = parseInt(inputElement.dataset.id);
        const client = db.clients.find(c => c.id === id);
        const customValue = parseInt(inputElement.value, 10);
        if (!isNaN(customValue) && customValue > 0) {
            db.bandwidthLimits[id] = customValue;
        }
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

    // --- Utility Functions ---
    function addBlockedSiteToDOM(url, isCategorySite, prepend = false) {
        const blockedSitesList = document.getElementById("blocked-sites-list");
        if (!blockedSitesList) return;
        const li = document.createElement("li");
        li.innerHTML = `<span>${url}</span> ${isCategorySite ? `<small style="color: var(--text-secondary);">(Blocked by category)</small>` : `<button class="btn btn-remove"><i class="fa-solid fa-trash"></i></button>`}`;
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
                { label: 'Download (KB/s)', backgroundColor: 'rgba(54,162,235,0.2)', borderColor: 'rgba(54,162,235,1)', data: labels.map(() => Math.floor(Math.random() * 400) + 50), fill: true },
                { label: 'Upload (KB/s)', backgroundColor: 'rgba(255,99,132,0.1)', borderColor: 'rgba(255,99,132,1)', data: labels.map(() => Math.floor(Math.random() * 80) + 10), fill: true }
            ]
        };
    }

    window.myTrafficChart = new Chart(ctx, {
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