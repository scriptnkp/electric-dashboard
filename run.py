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
file_budget_p = 'P.txt' # <--- เพิ่มไฟล์งบ P.txt

print("กำลังอ่านไฟล์ Excel และ Txt...")
df_stock = pd.read_excel(file_mb52)
df_demand = pd.read_excel(file_zmb25)
df_proj = pd.read_excel(file_cn43n)
df_me2n = pd.read_excel(file_me2n)

# 2. ฟังก์ชันและ Mapping พื้นฐาน
cat_map = {
    '1-00-001': 'ผลิตภัณฑ์คอนกรีต', '1-00-002': 'ผลิตภัณฑ์คอนกรีต', '1-00-004': 'ผลิตภัณฑ์คอนกรีต', '1-00-005': 'ผลิตภัณฑ์คอนกรีต', '1-00-011': 'ผลิตภัณฑ์คอนกรีต', '1-00-021': 'ผลิตภัณฑ์คอนกรีต',
    '1-02-001': 'สายไฟ', '1-02-002': 'สายไฟ', '1-02-003': 'สายไฟ', '1-02-004': 'สายไฟ', '1-02-005': 'สายไฟ', '1-02-006': 'สายไฟ', '1-02-007': 'สายไฟ', '1-02-008': 'สายไฟ',
    '1-03-000': 'ลูกถ้วย', '1-03-001': 'ลูกถ้วย', '1-03-002': 'ลูกถ้วย', '1-03-003': 'ลูกถ้วย',
    '1-04-000': 'แก้ไฟ', '1-04-001': 'แก้ไฟ', '1-04-002': 'แก้ไฟ', '1-04-003': 'แก้ไฟ',
    '1-05-000': 'หม้อแปลง', '1-05-001': 'หม้อแปลง',
    '1-06-002': 'มิเตอร์ ซีที วีที', '1-06-003': 'มิเตอร์ ซีที วีที', '1-06-004': 'มิเตอร์ ซีที วีที', '1-06-005': 'มิเตอร์ ซีที วีที', '1-06-006': 'มิเตอร์ ซีที วีที', '1-06-007': 'มิเตอร์ ซีที วีที', '1-06-008': 'มิเตอร์ ซีที วีที', '1-06-009': 'มิเตอร์ ซีที วีที',
    '1-06-010': 'อุปกรณ์ประกอบมิเตอร์',
    '1-42-028': 'ใบเสร็จรับเงิน', '1-42-035': 'ใบเสร็จรับเงิน',
    '1-02-030': 'PG', '1-02-018': 'เทป',
    '1-01-011': 'สลักเกลียว', '1-01-012': 'สลักเกลียว', '1-01-013': 'สลักเกลียว', '1-01-014': 'สลักเกลียว', '1-01-015': 'สลักเกลียว', '1-01-016': 'สลักเกลียว',
    '1-07-001': 'ชุดโคมไฟ', '1-07-003': 'ชุดโคมไฟ', '1-08-006': 'โซล่าเซล'
}
def get_category(mat_code): return cat_map.get(str(mat_code)[:8], 'วัสดุอื่นๆ')

def get_project_group(wbs):
    wbs = str(wbs).strip().upper()
    if wbs.startswith('C-68'): return 'ผู้ใช้ไฟ 68'
    elif wbs.startswith('C-69'): return 'ผู้ใช้ไฟ 69'
    elif wbs.startswith('I-67'): return 'ลงทุน 67'
    elif wbs.startswith('I-68'): return 'ลงทุน 68'
    elif wbs.startswith('I-69'): return 'ลงทุน 69'
    elif wbs.startswith('P-NHE03'): return 'คฟม'
    elif wbs.startswith('P-SEZ02'): return 'คพพ' 
    elif wbs.startswith('P-TDD01'): return 'คพจ1'
    elif wbs.startswith('P-TDD02'): return 'คพจ2'
    return 'อื่นๆ'

def get_short_status(x):
    if pd.isna(x): return ""
    s = str(x).strip()
    if not s: return ""
    s_clean = s.replace('//', '').strip()
    parts = s_clean.split()
    if len(parts) > 1: return f"{parts[0]} {parts[-1]}"
    elif len(parts) == 1: return parts[0]
    return ""

# 3. จัดการ WBS และ Dashboard
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

# 4. จัดการ ME2N รับเข้าและจัดสรร
df_me2n_in = df_me2n[df_me2n['โรงงาน'] == 'D060'].copy()
df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'] = pd.to_numeric(df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'], errors='coerce').fillna(0)
df_me2n_in['ที่เก็บสินค้า'] = df_me2n_in['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].apply(lambda x: x.zfill(4) if x.isdigit() else '-')
df_me2n_in['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'] = df_me2n_in['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].fillna('-ไม่ระบุ-')
df_me2n_in['ข้อความส่วนหัว'] = df_me2n_in['ข้อความส่วนหัว'].fillna('')
df_me2n_in['Category'] = df_me2n_in['วัสดุ'].apply(get_category)
me2n_active = df_me2n_in[df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'] > 0].copy()
me2n_summary = me2n_active.groupby(['วัสดุ', 'ข้อความสั้น', 'Category'])['ยังจะถูกส่งมอบ (ปริมาณ)'].sum().reset_index()
me2n_details = me2n_active[['เอกสารการจัดซื้อ', 'ผู้ขาย/โรงงานผู้จัดหาวัสดุ', 'ที่เก็บสินค้า', 'วัสดุ', 'ข้อความสั้น', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'ข้อความส่วนหัว', 'Category']]
me2n_vendors = sorted([str(v) for v in me2n_active['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].unique() if str(v) != '-ไม่ระบุ-'])

df_me2n_out = df_me2n[df_me2n['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].astype(str).str.contains('D060', na=False, case=False)].copy()
df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'] = pd.to_numeric(df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'], errors='coerce').fillna(0)
df_me2n_out['ที่เก็บสินค้า'] = df_me2n_out['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].apply(lambda x: x.zfill(4) if x.isdigit() else '-')
df_me2n_out['ข้อความส่วนหัว'] = df_me2n_out['ข้อความส่วนหัว'].fillna('')
df_me2n_out['Category'] = df_me2n_out['วัสดุ'].apply(get_category)
plant_map = {'D010': 'D010 คลังพัสดุ อุดรธานี', 'D020': 'D020 คลังพัสดุ หนองคาย', 'D030': 'D030 คลังพัสดุ หนองบัวลำภู', 'D040': 'D040 คลังพัสดุ เลย', 'D050': 'D050 คลังพัสดุ สกลนคร', 'D060': 'D060 คลังพัสดุ นครพนม', 'D070': 'D070 คลังพัสดุ บึงกาฬ', 'D090': 'D090 คลังพัสดุ หนองหาน', 'D100': 'D100 คลังพัสดุ พังโคน', 'D110': 'D110 คลังพัสดุ หนองบัวลำภู', 'D120': 'D120 คลังพัสดุ บ้านไผ่', 'D130': 'D130 คลังพัสดุ บึงกาฬ'}
df_me2n_out['โรงงาน'] = df_me2n_out['โรงงาน'].apply(lambda x: plant_map.get(str(x).strip(), str(x).strip())).fillna('-ไม่ระบุ-')
alloc_active = df_me2n_out[df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'] > 0].copy()
alloc_details = alloc_active[['เอกสารการจัดซื้อ', 'โรงงาน', 'ที่เก็บสินค้า', 'วัสดุ', 'ข้อความสั้น', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'ข้อความส่วนหัว', 'Category']]
alloc_plants = sorted([str(v) for v in alloc_active['โรงงาน'].unique() if str(v) != '-ไม่ระบุ-'])

# 5. จัดการ ME2N1 (แผนซื้อ กฟฉ.1 - กรอง DAN)
try:
    df_me2n1 = pd.read_excel(file_me2n1)
    df_me2n1_dan = df_me2n1[df_me2n1['กลุ่มการจัดซื้อ'] == 'DAN'].copy()
    df_me2n1_dan['ยังจะถูกส่งมอบ (ปริมาณ)'] = pd.to_numeric(df_me2n1_dan['ยังจะถูกส่งมอบ (ปริมาณ)'], errors='coerce').fillna(0)
    df_me2n1_dan['ที่เก็บสินค้า'] = df_me2n1_dan['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].apply(lambda x: x.zfill(4) if x.isdigit() else '-')
    df_me2n1_dan['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'] = df_me2n1_dan['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].fillna('-ไม่ระบุ-')
    df_me2n1_dan['ข้อความส่วนหัว'] = df_me2n1_dan['ข้อความส่วนหัว'].fillna('')
    df_me2n1_dan['Category'] = df_me2n1_dan['วัสดุ'].apply(get_category)
    me2n1_active = df_me2n1_dan[df_me2n1_dan['ยังจะถูกส่งมอบ (ปริมาณ)'] > 0].copy()
    me2n1_details = me2n1_active[['เอกสารการจัดซื้อ', 'ผู้ขาย/โรงงานผู้จัดหาวัสดุ', 'ที่เก็บสินค้า', 'วัสดุ', 'ข้อความสั้น', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'ข้อความส่วนหัว', 'Category']]
    me2n1_vendors = sorted([str(v) for v in me2n1_active['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].unique() if str(v) != '-ไม่ระบุ-'])
except Exception as e:
    print(f"Warning: ME2N1 error: {e}")
    me2n1_details = pd.DataFrame()
    me2n1_vendors = []

# ==========================================
# 6. จัดการไฟล์งบเงิน (อ่าน C.txt, I.txt, P.txt)
# ==========================================
budget_data = []

def process_budget_file(file_path, file_type):
    try:
        with open(file_path, 'r', encoding='cp874') as f:
            lines = f.readlines()
            
        for line in lines:
            if line.startswith('|') and 'WBS' not in line and 'รายการ' not in line and 'รวม' not in line:
                parts = line.split('|')
                if len(parts) >= 14:
                    wbs = parts[3].strip()
                    if not wbs: continue
                    
                    def get_val(idx):
                        try: return float(parts[idx].strip().replace(',', ''))
                        except: return 0.0

                    col_remain_11 = get_val(14)
                    
                    # [อัปเดตเงื่อนไขตามที่แจ้ง]
                    # NPN แสดงเสมอ (จากทุกไฟล์ C, I, P)
                    # AED และ POP แสดงเฉพาะถ้ามาจากงบ C (file_type == 'C')
                    show = False
                    if 'NPN' in wbs:
                        show = True
                    elif file_type == 'C' and ('AED' in wbs or 'POP' in wbs):
                        show = True
                    
                    if col_remain_11 > 0 and show:
                        budget_data.append({
                            'WBS': wbs,
                            'Col3': get_val(6),   
                            'Col4': get_val(7),   
                            'Col5': get_val(8),   
                            'Col6': get_val(9),   
                            'Col7': get_val(10),  
                            'Col8': get_val(11),  
                            'Col9': get_val(12),  
                            'Col10': get_val(13), 
                            'Col11': col_remain_11 
                        })
    except Exception as e:
        print(f"Warning: ข้ามการอ่านไฟล์งบเงิน {file_path} ({e})")

# ระบุประเภทไฟล์ตอนเรียกใช้งาน ('C', 'I', 'P')
process_budget_file(file_budget_c, 'C')
process_budget_file(file_budget_i, 'I')
process_budget_file(file_budget_p, 'P')

tz_th = timezone(timedelta(hours=7))
update_time = datetime.now(tz_th).strftime("%d/%m/%Y เวลา %H:%M น.")

# เขียนข้อมูลลงไฟล์ data.js
js_content = f"""// ไฟล์นี้ถูกสร้างอัตโนมัติจาก Python (ห้ามแก้ไขด้วยมือ)
const lastUpdated = "{update_time}";
const pieRawData = {json.dumps(pie_summary.to_dict(orient='records'))};
const mainData = {json.dumps(final_df.to_dict(orient='records'))};
const projectGroups = {json.dumps(project_cols)};
const wbsDataByMat = {json.dumps({mat: grp.to_dict(orient='records') for mat, grp in wbs_details.groupby('วัสดุ')})};
const wbsDataByWbs = {json.dumps({wbs: grp.to_dict(orient='records') for wbs, grp in wbs_details.groupby('WBS')})};
const me2nSummaryData = {json.dumps(me2n_summary.to_dict(orient='records'))};
const me2nDetailsData = {json.dumps(me2n_details.to_dict(orient='records'))};
const me2nVendors = {json.dumps(me2n_vendors)};
const me2n1DetailsData = {json.dumps(me2n1_details.to_dict(orient='records'))};
const me2n1Vendors = {json.dumps(me2n1_vendors)};
const allocDetailsData = {json.dumps(alloc_details.to_dict(orient='records'))};
const allocPlants = {json.dumps(alloc_plants)};
const budgetData = {json.dumps(budget_data)};
"""

with open('data.js', 'w', encoding='utf-8') as f: f.write(js_content)
print(f"สร้างไฟล์ data.js สำเร็จ! (อัปเดตข้อมูลเมื่อ: {update_time})")