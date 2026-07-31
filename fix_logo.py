import os

d = 'templates'
for f in os.listdir(d):
    if f.endswith('.html'):
        p = os.path.join(d, f)
        c = open(p, 'r', encoding='utf-8').read()
        old = '<div class="brand-icon"><i class="fas fa-shield-halved"></i></div>'
        new = '<img src="/static/logo.png" alt="Logo" style="width:40px;height:40px;border-radius:10px;">'
        if old in c:
            c = c.replace(old, new)
            open(p, 'w', encoding='utf-8').write(c)
            print('Fixed:', f)
print('Done')