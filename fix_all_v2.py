"""
Run: python fix_all_v2.py
Fixes ALL templates - removes icons, fixes sidebar, removes gradients.
"""
import os
import re

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
FILES = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith('.html') and f != 'dashboard.html']

for fname in FILES:
    path = os.path.join(TEMPLATES_DIR, fname)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    # ===== 1. REMOVE JINJA2 ICON BLOCKS =====
    # Matches: <i class="fas {% if 'violen' in atype %}fa-hand-fist{% elif ...{% endif %}"></i>
    content = re.sub(
        r'<i\s+class="fas\s+\{%.*?%\}"\s*>\s*</i>\s*',
        '',
        content,
        flags=re.DOTALL
    )

    # Remove plain FA icons in alert badges
    content = re.sub(r'<i class="fas fa-hand-fist"[^>]*></i>\s*', '', content)
    content = re.sub(r'<i class="fas fa-crosshairs"[^>]*></i>\s*', '', content)
    content = re.sub(r'<i class="fas fa-people-group"[^>]*></i>\s*', '', content)
    content = re.sub(r'<i class="fas fa-person-walking"[^>]*></i>\s*', '', content)
    content = re.sub(r'<i class="fas fa-triangle-exclamation"[^>]*></i>\s*', '', content)
    content = re.sub(r'<i class="fas fa-person-walking-dashed-line-arrow-right"[^>]*></i>\s*', '', content)

    # Remove stat card icon divs (the colored circles with icons)
    content = re.sub(
        r'<div class="stat-icon">.*?</div>',
        '',
        content,
        flags=re.DOTALL
    )

    # ===== 2. SIDEBAR COLOR =====
    content = content.replace('#1e293b', '#4A4E69')

    # ===== 3. BRAND ICON - FLAT, NO GRADIENT =====
    content = re.sub(
        r'background:\s*linear-gradient\(135deg,\s*var\(--accent\),\s*#1d4ed8\)',
        'background:#22223B',
        content
    )
    content = re.sub(
        r'background:\s*linear-gradient\(135deg,\s*#22223B,\s*#4A4E69\)',
        'background:#22223B',
        content
    )

    # ===== 4. USER AVATAR - FLAT =====
    content = re.sub(
        r'background:\s*linear-gradient\(135deg,\s*var\(--accent\),\s*var\(--info\)\)',
        'background:#22223B',
        content
    )

    # ===== 5. ACTIVE NAV - WHITE =====
    content = re.sub(
        r'background:\s*rgba\(37,\s*99,\s*235,\s*0\.15\);\s*color:\s*#60a5fa',
        'background:rgba(255,255,255,0.15);color:#ffffff',
        content
    )
    content = re.sub(
        r'background:\s*var\(--sidebar-active\);\s*color:\s*#60a5fa',
        'background:rgba(255,255,255,0.15);color:#ffffff',
        content
    )

    # ===== 6. ACTIVE BAR - WHITE =====
    content = re.sub(
        r'background:\s*var\(--accent\);\s*border-radius:\s*0\s+3px\s+3px\s+0',
        'background:#ffffff;border-radius:0 3px 3px 0',
        content
    )

    # ===== 7. ROLE BADGE COLOR =====
    content = content.replace('color:#60a5fa', 'color:rgba(255,255,255,0.5)')
    content = content.replace('color: #60a5fa', 'color: rgba(255,255,255,0.5)')

    # ===== 8. BRAND BOX SHADOW - REMOVE =====
    content = re.sub(
        r'box-shadow:\s*0\s+4px\s+15px\s+rgba\(37,\s*99,\s*235,\s*0\.3\)',
        'box-shadow:none',
        content
    )

    # ===== 9. LOGOUT BUTTON - SOFTER =====
    content = content.replace('color:#f87171', 'color:rgba(255,255,255,0.7)')
    content = content.replace('color: #f87171', 'color: rgba(255,255,255,0.7)')
    content = re.sub(
        r'border:\s*1px\s+solid\s+rgba\(239,\s*68,\s*68,\s*0\.2\)',
        'border:1px solid rgba(255,255,255,0.15)',
        content
    )
    content = re.sub(
        r'background:\s*rgba\(239,\s*68,\s*68,\s*0\.06\)',
        'background:rgba(255,255,255,0.05)',
        content
    )
    content = re.sub(
        r'background:\s*rgba\(239,\s*68,\s*68,\s*0\.12\)',
        'background:rgba(255,255,255,0.1)',
        content
    )
    content = re.sub(
        r'border-color:\s*rgba\(239,\s*68,\s*68,\s*0\.3\)',
        'color:#fff',
        content
    )

    # ===== 10. NAV BADGE - MUTED =====
    content = re.sub(
        r'background:\s*var\(--danger\);\s*color:\s*(?:white|#fff)',
        'background:#9A8C98;color:#fff',
        content
    )

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  FIXED: {fname}")
    else:
        print(f"  No changes: {fname}")

print("\nDone!")