import streamlit as st
import re
from pypdf import PdfReader

st.set_page_config(page_title="데이페이 계약서 변환기", page_icon="📷")
st.title("📷 데이페이 계약서 자동 변환기")
st.write("계약서 PDF 파일을 업로드하면 표 구조를 분석하여 누락 없이 완벽하게 장비를 추출합니다.")

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
        
        # 비고란 추출
        remarks_match = re.search(r'비\s*고\s*(.*?)(?=수량|총\s*대여시간|소계|입금은행|\Z)', text, re.DOTALL)
        if remarks_match:
            remarks = remarks_match.group(1).replace('\n', ' ').replace('|', '').strip()

        # 빈 줄 제거
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 관리번호 괄호 치환 함수
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
        
        # 표 내부에서 무시할 찌꺼기 텍스트들
        ignore_in_table = ['품명', '관리번호', '수량', '금액', '보험', '보증금']
        page_footers = ["데이페이", "DAYPAY", "PAGE", "국내 최고 수준", "고객지원센터", "1544-2338"]

        i = 0
        while i < len(lines):
            line_str = lines[i]
            
            # TOTAL 글자를 만나면 장비 추출 즉시 종료
            if "TOTAL" in line_str.upper():
                in_table = False
                break
            
            # 대여자 이름 추출
            if "임차인" in line_str and not renter_name:
                name_clean = re.sub(r'(임차인|성명|귀하|:|\||계약회사명)', '', line_str).strip()
                if name_clean: renter_name = name_clean
            
            # 대여/반납 일시 추출
            if not rent_start and re.search(r'(수령지점\s*/?\s*일시|대여일시|대여기간)', line_str):
                clean_str = re.sub(r'.*(수령지점\s*/?\s*일시|대여일시|대여기간)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_start = clean_str
                
            if not rent_end and re.search(r'(반납지점\s*/?\s*일시|반납일시)', line_str):
                clean_str = re.sub(r'.*(반납지점\s*/?\s*일시|반납일시)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_end = clean_str

            # 장비 표(테이블) 시작점 감지
            if re.search(r'^NO[\s\|]*품명', line_str) or line_str == 'NO':
                in_table = True
                i += 1
                continue
            
            # 장비 목록 표 내부일 때 작동
            if in_table:
                clean_check = line_str.replace('|', '').strip()
                
                # 표 제목, 페이지 꼬리말, 순수 가격 행은 무시하고 스킵
                if clean_check in ignore_in_table or not clean_check:
                    i += 1
                    continue
                if any(footer in clean_check.upper() for footer in page_footers):
                    i += 1
                    continue
                if re.match(r'^[\d,]+원$', clean_check) or clean_check == '₩':
                    i += 1
                    continue

                # ★ 똑똑한 줄 합치기: 현재 줄이 완전한 장비 텍스트가 될 때까지만 다음 줄을 끌어옴
                while i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    if "TOTAL" in next_line.upper():
                        break
                    
                    clean_next = next_line.replace('|', '').strip()
                    if any(footer in clean_next.upper() for footer in page_footers):
                        break
                        
                    # 현재 텍스트 끝에 '가격(₩)'이나 '수량(숫자)'이 존재하면 완벽한 한 줄이므로 합치기 중단
                    if '₩' in line_str or re.search(r'\s+\d+$', line_str.replace('|', '').strip()):
                        break
                        
                    # 다음 줄이 새로운 메인 장비 번호(1, 2 등)로 시작하면 합치기 중단
                    if re.match(r'^\d+[\s\.]+', clean_next):
                        break
                        
                    line_str += " " + next_line
                    i += 1

                # 불필요한 기호 및 단어 정리
                clean_line = line_str.replace('|', ' ').strip()
                is_main = bool(re.match(r'^\d+[\s\.]+', clean_line))
                
                clean_line = re.sub(r'^\d+[\s\.]+', '', clean_line)
                clean_line = re.sub(r'\s*₩\s*[\d,]+.*$', '', clean_line)
                clean_line = re.sub(r'\s+[\d,]+원.*$', '', clean_line)
                
                # 관리번호 치환 및 찌꺼기 텍스트 제거
                clean_line = re.sub(r'\bK\d{4,5}-((?:\d+(?:\s*[,、]\s*\d+)*))', format_k_number, clean_line)
                clean_line = re.sub(r'\bK\d{4,5}\b', '', clean_line)
                clean_line = re.sub(r'부천장비|합정장비', '', clean_line)
                clean_line = re.sub(r'\(\s*\)', '', clean_line) # 빈 괄호 지우기
                clean_line = re.sub(r'\s+', ' ', clean_line).strip()
                
                if not clean_line:
                    i += 1
                    continue

                # 맨 마지막 수량 분리 및 기호 부여 (- 또는 ㄴ)
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

        # 최종 텍스트 양식 조합
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
