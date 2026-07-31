lines = open('app.py', encoding='utf-8').readlines()

# Line 116 (index 115): flash needs indentation
lines[115] = "            flash(\"If this email exists, you'll receive a verification code shortly.\", \"info\")\n"

# Line 118 (index 117): duplicate return redirect - delete it
del lines[117]

# Now line 118 (index 117) is the render_template - fix its indent
lines[117] = "        return render_template('signup.html')\n"

open('app.py', 'w', encoding='utf-8').writelines(lines)
print("Fixed!")
