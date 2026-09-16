# Importação dos módulos locais
from desktop.models.alert_snackbar import AlertSnackbar

from backend.core.pdf_service import compress_pdf as _compress


# FUNÇÃO QUE COMPACTA E TRANSFORMA EM PRETO E BRANCO (GRAY) ARQUIVO PDF VIA PYMUPDF
def compress_pdf_with_ghostscript(input_pdf, output_pdf, quality='screen'):
    try:
        _compress(input_pdf=input_pdf, output_pdf=output_pdf, grayscale=True)
    except Exception as e:
        AlertSnackbar.show(message='Erro ao comprimir os PDFs')
        print(f'Error compressing {input_pdf}', e)

