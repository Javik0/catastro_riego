import win32com.client
import os
import traceback

try:
    html_path = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\informe_reunion_tecnica.html'
    docx_path = r'C:\Users\HP\OneDrive\Escritorio\CAYAMBE CATASTRO RIEGO\padron-app\public\informe_reunion_tecnica.docx'
    
    print(f"Abriendo {html_path}...")
    word = win32com.client.Dispatch('Word.Application')
    word.Visible = False
    
    doc = word.Documents.Open(os.path.abspath(html_path))
    print(f"Guardando como {docx_path}...")
    # 16 = wdFormatDocumentDefault (natively docx in newer Word)
    doc.SaveAs2(os.path.abspath(docx_path), FileFormat=16)
    doc.Close()
    word.Quit()
    print("Éxito total al generar el archivo .docx nativo!")
except Exception as e:
    print("Error:", str(e))
    traceback.print_exc()
