<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Admin Portal - NAV Updates</title>
    <link href="https://fonts.googleapis.com/css2?family=Great+Vibes&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <style>
        :root {
            --bg-main: #0b0f19;
            --bg-panel: #111827;
            --bg-card: #1f2937;
            --border-color: #374151;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --accent-gold: #fbbf24;
            --accent-orange: #f59e0b;
            --green: #00FF00;
            --red: #FF0800;
        }
        body { font-size: 16px !important; background-color: var(--bg-main) !important; color: var(--text-main) !important; font-family: 'Inter', system-ui, sans-serif; margin: 0; padding: 0; }
        .dashboard-container { max-width: 1440px; margin: 0 auto; padding: 24px; }
        .main-header { background: linear-gradient(135deg, var(--bg-panel) 0%, var(--bg-card) 100%); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px 30px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4); }
        .panel { background: var(--bg-panel); border: 1px solid var(--border-color); border-radius: 12px; padding: 22px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        .panel h3 { font-size: 17px !important; margin-top: 0; margin-bottom: 16px; color: var(--accent-gold); border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
        .approval-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        .approval-table th, .approval-table td { padding: 14px; text-align: left; border-bottom: 1px solid var(--border-color); font-size: 14px; }
        .approval-table th { background: var(--bg-card); color: var(--accent-gold); }
        .btn-app { background: var(--green); color: #000; border: none; padding: 7px 14px; border-radius: 5px; font-weight: 700; cursor: pointer; }
        .btn-dec { background: var(--red); color: #fff; border: none; padding: 7px 14px; border-radius: 5px; font-weight: 600; cursor: pointer; }
        .btn-batch { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #000; font-weight: 700; border: none; padding: 10px 16px; border-radius: 6px; cursor: pointer; text-decoration: none; display: inline-block; font-size: 13px; }
        .fund-table-full { width: 100%; border-collapse: collapse; background: var(--bg-panel); border-radius: 0 0 8px 8px; overflow: hidden; border: 1px solid var(--border-color); border-top: none; }
        .fund-table-full th { background: var(--bg-card); color: var(--accent-gold); text-align: left; padding: 14px; }
        .fund-table-full td { padding: 14px; border-bottom: 1px solid var(--border-color); }
        .fund-table-full tr:hover { background: rgba(255, 255, 255, 0.02); }
        .section-title-bar { font-size: 16px !important; padding: 14px 18px !important; background: linear-gradient(90deg, #1f2937 0%, #111827 100%); border-left: 4px solid var(--accent-orange); font-weight: 600; color: #fff; border-radius: 6px 6px 0 0; margin-top: 24px; }
        .modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(4px); z-index: 9999; justify-content: center; align-items: center; }
        .modal-content { background: var(--bg-panel); border: 1px solid var(--border-color); padding: 30px; border-radius: 12px; width: 650px; max-width: 90%; max-height: 90vh; overflow-y: auto; position: relative; }
        .modal-close { position: absolute; top: 15px; right: 20px; font-size: 26px; font-weight: bold; color: var(--text-muted); cursor: pointer; }
        .modal-returns-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        .modal-returns-table th, .modal-returns-table td { padding: 10px 12px; border-bottom: 1px solid var(--border-color); text-align: left; font-size: 14px; }
        .modal-returns-table th { background: var(--bg-card); color: var(--accent-gold); }
        .nav-red-alarm { color: var(--red); font-weight: 600; }
        .nav-green { color: var(--green); font-weight: 600; }
    </style>
</head>
<body>
    <div class="dashboard-container">
        
        <header class="main-header">
            <div>
                <h2>Admin Portal</h2>
                <span style="color: var(--text-muted); font-size: 14px;">Admin Control Center</span>
                <p style="color: var(--accent-gold); font-style: italic; margin: 4px 0;">Admin - Bijoosh Padmakumar</p>
            </div>
            <div style="text-align: right;">
                <p id="live-clock" style="font-size: 14px; color: #fcd34d; font-weight: 600; margin: 0;"></p>
                <p style="color: var(--green); font-weight: 600; font-size: 13px; margin-top: 4px;">● Admin Session Active</p>
            </div>
        </header>

        <!-- Download Approval Requests with Filters -->
        <div class="panel" style="margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
                <h3 style="margin: 0; border: none; padding: 0;">NAV Image Download Approval Requests</h3>
                <div style="display: flex; gap: 10px;">
                    <a href="{{ url_for('admin_dashboard', req_filter='all') }}" class="btn-batch" style="background: {% if req_filter == 'all' %}var(--accent-gold){% else %}var(--bg-card){% endif %}; color: {% if req_filter == 'all' %}#000{% else %}#fff{% endif %};">All Requests</a>
                    <a href="{{ url_for('admin_dashboard', req_filter='pending') }}" class="btn-batch" style="background: {% if req_filter == 'pending' %}var(--accent-orange){% else %}var(--bg-card){% endif %}; color: #000;">Pending</a>
                    <a href="{{ url_for('admin_dashboard', req_filter='approved') }}" class="btn-batch" style="background: {% if req_filter == 'approved' %}var(--green){% else %}var(--bg-card){% endif %}; color: #000;">Approved</a>
                </div>
            </div>
            <table class="approval-table">
                <thead>
                    <tr>
                        <th>User Name</th>
                        <th>Requested File</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Timestamp</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for req in download_requests %}
                    <tr>
                        <td>{{ req.username }}</td>
                        <td>{{ req.filename }}</td>
                        <td>{{ req.type }}</td>
                        <td>{{ req.status }}</td>
                        <td>{{ req.timestamp }}</td>
                        <td>
                            {% if req.status == 'Pending' %}
                            <form action="{{ url_for('approve_download', req_id=req.id) }}" method="POST" style="display:inline;">
                                <button type="submit" class="btn-app">Approve</button>
                            </form>
                            <form action="{{ url_for('reject_download', req_id=req.id) }}" method="POST" style="display:inline;">
                                <button type="submit" class="btn-dec">Reject</button>
                            </form>
                            {% else %}
                            <span style="color: var(--text-muted);">Processed</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" style="text-align: center; color: var(--text-muted);">No download requests found.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- User Approval & Filter Lists with Status, Online/Offline, and Login Time -->
        <div class="panel" style="margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; flex-wrap: wrap; gap: 10px;">
                <h3 style="margin: 0; border: none; padding: 0;">User Management & Presence List</h3>
                <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <a href="{{ url_for('admin_dashboard', user_filter='all') }}" class="btn-batch" style="background: {% if user_filter == 'all' %}var(--accent-gold){% else %}var(--bg-card){% endif %}; color: {% if user_filter == 'all' %}#000{% else %}#fff{% endif %};">All Users</a>
                    <a href="{{ url_for('admin_dashboard', user_filter='approved') }}" class="btn-batch" style="background: {% if user_filter == 'approved' %}var(--green){% else %}var(--bg-card){% endif %}; color: #000;">Approved List</a>
                    <a href="{{ url_for('admin_dashboard', user_filter='pending') }}" class="btn-batch" style="background: {% if user_filter == 'pending' %}var(--accent-orange){% else %}var(--bg-card){% endif %}; color: #000;">Pending List</a>
                    <form action="{{ url_for('toggle_auto_approval') }}" method="POST" style="margin: 0;">
                        <button type="submit" style="background: {% if auto_approval_enabled %}var(--green){% else %}var(--red){% endif %}; color: #000; border: none; padding: 10px 16px; border-radius: 6px; font-weight: 700; cursor: pointer; font-size: 13px;">
                            Auto-Approval: {% if auto_approval_enabled %}ON{% else %}OFF{% endif %}
                        </button>
                    </form>
                </div>
            </div>
            <table class="approval-table">
                <thead>
                    <tr>
                        <th>User Account</th>
                        <th>Mobile Number</th>
                        <th>Presence Status</th>
                        <th>Last Login / Activity</th>
                        <th>Account Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for user in users %}
                        {% if user_filter == 'all' or (user_filter == 'approved' and user.status == 'Approved') or (user_filter == 'pending' and user.status == 'Pending') %}
                        <tr>
                            <td><b>{{ user.name }}</b> (ID: {{ user.id }})</td>
                            <td>{{ user.mobile }}</td>
                            <td>
                                {% if user.is_online %}
                                    <span style="color: var(--green); font-weight: bold;">● Online</span>
                                {% else %}
                                    <span style="color: var(--text-muted);">○ Offline</span>
                                {% endif %}
                            </td>
                            <td>{{ user.last_login | default('N/A') }}</td>
                            <td><span style="font-weight: bold; color: {% if user.status == 'Approved' %}var(--green){% else %}var(--accent-orange){% endif %};">{{ user.status }}</span></td>
                            <td>
                                <form action="{{ url_for('update_user_status', user_id=user.id, status='Approved') }}" method="POST" style="display:inline;">
                                    <button type="submit" class="btn-app">Approve</button>
                                </form>
                                <form action="{{ url_for('update_user_status', user_id=user.id, status='Pending') }}" method="POST" style="display:inline;">
                                    <button type="submit" class="btn-dec">Decline</button>
                                </form>
                            </td>
                        </tr>
                        {% endif %}
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Funds Tables with Clickable Popups -->
        <div class="funds-stack-container">
            <div class="fund-section-box" style="margin-bottom: 24px;">
                <div class="section-title-bar">Equity Funds (Click any fund for full details)</div>
                <table class="fund-table-full">
                    <thead>
                        <tr>
                            <th>FUNDS</th>
                            <th>Inception Date</th>
                            <th>Benchmark Name</th>
                            <th>Since Inception</th>
                            <th>Highest NAV</th>
                            <th>Latest NAV</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in equity_data %}
                        <tr onclick='openModal({{ row | tojson | safe }})' style="cursor: pointer;">
                            <td><b style="color: var(--accent-gold); text-decoration: underline;">{{ row.fund }}</b></td>
                            <td>{{ row.inception }}</td>
                            <td>{{ row.benchmark }}</td>
                            <td class="nav-green">{{ row.since }}%</td>
                            <td>{{ row.high }}</td>
                            <td class="nav-green">{{ row.latest }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Fund Details Popup Modal -->
        <div id="fundModal" class="modal-overlay">
            <div class="modal-content">
                <span class="modal-close" onclick="closeModal()">&times;</span>
                <h2 id="modal-fund-name" style="color: var(--accent-gold); margin-top: 0; font-size: 20px;">Fund Name</h2>
                <div style="font-size: 14px; margin-bottom: 15px; color: var(--text-muted);">
                    <div><strong>Inception Date:</strong> <span id="modal-inception" style="color:#fff;"></span></div>
                    <div><strong>Benchmark Name:</strong> <span id="modal-benchmark" style="color:#fff;"></span></div>
                </div>
                <table class="modal-returns-table">
                    <thead>
                        <tr><th>Metric / Period</th><th>Value / Return</th></tr>
                    </thead>
                    <tbody>
                        <tr><td>Since Inception</td><td id="m-since"></td></tr>
                        <tr><td>1 Month</td><td id="m-1m"></td></tr>
                        <tr><td>6 Month</td><td id="m-6m"></td></tr>
                        <tr><td>1 Year</td><td id="m-1y"></td></tr>
                        <tr><td>Highest NAV</td><td id="m-high"></td></tr>
                        <tr><td>Latest NAV</td><td id="m-latest"></td></tr>
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <script>
        function updateClock() {
            const now = new Date();
            document.getElementById('live-clock').innerText = now.toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
        }
        setInterval(updateClock, 1000);
        updateClock();

        function openModal(data) {
            document.getElementById('modal-fund-name').innerText = data.fund;
            document.getElementById('modal-inception').innerText = data.inception;
            document.getElementById('modal-benchmark').innerText = data.benchmark;
            document.getElementById('m-since').innerText = (data.since || '0') + '%';
            document.getElementById('m-1m').innerText = (data.m1 || '0') + '%';
            document.getElementById('m-6m').innerText = (data.m6 || '0') + '%';
            document.getElementById('m-1y').innerText = (data.y1 || '0') + '%';
            document.getElementById('m-high').innerText = data.high || '0';
            document.getElementById('m-latest').innerText = data.latest || '0';
            document.getElementById('fundModal').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('fundModal').style.display = 'none';
        }

        window.onclick = function(event) {
            let modal = document.getElementById('fundModal');
            if (event.target == modal) { closeModal(); }
        }

        setInterval(() => {
            fetch('/api/heartbeat', {method: 'POST'}).catch(e => {});
        }, 30000);
    </script>
</body>
</html>