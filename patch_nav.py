# รันครั้งเดียวในโฟลเดอร์โปรเจกต์:  python patch_nav.py   (รันซ้ำได้ ไม่ซ้ำปุ่ม)
# - เพิ่มปุ่ม "🏗️ ผลิตภัณฑ์คอนกรีต" "🏬 คงคลัง MB52" "🔧 งานแก้ไฟ" และ "⚡ มิเตอร์" ใน navbar ของทุกหน้า
# - เพิ่มสีปุ่ม .btn-concrete / .btn-mb52 / .btn-repair / .btn-meter ใน style.css
import glob

BTNS = [
    ('concrete.html', '<a href="concrete.html" class="nav-btn btn-concrete">🏗️ ผลิตภัณฑ์คอนกรีต</a>', 'href="demand.html"'),
    ('mb52.html', '<a href="mb52.html" class="nav-btn btn-mb52">🏬 คงคลัง MB52</a>', 'href="concrete.html"'),
    ('repair.html', '<a href="repair.html" class="nav-btn btn-repair">🔧 งานแก้ไฟ</a>', 'href="mb52.html"'),
    ('meter.html', '<a href="meter.html" class="nav-btn btn-meter">⚡ มิเตอร์</a>', 'href="repair.html"'),
]
CSS = {
    'btn-concrete': ".btn-concrete { background-color: #e67e22; box-shadow: 0 4px 10px rgba(230, 126, 34, 0.3); }",
    'btn-mb52': ".btn-mb52 { background-color: #5c6bc0; box-shadow: 0 4px 10px rgba(92, 107, 192, 0.3); }",
    'btn-repair': ".btn-repair { background-color: #6d4c41; box-shadow: 0 4px 10px rgba(109, 76, 65, 0.3); }",
    'btn-meter': ".btn-meter { background-color: #388e3c; box-shadow: 0 4px 10px rgba(56, 142, 60, 0.3); }",
}

for f in glob.glob('*.html'):
    s = open(f, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in s else '\n'
    changed = False
    for page, btn, after in BTNS:
        if ('href="%s"' % page) in s:
            continue
        out, done = [], False
        for line in s.split(nl):
            out.append(line)
            if not done and after in line and 'nav-btn' in line:
                indent = line[:len(line) - len(line.lstrip())]
                out.append(indent + btn)
                done = True
        if done:
            s = nl.join(out)
            changed = True
    if changed:
        open(f, 'w', encoding='utf-8', newline='').write(s)
        print('patched', f)

css = open('style.css', encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in css else '\n'
add = ''.join(nl + line + nl for key, line in CSS.items() if key not in css)
if add:
    open('style.css', 'a', encoding='utf-8', newline='').write(add)
    print('patched style.css')
