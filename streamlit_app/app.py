import streamlit as st
import pandas as pd
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile

st.set_page_config(page_title="Excel to PDF 変換ツール", layout="wide")
st.title("Excel to PDF 変換ツール")
st.subheader("Excelファイルを読み込み、氏名欄に名前と電子印を追加してPDFに変換します")

def create_seal(name, size=(100, 100), color=(255, 0, 0, 128)):
    """
    指定された名前で電子印を作成する
    
    Parameters:
    name (str): 印鑑に表示する名前
    size (tuple): 印鑑のサイズ (width, height)
    color (tuple): 印鑑の色 (R, G, B, A)
    
    Returns:
    PIL.Image: 作成された電子印の画像
    """
    img = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    draw.ellipse([(0, 0), size], outline=color[:3], fill=color, width=3)
    
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf', size[0]//4)
    except IOError:
        font = ImageFont.load_default()
    
    text_width = draw.textlength(name, font=font)
    text_height = size[1] // 3  # おおよその高さ
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
    
    draw.text(position, name, font=font, fill=(255, 255, 255, 255))
    
    return img

def excel_to_pdf(df, name_column, name_value, seal_image):
    """
    DataFrameをPDFに変換し、指定された列に名前と印鑑を追加する
    
    Parameters:
    df (pandas.DataFrame): 変換するデータフレーム
    name_column (str): 名前と印鑑を追加する列名
    name_value (str): 追加する名前
    seal_image (PIL.Image): 追加する印鑑画像
    
    Returns:
    bytes: 生成されたPDFのバイトデータ
    """
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    try:
        pdfmetrics.registerFont(TTFont('HeiseiKakuGo-W5', '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf'))
        font_name = 'HeiseiKakuGo-W5'
    except:
        font_name = 'Helvetica'
    
    c.setFont(font_name, 16)
    c.drawString(50, height - 50, "Excel データ")
    
    c.setFont(font_name, 12)
    y_position = height - 80
    col_width = width / (len(df.columns) + 1)
    
    for i, col in enumerate(df.columns):
        c.drawString(50 + i * col_width, y_position, str(col))
    
    c.setFont(font_name, 10)
    for i, row in enumerate(df.itertuples()):
        y_position = height - 100 - i * 20
        
        for j, val in enumerate(row[1:]):  # index=0は行番号なのでスキップ
            if df.columns[j] == name_column and name_value:
                c.drawString(50 + j * col_width, y_position, f"{val} ({name_value})")
                
                seal_temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                seal_image.save(seal_temp.name)
                seal_temp.close()
                
                seal_size = 20
                seal_x = 50 + j * col_width + len(str(val)) * 5 + len(name_value) * 5 + 15
                seal_y = y_position - 5
                
                c.drawImage(seal_temp.name, seal_x, seal_y, width=seal_size, height=seal_size)
                os.unlink(seal_temp.name)
            else:
                c.drawString(50 + j * col_width, y_position, str(val))
    
    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

def main():
    uploaded_file = st.file_uploader("Excelファイルをアップロードしてください", type=["xlsx", "xls"])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            st.subheader("アップロードされたデータ")
            st.dataframe(df)
            
            columns = df.columns.tolist()
            name_column = st.selectbox("氏名を追加する列を選択してください", columns)
            
            name_value = st.text_input("追加する名前を入力してください")
            
            seal_color = st.color_picker("印鑑の色を選択してください", "#FF0000")
            r = int(seal_color[1:3], 16)
            g = int(seal_color[3:5], 16)
            b = int(seal_color[5:7], 16)
            
            if name_value:
                seal_image = create_seal(name_value, color=(r, g, b, 128))
                seal_preview = io.BytesIO()
                seal_image.save(seal_preview, format='PNG')
                
                st.subheader("電子印のプレビュー")
                st.image(seal_preview.getvalue(), width=100)
                
                if st.button("PDFに変換"):
                    with st.spinner("PDFを生成中..."):
                        pdf_data = excel_to_pdf(df, name_column, name_value, seal_image)
                        
                        st.success("PDFの生成が完了しました！")
                        st.download_button(
                            label="PDFをダウンロード",
                            data=pdf_data,
                            file_name="output.pdf",
                            mime="application/pdf"
                        )
            else:
                st.info("名前を入力すると電子印のプレビューが表示されます")
                
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
