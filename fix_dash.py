t = open('templates/dashboard.html', encoding='utf-8').read()

old = """       // Initial counts
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

new = """       // Alert stats: initial + auto-refresh
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

if old in t:
    t = t.replace(old, new)
    open('templates/dashboard.html', 'w', encoding='utf-8').write(t)
    print("Fixed!")
else:
    print("FAILED - pattern not found")
