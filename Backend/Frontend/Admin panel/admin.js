document.addEventListener("DOMContentLoaded", () => {
    
    // --- Mock Database (Simulation) ---
    const db = {
        clients: [
            // MODIFIED: Added all 15 students back
            { id: 1, studentId: 'S1024', device: 'Student Laptop', ip: '192.168.1.10', data: 4.2, activity: 'Studying (Canvas)', blocked: false },
            { id: 2, studentId: 'S1024', device: 'Smart TV', ip: '192.168.1.12', data: 15.8, activity: 'Streaming (Netflix)', blocked: true },
            { id: 3, studentId: 'ADMIN', device: 'Desktop', ip: '192.168.1.2', data: 0.8, activity: 'Network Management', blocked: false },
            { id: 4, studentId: 'S1025', device: 'iPhone 14', ip: '192.168.1.20', data: 25.4, activity: 'Gaming (League of Legends)', blocked: true },
            { id: 5, studentId: 'GUEST', device: 'Desktop', ip: '192.168.1.30', data: 1.1, activity: 'Research (JSTOR)', blocked: false },
            { id: 6, studentId: 'S1026', device: 'iPad Air', ip: '192.168.1.22', data: 3.2, activity: 'Social Media (TikTok)', blocked: true },
            { id: 7, studentId: 'S1027', device: 'MacBook Pro', ip: '192.168.1.14', data: 2.1, activity: 'Coding (GitHub)', blocked: false },
            { id: 8, studentId: 'S1028', device: 'Android Phone', ip: '192.168.1.17', data: 6.8, activity: 'Streaming (Spotify)', blocked: true },
            { id: 9, studentId: 'S1029', device: 'Windows PC', ip: '192.168.1.18', data: 18.2, activity: 'Gaming (Steam)', blocked: true },
            { id: 10, studentId: 'S1030', device: 'Student Laptop', ip: '192.168.1.19', data: 0.9, activity: 'Studying (Library DB)', blocked: false },
            { id: 11, studentId: 'S1031', device: 'Pixel 7', ip: '192.168.1.24', data: 2.5, activity: 'Social Media (Instagram)', blocked: true },
            { id: 12, studentId: 'S1032', device: 'Surface Pro', ip: '192.168.1.25', data: 3.1, activity: 'Video Call (Zoom)', blocked: false },
            { id: 13, studentId: 'S1033', device: 'Gaming Console', ip: '192.168.1.28', data: 22.1, activity: 'Gaming (PSN)', blocked: true },
            { id: 14, studentId: 'S1034', device: 'Chromebook', ip: '192.168.1.31', data: 1.5, activity: 'Research (Google Scholar)', blocked: false },
            { id: 15, studentId: 'S1035', device: 'Mac Studio', ip: '192.168.1.32', data: 5.5, activity: 'Design (Figma)', blocked: false }
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
            "Adult Content": { 
                active: true, 
                sites: ["placeholder-adult-site.com", "generic-tube-site.net", "example-xxx-video.com"] 
            }
        },
        bandwidthLimits: {
            4: "low",
            6: "low",
            5: 15 
        },
        logs: [
            { time: '11:25:01 AM', level: 'warn', user: 'S1025', action: 'High bandwidth detected (25.4 GB)' },
            { time: '11:24:15 AM', level: 'error', user: 'Unknown (192.168.1.45)', action: 'Failed login attempt (3)' },
            { time: '11:23:00 AM', level: 'info', user: 'ADMIN', action: 'Blocked user S1026' },
            { time: '11:20:11 AM', level: 'info', user: 'S1024', action: 'Connected to network (Student Laptop)' }
        ]
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

    // --- App-Scoped Chart Variables ---
    let myTrafficChart;
    let trafficInterval;

    // --- Page Loading Logic ---
    async function loadPage(pageName) {
        // Clear any running intervals from the dashboard
        if (trafficInterval) clearInterval(trafficInterval);
        if (myTrafficChart) myTrafficChart.destroy();
        
        try {
            contentArea.innerHTML = `<div class="loading-spinner"></div>`;
            const response = await fetch(`pages/${pageName}.html`);
            if (!response.ok) throw new Error(`Could not load page: ${response.status}`);
            const html = await response.text();
            contentArea.innerHTML = html;
            
            // Run the specific init function for the loaded page
            if (pageName === 'dashboard') initDashboard();
            else if (pageName === 'clients') initClients();
            else if (pageName === 'web_filtering') initWebFiltering();
            else if (pageName === 'bandwidth') initBandwidth();
            else if (pageName === 'logs') initLogs();
            else if (pageName === 'settings') initSettings();

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
        
        const logBody = document.getElementById("event-log-body");
        if(logBody) {
            logBody.innerHTML = "";
            db.logs.slice(0, 5).forEach(log => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${log.time}</td>
                    <td><span class="log-level-${log.level}">${log.level.toUpperCase()}</span></td>
                    <td>${log.user}</td>
                    <td>${log.action}</td>
                `;
                logBody.appendChild(tr);
            });
        }

        const ctx = document.getElementById('traffic-chart-canvas');
        if (!ctx) return;

        const initialLabels = ['-58s', '-48s', '-38s', '-28s', '-18s', '-8s'];
        const initialDownloadData = [120, 190, 300, 500, 220, 450];
        const initialUploadData = [30, 40, 20, 50, 80, 75];

        myTrafficChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: initialLabels,
                datasets: [
                    { label: 'Download (Mbps)', data: initialDownloadData, borderColor: 'var(--primary-blue)', backgroundColor: 'rgba(0, 92, 158, 0.1)', fill: true, tension: 0.4 },
                    { label: 'Upload (Mbps)', data: initialUploadData, borderColor: 'var(--green)', backgroundColor: 'rgba(40, 167, 69, 0.1)', fill: true, tension: 0.4 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: { 
                    y: { beginAtZero: true },
                    x: { ticks: { autoSkip: false, maxRotation: 0 } }
                },
                interaction: { mode: 'index', intersect: false }
            }
        });

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
        }, 2000);
    }

    function initClients() {
        const clientListBody = document.getElementById("client-list-body");
        if (!clientListBody) return;
        
        clientListBody.innerHTML = ""; // Clear list
        db.clients.forEach(client => {
            const statusClass = client.blocked ? "status-blocked" : "status-active";
            const statusText = client.blocked ? "Blocked" : "Active";
            
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${client.studentId} (${client.device})</td>
                <td>${client.ip}</td>
                <td>${client.data} GB</td>
                <td>${client.activity}</td>
                <td class="${statusClass}">${statusText}</td>
                <td>
                    <button class="btn ${client.blocked ? 'btn-success' : 'btn-danger'} btn-block" data-id="${client.id}">
                        ${client.blocked ? 'Unblock' : 'Block'}
                    </button>
                </td>
            `;
            clientListBody.appendChild(row);
        });
    }

    function initWebFiltering() {
        const blockedSitesList = document.getElementById("blocked-sites-list");
        if (!blockedSitesList) return;
        
        blockedSitesList.innerHTML = "";
        
        // Render manual sites first
        db.blockedSites.forEach(url => addBlockedSiteToDOM(url, false));
        // Render category sites
        Object.keys(db.siteCategories).forEach(key => {
            if (db.siteCategories[key].active) {
                db.siteCategories[key].sites.forEach(site => {
                    if (!db.blockedSites.includes(site)) {
                        addBlockedSiteToDOM(site, true);
                    }
                });
            }
        });
        
        const categories = document.getElementById("filter-categories");
        categories.innerHTML = "";
        Object.keys(db.siteCategories).forEach(key => {
            const btn = document.createElement("button");
            btn.className = `filter-toggle ${db.siteCategories[key].active ? 'active' : ''}`;
            btn.textContent = key;
            btn.dataset.category = key;
            categories.appendChild(btn);
        });
    }

    function initBandwidth() {
        const bandwidthListBody = document.getElementById("bandwidth-list-body");
        if (!bandwidthListBody) return;
        
        bandwidthListBody.innerHTML = "";
        db.clients.forEach(client => {
            if (client.studentId === 'ADMIN') return;
            
            const limit = db.bandwidthLimits[client.id];
            const isCustom = typeof limit === 'number';
            
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${client.studentId} (${client.device})</td>
                <td>${client.data} GB</td>
                <td>${client.activity}</td> 
                <td>
                    <div class="bandwidth-control-cell">
                        <select class="limit-select" data-id="${client.id}">
                            <option value="vlow" ${limit === 'vlow' ? 'selected' : ''}>Very Low (2 Mbps)</option>
                            <option value="low" ${limit === 'low' ? 'selected' : ''}>Low (10 Mbps)</option>
                            <option value="standard" ${!limit || limit === 'standard' ? 'selected' : ''}>Standard (25 Mbps)</option>
                            <option value="high" ${limit === 'high' ? 'selected' : ''}>High (100 Mbps)</option>
                            <option value="unlimited" ${limit === 'unlimited' ? 'selected' : ''}>Unlimited</option>
                            <option value="custom" ${isCustom ? 'selected' : ''}>Manual...</option>
                        </select>
                        <span class="custom-bw-group ${isCustom ? '' : 'hidden'}">
                            <input type="number" class="custom-bw-input" data-id="${client.id}" value="${isCustom ? limit : '50'}" min="1">
                            <span>Mbps</span>
                        </span>
                    </div>
                </td>
                <td>
                    <button class="btn ${client.blocked ? 'btn-success' : 'btn-danger'} btn-block" data-id="${client.id}">
                        ${client.blocked ? 'Unblock' : 'Block'}
                    </button>
                </td>
            `;
            bandwidthListBody.appendChild(row);
        });
    }

    function initLogs() {
        const logBody = document.getElementById("log-body");
        if (!logBody) return;
        
        logBody.innerHTML = "";
        db.logs.forEach(log => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${log.time}</td>
                <td><span class="log-level-${log.level}">${log.level.toUpperCase()}</span></td>
                <td>${log.user} / ${log.ip || 'N/A'}</td>
                <td>${log.action}</td>
            `;
            logBody.appendChild(tr);
        });
    }
    
    function initSettings() {
        // This function is here to attach the listener after the page loads
        // The listener is now on document.body, so this function is just a placeholder
        // in case you want to add specific JS to the settings page later.
    }

    // --- Global Event Listeners (using delegation on document.body) ---
    // This is the most reliable method and fixes all button issues.
    
    // --- 1. CLICK Listener ---
    document.body.addEventListener('click', (e) => {
        
        // --- Profile Dropdown Logic ---
        if (e.target.closest('#profile-menu-toggle')) {
            profileDropdown.classList.toggle('active');
            notificationTray.classList.remove('active');
        } else if (!e.target.closest('.profile-dropdown')) {
            profileDropdown.classList.remove('active');
        }
        
        // --- Notification Bell Logic ---
        if (e.target.closest('#notification-bell')) {
            notificationTray.classList.toggle('active');
            notificationBadge.classList.add('hidden');
            profileDropdown.classList.remove('active');
        } else if (!e.target.closest('.notification-dropdown')) {
            notificationTray.classList.remove('active');
        }

        // --- Sidebar Menu ---
        const menuItem = e.target.closest('.menu-item');
        if (menuItem) {
            e.preventDefault();
            const pageName = menuItem.getAttribute("data-page");
            
            menuItems.forEach(i => i.classList.remove("active"));
            menuItem.classList.add("active");
            
            pageTitle.textContent = menuItem.querySelector("span").textContent;
            loadPage(pageName);

            if (window.innerWidth <= 768) {
                sidebar.classList.remove("open");
            }
        }

        // --- Mobile Menu Toggle ---
        if (e.target.closest('#menu-toggle')) {
            sidebar.classList.toggle("open");
        }

        // --- Client Block/Unblock Button ---
        if (e.target.classList.contains('btn-block')) {
            handleBlockUnblock(e.target);
        }

        // --- Web Filtering Remove Button ---
        if (e.target.closest('.btn-remove')) {
            handleRemoveSite(e.target);
        }
        
        // --- Category Toggle Button ---
        if (e.target.classList.contains('filter-toggle')) {
            handleCategoryToggle(e.target);
        }

        // --- Settings Reboot Button ---
        if (e.target.id === 'reboot-button') {
            handleReboot();
        }
    });

    // --- 2. SUBMIT Listener (FIXED) ---
    // This listener is now on document.body to catch form submissions
    // from dynamically loaded content.
    document.body.addEventListener('submit', (e) => {
        // --- Add New Client Form ---
        if (e.target.id === 'add-client-form') {
            e.preventDefault();
            const studentId = document.getElementById('client-id').value;
            const device = document.getElementById('client-device').value;
            const ip = document.getElementById('client-ip').value;
            
            if (studentId && device && ip) {
                const newClient = {
                    id: db.clients.length + 1,
                    studentId: studentId,
                    device: device,
                    ip: ip,
                    data: 0.1, // Default low data
                    activity: 'Idle', // Default activity
                    blocked: false
                };
                db.clients.push(newClient);
                db.bandwidthLimits[newClient.id] = 'standard'; // Default bandwidth
                
                addLog('info', 'ADMIN', `Added new client ${studentId} (${device})`);
                initClients(); // <-- THIS IS THE FIX
                initDashboard(); // <-- THIS IS THE FIX
                e.target.reset();
                alert('Client added successfully!');
            }
        }
        
        // --- Add Blocked Site Form ---
        if (e.target.id === 'website-block-form') {
            e.preventDefault();
            const websiteInput = document.getElementById("website-input");
            const url = websiteInput.value.trim();
            if (url && !db.blockedSites.includes(url)) {
                db.blockedSites.unshift(url);
                addLog('warn', 'ADMIN', `Manually blocked site: ${url}`);
                addBlockedSiteToDOM(url, false, true); // true = prepend
                websiteInput.value = "";
            } else if (db.blockedSites.includes(url)) {
                alert('This site is already in the manual block list.');
            }
        }

        // --- Network Settings form ---
        if (e.target.id === 'network-settings-form') {
            e.preventDefault();
            addLog('info', 'ADMIN', 'Network settings saved');
            alert('Network settings saved successfully! (Demo)');
        }
    });
    
    // --- 3. CHANGE Listener (FIXED) ---
    // This listener is also on document.body.
    document.body.addEventListener('change', (e) => {
        // --- Bandwidth Limit Select ---
        if (e.target.classList.contains('limit-select')) {
            handleBandwidthChange(e.target);
        }
    });

    // --- 4. INPUT Listener (FIXED) ---
    // This listener is also on document.body.
    document.body.addEventListener('input', (e) => {
        if (e.target.classList.contains('custom-bw-input')) {
            handleCustomBandwidthInput(e.target);
        }
    });
    
    // --- Event Handler Functions ---
    // These functions are now called by the listeners above

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
    
    function handleAddBlockedSite(e) {
        // Logic is handled by the 'submit' listener on document.body
    }
    
    function handleSaveSettings(e) {
        // Logic is handled by the 'submit' listener on document.body
    }
    
    function handleRemoveSite(button) {
        const li = button.closest("li");
        const url = li.querySelector("span").textContent;
        
        let index = db.blockedSites.indexOf(url);
        if (index > -1) db.blockedSites.splice(index, 1);
        
        let isInCategory = false;
        Object.keys(db.siteCategories).forEach(key => {
            if (db.siteCategories[key].active && db.siteCategories[key].sites.includes(url)) {
                isInCategory = true;
            }
        });

        if(isInCategory) {
            alert(`Cannot manually remove ${url}. It is part of an active blocked category. Disable the category first.`);
            return;
        }
        
        addLog('info', 'ADMIN', `Removed ${url} from block list`);
        li.remove();
    }
    
    function handleCategoryToggle(button) {
        const category = button.dataset.category;
        db.siteCategories[category].active = !db.siteCategories[category].active;
        
        if (db.siteCategories[category].active) {
            addLog('warn', 'ADMIN', `Enabled category block: ${category}`);
        } else {
            addLog('info', 'ADMIN', `Disabled category block: ${category}`);
        }
        initWebFiltering(); // Re-render the page
    }

    function handleReboot() {
        if (confirm("Are you sure you want to reboot the main router? This will disconnect all users.")) {
            addLog('error', 'ADMIN', '!!! MAIN ROUTER REBOOT INITIATED !!!');
            alert("Simulating router reboot... (This is a demo)");
        }
    }

    function handleBandwidthChange(selectElement) {
        const id = parseInt(selectElement.dataset.id);
        const client = db.clients.find(c => c.id === id);
        const limit = selectElement.value;
        
        const customInputSpan = selectElement.closest('.bandwidth-control-cell').querySelector('.custom-bw-group');
        
        if (limit === 'custom') {
            customInputSpan.classList.remove('hidden');
            const customValue = parseInt(customInputSpan.querySelector('.custom-bw-input').value, 10);
            db.bandwidthLimits[id] = customValue;
            addLog('info', 'ADMIN', `Set bandwidth for ${client.studentId} to ${customValue} Mbps`);
        } else {
            customInputSpan.classList.add('hidden');
            db.bandwidthLimits[id] = limit;
            addLog('info', 'ADMIN', `Set bandwidth for ${client.studentId} to ${limit}`);
        }
    }

    function handleCustomBandwidthInput(inputElement) {
        const id = parseInt(inputElement.dataset.id);
        const client = db.clients.find(c => c.id === id);
        const customValue = parseInt(inputElement.value, 10);
        
        if (!isNaN(customValue) && customValue > 0) {
            db.bandwidthLimits[id] = customValue;
            // Log when they click away (in the 'change' event)
        }
    }

    // --- Utility Functions ---
    function addBlockedSiteToDOM(url, isCategorySite, prepend = false) {
        const blockedSitesList = document.getElementById("blocked-sites-list");
        if (!blockedSitesList) return;
        const li = document.createElement("li");
        
        li.innerHTML = `
            <span>${url}</span>
            ${isCategorySite ? 
                `<small style="color: var(--text-secondary);">(Blocked by category)</small>` : 
                `<button class="btn btn-remove"><i class="fa-solid fa-trash"></i></button>`
            }
        `;
        
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
        
        if(document.getElementById('log-page')) initLogs();
        if(document.getElementById('dashboard-page')) initDashboard();
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
        notificationList.innerHTML = ''; // Clear list
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

    // --- Initial Load ---
    loadPage('dashboard');
    initNotificationTray();
});