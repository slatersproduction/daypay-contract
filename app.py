import streamlit as st
import re
import urllib.parse
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
                extracted = page.extract_text(layout=True)
                if extracted:
                    text += extracted + "\n"
        
        renter_name = ""
        rent_start = ""
        rent_end = ""
        remarks = ""
        branch_name = "합정" if "합정" in text else "부천" if "부천" in text else "지점"
        
        # 일반 비고란 추출
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
            
            # TOTAL 라인 감지 및 특별 비고 추출
            if "TOTAL" in line_str.upper():
                in_table = False
                total_text = re.sub(r'.*TOTAL[\s\|]*', '', line_str, flags=re.IGNORECASE).strip()
                total_text = re.sub(r'[\d,]+원?|₩\s*[\d,]+', '', total_text).strip()
                if total_text:
                    if remarks:
                        remarks += " " + total_text
                    else:
                        remarks = total_text
                i += 1
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

                # 표 내부 장비 텍스트 가로 병합
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
                
                # 관리번호 치환 및 찌꺼기 제거
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

        # ----------------------------------------------------
        # ★ 비고란 결제 문구 깔끔하게 청소 (강력 필터)
        # ----------------------------------------------------
        if remarks:
            junk_patterns = [
                r'할인합계', r'추가\s*요금', r'안심보험', r'총합계.*?\(inc VAT\)',
                r'보증금', r'연장\s*요금', r'소계', r'부가세', r'사용포인트',
                r'렌탈금액', r'수량', r'총\s*대여시간',
                r'₩\s*[\d,]+', r'[\d,]+\s*원', r'\b0\b', r'WO', r'W0',
                r'\d+시간', r'\d+일', r'inc VAT', r'합계금액\(부가세 포함\)'
            ]
            for junk in junk_patterns:
                remarks = re.sub(junk, '', remarks, flags=re.IGNORECASE)
            
            remarks = re.sub(r'\|\s*\|', '', remarks) # 불필요한 파이프 기호 제거
            remarks = re.sub(r'\s{2,}', ' ', remarks).strip() # 여러 번 띄어쓰기 된 것 하나로 압축

        # ----------------------------------------------------
        # 구글 캘린더 다이렉트 URL 생성 로직
        # ----------------------------------------------------
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

        # 최종 텍스트 양식 구성
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
            title_text = f"[{branch_name}] {name_str}"
            encoded_title = urllib.parse.quote(title_text)
            
            # ----------------------------------------------------
            # ★ 구글 캘린더 연동 시 수량, 특정 장비 Bold(굵게) 처리
            # ----------------------------------------------------
            cal_details = result.strip()
            # 1. '-- 숫자EA' 부분을 굵게 (HTML <b> 태그 적용)
            cal_details = re.sub(r'--\s*\d+EA', r'<b>\g<0></b>', cal_details)
            # 2. '(숫자) 합정' 부분을 굵게
            cal_details = re.sub(r'\(\d+\)\s*합정', r'<b>\g<0></b>', cal_details)
            # 3. 구글 캘린더가 HTML을 인식할 수 있도록 엔터(\n)를 <br>로 변환
            cal_details = cal_details.replace('\n', '<br>')
            
            encoded_details = urllib.parse.quote(cal_details)
            cal_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={encoded_title}&dates={cal_start}/{cal_end}&details={encoded_details}"
            
            st.subheader("🎉 클릭 한 번으로 등록 완료")
            st.markdown(
                f'<a href="{cal_url}" target="_blank">'
                f'<button style="background-color:#4285F4; color:white; padding:12px 24px; border:none; border-radius:8px; cursor:pointer; font-size:16px; font-weight:bold;">'
                f'📅 구글 캘린더에 바로 추가하기'
                f'</button></a>',
                unsafe_allow_html=True
            )
            st.write("위 버튼을 누르면 제목, 날짜, 시간, 장비 목록이 모두 채워진 캘린더 창이 열립니다. (수량 및 합정 장비 볼드 처리됨!)")

        st.subheader("📝 텍스트 수동 복사 (필요시)")
        st.text_area("결과 텍스트 (박스 안을 클릭하고 Ctrl+A, Ctrl+C)", result.strip(), height=350)

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
