import streamlit as st
import re
import urllib.parse
import pdfplumber

st.set_page_config(page_title="데이페이 계약서 변환기", page_icon="📷")
st.title("📷 데이페이 계약서 자동 변환기")
st.write("키워드 없이 표 구조를 완벽히 분석하여 어떤 장비든 100% 자동 추출합니다.")

uploaded_file = st.file_uploader("계약서 PDF 파일을 여기에 드래그해 주세요", type=["pdf"])

if uploaded_file is not None:
    try:
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text(layout=True)
                if extracted:
                    text += extracted + "\n"
        
        renter_name = ""
        rent_start = ""
        rent_end = ""
        branch_name = "합정" if "합정" in text else "부천" if "부천" in text else "지점"
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        def format_k_number(match):
            nums_str = match.group(1)
            nums = re.split(r'[,、]', nums_str)
            res = []
            for n in nums:
                n = n.strip()
                if not n: continue
                if len(n) == 2: res.append(f"({n}) 합정")
                elif len(n) == 3: res.append(f"({n}) 부천")
                else: res.append(f"({n})")
            return " ".join(res)

        equipments = []
        remarks_lines = []
        in_table = False
        in_remarks = False
        
        ignore_in_table = ['품명', '관리번호', '수량', '금액', '보험', '보증금', 'NO']
        page_footers = ["국내 최고 수준", "고객지원센터", "1544-2338"]
        
        billing_labels = [
            '수량', '총 대여시간', '렌탈금액', '할인합계', '안심보험', '보증금', '사용포인트', 
            '소계', '부가세', '추가 요금', '총합계 (inc VAT)', '총합계', '연장 요금'
        ]
        billing_labels = sorted(billing_labels, key=len, reverse=True)

        current_item = ""

        for line_str in lines:
            if "임차인" in line_str and not renter_name:
                name_clean = re.sub(r'(임차인|성명|귀하|:|\||계약회사명)', '', line_str).strip()
                if name_clean and not re.search(r'\d{6}-\d', name_clean):
                    renter_name = name_clean
            
            if not rent_start and re.search(r'(수령지점\s*/?\s*일시|대여일시|대여기간)', line_str):
                clean_str = re.sub(r'.*(수령지점\s*/?\s*일시|대여일시|대여기간)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_start = clean_str
                
            if not rent_end and re.search(r'(반납지점\s*/?\s*일시|반납일시)', line_str):
                clean_str = re.sub(r'.*(반납지점\s*/?\s*일시|반납일시)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_end = clean_str

            if "TOTAL" in line_str.upper():
                in_table = False
                in_remarks = True
                
                clean_total = line_str.split('TOTAL')[0].replace('|', '').strip()
                clean_total = re.sub(r'^(비\s*고|비|고)\s*', '', clean_total).strip()
                if clean_total:
                    for word in billing_labels:
                        clean_total = clean_total.replace(word, ' ')
                    chunks = re.split(r'\s{2,}', clean_total)
                    valid_chunks = []
                    for chunk in chunks:
                        c = chunk.strip()
                        if not c: continue
                        if re.match(r'^(\d+시간|\d+일|₩?\s*[\d,]+|WO|W0|0)$', c, re.IGNORECASE): continue
                        valid_chunks.append(c)
                    if valid_chunks:
                        remarks_lines.append(" ".join(valid_chunks))
                continue
            
            if in_remarks:
                if "입금은행" in line_str or "국내 최고 수준" in line_str or "고객지원센터" in line_str:
                    continue 
                if re.search(r'PAGE\s*\d+/\d+', line_str.upper()):
                    continue
                    
                left_chunk = line_str.split('|')[0].strip()
                left_chunk = re.sub(r'^(비\s*고|비|고)\s*', '', left_chunk).strip()
                left_chunk = re.sub(r'[-—]*\s*PAGE\s*\d+/\d+\s*[-—]*', '', left_chunk, flags=re.IGNORECASE).strip()
                
                for word in billing_labels:
                    left_chunk = left_chunk.replace(word, ' ')
                    
                chunks = re.split(r'\s{2,}', left_chunk)
                valid_chunks = []
                for chunk in chunks:
                    c = chunk.strip()
                    if not c: continue
                    if re.match(r'^(\d+시간|\d+일|₩?\s*[\d,]+|WO|W0|0)$', c, re.IGNORECASE): continue
                    valid_chunks.append(c)
                    
                if valid_chunks:
                    remarks_lines.append(" ".join(valid_chunks))
                continue
            
            if re.search(r'^NO[\s\|]*품명', line_str) or line_str == 'NO':
                in_table = True
                continue
            
            if in_table:
                clean_check = line_str.replace('|', '').strip()
                
                if not clean_check or clean_check in ignore_in_table: continue
                if any(footer in clean_check.upper() for footer in page_footers): continue
                if re.match(r'^[\d,]+원$', clean_check) or clean_check == '₩': continue
                if re.search(r'PAGE\s*\d+/\d+', clean_check.upper()): continue

                if current_item:
                    current_item += " " + clean_check
                else:
                    current_item = clean_check
                    
                check_str = re.sub(r'\s*₩\s*[\d,]+.*$', '', current_item).strip()
                check_str = re.sub(r'\s+[\d,]+원.*$', '', check_str).strip()
                
                match = re.search(r'\s+(\d+)$', check_str)
                
                if match:
                    qty = match.group(1)
                    name_part = check_str[:match.start()].strip()
                    
                    is_main = bool(re.match(r'^\d+[\s\.]+', name_part))
                    name_part = re.sub(r'^\d+[\s\.]+', '', name_part)
                    
                    name_part = re.sub(r'\bK\d{4,5}-((?:\d+(?:\s*[,、]\s*\d+)*))', format_k_number, name_part)
                    name_part = re.sub(r'\bK\d{4,5}\b', '', name_part)
                    name_part = re.sub(r'부천장비|합정장비', '', name_part)
                    name_part = re.sub(r'\(\s*\)', '', name_part)
                    name_part = re.sub(r'\s+', ' ', name_part).strip()
                    
                    if name_part:
                        prefix = "- " if is_main else "ㄴ "
                        if qty == '1':
                            equipments.append(f"{prefix}{name_part}")
                        else:
                            equipments.append(f"{prefix}{name_part} -- {qty}EA")
                            
                    current_item = "" 

        remarks =
