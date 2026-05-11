import pandas as pd
import json
import os
import re
from datetime import datetime, timezone, timedelta

# 1. ตั้งค่าไฟล์เป็น .txt ทั้งหมด 100%
file_mb52 = '6.mb52.txt'       
file_zmb25 = '11.zmb25.txt'      
file_cn43n = '14.CN43N.txt'     
file_me2n = '12.ME2N.txt'       
file_me2n1 = '13.ME2N1.txt'     
file_budget_c = 'C.txt' 
file_budget_i = 'I.txt'
file_budget_p = 'P.txt'
file_budget_n = 'N.txt'
file_z005 = 'z005.txt'
file_n_z005 = 'n-z005.txt'
file_z048 = 'z048.txt' 

print("กำลังอ่านไฟล์ TXT ทั้งหมด...")

def read_sap_txt(filepath):
    data = []
    headers = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f: lines = f.readlines()
    except:
        try:
            with open(filepath, 'r', encoding='cp874') as f: lines = f.readlines()
        except: return pd.DataFrame()
            
    for line in lines:
        if line.startswith('|'):
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if not headers:
                if any(k in p for p in parts for k in ['วัสดุ', 'องค์ประกอบ WBS', 'รง.', 'Lev', 'ค่าแรง']):
                    headers = [h.strip() for h in parts]
            elif headers:
                if not parts[0].startswith('---'):
                    if len(parts) == len(headers):
                        data.append(parts)
                    elif len(parts) > len(headers):
                        idx = -1
                        if 'ข้อความส่วนหัว' in headers: idx = headers.index('ข้อความส่วนหัว')
                        elif 'ชื่อ' in headers: idx = headers.index('ชื่อ')
                        if idx != -1:
                            extra = len(parts) - len(headers)
                            merged = ' | '.join(parts[idx : idx + extra + 1])
                            new_parts = parts[:idx] + [merged] + parts[idx + extra + 1:]
                            if len(new_parts) == len(headers): data.append(new_parts)
    if headers and data:
        return pd.DataFrame(data, columns=headers)
    return pd.DataFrame()

def parse_sap_num(x):
    s = str(x).replace(',', '').strip()
    if not s: return 0.0
    if s.endswith('-'): s = '-' + s[:-1]
    try: return float(s)
    except: return 0.0

def ensure_cols(df, cols, default_val='-'):
    for c in cols:
        if c not in df.columns: df[c] = default_val
    return df

df_stock = read_sap_txt(file_mb52)
df_stock.rename(columns={'Plnt': 'โรงงาน', 'SLoc': 'ที่เก็บสินค้า'}, inplace=True)
df_stock = ensure_cols(df_stock, ['วัสดุ', 'คำอธิบายวัสดุ', 'โรงงาน', 'ที่เก็บสินค้า', 'ที่ใช้ได้'], 0)
df_stock['ที่ใช้ได้'] = df_stock['ที่ใช้ได้'].apply(parse_sap_num)

df_demand = read_sap_txt(file_zmb25)
df_demand.rename(columns={'ปริมาณต่าง': 'ปริมาณผลต่าง'}, inplace=True)
df_demand = ensure_cols(df_demand, ['วัสดุ', 'คำอธิบายวัสดุ', 'องค์ประกอบ WBS', 'โครงข่าย', 'ปริมาณผลต่าง'], 0)
df_demand['ปริมาณผลต่าง'] = df_demand['ปริมาณผลต่าง'].apply(parse_sap_num)

df_proj = read_sap_txt(file_cn43n)
df_proj = ensure_cols(df_proj, ['องค์ประกอบ WBS', 'ชื่อ', 'สถานะ', 'ผู้สมัคร', 'วท.ชำระ', 'Basic strt'])

# === เพิ่มการอ่านไฟล์ z048 เพื่อคำนวณค่าใช้จ่าย (ดึงตัวย่อยมาด้วย) ===
df_z048 = read_sap_txt(file_z048)
df_z048 = ensure_cols(df_z048, ['WBS', 'Network', 'Pln.ค่าแรง', 'Pln.ค่าควบคุมงาน', 'Pln.ค่าขนส่ง', 'Pln.ค่าเบ็ดเตล็ด', 'Act.ค่าแรง', 'Act.ค่าควบคุมงาน', 'Act.ค่าขนส่ง', 'Act.ค่าเบ็ดเตล็ด'], 0)

if not df_z048.empty:
    df_z048['Network'] = df_z048['Network'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_z048['WBS'] = df_z048['WBS'].astype(str).str.strip()
    
    for col in ['Pln.ค่าแรง', 'Pln.ค่าควบคุมงาน', 'Pln.ค่าขนส่ง', 'Pln.ค่าเบ็ดเตล็ด', 'Act.ค่าแรง', 'Act.ค่าควบคุมงาน', 'Act.ค่าขนส่ง', 'Act.ค่าเบ็ดเตล็ด']:
        df_z048[col] = df_z048[col].apply(parse_sap_num)
        
    df_z048['Pln.Total'] = df_z048['Pln.ค่าแรง'] + df_z048['Pln.ค่าควบคุมงาน'] + df_z048['Pln.ค่าขนส่ง'] + df_z048['Pln.ค่าเบ็ดเตล็ด']
    df_z048['Act.Total'] = df_z048['Act.ค่าแรง'] + df_z048['Act.ค่าควบคุมงาน'] + df_z048['Act.ค่าขนส่ง'] + df_z048['Act.ค่าเบ็ดเตล็ด']
    
    # รวมค่าใช้จ่ายเข้า WBS แบบแยกรายการ
    cost_by_wbs = df_z048[df_z048['Network'] != ''].groupby('WBS').agg({
        'Pln.Total': 'sum',
        'Act.Total': 'sum',
        'Act.ค่าแรง': 'sum',
        'Act.ค่าควบคุมงาน': 'sum',
        'Act.ค่าขนส่ง': 'sum',
        'Act.ค่าเบ็ดเตล็ด': 'sum'
    }).reset_index()
else:
    cost_by_wbs = pd.DataFrame(columns=['WBS', 'Pln.Total', 'Act.Total', 'Act.ค่าแรง', 'Act.ค่าควบคุมงาน', 'Act.ค่าขนส่ง', 'Act.ค่าเบ็ดเตล็ด'])

renames_me2n = {'รง.': 'โรงงาน', 'ผู้ขาย/โรงงานจัดหา': 'ผู้ขาย/โรงงานผู้จัดหาวัสดุ', 'SLoc': 'ที่เก็บสินค้า', 'เอกสารซื้อ': 'เอกสารการจัดซื้อ', 'To be del.': 'ยังจะถูกส่งมอบ (ปริมาณ)', 'PGr': 'กลุ่มการจัดซื้อ', 'วันส่งมอบ': 'วันที่ส่งมอบ'}
df_me2n = read_sap_txt(file_me2n)
df_me2n.rename(columns=renames_me2n, inplace=True)
df_me2n = ensure_cols(df_me2n, ['โรงงาน', 'ผู้ขาย/โรงงานผู้จัดหาวัสดุ', 'ที่เก็บสินค้า', 'เอกสารการจัดซื้อ', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'กลุ่มการจัดซื้อ', 'วันที่ส่งมอบ', 'วัสดุ', 'ข้อความสั้น', 'ข้อความส่วนหัว'])

df_me2n1 = read_sap_txt(file_me2n1)
df_me2n1.rename(columns=renames_me2n, inplace=True)
df_me2n1 = ensure_cols(df_me2n1, ['โรงงาน', 'ผู้ขาย/โรงงานผู้จัดหาวัสดุ', 'ที่เก็บสินค้า', 'เอกสารการจัดซื้อ', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'กลุ่มการจัดซื้อ', 'วันที่ส่งมอบ', 'วัสดุ', 'ข้อความสั้น', 'ข้อความส่วนหัว'])

cat_map = {'1-00-001': 'ผลิตภัณฑ์คอนกรีต', '1-02-001': 'สายไฟ', '1-03-000': 'ลูกถ้วย', '1-04-000': 'แก้ไฟ', '1-05-000': 'หม้อแปลง'}
def get_category(mat_code): return cat_map.get(str(mat_code)[:8], 'วัสดุอื่นๆ')
def get_short_status(x):
    if pd.isna(x) or str(x) == '-': return "-"
    parts = str(x).replace('//', '').strip().split()
    if len(parts) > 1: return f"{parts[0]} {parts[-1]}"
    elif len(parts) == 1: return parts[0]
    return "-"

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

def get_branch(wbs):
    wbs = str(wbs).upper()
    if 'NPN' in wbs: return 'นครพนม'
    if 'TPN' in wbs: return 'ธาตุพนม'
    if 'NGE' in wbs: return 'นาแก'
    if 'BPG' in wbs: return 'บ้านแพง'
    return 'อื่นๆ'

def get_team(name):
    name = str(name).strip()
    match = re.search(r'([a-zA-Z]+)[^a-zA-Z]*$', name)
    if match: return match.group(1).upper()
    return '-'

target_locs = ['0021', '0022', '0023', '0024', '0025', '6001', '6002', '6003', '6004', '6006', '6007', '6008', '6009', '6010', '6011']
df_stock['ที่เก็บสินค้า'] = df_stock['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].str.zfill(4)
stock_summary = df_stock[(df_stock['โรงงาน'] == 'D060') & (df_stock['ที่เก็บสินค้า'].isin(target_locs))].groupby('วัสดุ')['ที่ใช้ได้'].sum().reset_index().rename(columns={'ที่ใช้ได้': 'Stock'})

df_demand_pending = df_demand[df_demand['ปริมาณผลต่าง'] > 0].copy()

if not df_demand_pending.empty:
    wbs_summary_grp = df_demand_pending.groupby('องค์ประกอบ WBS').agg({'โครงข่าย': 'first', 'วัสดุ': 'nunique'}).reset_index().rename(columns={'วัสดุ': 'PendingItems'})
else:
    wbs_summary_grp = pd.DataFrame(columns=['องค์ประกอบ WBS', 'โครงข่าย', 'PendingItems'])

wbs_summary_df = pd.merge(wbs_summary_grp, df_proj, on='องค์ประกอบ WBS', how='left').fillna('-')
wbs_summary_df.rename(columns={'องค์ประกอบ WBS': 'WBS'}, inplace=True)
wbs_summary_df = ensure_cols(wbs_summary_df, ['ชื่อ', 'สถานะ', 'ผู้สมัคร', 'วท.ชำระ', 'Basic strt'])

wbs_summary_df['Branch'] = wbs_summary_df['WBS'].apply(get_branch)
wbs_summary_df['Team'] = wbs_summary_df['ชื่อ'].apply(get_team)
wbs_summary_df['Supervisor'] = wbs_summary_df['ผู้สมัคร'].replace('', '-').fillna('-')
wbs_summary_df['Status_Short'] = wbs_summary_df['สถานะ'].apply(get_short_status)
wbs_summary_df['Network'] = wbs_summary_df['โครงข่าย'].fillna('-').astype(str).str.replace(r'\.0$', '', regex=True)

# จับคู่ค่าใช้จ่ายเข้ากับ WBS
wbs_summary_df = pd.merge(wbs_summary_df, cost_by_wbs, on='WBS', how='left').fillna(0)

# จัดรูปแบบ JSON ให้เก็บรายละเอียดส่งไปตีความที่หน้าเว็บ
def format_cost(row):
    act = float(row.get('Act.Total', 0))
    pln = float(row.get('Pln.Total', 0))
    act_labor = float(row.get('Act.ค่าแรง', 0))
    act_control = float(row.get('Act.ค่าควบคุมงาน', 0))
    act_transport = float(row.get('Act.ค่าขนส่ง', 0))
    act_misc = float(row.get('Act.ค่าเบ็ดเตล็ด', 0))

    if pln == 0:
        if act == 0: return "-"
        pct_text = f"100% = {act:,.0f}"
        remain = 0
    else:
        pct = (act / pln) * 100
        pct_text = f"{pct:.0f}% = {act:,.0f}"
        remain = pln - act

    return json.dumps({
        'text': pct_text,
        'pln': pln,
        'act': act,
        'remain': remain,
        'labor': act_labor,
        'control': act_control,
        'transport': act_transport,
        'misc': act_misc
    })

wbs_summary_df['CostData'] = wbs_summary_df.apply(format_cost, axis=1)

wbs_summary_data = []
for _, r in wbs_summary_df.iterrows():
    wbs_summary_data.append({
        'WBS': str(r['WBS']),
        'Network': str(r['Network']),
        'ProjectName': str(r['ชื่อ']),
        'Status': str(r['Status_Short']),
        'PendingItems': float(r['PendingItems']),
        'PayDate': str(r['วท.ชำระ']),
        'BasicStart': str(r['Basic strt']),
        'Branch': str(r['Branch']),
        'Supervisor': str(r['Supervisor']),
        'Team': str(r['Team']),
        'CostData': str(r['CostData']) # ส่งข้อความ JSON ค่าใช้จ่ายออกไป
    })

mat_desc_demand = df_demand[['วัสดุ', 'คำอธิบายวัสดุ']].copy()
mat_desc_stock = df_stock[['วัสดุ', 'คำอธิบายวัสดุ']].copy()
mat_desc = pd.concat([mat_desc_demand, mat_desc_stock])
mat_desc['คำอธิบายวัสดุ'] = mat_desc['คำอธิบายวัสดุ'].astype(str).replace(r'^\s*$', pd.NA, regex=True)
mat_desc = mat_desc.dropna(subset=['คำอธิบายวัสดุ']).drop_duplicates(subset=['วัสดุ'], keep='first')

demand_details = pd.merge(df_demand_pending.drop(columns=['คำอธิบายวัสดุ'], errors='ignore'), stock_summary, on='วัสดุ', how='left').fillna(0)
demand_details = pd.merge(demand_details, mat_desc, on='วัสดุ', how='left').fillna('-ไม่ระบุ-')
demand_details['Balance'] = demand_details['Stock'] - demand_details['ปริมาณผลต่าง']
demand_details.rename(columns={'องค์ประกอบ WBS': 'WBS', 'ปริมาณผลต่าง': 'Qty', 'คำอธิบายวัสดุ': 'MatDesc'}, inplace=True)
demand_details_data = demand_details[['WBS', 'วัสดุ', 'MatDesc', 'Qty', 'Stock', 'Balance']].to_dict(orient='records')

df_demand['Project_Group'] = df_demand['องค์ประกอบ WBS'].apply(get_project_group)
pie_summary = df_demand.groupby('Project_Group')['องค์ประกอบ WBS'].nunique().reset_index().rename(columns={'องค์ประกอบ WBS': 'WBS_Count'})
pivot_demand = df_demand.pivot_table(index='วัสดุ', columns='Project_Group', values='ปริมาณผลต่าง', aggfunc='sum', fill_value=0).reset_index()
project_cols = [col for col in pivot_demand.columns if col != 'วัสดุ']
if project_cols: pivot_demand['Total_Demand'] = pivot_demand[project_cols].sum(axis=1)
else: pivot_demand['Total_Demand'] = 0

final_df = pd.merge(pivot_demand, stock_summary, on='วัสดุ', how='outer').fillna(0)
final_df = pd.merge(final_df, mat_desc, on='วัสดุ', how='left').fillna('-ไม่ระบุ-')
final_df = ensure_cols(final_df, ['Stock', 'Total_Demand'], 0)
final_df['Balance'] = final_df['Stock'] - final_df['Total_Demand']
final_df['Category'] = final_df['วัสดุ'].apply(get_category)
final_df.rename(columns={'คำอธิบายวัสดุ': 'MatDesc'}, inplace=True)
for col in project_cols:
    if col not in final_df.columns: final_df[col] = 0

df_proj['Status_Short'] = df_proj['สถานะ'].apply(get_short_status)
wbs_details = pd.merge(df_demand[['วัสดุ', 'องค์ประกอบ WBS', 'โครงข่าย', 'ปริมาณผลต่าง']], df_proj[['องค์ประกอบ WBS', 'ชื่อ', 'สถานะ', 'ผู้สมัคร']], on='องค์ประกอบ WBS', how='left')
wbs_details = pd.merge(wbs_details, df_demand[df_demand['ปริมาณผลต่าง'] != 0].groupby('องค์ประกอบ WBS')['วัสดุ'].nunique().reset_index(name='PendingCount'), on='องค์ประกอบ WBS', how='left').fillna(0)
wbs_details = pd.merge(wbs_details, final_df[['วัสดุ', 'Stock', 'Balance', 'MatDesc']], on='วัสดุ', how='left').fillna('-')
wbs_details['Status_Short'] = wbs_details['สถานะ'].apply(get_short_status)
wbs_details.rename(columns={'องค์ประกอบ WBS': 'WBS', 'โครงข่าย': 'Network', 'ปริมาณผลต่าง': 'Qty', 'ชื่อ': 'Project_Name', 'Status_Short': 'Status', 'ผู้สมัคร': 'Applicant'}, inplace=True)
wbs_details['Network'] = wbs_details['Network'].fillna('-').astype(str).str.replace(r'\.0$', '', regex=True)

df_me2n_in = df_me2n[df_me2n['โรงงาน'] == 'D060'].copy() if not df_me2n.empty else pd.DataFrame()
if not df_me2n_in.empty:
    df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'] = df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'].apply(parse_sap_num)
    df_me2n_in['ที่เก็บสินค้า'] = df_me2n_in['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].apply(lambda x: x.zfill(4) if x.isdigit() else '-')
    df_me2n_in['Category'] = df_me2n_in['วัสดุ'].apply(get_category)
me2n_active = df_me2n_in[df_me2n_in['ยังจะถูกส่งมอบ (ปริมาณ)'] > 0].copy() if not df_me2n_in.empty else pd.DataFrame()
me2n_summary = me2n_active.groupby(['วัสดุ', 'ข้อความสั้น', 'Category'])['ยังจะถูกส่งมอบ (ปริมาณ)'].sum().reset_index() if not me2n_active.empty else pd.DataFrame()
me2n_details = me2n_active[['เอกสารการจัดซื้อ', 'ผู้ขาย/โรงงานผู้จัดหาวัสดุ', 'ที่เก็บสินค้า', 'วัสดุ', 'ข้อความสั้น', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'ข้อความส่วนหัว', 'Category']] if not me2n_active.empty else pd.DataFrame()
me2n_vendors = sorted([str(v) for v in me2n_active['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].unique() if str(v) != '-ไม่ระบุ-']) if not me2n_active.empty else []

df_me2n_out = df_me2n[df_me2n['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].astype(str).str.contains('D060', na=False, case=False)].copy() if not df_me2n.empty else pd.DataFrame()
if not df_me2n_out.empty:
    df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'] = df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'].apply(parse_sap_num)
    df_me2n_out['ที่เก็บสินค้า'] = df_me2n_out['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].apply(lambda x: x.zfill(4) if x.isdigit() else '-')
    df_me2n_out['Category'] = df_me2n_out['วัสดุ'].apply(get_category)
    plant_map = {'D010': 'D010 คลังพัสดุ อุดรธานี', 'D020': 'D020 คลังพัสดุ หนองคาย', 'D030': 'D030 คลังพัสดุ หนองบัวลำภู', 'D040': 'D040 คลังพัสดุ เลย', 'D050': 'D050 คลังพัสดุ สกลนคร', 'D060': 'D060 คลังพัสดุ นครพนม', 'D070': 'D070 คลังพัสดุ บึงกาฬ', 'D090': 'D090 คลังพัสดุ หนองหาน', 'D100': 'D100 คลังพัสดุ พังโคน', 'D110': 'D110 คลังพัสดุ หนองบัวลำภู', 'D120': 'D120 คลังพัสดุ บ้านไผ่', 'D130': 'D130 คลังพัสดุ บึงกาฬ'}
    df_me2n_out['โรงงาน'] = df_me2n_out['โรงงาน'].apply(lambda x: plant_map.get(str(x).strip(), str(x).strip())).fillna('-ไม่ระบุ-')
alloc_active = df_me2n_out[df_me2n_out['ยังจะถูกส่งมอบ (ปริมาณ)'] > 0].copy() if not df_me2n_out.empty else pd.DataFrame()
alloc_details = alloc_active[['เอกสารการจัดซื้อ', 'โรงงาน', 'ที่เก็บสินค้า', 'วัสดุ', 'ข้อความสั้น', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'ข้อความส่วนหัว', 'Category']] if not alloc_active.empty else pd.DataFrame()
alloc_plants = sorted([str(v) for v in alloc_active['โรงงาน'].unique() if str(v) != '-ไม่ระบุ-']) if not alloc_active.empty else []

me2n1_due_dates = {}
if not df_me2n1.empty:
    if 'วันที่ส่งมอบ' in df_me2n1.columns and 'เอกสารการจัดซื้อ' in df_me2n1.columns:
        for _, r in df_me2n1.iterrows():
            po_id = str(r['เอกสารการจัดซื้อ']).split('.')[0].strip()
            mat_id = str(r.get('วัสดุ', '')).strip()
            date_val = str(r['วันที่ส่งมอบ']).strip()
            if date_val and date_val != '-' and date_val != 'nan':
                try:
                    d_obj = datetime.strptime(date_val, '%d.%m.%Y')
                    d_str = d_obj.strftime('%d.%m.%Y')
                    me2n1_due_dates[po_id] = (d_str, d_obj)
                    if mat_id: me2n1_due_dates[f"{po_id}_{mat_id}"] = (d_str, d_obj)
                except: pass

    df_me2n1_dan = df_me2n1[df_me2n1['กลุ่มการจัดซื้อ'] == 'DAN'].copy()
    df_me2n1_dan['ยังจะถูกส่งมอบ (ปริมาณ)'] = df_me2n1_dan['ยังจะถูกส่งมอบ (ปริมาณ)'].apply(parse_sap_num)
    df_me2n1_dan['ที่เก็บสินค้า'] = df_me2n1_dan['ที่เก็บสินค้า'].astype(str).str.split('.').str[0].apply(lambda x: x.zfill(4) if x.isdigit() else '-')
    df_me2n1_dan['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'] = df_me2n1_dan['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].fillna('-ไม่ระบุ-')
    df_me2n1_dan['ข้อความส่วนหัว'] = df_me2n1_dan['ข้อความส่วนหัว'].fillna('')
    df_me2n1_dan['Category'] = df_me2n1_dan['วัสดุ'].apply(get_category)
    me2n1_active = df_me2n1_dan[df_me2n1_dan['ยังจะถูกส่งมอบ (ปริมาณ)'] > 0].copy()
    me2n1_details = me2n1_active[['เอกสารการจัดซื้อ', 'ผู้ขาย/โรงงานผู้จัดหาวัสดุ', 'ที่เก็บสินค้า', 'วัสดุ', 'ข้อความสั้น', 'ยังจะถูกส่งมอบ (ปริมาณ)', 'ข้อความส่วนหัว', 'Category']]
    me2n1_vendors = sorted([str(v) for v in me2n1_active['ผู้ขาย/โรงงานผู้จัดหาวัสดุ'].unique() if str(v) != '-ไม่ระบุ-'])
else:
    me2n1_details = pd.DataFrame(); me2n1_vendors = []

wbs_names_map = {}
try:
    with open(file_budget_n, 'r', encoding='utf-8') as f: lines = f.readlines()
except:
    try:
        with open(file_budget_n, 'r', encoding='cp874') as f: lines = f.readlines()
    except: lines = []

for line in lines:
    if line.startswith('|') and 'องค์ประกอบ WBS' not in line:
        parts = line.split('|')
        if len(parts) > 3:
            w = parts[2].strip()
            name = parts[3].strip()
            if w and name: wbs_names_map[w] = name

budget_data = []
def process_budget_file(file_path, file_type):
    try:
        with open(file_path, 'r', encoding='cp874') as f: lines = f.readlines()
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
                    show = False
                    if 'NPN' in wbs: show = True
                    elif file_type == 'C' and ('AED' in wbs or 'POP' in wbs): show = True
                    if col_remain_11 > 0 and show:
                        budget_data.append({
                            'WBS': wbs, 'Project_Name': wbs_names_map.get(wbs, '-'),
                            'Col3': get_val(6), 'Col4': get_val(7), 'Col5': get_val(8), 'Col6': get_val(9),   
                            'Col7': get_val(10), 'Col8': get_val(11), 'Col9': get_val(12), 'Col10': get_val(13), 
                            'Col11': col_remain_11 
                        })
    except: pass

process_budget_file(file_budget_c, 'C')
process_budget_file(file_budget_i, 'I')
process_budget_file(file_budget_p, 'P')

purchase_data = []
vendor_map = {}
try:
    with open(file_n_z005, 'r', encoding='utf-8') as f: lines = f.readlines()
except:
    try:
        with open(file_n_z005, 'r', encoding='cp874') as f: lines = f.readlines()
    except: lines = []

for line in lines:
    if '|' in line and 'รหัส' not in line:
        parts = line.split('|')
        if len(parts) >= 2: vendor_map[parts[0].strip()] = parts[1].strip()

current_date = datetime(2026, 5, 1)
try:
    with open(file_z005, 'r', encoding='utf-8') as f: lines = f.readlines()
except:
    try:
        with open(file_z005, 'r', encoding='cp874') as f: lines = f.readlines()
    except: lines = []

for line in lines:
    if line.startswith('|') and 'องค์ประกอบ WBS' not in line:
        parts = line.split('|')
        if len(parts) >= 21:
            wbs = parts[3].strip(); mat = parts[5].strip(); desc = parts[6].strip()
            pr_num = parts[7].strip(); po_num = parts[8].strip(); gr_ir = parts[10].strip()
            
            pr_qty = parse_sap_num(parts[13])
            pr_price = parse_sap_num(parts[14])
            po_date_str = parts[15].strip()
            po_qty = parse_sap_num(parts[16])
            po_price = parse_sap_num(parts[17])
            vendor = parts[20].strip()
            
            if gr_ir == '':
                has_po = len(po_num) > 0
                doc_num = po_num if has_po else pr_num
                doc_type = 'PO' if has_po else 'PR'
                qty = po_qty if has_po and po_qty > 0 else pr_qty
                price = po_price if has_po and po_price > 0 else pr_price
                amount = qty * price
                company_name = vendor_map.get(vendor, vendor) if vendor else '-'
                due_date_str = '-'; overdue_days = '-'
                
                if doc_type == 'PO':
                    due_info = me2n1_due_dates.get(f"{doc_num}_{mat}", me2n1_due_dates.get(doc_num))
                    if due_info:
                        due_date_str, due_date_obj = due_info
                        diff = (current_date - due_date_obj).days
                        overdue_days = diff if diff > 0 else 0
                purchase_data.append({
                    'WBS': wbs, 'Company': company_name, 'DocNum': doc_num, 'DocType': doc_type, 'Mat': mat,
                    'Desc': desc, 'Qty': qty, 'Amount': amount, 'PoDate': po_date_str if po_date_str else '-',
                    'DueDate': due_date_str, 'OverdueDays': overdue_days
                })

tz_th = timezone(timedelta(hours=7))
update_time = datetime.now(tz_th).strftime("%d/%m/%Y เวลา %H:%M น.")

js_content = f"""// ไฟล์นี้ถูกสร้างอัตโนมัติจาก Python (ห้ามแก้ไขด้วยมือ)
const lastUpdated = "{update_time}";
const wbsSummaryData = {json.dumps(wbs_summary_data)};
const demandDetailsData = {json.dumps(demand_details_data)};
const pieRawData = {json.dumps(pie_summary.to_dict(orient='records'))};
const mainData = {json.dumps(final_df.to_dict(orient='records'))};
const projectGroups = {json.dumps(project_cols)};
const wbsDataByMat = {json.dumps({mat: grp.to_dict(orient='records') for mat, grp in wbs_details.groupby('วัสดุ')})};
const wbsDataByWbs = {json.dumps({wbs: grp.to_dict(orient='records') for wbs, grp in wbs_details.groupby('WBS')})};
const me2nSummaryData = {json.dumps(me2n_summary.to_dict(orient='records') if not me2n_summary.empty else [])};
const me2nDetailsData = {json.dumps(me2n_details.to_dict(orient='records') if not me2n_details.empty else [])};
const me2nVendors = {json.dumps(me2n_vendors)};
const me2n1DetailsData = {json.dumps(me2n1_details.to_dict(orient='records') if not me2n1_details.empty else [])};
const me2n1Vendors = {json.dumps(me2n1_vendors)};
const allocDetailsData = {json.dumps(alloc_details.to_dict(orient='records') if not alloc_details.empty else [])};
const allocPlants = {json.dumps(alloc_plants)};
const budgetData = {json.dumps(budget_data)};
const purchaseData = {json.dumps(purchase_data)};
"""

with open('data.js', 'w', encoding='utf-8') as f: f.write(js_content)
print(f"สร้างไฟล์ data.js สำเร็จ! (อัปเดตข้อมูลเมื่อ: {update_time})")