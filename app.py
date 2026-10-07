import streamlit as st
import re
from pypdf import PdfReader

st.set_page_config(page_title="데이페이 계약서 변환기", page_icon="📷")
st.title("📷 데이페이 계약서 자동 변환기")
st.write("계약서 PDF 파일을 업로드하면 캘린더 자동 등록용 제목과 장비 목록을 추출합니다.")

uploaded_file = st.file_uploader("계약서 PDF 파일을 여기에 드래그해 주세요", type=["pdf"])

if uploaded_file is not None:
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        equipments = []
        renter_name = ""
        rent_start = ""
        rent_end = ""
        remarks = ""
        
        # 비고란 추출
        remarks_match = re.search(r'비\s*고\s*(.*?)(?=수량|총\s*대여시간|소계|입금은행|\Z)', text, re.DOTALL)
        if remarks_match:
            remarks = remarks_match.group(1).replace('\n', ' ').replace('|', '').strip()
        
        exclude_keywords = [
            "계약서", "사업자등록번호", "대표자", "연락처", "주소", "대여기간", "반납일시",
            "총금액", "결제금액", "보증금", "서명", "인", "특약사항", "주의사항", "환불", 
            "영수증", "부가가치세", "합계", "데이페이", "수령지점", "반납지점", "임차인"
        ]

        keywords = [
            "Sony", "Canon", "DJI", "Aputure", "Manfrotto", "렌즈", "카메라", "GM", "Mark",
            "FX", "Alpha", "EOS", "Sennheiser", "Rode", "Godox", "Nanlite", "Profoto",
            "Blackmagic", "RED", "ARRI", "Sigma", "Samyang", "Tamron", "Nikon", "Panasonic",
            "삼각대", "헤드", "조명", "배터리", "메모리", "마이크", "모니터", "송수신기",
            "스탠드", "소프트박스", "플레이트", "클램프", "케이블", "젠더", "가방", "무선", "릴선", 
            "CFexpress", "Umbrella", "Marsace", "Sirui", "SD", "샌디스크", "부천장비", "합정장비"
        ]

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

        i = 0
        while i < len(lines):
            line_str = lines[i]
            
            if "렌탈금액" in line_str or "소계" in line_str:
                break
            
            line_str = re.sub(r'\bTOTAL\b', '', line_str, flags=re.IGNORECASE)
            
            if "임차인" in line_str and not renter_name:
                name_clean = re.sub(r'(임차인|성명|귀하|:|\||계약회사명)', '', line_str).strip()
                if name_clean: renter_name = name_clean
            
            if not rent_start and re.search(r'(수령지점\s*/?\s*일시|대여일시|대여기간)', line_str):
                clean_str = re.sub(r'.*(수령지점\s*/?\s*일시|대여일시|대여기간)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_start = clean_str
                    
            if not rent_end and re.search(r'(반납지점\s*/?\s*일시|반납일시)', line_str):
                clean_str = re.sub(r'.*(반납지점\s*/?\s*일시|반납일시)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_end = clean_str

            if any(ex in line_str for ex in exclude_keywords):
                i += 1
                continue

            is_equipment = ('₩' in line_str) or any(k.lower() in line_str.lower() for k in keywords) or re.search(r'K\d{4,5}', line_str)

            if is_equipment:
                while i + 1 < len(lines):
                    next_line = lines[i+1]
                    if "렌탈금액" in next_line or "소계" in next_line:
                        break
                    
                    next_line = re.sub(r'\bTOTAL\b', '', next_line, flags=re.IGNORECASE)
                    
                    if '₩' in line_str:
                        break
                    
                    is_next_new_main = bool(re.match(r'^\d+[\s\.]+', next_line.strip()))
                    has_kw_next = any(k.lower() in next_line.lower() for k in keywords) or re.search(r'K\d{4,5}', next_line)
                    
                    if is_next_new_main or has_kw_next:
                        break
                    
                    line_str += " " + next_line
                    i += 1
                        
                clean_line = line_str.replace('|', ' ').strip()
                is_main = bool(re.match(r'^\d+[\s\.]+', clean_line))
                
                clean_line = re.sub(r'^\d+[\s\.]+', '', clean_line)
                clean_line = re.sub(r'\s*₩\s*[\d,]+.*$', '', clean_line)
                clean_line = re.sub(r'\s+[\d,]+원.*$', '', clean_line)
                
                clean_line = re.sub(r'\bK\d{4,5}-((?:\d+(?:\s*[,、]\s*\d+)*))', format_k_number, clean_line)
                clean_line = re.sub(r'\bK\d{4,5}\b', '', clean_line)
                
                clean_line = re.sub(r'부천장비|합정장비', '', clean_line)
                clean_line = re.sub(r'\s+', ' ', clean_line).strip()
                
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
        # ★ 구글 캘린더 제목용 스마트 날짜/시간 로직
        # ----------------------------------------------------
        def get_dt_info(dt_string):
            # "2026/10/24 11:00" 등에서 월/일, 시간만 추출
            match = re.search(r'(?:20\d{2}[-/.])?(\d{1,2})[-/.](\d{1,2})\s+(\d{1,2}:\d{2})', dt_string)
            if match:
                month = match.group(1).zfill(2)
                day = match.group(2).zfill(2)
                time = match.group(3)
                return f"{month}/{day}", time
            return None, None

        start_date, start_time = get_dt_info(rent_start)
        end_date, end_time = get_dt_info(rent_end)

        cal_title = ""
        name_str = renter_name if renter_name else '이름없음'
        
        if start_date and start_time and end_date and end_time:
            if start_date == end_date:
                # 당일 예약 (예: 11:00-21:00 백주암)
                cal_title = f"{start_time}-{end_time} {name_str}"
            else:
                # 다중 날짜 예약 (예: 10/10 08:00 - 10/12 10:00 백주암)
                cal_title = f"{start_date} {start_time} - {end_date} {end_time} {name_str}"
        else:
            cal_title = f"시간확인불가 {name_str}"


        # 캘린더 설명란용 결과 텍스트
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
        
        st.subheader("1. 캘린더 '제목' 복사용 (지점명 제거, 시간 자동설정)")
        st.info("이 내용을 구글 캘린더 '제목'에 붙여넣고 엔터를 치면 며칠짜리 일정도 시간이 자동 설정됩니다.")
        st.code(cal_title, language="text")
        
        st.subheader("2. 캘린더 '설명' 복사용 (장비 목록)")
        st.text_area("박스 안을 클릭하고 Ctrl+A, Ctrl+C 로 복사하세요", result.strip(), height=400)

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
