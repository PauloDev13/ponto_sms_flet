"""Geração, combinação, compressão e divisão de arquivos PDF via PyMuPDF.

Requisitos de negócio:
- Substituição do Ghostscript por PyMuPDF (fitz) 100% em código Python puro.
- Conversão nativa em escala de cinza (DeviceGray) e compressão otimizada.
- Divisão condicional: fatiamento apenas se o arquivo consolidado for > 5MB.
  Nenhuma parte individual pode ultrapassar 5MB.
- Gerenciamento de arquivos: se <= 5MB mantém apenas o arquivo consolidado;
  se > 5MB gera partes no padrão `_part_01.pdf` e exclui o arquivo original.
"""
import base64
import logging
import os
from pathlib import Path

import pymupdf

from .exceptions import FileGenerationError

logger = logging.getLogger(__name__)

DEFAULT_MAX_SIZE_MB: float = 5.0


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


def combine_pdfs(
        pdf_bytes_list: list[bytes],
        output_path: str | Path,
        compress_grayscale: bool = True,
) -> Path:
    """Combina os PDFs individuais num único arquivo com compressão e escala de cinza."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        merged = pymupdf.open()
        for pdf_bytes in pdf_bytes_list:
            if not pdf_bytes:
                continue
            src = pymupdf.open(stream=pdf_bytes, filetype='pdf')
            merged.insert_pdf(src)
            src.close()

        if compress_grayscale and len(merged) > 0:
            try:
                merged.recolor(1)  # Converte páginas para DeviceGray (1 componente)
            except Exception as e:
                logger.warning('Aviso ao aplicar grayscale no PDF: %s', e)

        merged.save(
            str(output),
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            garbage=4,
            clean=True,
        )
        merged.close()
        return output
    except Exception as e:
        raise FileGenerationError(f'Erro ao combinar PDFs: {e}', cause=e) from e


def compress_pdf(
        input_pdf: str | Path,
        output_pdf: str | Path,
        grayscale: bool = True,
) -> Path:
    """Compacta e converte para escala de cinza um arquivo PDF existente."""
    input_path = Path(input_pdf)
    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = pymupdf.open(str(input_path))
        if grayscale and len(doc) > 0:
            try:
                doc.recolor(1)
            except Exception as e:
                logger.warning('Aviso ao aplicar grayscale: %s', e)

        doc.save(
            str(output_path),
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            garbage=4,
            clean=True,
        )
        doc.close()
        return output_path
    except Exception as e:
        raise FileGenerationError(f'Erro ao compactar PDF: {e}', cause=e) from e


def compress_pdf_with_ghostscript(
        input_pdf: str | Path,
        output_pdf: str | Path,
        quality: str = 'screen',
        binary: str | None = None,
) -> Path:
    """Compatibilidade legada: delega a compressão ao motor nativo PyMuPDF."""
    return compress_pdf(input_pdf, output_pdf, grayscale=True)


def divide_pdf_by_size(
        input_pdf: str | Path,
        max_size_mb: float = DEFAULT_MAX_SIZE_MB,
        output_prefix: str | Path | None = None,
) -> list[Path]:
    """Divide o PDF em partes de até max_size_mb com sufixos _part_01.pdf, _part_02.pdf.

    Garante que nenhuma parte exceda o limite de bytes estipulado.
    """
    input_path = Path(input_pdf)
    max_size_bytes = int(max_size_mb * 1024 * 1024)

    if output_prefix is None:
        prefix = input_path.with_suffix('')
    else:
        prefix = Path(output_prefix)

    # prefix.name (e não prefix.stem): preserva pontuações do CPF no nome
    base_name = prefix.name
    parent_dir = prefix.parent

    try:
        doc = pymupdf.open(str(input_path))
        total_pages = len(doc)
        created: list[Path] = []

        if total_pages == 0:
            doc.close()
            return created

        part_number = 1
        start_page = 0
        current_doc = pymupdf.open()

        for page_idx in range(total_pages):
            current_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            current_bytes = current_doc.tobytes(
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                garbage=4,
                clean=True,
            )

            # Se ultrapassou o limite e já havia páginas acumuladas na parte
            if len(current_bytes) > max_size_bytes and len(current_doc) > 1:
                current_doc.close()

                # Salva o bloco anterior que cabe no limite
                valid_doc = pymupdf.open()
                valid_doc.insert_pdf(doc, from_page=start_page, to_page=page_idx - 1)
                output_path = parent_dir / f'{base_name}_part_{part_number:02d}.pdf'
                valid_doc.save(
                    str(output_path),
                    deflate=True,
                    deflate_images=True,
                    deflate_fonts=True,
                    garbage=4,
                    clean=True,
                )
                valid_doc.close()
                created.append(output_path)

                part_number += 1
                start_page = page_idx

                current_doc = pymupdf.open()
                current_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)

        if len(current_doc) > 0:
            output_path = parent_dir / f'{base_name}_part_{part_number:02d}.pdf'
            current_doc.save(
                str(output_path),
                deflate=True,
                deflate_images=True,
                deflate_fonts=True,
                garbage=4,
                clean=True,
            )
            current_doc.close()
            created.append(output_path)

        doc.close()
        return created
    except Exception as e:
        raise FileGenerationError(f'Erro ao dividir PDF: {e}', cause=e) from e


def process_pdf_artifact(
        pdf_bytes_list: list[bytes],
        output_path: str | Path,
        max_size_mb: float = DEFAULT_MAX_SIZE_MB,
        compress: bool = True,
        binary: str | None = None,
) -> list[Path]:
    """Pipeline completo do artefato PDF (combina + grayscale/compressão + divisão condicional).

    Regras de negócio:
    1. Combina os PDFs em um único arquivo consolidado com compressão e escala de cinza.
    2. Verifica o tamanho final do arquivo consolidado em disco:
       - Se <= max_size_mb (5MB por padrão): mantém apenas o arquivo consolidado otimizado.
       - Se > max_size_mb: divide em partes '_part_01.pdf', '_part_02.pdf', etc.,
         garantindo que nenhuma parte ultrapasse max_size_mb, e EXCLUI PERMANENTEMENTE
         o arquivo original consolidado.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    combined = combine_pdfs(pdf_bytes_list, output, compress_grayscale=compress)

    max_size_bytes = int(max_size_mb * 1024 * 1024)
    file_size = output.stat().st_size

    # Se o arquivo tem até 5MB, mantém apenas o arquivo consolidado
    if file_size <= max_size_bytes:
        logger.info(
            'PDF consolidado tem %.2f MB (<= %.2f MB). Nenhuma divisão necessária: %s',
            file_size / (1024 * 1024), max_size_mb, output.name,
        )
        return [output]

    # Se maior que 5MB, divide em partes
    logger.info(
        'PDF consolidado tem %.2f MB (> %.2f MB). Dividindo em partes: %s',
        file_size / (1024 * 1024), max_size_mb, output.name,
    )
    prefix = output.with_suffix('')
    try:
        parts = divide_pdf_by_size(output, max_size_mb=max_size_mb, output_prefix=prefix)
        # Se dividiu em múltiplas partes, remove o arquivo original consolidado
        if len(parts) > 1:
            if output.exists():
                output.unlink(missing_ok=True)
                logger.info('Arquivo original consolidado removido com sucesso: %s', output.name)
            return parts
        return parts or [output]
    except Exception as e:
        logger.warning('Falha na divisão do PDF: %s. Mantendo arquivo original consolidado.', e)
        return [output]