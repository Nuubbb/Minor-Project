lines = open('templates/dashboard.html', encoding='utf-8').readlines()

# Replace lines 1170-1183 (index 1169-1182)
new_code = '''       // Alert stats: initial + auto-refresh
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
        setInterval(updateAlertStats, 3000);
'''

lines[1169:1183] = [new_code]
open('templates/dashboard.html', 'w', encoding='utf-8').writelines(lines)
print("Fixed!")
