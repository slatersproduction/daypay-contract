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
        remarks = ""
        branch_name = "합정" if "합정" in text else "부천" if "부천" in text else "지점"
        
        remarks_match = re.search(r'비\s*고\s*(.*?)(?=입금은행|국내\s*최고\s*수준|\Z)', text, re.DOTALL)
        if remarks_match:
            remarks = remarks_match.group(1).replace('\n', ' ').replace('|', '').strip()

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
        in_table = False
        
        ignore_in_table = ['품명', '관리번호', '수량', '금액', '보험', '보증금', 'NO']
        
        page_footers = ["국내 최고 수준", "고객지원센터", "1544-2338", "PAGE"]

        current_item = ""

        for line_str in lines:
            if "TOTAL" in line_str.upper():
                in_table = False
                total_text = re.sub(r'.*TOTAL[\s\|]*', '', line_str, flags=re.IGNORECASE).strip()
                total_text = re.sub(r'[\d,]+원?|₩\s*[\d,]+', '', total_text).strip()
                if total_text:
                    if remarks: remarks += " " + total_text
                    else: remarks = total_text
                continue
            
            if "임차인" in line_str and not renter_name:
                name_clean = re.sub(r'(임차인|성명|귀하|:|\||계약회사명)', '', line_str).strip()
                if name_clean: renter_name = name_clean
            
            if not rent_start and re.search(r'(수령지점\s*/?\s*일시|대여일시|대여기간)', line_str):
                clean_str = re.sub(r'.*(수령지점\s*/?\s*일시|대여일시|대여기간)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_start = clean_str
                
            if not rent_end and re.search(r'(반납지점\s*/?\s*일시|반납일시)', line_str):
                clean_str = re.sub(r'.*(반납지점\s*/?\s*일시|반납일시)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_end = clean_str

            if re.search(r'^NO[\s\|]*품명', line_str) or line_str == 'NO':
                in_table = True
                continue
            
            if in_table:
                clean_check = line_str.replace('|', '').strip()
                
                if not clean_check or clean_check in ignore_in_table: continue
                if any(footer in clean_check.upper() for footer in page_footers): continue
                if re.
