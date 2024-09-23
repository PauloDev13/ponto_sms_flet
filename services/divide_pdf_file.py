import os
from pypdf import PdfReader, PdfWriter


def get_page_size(reader: PdfReader, page_num: int) -> int:

    # Retorna o tamanho em bytes de uma única página gerada temporariamente.
    temp_writer = PdfWriter()
    temp_writer.add_page(reader.pages[page_num])

    temp_filename = f"temp_page_{page_num}.pdf"
    with open(temp_filename, "wb") as temp_file:
        temp_writer.write(temp_file)

    size = os.path.getsize(temp_filename)
    os.remove(temp_filename)  # Remove o arquivo temporário

    return size


def divide_pdf_by_size(input_pdf: str, max_size_mb: float, output_prefix: str):
    max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)

    writer = PdfWriter()
    part_number = 1
    current_size = 0

    for page_num in range(total_pages):
        page_size = get_page_size(reader, page_num)

        # Se a página atual ultrapassa o limite, salva o arquivo atual
        if current_size + page_size > max_size_bytes:
            output_filename = f"{output_prefix}_part{part_number}.pdf"
            with open(output_filename, "wb") as output_file:
                writer.write(output_file)
            # print(f'Arquivo {output_filename} salvo com {os.path.getsize(output_filename) / (1024 * 1024):.2f} MB.')

            # Reiniciar o writer e o tamanho acumulado
            writer = PdfWriter()
            current_size = 0
            part_number += 1

        # Adicionar a página e acumula seu tamanho
        writer.add_page(reader.pages[page_num])
        current_size += page_size

    # Salva o restante das páginas, se houver
    if current_size > 0:
        final_output = f'{output_prefix}_part{part_number}.pdf'
        with open(final_output, "wb") as output_file:
            writer.write(output_file)
        # print(f"Arquivo 2 {final_output} salvo com {os.path.getsize(final_output) / (1024 * 1024):.2f} MB.")

