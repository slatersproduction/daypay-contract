import streamlit as st
import re
from pypdf import PdfReader

st.set_page_config(page_title="데이페이 계약서 변환기", page_icon="📷")
st.title("📷 데이페이 계약서 자동 변환기")
st.write("계약서 PDF 파일을 업로드하면 이름, 날짜, 장비를 누락 없이 추출합니다.")

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
            "스탠드", "소프트박스", "플레이트", "클램프", "케이블", "젠더", "가방", "무선"
        ]

        for line in text.split('\n'):
            line_str = line.strip()
            if not line_str:
                continue
            
            # 1. 이름 추출 (계약회사명 등 불필요한 단어 깔끔하게 제거)
            if "임차인" in line_str and not renter_name:
                name_clean = re.sub(r'(임차인|성명|귀하|:|\||계약회사명)', '', line_str).strip()
                if name_clean: renter_name = name_clean
            
            # 2. 대여/반납 일시 추출 ('수령지점/일시', '반납지점/일시' 키워드 추가)
            if not rent_start and re.search(r'(수령지점\s*/?\s*일시|대여일시|대여기간)', line_str):
                clean_str = re.sub(r'.*(수령지점\s*/?\s*일시|대여일시|대여기간)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_start = clean_str
                
            if not rent_end and re.search(r'(반납지점\s*/?\s*일시|반납일시)', line_str):
                clean_str = re.sub(r'.*(반납지점\s*/?\s*일시|반납일시)[\s:\|]*', '', line_str).strip()
                if clean_str: rent_end = clean_str

            # 일반 계약 문구 제외
            if any(ex in line_str for ex in exclude_keywords):
                continue

            # 장비 정보 추출
            is_equipment = ('₩' in line_str) or any(k.lower() in line_str.lower() for k in keywords)

            if is_equipment:
                clean_line = line_str.replace('|', ' ').strip()
                clean_line = re.sub(r'^\d+[\s\.]+', '', clean_line)
                clean_line = re.sub(r'\s*₩\s*[\d,]+.*$', '', clean_line)
                clean_line = re.sub(r'\s+[\d,]+원.*$', '', clean_line)
                
                match = re.search(r'\s+(\d+)$', clean_line)
                if match:
                    qty = match.group(1)
                    name = clean_line[:match.start()].strip()
                    if name:
                        if qty == '1':
                            equipments.append(name)
                        else:
                            equipments.append(f"{name} {qty}EA")
                else:
                    if clean_line:
                        equipments.append(clean_line)

        result = f"👤 대여자: {renter_name if renter_name else '확인 불가'}\n"
        result += f"📅 대여 일시: {rent_start if rent_start else '확인 불가'}\n"
        result += f"📅 반납 일시: {rent_end if rent_end else '확인 불가'}\n\n"
        result += "*장비 목록\n"
        
        if equipments:
            for eq in equipments:
                result += f"- {eq}\n"
        else:
            result += "- 장비 목록을 자동으로 찾을 수 없습니다.\n"

        st.success("대여자 정보 및 장비 추출 완료!")
        st.subheader("캘린더 복사용 결과")
        st.code(result.strip(), language="text")

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
