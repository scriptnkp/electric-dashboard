# รันครั้งเดียวในโฟลเดอร์โปรเจกต์: python patch_nav.py
# - เพิ่มปุ่ม "🏗️ ผลิตภัณฑ์คอนกรีต" ใน navbar ของทุกหน้า (ต่อจากปุ่มตารางความต้องการ)
# - เพิ่มสีปุ่ม .btn-concrete ใน style.css
import glob

BTN = '<a href="concrete.html" class="nav-btn btn-concrete">🏗️ ผลิตภัณฑ์คอนกรีต</a>'
CSS = "\n.btn-concrete { background-color: #e67e22; box-shadow: 0 4px 10px rgba(230, 126, 34, 0.3); }\n"

for f in glob.glob('*.html'):
    if f == 'concrete.html':
        continue
    s = open(f, encoding='utf-8', newline='').read()
    if 'concrete.html' in s or 'href="demand.html"' not in s:
        continue
    nl = '\r\n' if '\r\n' in s else '\n'
    out, done = [], False
    for line in s.split(nl):
        out.append(line)
        if not done and 'href="demand.html"' in line and 'nav-btn' in line:
            indent = line[:len(line) - len(line.lstrip())]
            out.append(indent + BTN)
            done = True
    open(f, 'w', encoding='utf-8', newline='').write(nl.join(out))
    print('patched', f)

css = open('style.css', encoding='utf-8', newline='').read()
if 'btn-concrete' not in css:
    open('style.css', 'a', encoding='utf-8', newline='').write(CSS.replace('\n', '\r\n' if '\r\n' in css else '\n'))
    print('patched style.css')
