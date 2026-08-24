"""
NetGravity -- Standalone HTML Bundle Generator
==============================================
Inlines CSS stylesheets and JS ES modules into self-contained HTML distribution files.
"""

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(REPO_ROOT, "app", "frontend")

html_path = os.path.join(FRONTEND_DIR, "index.html")
landing_css_path = os.path.join(FRONTEND_DIR, "css", "landing.css")
auth_css_path = os.path.join(FRONTEND_DIR, "css", "auth.css")
style_css_path = os.path.join(FRONTEND_DIR, "css", "style.css")

js_files = [
    "data.js",
    "basemap-data.js",
    "map.js",
    "twin3d.js",
    "charts.js",
    "scenarios.js",
    "agent.js",
    "landing.js",
    "auth.js",
    "ingestion.js",
    "app.js"
]

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

landing_css = ""
if os.path.exists(landing_css_path):
    with open(landing_css_path, "r", encoding="utf-8") as f:
        landing_css = f.read()

auth_css = ""
if os.path.exists(auth_css_path):
    with open(auth_css_path, "r", encoding="utf-8") as f:
        auth_css = f.read()

with open(style_css_path, "r", encoding="utf-8") as f:
    style_css = f.read()

js_combined = []
for jf in js_files:
    p = os.path.join(FRONTEND_DIR, "js", jf)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            code = f.read()
            # Clean local module import statements (leave external library imports intact)
            code = re.sub(r'import\s+[\s\S]*?from\s+[\'"]\.\/[^\'"]+[\'"];?', '', code)
            
            # Clean all forms of export statements
            code = re.sub(r'\bexport\s+async\s+function\s+', 'async function ', code)
            code = re.sub(r'\bexport\s+function\s+', 'function ', code)
            code = re.sub(r'\bexport\s+const\s+', 'const ', code)
            code = re.sub(r'\bexport\s+let\s+', 'let ', code)
            code = re.sub(r'\bexport\s+var\s+', 'var ', code)
            code = re.sub(r'\bexport\s+default\s+', '', code)
            code = re.sub(r'\bexport\s*\{[\s\S]*?\};?', '', code)
            
            js_combined.append(f"/* ═════════ {jf} ═════════ */\n" + code)

# Replace CSS links with inlined style tags
if '<link rel="stylesheet" href="css/landing.css">' in html:
    html = html.replace('<link rel="stylesheet" href="css/landing.css">', f"<style>\n{landing_css}\n</style>")

if '<link rel="stylesheet" href="css/auth.css">' in html:
    html = html.replace('<link rel="stylesheet" href="css/auth.css">', f"<style>\n{auth_css}\n</style>")

css_tag = '<link rel="stylesheet" href="css/style.css">'
html = html.replace(css_tag, f"<style>\n{style_css}\n</style>")

# Replace module script with bundled standard script for universal local file execution
js_script_tag = '<script type="module" src="js/app.js"></script>'
bundled_js = "\n\n".join(js_combined)
html = html.replace(js_script_tag, f'<script>\n{bundled_js}\n</script>')

out_root = os.path.join(REPO_ROOT, "netgravity_standalone.html")
out_frontend = os.path.join(FRONTEND_DIR, "netgravity_standalone.html")
out_app_standalone = os.path.join(REPO_ROOT, "app", "standalone", "netgravity_standalone.html")

for out_p in [out_root, out_frontend, out_app_standalone]:
    os.makedirs(os.path.dirname(out_p), exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote standalone bundle: {out_p} ({len(html)} bytes)")

print("Successfully regenerated all standalone HTML distribution bundles.")
