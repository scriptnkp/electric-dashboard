import pandas as pd
import json
import os
import re
from datetime import datetime, timezone, timedelta

# 1. ตั้งค่าไฟล์
file_mb52 = '6.mb52.XLSX'
file_zmb25 = '11.zmb25.XLSX'
file_cn43n = '14.CN43N.xlsx'
file_me2n = '12.ME2N.xlsx'
file_me2n1 = '13.ME2N1.xlsx'
file_budget_c = 'C.txt' 
file_budget_i = 'I.txt'
file_budget_p = 'P.txt'
file_budget_n = 'N.txt'
file_z005 = 'z005.txt'     # <--- เพิ่มไฟล์ใหม่
file_n_z005 = 'n-z005.txt' # <--- เพิ่มไฟล์ใหม่

print("กำลังอ่านไฟล์ Excel และ Txt...")
# ... [โค้ดส่วนดึงไฟล์ Excel และ Mapping เหมือนเดิม] ...
df_stock = pd.read_excel(file_mb52)
df_demand = pd.read_excel(file_zmb25)
df_proj = pd.read_excel(file_cn43n)
df_me2n = pd.read_excel(file_me2n)

cat_map = { '1-00-001': 'ผลิตภัณฑ์คอนกรีต', '1-02-001': 'สายไฟ', '1-03-000': 'ลูกถ้วย', '1-04-000': 'แก้ไฟ', '1-05-000': 'หม้อแปลง' }
def get_category(mat_code): return cat_map.get(str(mat_code)[:8], 'วัสดุอื่นๆ')

def get_project_group(wbs):
    wbs = str(wbs).strip().upper()
    if wbs.startswith('C-68'): return 'ผู้ใช้ไฟ 68'
    elif wbs.startswith('C-69'): return 'ผู้ใช้ไฟ 69'
    elif wbs.startswith('P-NHE03'): return 'คฟม'
    elif wbs.startswith('P-SEZ02'): return 'คพพ' 
    return 'อื่นๆ'

def get_short_status(x):
    if pd.isna(x): return ""
    parts = str(x).replace('//', '').strip().split()
    if len(parts) > 1: return f"{parts[0]} {parts[-1]}"
    elif len(parts) == 1: return parts[0]
    return ""

# จัดการข้อมูลความต้องการ
df_demand['Project_Group'] = df_demand['องค์ประกอบ WBS'].apply(get_project_group)
pie_summary = df_demand.groupby('Project_Group')['องค์ประกอบ WBS'].nunique().reset_index().rename(columns={'องค์ประกอบ WBS': 'WBS_Count'})
pivot_demand = df_demand.pivot_table(index='วัสดุ', columns='Project_Group', values='ปริมาณผลต่าง', aggfunc='sum', fill_value=0).reset_index()
project_cols = [col for col in pivot_demand.columns if col != 'วัสดุ']
pivot_demand['Total_Demand'] = pivot_demand[project_cols].sum(axis=1)

mat_desc_demand = df_demand[['วัสดุ', 'คำอธิบายวัสดุ']].replace(r'^\s*$', pd.NA, regex=True).dropna(subset=['คำอธิบายวัสดุ']).drop_duplicates(subset=['วัสดุ'])
mat_desc_stock = df_stock[['วัสดุ', 'คำอธิบายวัสดุ']].replace(r'^\s*$', pd.NA, regex=True).dropna(subset=['คำอธิบายวัสดุ']).drop_duplicates(subset=['วัสดุ'])
mat_desc = pd.concat([mat_desc_demand, mat_desc_stock]).drop_duplicates(subset=['วัสดุ'], keep='first')

target_locs = ['0021', '0022', '0023', '0024', '0025', '6001', '6002', '6003', '6004', '6006', '6007', '6008', '6009', '6010', '6011']
df_stock['ที่เก็บสินค้า'] = df_stock['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].str.zfill(4)
stock_summary = df_stock[(df_stock['โรงงาน'] == 'D060') & (df_stock['ที่เก็บสินค้า'].isin(target_locs))].groupby('วัสดุ')['ที่ใช้ได้'].sum().reset_index().rename(columns={'ที่ใช้ได้': 'Stock'})

final_df = pd.merge(pivot_demand, stock_summary, on='วัสดุ', how='outer').fillna(0)
final_df = pd.merge(final_df, mat_desc, on='วัสดุ', how='left').fillna('-ไม่ระบุ-')
final_df['Balance'] = final_df['Stock'] - final_df['Total_Demand']
final_df['Category'] = final_df['วัสดุ'].apply(get_category)
for col in project_cols:
    if col not in final_df.columns: final_df[col] = 0

df_proj['Status_Short'] = df_proj['สถานะ'].apply(get_short_status)
wbs_pending = df_demand[df_demand['ปริมาณผลต่าง'] != 0].groupby('องค์ประกอบ WBS')['วัสดุ'].nunique().reset_index(name='PendingCount')
wbs_details = pd.merge(df_demand[['วัสดุ', 'องค์ประกอบ WBS', 'โครงข่าย', 'ปริมาณผลต่าง']], df_proj[['องค์ประกอบ WBS', 'ชื่อ', 'Status_Short', 'ผู้สมัคร']], on='องค์ประกอบ WBS', how='left')
wbs_details = pd.merge(wbs_details, wbs_pending, on='องค์ประกอบ WBS', how='left').fillna(0)
wbs_details = pd.merge(wbs_details, final_df[['วัสดุ', 'คำอธิบายวัสดุ', 'Stock', 'Balance']], on='วัสดุ', how='left').fillna('-')
wbs_details.rename(columns={'องค์ประกอบ WBS': 'WBS', 'โครงข่าย': 'Network', 'ปริมาณผลต่าง': 'Qty', 'ชื่อ': 'Project_Name', 'Status_Short': 'Status', 'ผู้สมัคร': 'Applicant', 'คำอธิบายวัสดุ': 'MatDesc'}, inplace=True)
wbs_details['Network'] = wbs_details['Network'].fillna('-').astype(str).str.replace(r'\.0$', '', regex=True)

# จัดการ ME2N
df_me2n_in = df_me2n[df_me2n['โรงงาน'] == 'D060'].copy()
df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'] = pd.to_numeric(df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'], errors='coerce').fillna(0)
df_me2n_in['ที่เก็บสินค้า'] = df_me2n_in['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].apply(lambda x: x.zfill(4) if x.isdigit() else '-')
me2n_active = df_me2n_in[df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'] > 0].copy()
me2n_summary = me2n_active.groupby(['วัสดุ', 'ข้อความสั้น'])['ยังจะถูกส่งมอบ (ปริมาณ)'].sum().reset_index()
me2n_details = me2n_active[['เอกสารการจัดซื้อ', 'ผู้ขาย/โรงงานผู้จัดหาวัสดุ', 'ที่เก็บสินค้า', 'วัสดุ', 'ข้อความสั้น', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'ข้อความส่วนหัว']]
me2n_vendors = []

df_me2n_out = df_me2n[df_me2n['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].astype(str).str.contains('D060', na=False, case=False)].copy()
df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'] = pd.to_numeric(df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'], errors='coerce').fillna(0)
alloc_active = df_me2n_out[df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'] > 0].copy()
alloc_details = alloc_active[['เอกสารการจัดซื้อ', 'โรงงาน', 'ที่เก็บสินค้า', 'วัสดุ', 'ข้อความสั้น', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'ข้อความส่วนหัว']]
alloc_plants = []
me2n1_details = pd.DataFrame(); me2n1_vendors = []

# ไฟล์งบการเงิน
budget_data = []

# ==========================================
# จัดการไฟล์รายการจัดซื้อ (z005.txt และ n-z005.txt)
# ==========================================
purchase_data = []

# 1. อ่านชื่อบริษัทจาก n-z005
vendor_map = {}
try:
    with open(file_n_z005, 'r', encoding='utf-8') as f: lines = f.readlines()
except:
    try:
        with open(file_n_z005, 'r', encoding='cp874') as f: lines = f.readlines()
    except Exception as e:
        print(f"Warning: อ่านไฟล์ n-z005.txt ไม่ได้ ({e})")
        lines = []

for line in lines:
    if '|' in line and 'รหัส' not in line:
        parts = line.split('|')
        if len(parts) >= 2:
            vendor_map[parts[0].strip()] = parts[1].strip()

# 2. อ่านข้อมูลจัดซื้อจาก z005
current_date = datetime(2026, 5, 1) # ใช้วันที่ 01.05.2026 เป็นเกณฑ์ตั้งต้น
try:
    with open(file_z005, 'r', encoding='utf-8') as f: lines = f.readlines()
except:
    try:
        with open(file_z005, 'r', encoding='cp874') as f: lines = f.readlines()
    except Exception as e:
        print(f"Warning: อ่านไฟล์ z005.txt ไม่ได้ ({e})")
        lines = []

for line in lines:
    if line.startswith('|') and 'องค์ประกอบ WBS' not in line:
        parts = line.split('|')
        if len(parts) >= 21:
            wbs = parts[3].strip()
            mat = parts[5].strip()
            desc = parts[6].strip()
            pr_num = parts[7].strip()
            po_num = parts[8].strip()
            gr_ir = parts[10].strip()
            
            # แปลงตัวเลข
            def get_num(val):
                try: return float(val.strip().replace(',', ''))
                except: return 0.0
                
            pr_qty = get_num(parts[13])
            pr_price = get_num(parts[14])
            po_date_str = parts[15].strip()
            po_qty = get_num(parts[16])
            po_price = get_num(parts[17])
            vendor = parts[20].strip()
            
            # เงื่อนไข: ให้ GR ดูจากช่องว่าง (คือยังไม่รับของเข้า)
            if gr_ir == '':
                # ถ้ามี PO โชว์ PO, ถ้าไม่มี โชว์ PR
                has_po = len(po_num) > 0
                
                doc_num = po_num if has_po else pr_num
                doc_type = 'PO' if has_po else 'PR'
                qty = po_qty if has_po and po_qty > 0 else pr_qty
                price = po_price if has_po and po_price > 0 else pr_price
                amount = qty * price
                
                # แมตช์ชื่อบริษัท
                company_name = vendor_map.get(vendor, vendor) if vendor else '-'
                
                # คำนวณวันเกินกำหนด
                overdue_days = '-'
                if po_date_str:
                    try:
                        po_date = datetime.strptime(po_date_str, '%d.%m.%Y')
                        diff = (current_date - po_date).days
                        if diff > 0:
                            overdue_days = diff
                        else:
                            overdue_days = 0 # ยังไม่ถึงกำหนด
                    except:
                        pass
                
                purchase_data.append({
                    'WBS': wbs,
                    'Company': company_name,
                    'DocNum': doc_num,
                    'DocType': doc_type,
                    'Mat': mat,
                    'Desc': desc,
                    'Qty': qty,
                    'Amount': amount,
                    'DeliveryDate': po_date_str if po_date_str else '-',
                    'OverdueDays': overdue_days
                })

tz_th = timezone(timedelta(hours=7))
update_time = datetime.now(tz_th).strftime("%d/%m/%Y เวลา %H:%M น.")

# เขียนข้อมูลลงไฟล์ data.js (เพิ่ม purchaseData)
js_content = f"""// ไฟล์นี้ถูกสร้างอัตโนมัติจาก Python (ห้ามแก้ไขด้วยมือ)
const lastUpdated = "{update_time}";
const pieRawData = {json.dumps(pie_summary.to_dict(orient='records'))};
const mainData = {json.dumps(final_df.to_dict(orient='records'))};
const projectGroups = {json.dumps(project_cols)};
const wbsDataByMat = {json.dumps({mat: grp.to_dict(orient='records') for mat, grp in wbs_details.groupby('วัสดุ')})};
const wbsDataByWbs = {json.dumps({wbs: grp.to_dict(orient='records') for wbs, grp in wbs_details.groupby('WBS')})};
const me2nSummaryData = {json.dumps(me2n_summary.to_dict(orient='records'))};
const me2nDetailsData = {json.dumps(me2n_details.to_dict(orient='records'))};
const me2nVendors = [];
const me2n1DetailsData = [];
const me2n1Vendors = [];
const allocDetailsData = {json.dumps(alloc_details.to_dict(orient='records'))};
const allocPlants = [];
const budgetData = [];
const purchaseData = {json.dumps(purchase_data)};
"""

with open('data.js', 'w', encoding='utf-8') as f: f.write(js_content)
print(f"สร้างไฟล์ data.js สำเร็จ! (อัปเดตข้อมูลเมื่อ: {update_time})")
