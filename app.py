import streamlit as st
import re
from pypdf import PdfReader
import urllib.parse

st.set_page_config(page_title="데이페이 계약서 변환기", page_icon="📷")
st.title("📷 데이페이 계약서 자동 변환기")
st.write("계약서 PDF 파일을 업로드하면 장비 목록을 추출하고 구글 캘린더에 원클릭으로 등록합니다.")

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
        branch_name = "합정" if "합정" in text else "부천" if "부천" in text else "지점"
        
        # 일반 비고란 추출
        remarks_match = re.search(r'비\s*고\s*(.*?)(?=수량|총\s*대여시간|소계|입금은행|\Z)', text, re.DOTALL)
        if remarks_
