p = 'app.py'
t = open(p, encoding='utf-8').read()
t = t.replace('    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">\n', '')
open(p, 'w', encoding='utf-8').write(t)
print("Fixed!")
