import os

d = 'templates'
for f in os.listdir(d):
    if f.endswith('.html'):
        p = os.path.join(d, f)
        c = open(p, 'r', encoding='utf-8').read()

        # Fix the broken hardcoded path version
        old1 = '<img src="/static/logo.png" alt="Logo" style="width:40px;height:40px;border-radius:10px;">'
        new = """<img src="{{ url_for('static', filename='logo.png') }}" alt="Logo" style="width:40px;height:40px;border-radius:10px;object-fit:contain;">"""

        if old1 in c:
            c = c.replace(old1, new)
            open(p, 'w', encoding='utf-8').write(c)
            print('Fixed:', f)
print('Done')