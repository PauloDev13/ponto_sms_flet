import subprocess


# FUNÇÃO QUE COMPACTA E TRANSFORMA EM PRETO E BRANCO (GRAY) ARQUIVO PDF
# OBS: É preciso instalar no PC o aplicativo (ghostscript) e configurar
# a variável de ambiente do Windows para o executável do aplicativo
def compress_pdf_with_ghostscript(input_pdf, output_pdf, quality='screen'):
    # Caminho para o executável do aplicativo (ghostscript)
    gs = r'C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe'

    # Definir o comando Ghostscript para compressão
    gs_command = [
        gs,
        '-sDEVICE=pdfwrite',
        '-sColorConversionStrategy=Gray',  # Converte para preto e branco
        '-dProcessColorModel=/DeviceGray',
        f'-dPDFSETTINGS=/{quality}',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        f'-sOutputFile={output_pdf}',
        input_pdf
    ]

    # Executar o comando Ghostscript
    subprocess.run(gs_command)
