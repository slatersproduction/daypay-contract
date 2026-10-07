import streamlit as st
import re
import pdfplumber

st.set_page_config(page_title="데이페이 계약서 변환기", page_icon="📷")
st.title("📷 데이페이 계약서 자동 변환기")
st.write("표 인식 전용 엔진을 탑재하여 어떤 형태의 계약서든 완벽하게 장비를 추출합니다.")

uploaded_file = st.file_uploader("계약서 PDF 파일을 여기에 드래그해 주세요", type=["pdf"])

if uploaded_file is not None:
    try:
        text = ""
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                # layout=True: 시각적 표 형태를 그대로 유지하여 세로 쪼개짐 완벽 방지
                extracted = page.extract_text(layout=True)
                if extracted:
                    text += extracted + "\n"
        
        renter_name = ""
        rent_start = ""
        rent_end = ""
        remarks = ""
        
        # 1. 일반 비고란 추출
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
        
        ignore_in_table = ['품명', '관리번호', '수량', '금액', '보험', '보증금']
        page_footers = ["데이페이", "DAYPAY", "PAGE", "국내 최고 수준", "고객지원센터", "1544-2338"]

        i = 0
        while i < len(lines):
            line_str = lines[i]
            
            # 2. TOTAL 라인 감지 및 특별 비고(예: 보증금 안내) 추출
            if "TOTAL" in line_str.upper():
                in_table = False
                # TOTAL 옆에 적힌 텍스트(예: 보증금 실물신분증 안내완) 캐치
                total_text = re.sub(r'.*TOTAL[\s\|]*', '', line_str).strip()
                total_text = re.sub(r'[\d,]+원?|₩\s*[\d,]+', '', total_text).strip()
                if total_text:
                    if remarks:
                        remarks += " " + total_text
                    else:
                        remarks = total_text
                break
            
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
                i += 1
                continue
            
            if in_table:
                clean_check = line_str.replace('|', '').strip()
                
                if clean_check in ignore_in_table or not clean_check:
                    i += 1
                    continue
                if any(footer in clean_check.upper() for footer in page_footers):
                    i += 1
                    continue
                if re.match(r'^[\d,]+원$', clean_check) or clean_check == '₩':
                    i += 1
                    continue

                # 표 내부 장비 텍스트 병합
                while i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if "TOTAL" in next_line.upper():
                        break
                    
                    clean_next = next_line.replace('|', '').strip()
                    if any(footer in clean_next.upper() for footer in page_footers):
                        break
                        
                    if '₩' in line_str or re.search(r'\s+\d+$', line_str.replace('|', '').strip()):
                        break
                        
                    if re.match(r'^\d+[\s\.]+', clean_next):
                        break
                        
                    line_str += " " + next_line
                    i += 1

                clean_line = line_str.replace('|', ' ').strip()
                is_main = bool(re.match(r'^\d+[\s\.]+', clean_line))
                
                clean_line = re.sub(r'^\d+[\s\.]+', '', clean_line)
                clean_line = re.sub(r'\s*₩\s*[\d,]+.*$', '', clean_line)
                clean_line = re.sub(r'\s+[\d,]+원.*$', '', clean_line)
                
                # 관리번호 치환 및 찌꺼기 텍스트 제거
                clean_line = re.sub(r'\bK\d{4,5}-((?:\d+(?:\s*[,、]\s*\d+)*))', format_k_number, clean_line)
                clean_line = re.sub(r'\bK\d{4,5}\b', '', clean_line)
                clean_line = re.sub(r'부천장비|합정장비', '', clean_line)
                clean_line = re.sub(r'\(\s*\)', '', clean_line)
                clean_line = re.sub(r'\s+', ' ', clean_line).strip()
                
                if not clean_line:
                    i += 1
                    continue

                match = re.search(r'\s+(\d+)$', clean_line)
                if match:
                    qty = match.group(1)
                    name = clean_line[:match.start()].strip()
                    if name:
                        prefix = "- " if is_main else "ㄴ "
                        if qty == '1':
                            equipments.append(f"{prefix}{name}")
                        else:
                            equipments.append(f"{prefix}{name} -- {qty}EA")
                else:
                    if clean_line:
                        prefix = "- " if is_main else "ㄴ "
                        equipments.append(f"{prefix}{clean_line}")

            i += 1

        result = f"👤 대여자: {renter_name if renter_name else '확인 불가'}\n"
        result += f"📅 대여 일시: {rent_start if rent_start else '확인 불가'}\n"
        result += f"📅 반납 일시: {rent_end if rent_end else '확인 불가'}\n\n"
        result += "*장비 목록\n"
        
        if equipments:
            for eq in equipments:
                result += f"{eq}\n"
        else:
            result += "- 장비 목록을 자동으로 찾을 수 없습니다.\n"
            
        if remarks:
            result += f"\n*비고\n{remarks}\n"

        st.success("양식 변환 및 추출 완료!")
        st.text_area("결과 텍스트 (박스 안을 클릭하고 Ctrl+A, Ctrl+C 로 복사하세요)", result.strip(), height=500)

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
