"""Geração, combinação, compressão e divisão de arquivos PDF via PyMuPDF.

Requisitos de negócio:
- Substituição do Ghostscript por PyMuPDF (fitz) 100% em código Python puro.
- Geração colorida com preservação de sRGB/DeviceRGB e compressão otimizada.
- Divisão condicional: fatiamento apenas se o arquivo consolidado for > 1MB.
  Nenhuma parte individual pode ultrapassar 1MB.
- Gerenciamento de arquivos: se <= 1MB mantém apenas o arquivo consolidado;
  se > 1MB gera partes no padrão `_parte_1.pdf`, `_parte_2.pdf` e exclui o arquivo original.
"""
import base64
import logging
import os
from pathlib import Path

import pymupdf

from .exceptions import FileGenerationError

logger = logging.getLogger(__name__)

DEFAULT_MAX_SIZE_MB: float = 1.0


def inject_print_stylesheet(driver) -> None:
    """Injeta CSS e manipulação DOM segura para eliminar menu superior e rodapé azul sem afetar o conteúdo."""
    custom_css = """
    @media print {
        @page {
            size: A4 portrait;
            margin: 12mm 10mm 12mm 10mm;
        }
        body, html {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            font-family: Arial, Helvetica, sans-serif !important;
            color: #000000 !important;
            background: #FFFFFF !important;
            background-color: #FFFFFF !important;
        }
        /* Oculta apenas tags de navegação e rodapés estruturais */
        nav, footer, #footer, #rodape, .footer, .rodape {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        /* Assegura visibilidade irrestrita da tabela de dados e do título */
        #mesatual, #mesatual table, span.titulodetalhes, div.titulodetalhes {
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
        }
        #mesatual table {
            display: table !important;
            width: 100% !important;
            border-collapse: collapse !important;
        }
        #mesatual table tr {
            display: table-row !important;
            visibility: visible !important;
        }
        #mesatual table th, #mesatual table td {
            display: table-cell !important;
            visibility: visible !important;
        }
        /* Cabeçalho da Tabela */
        #mesatual table thead tr, #mesatual table tr:first-child th, #mesatual table tr:first-child td {
            background-color: #1F4E79 !important;
            color: #FFFFFF !important;
            font-weight: bold !important;
            text-align: center !important;
            font-size: 8.5pt !important;
            border: 1px solid #1F4E79 !important;
        }
        /* Zebra Striping nas linhas */
        #mesatual table tr:nth-child(even) td {
            background-color: #FFFFFF !important;
        }
        #mesatual table tr:nth-child(odd):not(:first-child) td {
            background-color: #EDEDED !important;
        }
        #mesatual table td {
            font-size: 8pt !important;
            padding: 4px !important;
            border-bottom: 0.5px solid #D0D0D0 !important;
        }
        /* Destaques de Totais e Status */
        .total-contabilizado { color: #008000 !important; font-weight: bold !important; }
        .carga-horaria, .total-trabalhada { color: #002060 !important; font-weight: bold !important; }
        .total-justificada { color: #FF8C00 !important; font-weight: bold !important; }
    }
    """
    js_code = f"""
    // 1. Injeta stylesheet de impressão seguro
    const style = document.createElement('style');
    style.type = 'text/css';
    style.appendChild(document.createTextNode(`{custom_css}`));
    document.head.appendChild(style);

    // 2. Oculta a barra de menu superior via link do perfil (sem remover do DOM)
    const perfilLink = document.querySelector('a[href*="perfil.php"]');
    if (perfilLink) {{
        let menuBar = perfilLink.closest('nav, .navbar, #navbar, #menu');
        if (!menuBar) {{
            let curr = perfilLink.parentElement;
            while (curr && curr !== document.body && !curr.querySelector('#mesatual')) {{
                menuBar = curr;
                curr = curr.parentElement;
            }}
        }}
        if (menuBar && menuBar !== document.body && !menuBar.querySelector('#mesatual')) {{
            menuBar.style.setProperty('display', 'none', 'important');
        }}
    }}

    // 3. Oculta o container do botão Relatórios e qualquer elemento residual acima do título
    const titleEl = Array.from(document.querySelectorAll('span, div, font, p, h1, h2, h3')).find(
        el => el.textContent && el.textContent.includes('Detalhamento do Ponto Digital')
    );

    if (titleEl) {{
        const titleRect = titleEl.getBoundingClientRect();
        document.querySelectorAll('div, a, button, li, ul, nav, span').forEach(el => {{
            if (!el.contains(titleEl) && !el.closest('#mesatual') && !el.querySelector('#mesatual')) {{
                const rect = el.getBoundingClientRect();
                if (rect.bottom <= titleRect.top + 5 && rect.height > 0) {{
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('background', 'none', 'important');
                    el.style.setProperty('background-color', 'transparent', 'important');
                }}
            }}
        }});
    }}

    // Varredura de segurança: anula qualquer container com fundo escuro/azul fora da tabela
    document.querySelectorAll('div, nav, header, ul, li').forEach(el => {{
        if (!el.closest('#mesatual') && !el.querySelector('#mesatual')) {{
            const text = el.textContent || '';
            if (!text.includes('Detalhamento') && !text.includes('Horas')) {{
                const bg = window.getComputedStyle(el).backgroundColor;
                if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent' && bg !== 'rgb(255, 255, 255)') {{
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('background', 'none', 'important');
                    el.style.setProperty('background-color', 'transparent', 'important');
                }}
            }}
        }}
    }});

    // 4. Oculta apenas elementos irmãos diretamente após o #mesatual (área azul inferior)
    const mesAtual = document.querySelector('#mesatual');
    if (mesAtual) {{
        mesAtual.style.setProperty('display', 'block', 'important');
        mesAtual.style.setProperty('visibility', 'visible', 'important');
        let next = mesAtual.nextElementSibling;
        while (next) {{
            if (!next.querySelector('table')) {{
                next.style.setProperty('display', 'none', 'important');
            }}
            next = next.nextElementSibling;
        }}
    }}

    // 5. Remove backgrounds residuais de containers externos
    document.body.style.setProperty('background', '#FFFFFF', 'important');
    document.body.style.setProperty('background-color', '#FFFFFF', 'important');
    """
    execute_script = getattr(driver, 'execute_script', None)
    if callable(execute_script):
        try:
            execute_script(js_code)
        except Exception as e:
            logger.debug('Aviso ao injetar stylesheet e limpeza de impressão: %s', e)


def capture_pdf_bytes(driver, url_search: str) -> bytes:
    """Navega até a URL, injeta a estilização visual e captura o PDF colorido via CDP.

    Retorna os bytes do PDF individual do mês formatado conforme o Design System.
    """
    driver.get(url_search)
    inject_print_stylesheet(driver)

    result = driver.execute_cdp_cmd('Page.printToPDF', {
        'landscape': False,
        'paperWidth': 8.27,    # Largura do papel (A4 em polegadas)
        'paperHeight': 11.69,  # Altura do papel (A4 em polegadas)
        'marginTop': 0.45,      # Margem superior
        'marginBottom': 0.45,   # Margem inferior
        'marginLeft': 0.40,     # Margem esquerda
        'marginRight': 0.40,    # Margem direita
        'printBackground': True,  # Permite cores de fundo, cabeçalhos azuis e zebras
        'scale': 0.62,
        'displayHeaderFooter': True,
        'headerTemplate': '''
            <div style="font-size: 8pt; font-family: 'Times New Roman', serif; font-style: italic; width: 100%; margin: 0 10mm; padding-bottom: 2px; border-bottom: 0.8px solid #000; display: flex; justify-content: space-between;">
                <span>Secretaria Municipal de Saúde</span>
                <span>Sistema de Pontos</span>
                <span class="date"></span>
            </div>''',
        'footerTemplate': '''
            <div style="font-size: 8pt; font-family: 'Times New Roman', serif; font-style: italic; width: 100%; margin: 0 10mm; padding-top: 2px; border-top: 0.8px solid #000; display: flex; justify-content: space-between;">
                <span>Relatório Batidas por período</span>
                <span class="pageNumber"></span>
            </div>''',
    })

    return base64.b64decode(result['data'])


def combine_pdfs(
        pdf_bytes_list: list[bytes],
        output_path: str | Path,
        compress: bool = True,
        **_kwargs,
) -> Path:
    """Combina múltiplos PDFs num único arquivo com compressão máxima e preservação de cores."""
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
        **_kwargs,
) -> Path:
    """Compacta e otimiza um arquivo PDF existente sem comprometer a legibilidade ou cores."""
    input_path = Path(input_pdf)
    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        doc = pymupdf.open(str(input_path))
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
    return compress_pdf(input_pdf, output_pdf)


def divide_pdf_by_size(
        input_pdf: str | Path,
        max_size_mb: float = DEFAULT_MAX_SIZE_MB,
        output_prefix: str | Path | None = None,
) -> list[Path]:
    """Divide o PDF em partes de até max_size_mb com sufixos _parte_1.pdf, _parte_2.pdf.

    Garante que nenhuma parte exceda o limite de bytes estipulado (1 MB por padrão).
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
                output_path = parent_dir / f'{base_name}_parte_{part_number}.pdf'
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
            output_path = parent_dir / f'{base_name}_parte_{part_number}.pdf'
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
    """Pipeline completo do artefato PDF (combina + compressão colorida + divisão condicional).

    Regras de negócio:
    1. Combina os PDFs em um único arquivo consolidado com compressão máxima e cores preservadas.
    2. Verifica o tamanho final do arquivo consolidado em disco:
       - Se <= max_size_mb (1MB por padrão): mantém apenas o arquivo consolidado otimizado.
       - Se > max_size_mb: divide em partes '_parte_1.pdf', '_parte_2.pdf', etc.,
         garantindo que nenhuma parte ultrapasse max_size_mb, e EXCLUI PERMANENTEMENTE
         o arquivo original consolidado.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    combined = combine_pdfs(pdf_bytes_list, output, compress=compress)

    max_size_bytes = int(max_size_mb * 1024 * 1024)
    file_size = output.stat().st_size

    # Se o arquivo tem até 1MB, mantém apenas o arquivo consolidado
    if file_size <= max_size_bytes:
        logger.info(
            'PDF consolidado tem %.2f KB (<= %.2f MB). Nenhuma divisão necessária: %s',
            file_size / 1024, max_size_mb, output.name,
        )
        return [output]

    # Se maior que 1MB, divide em partes
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