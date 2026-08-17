# Importação dos módulos locais
from desktop.models.alert_snackbar import AlertSnackbar

from backend.core.pdf_service import compress_pdf_with_ghostscript as _compress


# FUNÇÃO QUE COMPACTA E TRANSFORMA EM PRETO E BRANCO (GRAY) ARQUIVO PDF
# OBS: É preciso instalar no PC o aplicativo (ghostscript) e configurar
# a variável de ambiente do Windows para o executável do aplicativo
def compress_pdf_with_ghostscript(input_pdf, output_pdf, quality='screen'):
    try:
        # Delega a compactação ao backend.core (que localiza o Ghostscript)
        _compress(input_pdf=input_pdf, output_pdf=output_pdf, quality=quality)
    except Exception as e:
        AlertSnackbar.show(message='Erro ao comprimir os PDFs')
        print(f'Error compressing {input_pdf}', e)
