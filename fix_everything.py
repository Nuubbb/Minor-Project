import os
import re

d = 'templates'
for f in os.listdir(d):
    if f.endswith('.html') and f != 'dashboard.html':
        p = os.path.join(d, f)
        c = open(p, 'r', encoding='utf-8').read()
        orig = c

        # Sidebar color to black
        c = c.replace('#373B53', '#000000')
        c = c.replace('#4A4E69', '#000000')
        c = c.replace('#1e293b', '#000000')

        # Brand icon - replace div with img
        c = re.sub(
            r'<div class="brand-icon">.*?</div>',
            """<img src="{{ url_for('static', filename='logo.png') }}" alt="Logo" style="width:40px;height:40px;border-radius:10px;object-fit:contain;">""",
            c,
            count=1,
            flags=re.DOTALL
        )

        # Also catch the img that was already replaced but with hardcoded path
        c = c.replace(
            '<img src="/static/logo.png" alt="Logo" style="width:40px;height:40px;border-radius:10px;">',
            """<img src="{{ url_for('static', filename='logo.png') }}" alt="Logo" style="width:40px;height:40px;border-radius:10px;object-fit:contain;">"""
        )

        # Footer border - remove
        c = re.sub(r'border-top:\s*1px solid rgba\(255,\s*255,\s*255,\s*0\.0?[0-9]+\)', 'border-top:none', c)

        # User card background - transparent
        c = re.sub(r'(\.user-card\s*\{[^}]*?)background:\s*rgba\(255,\s*255,\s*255,\s*0\.0[0-9]+\)', r'\1background:transparent', c)

        # User avatar - subtle white
        c = c.replace('background:#22223B', 'background:rgba(255,255,255,0.15)')
        c = c.replace('background: #22223B', 'background: rgba(255,255,255,0.15)')

        # Remove gradients from brand icon
        c = re.sub(r'background:\s*linear-gradient\(135deg,\s*var\(--accent\),\s*#1d4ed8\)', 'background:rgba(255,255,255,0.15)', c)
        c = re.sub(r'background:\s*linear-gradient\(135deg,\s*#22223B,\s*#000000\)', 'background:rgba(255,255,255,0.15)', c)

        # Remove gradients from user avatar
        c = re.sub(r'background:\s*linear-gradient\(135deg,\s*var\(--accent\),\s*var\(--info\)\)', 'background:rgba(255,255,255,0.15)', c)

        # Logout button - blend in
        c = re.sub(
            r'border:\s*1px solid rgba\(239,\s*68,\s*68,\s*0\.2\)',
            'border:none', c)
        c = re.sub(
            r'background:\s*rgba\(239,\s*68,\s*68,\s*0\.06\)',
            'background:transparent', c)
        c = c.replace('color:#f87171', 'color:rgba(255,255,255,0.4)')
        c = c.replace('color: #f87171', 'color: rgba(255,255,255,0.4)')
        c = re.sub(
            r'border:\s*1px solid rgba\(255,\s*255,\s*255,\s*0\.15\);\s*background:\s*rgba\(255,\s*255,\s*255,\s*0\.05\);\s*color:\s*rgba\(255,\s*255,\s*255,\s*0\.7\)',
            'border:none;background:transparent;color:rgba(255,255,255,0.4)', c)

        # Logout hover
        c = re.sub(
            r'background:\s*rgba\(239,\s*68,\s*68,\s*0\.12\)',
            'background:rgba(255,255,255,0.08)', c)
        c = re.sub(
            r'border-color:\s*rgba\(239,\s*68,\s*68,\s*0\.3\)',
            'color:rgba(255,255,255,0.7)', c)

        # Active nav - white
        c = re.sub(
            r'background:\s*rgba\(37,\s*99,\s*235,\s*0\.15\);\s*color:\s*#60a5fa',
            'background:rgba(255,255,255,0.15);color:#ffffff', c)
        c = re.sub(
            r'background:\s*var\(--sidebar-active\);\s*color:\s*#60a5fa',
            'background:rgba(255,255,255,0.15);color:#ffffff', c)

        # Active bar - white
        c = re.sub(
            r'background:\s*var\(--accent\);\s*border-radius:\s*0\s+3px\s+3px\s+0',
            'background:#ffffff;border-radius:0 3px 3px 0', c)

        # Role badge color
        c = c.replace('color:#60a5fa', 'color:rgba(255,255,255,0.4)')
        c = c.replace('color: #60a5fa', 'color: rgba(255,255,255,0.4)')

        # Nav badge - muted
        c = re.sub(
            r'background:\s*var\(--danger\);\s*color:\s*(?:white|#fff)',
            'background:#9A8C98;color:#fff', c)

        # Brand box shadow - remove
        c = re.sub(
            r'box-shadow:\s*0\s+4px\s+15px\s+rgba\(37,\s*99,\s*235,\s*0\.3\)',
            'box-shadow:none', c)

        # Remove Jinja2 icon blocks from alert badges
        c = re.sub(r'<i\s+class="fas\s+\{%.*?%\}"\s*>\s*</i>\s*', '', c, flags=re.DOTALL)

        # Remove plain FA icons from alert badges
        for icon in ['fa-hand-fist','fa-crosshairs','fa-people-group','fa-person-walking','fa-triangle-exclamation','fa-person-walking-dashed-line-arrow-right']:
            c = re.sub(r'<i class="fas ' + icon + r'"[^>]*></i>\s*', '', c)

        # Remove stat card icon divs
        c = re.sub(r'<div class="stat-icon">.*?</div>', '', c, flags=re.DOTALL)

        if c != orig:
            open(p, 'w', encoding='utf-8').write(c)
            print('FIXED:', f)
        else:
            print('No changes:', f)

print('\nDone! All templates updated.')