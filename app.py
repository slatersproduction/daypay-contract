import streamlit as st
import re
from pypdf import PdfReader

st.set_page_config(page_title="데이페이 계약서 변환기", page_icon="📷")
st.title("📷 데이페이 계약서 자동 변환기")
st.write("계약서 PDF 파일을 업로드하면 캘린더 양식에 맞춰 텍스트를 추출합니다.")

uploaded_file = st.file_uploader("계약서 PDF 파일을 여기에 드래그해 주세요", type=["pdf"])

if uploaded_file is not None:
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

        equipments = []
        keywords = ["Sony", "Canon", "DJI", "Aputure", "Manfrotto", "렌즈", "카메라", "GM", "Mark"]

        for line in text.split('\n'):
            if any(k in line for k in keywords):
                clean_line = line.replace('|', ' ').strip()
                clean_line = re.sub(r'^\d+\s+', '', clean_line)
                clean_line = re.sub(r'\s*₩[\d,]+.*$', '', clean_line)
                
                match = re.search(r'\s+(\d+)$', clean_line)
                if match:
                    qty = match.group(1)
                    name = clean_line[:match.start()].strip()
                    if qty == '1':
                        equipments.append(name)
                    else:
                        equipments.append(f"{name} {qty}EA")
                else:
                    equipments.append(clean_line)

        result = "*장비 목록\n"
        if equipments:
            for eq in equipments:
                result += f"- {eq}\n"
        else:
            result += "- 장비 목록을 자동으로 찾을 수 없습니다.\n"

        st.success("추출 완료!")
        st.subheader("캘린더 복사용 결과")
        st.code(result.strip(), language="text")

    except Exception as e:
        st.error(f"오류 발생: {str(e)}")
