import streamlit as st
import re
from pypdf import PdfReader

st.set_page_config(page_title="데이페이 계약서 변환기", page_icon="📷")
st.title("📷 데이페이 계약서 자동 변환기")
st.write("계약서 PDF 파일을 업로드하면 구조를 분석하여 모든 장비를 키워드 없이 완벽하게 추출합니다.")

uploaded_file = st.file_uploader("계약서 PDF 파일을 여기에 드래그해 주세요", type=["pdf"])

if uploaded_file is not None:
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        renter_name = ""
        rent_start = ""
        rent_end = ""
        remarks = ""
        
        remarks_match = re.search(r'비\s*고\s*(.*?)(?=수량|총\s*대여시간|소계|입금은행|\Z)', text, re.DOTALL)
        if remarks_match:
            remarks = remarks_match.group(1).replace('\n', ' ').replace('|', '').strip()

        lines = [line for line in text.split('\n') if line.strip()]
        
        equipments = []
        in_table = False
        
        current_name = ""
        current_qty = ""
        current_is_main = False
        
        # 장비 텍스트와 관리번호를 최종 양식으로 다듬는 함수
        def format_final_item(name, qty, is_main):
            def repl(match):
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
            
            # 관리번호 괄호 치환 및 지점명 추가
            name = re.sub(r'\bK\d{4,5}-((?:\d+(?:\s*[,、]\s*\d+)*))', repl, name)
            name = re.sub(r'\bK\d{4,5}\b', '', name) # 하이픈 없는 K번호 찌꺼기 제거
            name = re.sub(r'\s+', ' ', name).strip()
            
            q = qty if qty else "1"
            prefix = "- " if is_main else "ㄴ "
            
            if q == "1":
                return f"{prefix}{name}"
            else:
                return f"{prefix}{name} -- {q}EA"

        for line in lines:
            line_str = line.strip()
            
            if "TOTAL" in line_str.upper():
                if current_name:
                    equipments.append(format_final_item(current_name, current_qty, current_is_main))
                in_table = False
                break
                
            # 기본 정보 추출 (표 밖의 내용)
            if "임차인" in line_str and not renter_name:
                name_clean = re.sub(r'(임차인|성명|귀하|:|\||계약회사명)', '', line_str).strip()
                if name_clean: renter_name = name_clean
            
            if not rent_start and re.search(r'(수령지점\s*/?\s*일시|대여일시|대여기간)', line_str):
                clean_str = re.sub(r'.*(수령지점\s*/?\s*일시|대여일시|대여기간)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_start = clean_str
                
            if not rent_end and re.search(r'(반납지점\s*/?\s*일시|반납일시)', line_str):
                clean_str = re.sub(r'.*(반납지점\s*/?\s*일시|반납일시)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_end = clean_str

            # 테이블(장비 목록) 시작 감지
            if line_str == 'NO' or re.search(r'^NO[\s\|]*품명', line_str):
                in_table = True
                continue
                
            if not in_table:
                continue
                
            # --- 여기서부터는 키워드 없이 '표 구조' 자체를 분석합니다 ---
            clean_line = line_str.replace('|', '').strip()
            
            # 1. 쓸모없는 표 헤더나 빈칸 무시
            if not clean_line or clean_line in ['품명', '관리번호', '수량', '금액', '보험', '보증금']:
                continue
            
            # 2. 가격 기호(₩)나 원 단위 금액 무시
            if '₩' in clean_line or re.match(r'^[\d,]+원$', clean_line):
                continue
                
            # 3. 지점장비 안내 텍스트 무시
            if clean_line in ['부천장비', '합정장비']:
                continue

            # 4. K번호만 단독으로 있는 줄이면 현재 장비 이름에 슬쩍 붙임
            if re.match(r'^K\d{4,5}(?:-\d+)?(?:,\s*\d+)*$', clean_line):
                current_name += f" {clean_line}"
                continue
                
            # 5. 순번(NO) 또는 수량(Qty) 처리 (문자 없이 순수 숫자만 있는 경우)
            if re.match(r'^\d+$', clean_line):
                if not current_name:
                    current_is_main = True # 이름이 아직 없으면 순번 (메인 장비 시작)
                else:
                    current_qty = clean_line # 이름이 있으면 그 장비의 수량
                continue
                
            # 6. "1 | Canon..." 처럼 순번과 이름이 한 줄에 붙어서 나오는 경우
            match_mixed = re.match(r'^(\d+)[\s\|]+(.+)', line_str)
            if match_mixed and not current_name:
                current_is_main = True
                current_name = match_mixed.group(2).replace('|', '').strip()
                continue
                
            # 7. 장비 이름 (일반 텍스트)
            # 이미 이전 장비의 이름과 수량이 확보된 상태에서 또 텍스트가 나오면, 이전 장비 목록 완성!
            if current_name and current_qty:
                equipments.append(format_final_item(current_name, current_qty, current_is_main))
                current_name = ""
                current_qty = ""
                current_is_main = False
            
            # 텍스트 이어 붙이기 (FIXED SET 등 두 줄로 쪼개진 이름 대응)
            if current_name:
                current_name += f" {clean_line}"
            else:
                current_name = clean_line

        # 최종 텍스트 조합
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
