# Fix 1: Remove <link> tag from get_alerts in app.py
t = open('app.py', encoding='utf-8').read()
old_link = '    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">\n'
if old_link in t:
    t = t.replace(old_link, '')
    open('app.py', 'w', encoding='utf-8').write(t)
    print("app.py: removed <link> tag")
else:
    print("app.py: <link> tag already removed")

# Fix 2: Replace the broken initial counts in dashboard.html
d = open('templates/dashboard.html', encoding='utf-8').read()

old_js = """        // Initial counts
        (function() {
            let total = 0, active = 0, dismissed = 0;
            document.querySelectorAll('#alerts-tbody tr').forEach(r => {
                if (r.querySelector('td')) {
                    total++;
                    if (r.innerHTML.includes('Dismissed')) dismissed++;
                    else active++;
                }
            });
            document.getElementById('stat-total').textContent = total;
            document.getElementById('stat-active').textContent = active;
            document.getElementById('stat-dismissed').textContent = dismissed;
        })();"""

if old_js not in d:
    # Maybe still the broken Jinja version
    import re
    pattern = r'// Initial counts.*?\(\)\);'
    match = re.search(pattern, d, re.DOTALL)
    if match:
        old_js = match.group(0)

new_js = """        // Initial counts + auto-refresh
        function updateAlertStats() {
            fetch("/get_alerts").then(r => r.text()).then(h => {
                document.getElementById('alerts-tbody').innerHTML = h;
                let total = 0, active = 0, dismissed = 0;
                let tmp = document.createElement('div');
                tmp.innerHTML = '<table>' + h + '</table>';
                tmp.querySelectorAll('tr').forEach(r => {
                    if (r.querySelector('td') && !r.querySelector('td[colspan]')) {
                        total++;
                        if (r.innerHTML.includes('Dismissed')) dismissed++;
                        else active++;
                    }
                });
                document.getElementById('stat-total').textContent = total;
                document.getElementById('stat-active').textContent = active;
                document.getElementById('stat-dismissed').textContent = dismissed;
            });
        }
        updateAlertStats();
        setInterval(updateAlertStats, 3000);"""

d = d.replace(old_js, new_js)

# Also remove the old separate setInterval block if it exists
old_interval = '''        // Auto-refresh alerts
        setInterval(() => {
            fetch("/get_alerts").then(r => r.text()).then(h => {
                document.getElementById('alerts-tbody').innerHTML = h;
                let total = 0,
                    active = 0,
                    dismissed = 0;
                document.querySelectorAll('#alerts-tbody tr').forEach(r => {
                    if (r.querySelector('td')) {
                        total++;
                        if (r.innerHTML.includes('Dismissed')) dismissed++;
                        else active++;
                    }
                });
                if (total > 0 || !document.querySelector('.no-alerts')) {
                    document.getElementById('stat-total').textContent = total;
                    document.getElementById('stat-active').textContent = active;
                    document.getElementById('stat-dismissed').textContent = dismissed;
                }
            });
        }, 3000);'''
if old_interval in d:
    d = d.replace(old_interval, '')
    print("dashboard.html: removed duplicate setInterval")

open('templates/dashboard.html', 'w', encoding='utf-8').write(d)
print("dashboard.html: fixed stats update logic")
print("Done! Restart app.py")
