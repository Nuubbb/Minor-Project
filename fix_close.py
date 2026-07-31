t = open('templates/dashboard.html', encoding='utf-8').read()
if '</body>' not in t:
    t = t + '\n</body>\n</html>'
    open('templates/dashboard.html', 'w', encoding='utf-8').write(t)
    print("Added missing closing tags!")
else:
    print("Closing tags already present")
