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

        # ★ 강력한 비고란 청소기 (띄어쓰기, 변형 단어 완벽 대응)
        def clean_remarks_text(raw_text):
            pat_list = [
                r'수량\s*\d+', 
                r'사용\s*포인트\s*\d*', 
                r'총\s*대여시간\s*\d*(일|시간)?',
                r'소계\s*₩?\s*[\d,]*', 
                r'부가세\s*₩?\s*[\d,]*', 
                r'추가\s*요금\s*[A-Za-z0-9\-]*',
                r'총합계.*?(₩?\s*[\d,]+)?', 
                r'연장\s*요금', 
                r'대여\s*금액', 
                r'할인\s*합계', 
                r'안심\s*합계', 
                r'보증금', 
                r'\(?\s*포함\s*\)?',
                r'₩?\s*[\d,]{4,}'
            ]
            cleaned = raw_text
            for pat in pat_list:
                cleaned = re.sub(pat, ' ', cleaned, flags=re.IGNORECASE)
                
            chunks = re.split(r'\s{2,}', cleaned)
            valid = []
            for c in chunks:
                c = c.strip()
                if not c: continue
                # 고립된 쓰레기 데이터(0, -WO 등) 최종 삭제
                if re.match(r'^(\d+시간|\d+일|₩?\s*[\d,]+|-?WO|-?W0|OM-|0|\d+)$', c, re.IGNORECASE): continue
                valid.append(c)
            return " ".join(valid)

        equipments = []
        remarks_lines = []
        in_table = False
        in_remarks = False
        
        ignore_in_table = ['품명', '관리번호', '수량', '금액', '보험', '보증금', 'NO']
        page_footers = ["국내 최고 수준", "고객지원센터", "1544-2338"]
        current_item = ""

        i = 0
        while i < len(lines):
            line_str = lines[i]
            
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

            # 비고란 진입 (TOTAL 라인부터 끝까지)
            if "TOTAL" in line_str.upper():
                in_table = False
                in_remarks = True
                
                clean_total = line_str.split('TOTAL')[0].replace('|', '').strip()
                clean_total = re.sub(r'^(비\s*고|비|고)\s*', '', clean_total).strip()
                result_text = clean_remarks_text(clean_total)
                if result_text: remarks_lines.append(result_text)
                i += 1
                continue
            
            if in_remarks:
                if "입금은행" in line_str or "국내 최고 수준" in line_str or "고객지원센터" in line_str:
                    i += 1; continue 
                if re.search(r'PAGE\s*\d+/\d+', line_str.upper()):
                    i += 1; continue
                    
                left_chunk = line_str.split('|')[0].strip()
                left_chunk = re.sub(r'^(비\s*고|비|고)\s*', '', left_chunk).strip()
                left_chunk = re.sub(r'[-—]*\s*PAGE\s*\d+/\d+\s*[-—]*', '', left_chunk, flags=re.IGNORECASE).strip()
                
                result_text = clean_remarks_text(left_chunk)
                if result_text: remarks_lines.append(result_text)
                i += 1
                continue
            
            # 표 장비 목록 추출
            if re.search(r'^NO[\s\|]*품명', line_str) or line_str == 'NO':
                in_table = True
                i += 1
                continue
            
            if in_table:
                clean_check = line_str.replace('|', '').strip()
                
                if not clean_check or clean_check in ignore_in_table:
                    i += 1; continue
                if any(footer in clean_check.upper() for footer in page_footers):
                    i += 1; continue
                if re.match(r'^[\d,]+원$', clean_check) or clean_check == '₩':
                    i += 1; continue
                if re.search(r'PAGE\s*\d+/\d+', clean_check.upper()):
                    i += 1; continue

                if current_item:
                    current_item += " " + clean_check
                else:
                    current_item = clean_check
                    
                # ★ 장비 분리 조건: 끝에 가격(-WO, OM-, ₩ 등)이 있거나, 다음 줄이 새 장비일 때
                has_price = re.search(r'(₩\s*[\d,]+|[\d,]+\s*원|-WO|-W0|OM-)\s*$', current_item.replace(' ', ''))
                
                next_is_new = False
                if i + 1 < len(lines):
                    next_line = lines[i+1].replace('|', '').strip()
                    if re.match(r'^\d+[\s\.]+[A-Za-z가-힣]', next_line) or "TOTAL" in next_line.upper():
                        next_is_new = True
                else:
                    next_is_new = True
                    
                if has_price or next_is_new:
                    # 가격(찌꺼기) 분리 후 수량 추출
                    check_str = re.sub(r'\s*(₩\s*[\d,]+|[\d,]+\s*원|-WO|-W0|OM-)\s*$', '', current_item).strip()
                    
                    match = re.search(r'\s+(\d+)$', check_str)
                    if match:
                        qty = match.group(1)
                        name_part = check_str[:match.start()].strip()
                    else:
                        qty = '1'
                        name_part = check_str
                        
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

            i += 1

        remarks = "\n".join(remarks_lines).strip()

        def get_cal_datetime(dt_string):
            if not dt_string: return None
            match = re.search(r'(?:(20\d{2})[-/.])?(\d{1,2})[-/.](\d{1,2})\s+(\d{1,2}:\d{2})', dt_string)
            if match:
                year = match.group(1) if match.group(1) else "2026"
                month = match.group(2).zfill(2)
                day = match.group(3).zfill(2)
                time_str = match.group(4).replace(":", "") + "00"
                return f"{year}{month}{day}T{time_str}"
            return None

        cal_start = get_cal_datetime(rent_start)
        cal_end = get_cal_datetime(rent_end)
        name_str = renter_name if renter_name else '이름없음'

        result = f"👤 대여자: {name_str}\n"
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

        if cal_start and cal_end:
            title_text = f"{name_str}"
            encoded_title = urllib.parse.quote(title_text)
            
            cal_details = result.strip()
            cal_details = re.sub(r'--\s*\d+EA', r'<b>\g<0></b>', cal_details)
            cal_details = re.sub(r'\(\d+\)\s*합정', r'<b>\g<0></b>', cal_details)
            cal_details = cal_details.replace('\n', '<br>')
            
            encoded_details = urllib.parse.quote(cal_details)
            cal_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={encoded_title}&dates={cal_start}/{cal_end}&details={encoded_details}"
            
            st.subheader("🎉 클릭 한 번으로 등록 완료")
            st.markdown(
                f'<a href="{cal_url}" target="_blank">'
                f'<button style="background-color:#4285F4; color:white; padding:12px 24px; border:none; border-radius:8px; cursor:pointer; font-size:16px; font-weight:bold; width:100%;">'
                f'📅 구글 캘린더에 바로 추가하기'
                f'</button></a>',
                unsafe_allow_html=True
            )

        st.text_area("결과 텍스트 수동 복사용 (Ctrl+A, Ctrl+C)", result.strip(), height=350)

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
