"""
Run from project root:  python fix_all_templates.py
Fixes sidebar color, removes gradients, removes alert icons across ALL templates.
"""
import os
import re

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
FILES = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith('.html') and f != 'dashboard.html']

replacements = [
    # Sidebar bg color
    ('--sidebar-bg: #1e293b', '--sidebar-bg: #4A4E69'),
    ('--sidebar-bg:#1e293b', '--sidebar-bg:#4A4E69'),
    ('sidebar-bg: #1e293b', 'sidebar-bg: #4A4E69'),
    # Also catch inline background on sidebar
    ('background: #1e293b', 'background: #4A4E69'),
    ('background:#1e293b', 'background:#4A4E69'),
    ('background:var(--sidebar-bg)', 'background:var(--sidebar-bg)'),

    # Brand icon - flat color, no gradient
    ('background:linear-gradient(135deg, var(--accent), #1d4ed8)', 'background:#22223B'),
    ('background:linear-gradient(135deg,var(--accent),#1d4ed8)', 'background:#22223B'),
    ('background: linear-gradient(135deg, var(--accent), #1d4ed8)', 'background: #22223B'),
    ('background:linear-gradient(135deg,#22223B,#4A4E69)', 'background:#22223B'),
    ('background: linear-gradient(135deg, #22223B, #4A4E69)', 'background: #22223B'),

    # User avatar - flat color, no gradient
    ('background:linear-gradient(135deg, var(--accent), var(--info))', 'background:#22223B'),
    ('background:linear-gradient(135deg,var(--accent),var(--info))', 'background:#22223B'),
    ('background: linear-gradient(135deg, var(--accent), var(--info))', 'background: #22223B'),

    # Active nav item - white text on subtle bg
    ('background:rgba(37,99,235,0.15);color:#60a5fa', 'background:rgba(255,255,255,0.15);color:#ffffff'),
    ('background: rgba(37,99,235,0.15); color: #60a5fa', 'background: rgba(255,255,255,0.15); color: #ffffff'),
    ('background:rgba(37, 99, 235, 0.15);color:#60a5fa', 'background:rgba(255,255,255,0.15);color:#ffffff'),
    ('background:var(--sidebar-active);color:#60a5fa', 'background:rgba(255,255,255,0.15);color:#ffffff'),

    # Active bar color - white
    ('background:var(--accent);border-radius:0 3px 3px 0', 'background:#ffffff;border-radius:0 3px 3px 0'),
    ('background: var(--accent); border-radius: 0 3px 3px 0', 'background: #ffffff; border-radius: 0 3px 3px 0'),

    # Role badge text color
    ('color:#60a5fa;font-weight:600', 'color:rgba(255,255,255,0.5);font-weight:600'),
    ('color: #60a5fa; font-weight: 600', 'color: rgba(255,255,255,0.5); font-weight: 600'),
    ('color:#60a5fa', 'color:rgba(255,255,255,0.5)'),
    ('color: #60a5fa', 'color: rgba(255,255,255,0.5)'),

    # Brand icon box shadow - remove
    ('box-shadow:0 4px 15px rgba(37,99,235,0.3)', 'box-shadow:none'),
    ('box-shadow: 0 4px 15px rgba(37,99,235,0.3)', 'box-shadow: none'),
    ('box-shadow:0 4px 15px rgba(37, 99, 235, 0.3)', 'box-shadow:none'),

    # Logout button - softer
    ('border:1px solid rgba(239,68,68,0.2);background:rgba(239,68,68,0.06);color:#f87171',
     'border:1px solid rgba(255,255,255,0.15);background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.7)'),
    ('border: 1px solid rgba(239, 68, 68, 0.2); background: rgba(239, 68, 68, 0.06); color: #f87171',
     'border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.7)'),
    ('border:1px solid rgba(239,68,68,0.2)', 'border:1px solid rgba(255,255,255,0.15)'),
    ('background:rgba(239,68,68,0.06)', 'background:rgba(255,255,255,0.05)'),
    ('color:#f87171;font-size', 'color:rgba(255,255,255,0.7);font-size'),

    # Logout hover
    ('background:rgba(239,68,68,0.12);border-color:rgba(239,68,68,0.3)',
     'background:rgba(255,255,255,0.1);color:#fff'),
    ('background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.3)',
     'background: rgba(255,255,255,0.1); color: #fff'),

    # Nav badge - muted
    ('background:var(--danger);color:white', 'background:#9A8C98;color:white'),
    ('background:var(--danger);color:#fff', 'background:#9A8C98;color:#fff'),
    ('background: var(--danger); color: white', 'background: #9A8C98; color: white'),
]

# Regex patterns for removing icons from alert badges
icon_patterns = [
    r'<i class="fas fa-hand-fist"[^>]*></i>\s*',
    r'<i class="fas fa-crosshairs"[^>]*></i>\s*',
    r'<i class="fas fa-people-group"[^>]*></i>\s*',
    r'<i class="fas fa-person-walking"[^>]*></i>\s*',
    r'<i class="fas fa-triangle-exclamation"[^>]*></i>\s*',
    r'<i class="fas fa-person-walking-dashed-line-arrow-right"[^>]*></i>\s*',
]

for fname in FILES:
    path = os.path.join(TEMPLATES_DIR, fname)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    for old, new in replacements:
        content = content.replace(old, new)

    for pattern in icon_patterns:
        content = re.sub(pattern, '', content)

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Updated: {fname}")
    else:
        print(f"  No changes needed: {fname}")

print("\nDone! All templates updated.")