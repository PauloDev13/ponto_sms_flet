"""Geração, combinação, compressão e divisão de arquivos PDF.

Port de services/data/generate_pdf_service.py + services/compress_pdf_file.py
+ services/divide_pdf_file.py sem dependências de UI (Flet).

Diferenças em relação ao desktop:
- O binário do Ghostscript é localizado por settings.ghostscript_binary
  (environment GHOSTSCRIPT_BIN) ou por shutil.which, em vez do path fixo.
- Os arquivos temporários da divisão são criados em um diretório temporário
  controlado, não no diretório de trabalho (CWD).
"""
import base64
import logging
import os
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .exceptions import FileGenerationError
from .settings import settings

logger = logging.getLogger(__name__)


def capture_pdf_bytes(driver, url_search: str) -> bytes:
    """Navega até a URL e captura o PDF da página (via CDP).

    Retorna os bytes do PDF individual do mês. Não acumula em variáveis
    globais (o desktop usa o array global 'array_pdf_files').
    """
    driver.get(url_search)

    result = driver.execute_cdp_cmd('Page.printToPDF', {
        'landscape': False,
        'paperWidth': 8.27,   # Largura do papel (A4)
        'paperHeight': 11.69,  # Altura do papel (A4)
        'marginTop': 0.5,      # Margem superior
        'marginBottom': 0.5,   # Margem inferior
        'marginLeft': 0.5,     # Margem esquerda
        'marginRight': 0.5,    # Margem direita
        'printBackground': False,
        # Escala reduzida para o modo retrato: a tabela de ponto do portal
        # é larga e, em A4 vertical (área útil ~7,27"), estoura a margem
        # direita (corte) e transborda para uma 2ª página em branco. Com
        # scale 0.6 o conteúdo cabe na área imprimível de uma única página.
        'scale': 0.6,
        'displayHeaderFooter': True,
        # Cabeçalho intencionalmente vazio: evita expor o título da página.
        'headerTemplate': '',
        # Rodapé com apenas data/hora e numeração de páginas. O token
        # "url" (que continha o CPF na query string) foi removido para
        # não vazar dados sensíveis do servidor no PDF.
        'footerTemplate': '''
                <div style="font-size:10px; width: 100%; text-align: center;">
                    <span class="date"></span> |
                    Página <span class="pageNumber"></span> de <span class="totalPages"></span>
                </div>''',
    })

    return base64.b64decode(result['data'])


def combine_pdfs(pdf_bytes_list: list[bytes], output_path: str | Path) -> Path:
    """Combina os PDFs individuais num único arquivo.

    Retorna o caminho do arquivo combinado (sem compressão/divisão, que
    ficam a cargo da camada de chamada — ver process_pdf_artifact).
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        pdf_writer = PdfWriter()
        for pdf_bytes in pdf_bytes_list:
            if not pdf_bytes:
                continue
            pdf_reader = PdfReader(BytesIO(pdf_bytes))
            pdf_writer.append(pdf_reader)

        with open(output, 'wb') as output_pdf:
            pdf_writer.write(output_pdf)
        return output
    except Exception as e:
        raise FileGenerationError(f'Erro ao combinar PDFs: {e}', cause=e) from e


def find_ghostscript() -> str | None:
    """Localiza o executável do Ghostscript (env, PATH ou path padrão)."""
    if settings.ghostscript_binary and Path(settings.ghostscript_binary).exists():
        return settings.ghostscript_binary
    found = shutil.which('gswin64c') or shutil.which('gswin32c') or shutil.which('gs')
    if found:
        return found
    default = Path(r'C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe')
    return str(default) if default.exists() else None


def compress_pdf_with_ghostscript(
        input_pdf: str | Path,
        output_pdf: str | Path,
        quality: str = 'screen',
        binary: str | None = None,
) -> Path:
    """Compacta (e converte para grayscale) o PDF usando Ghostscript."""
    gs = binary or find_ghostscript()
    if not gs:
        logger.warning('Ghostscript não encontrado; PDF será mantido sem compressão.')
        raise FileGenerationError('Ghostscript não encontrado: instale o Ghostscript ou defina GHOSTSCRIPT_BIN.')

    output = Path(output_pdf)
    output.parent.mkdir(parents=True, exist_ok=True)

    gs_command = [
        gs,
        '-sDEVICE=pdfwrite',
        '-sColorConversionStrategy=Gray',
        '-dProcessColorModel=/DeviceGray',
        f'-dPDFSETTINGS=/{quality}',
        '-dNOPAUSE',
        '-dQUIET',
        '-dBATCH',
        f'-sOutputFile={output}',
        str(input_pdf),
    ]
    try:
        result = subprocess.run(gs_command, capture_output=True, text=True)
        if result.returncode != 0:
            raise FileGenerationError(
                f'Ghostscript falhou (código {result.returncode}): {result.stderr[:500]}')
        return output
    except FileNotFoundError as e:
        raise FileGenerationError(f'Executável Ghostscript não encontrado: {gs}', cause=e) from e


def get_page_size(reader: PdfReader, page_num: int, workdir: Path) -> int:
    """Tamanho em bytes de uma única página (escrita em workdir temporário)."""
    temp_writer = PdfWriter()
    temp_writer.add_page(reader.pages[page_num])

    temp_filename = workdir / f"temp_page_{page_num}.pdf"
    with open(temp_filename, "wb") as temp_file:
        temp_writer.write(temp_file)

    size = os.path.getsize(temp_filename)
    temp_filename.unlink(missing_ok=True)
    return size


def divide_pdf_by_size(
        input_pdf: str | Path,
        max_size_mb: float,
        output_prefix: str | Path,
) -> list[Path]:
    """Divide o PDF em partes de até max_size_mb, retornando os caminhos criados."""
    max_size_bytes = max_size_mb * 1024 * 1024
    reader = PdfReader(str(input_pdf))
    total_pages = len(reader.pages)

    created: list[Path] = []
    prefix = Path(output_prefix)
    # prefix.name (e não prefix.stem): o stem interpretaria os pontos do
    # CPF (ex.: 'CPF_026.930.289-14') como extensões e cortaria o nome.
    base_name = prefix.name

    with tempfile.TemporaryDirectory(prefix='pdfsplit_') as tmp:
        tmp_dir = Path(tmp)
        writer = PdfWriter()
        part_number = 1
        current_size = 0

        for page_num in range(total_pages):
            page_size = get_page_size(reader, page_num, tmp_dir)

            if current_size + page_size > max_size_bytes:
                output_filename = f"{base_name}_part{part_number}.pdf"
                output_path = prefix.with_name(output_filename)
                with open(output_path, "wb") as output_file:
                    writer.write(output_file)
                created.append(output_path)

                writer = PdfWriter()
                current_size = 0
                part_number += 1

            writer.add_page(reader.pages[page_num])
            current_size += page_size

        if current_size > 0:
            final_output = f'{base_name}_part{part_number}.pdf'
            output_path = prefix.with_name(final_output)
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            created.append(output_path)

    return created


def process_pdf_artifact(
        pdf_bytes_list: list[bytes],
        output_path: str | Path,
        max_size_mb: float = 6.5,
        compress: bool = True,
        binary: str | None = None,
) -> list[Path]:
    """Pipeline completo do artefato PDF (combina + compacta + divide).

    Retorna a lista dos arquivos finais gerados. Se a compressão com
    Ghostscript não estiver disponível, o PDF combinado é mantido como está
    (com aviso no log) em vez de quebrar o fluxo.
    """
    combined = combine_pdfs(pdf_bytes_list, output_path)

    if not compress:
        return [combined]

    compressed_path = combined.with_name(combined.stem + '_pb.pdf')
    try:
        compress_pdf_with_ghostscript(combined, compressed_path, binary=binary)
    except FileGenerationError:
        logger.warning('Compressão indisponível; mantendo PDF combinado original.')
        compressed_path = combined

    prefix = compressed_path.with_suffix('')
    try:
        parts = divide_pdf_by_size(compressed_path, max_size_mb, prefix)
    except Exception as e:
        logger.warning('Falha na divisão do PDF: %s', e)
        parts = [compressed_path]

    return parts