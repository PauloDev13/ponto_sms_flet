import flet as ft

# Busca no arquivo (.env) o caminho para o arquivo .csv  (PATH_CSV)
from config.config_env import PATH_CSV

# Importações dos módulos locais
from services.data.data_read_csv import read_csv_text_field

# Atribui à variável (data_csv) o retorno da função
# (read_csv_text_field) que lê o arquivo .CSV
data_csv: list[dict[str, str]] = read_csv_text_field(PATH_CSV)


# FUNÇÃO CHAMADA QUANDO O USUÁRIO DIGITA NO TEXTFIELD PARA PESQUISAR AS UNIDADES
def search_description(e) -> None:
    # Atribui à variável (input_text) o valor do
    # controle FieldText passado no parâmetro (e)
    input_text: str = e.control.value.lower()

    # Limpa o conteúdo do controle (results) que é um ListView
    results.clean()
    results.update()

    # Atribui à variável (filtered_items) o dicionário com o resultado
    # da pesquisa no arquivo CSV quando o texto pesquisado tiver mais
    # de 2 caracteres e estiver contido na chave (description) do dicionário
    filtered_items = [
        item for item in data_csv if len(input_text) > 1 and input_text in item['description'].lower()
    ]

    # Se o tamanho de (filtered_items) for maior que zero - retornou resultados,
    # itera sobre ele e adiciona ao ListView (results) os items. No evento (on_click)
    # do ListView, chama a função (selected_item) passando o (item) como argumento
    if len(filtered_items) > 0:
        for item in filtered_items:
            # Adiciona o item filtrado à lista de resultados
            results.controls.append(ft.ListTile(
                title=ft.Text(value=f'{item.get('code')}-{item.get('description')}'),
                leading=ft.Icon(ft.icons.HEALTH_AND_SAFETY_OUTLINED),
                icon_color='#5a90fc',
                on_click=lambda _, item=item: selected_item(item)
            ))


        # Exibe o Container (list_results) com a lista de unidades filtrada
        list_results.visible = True
    else:
        # Esconde o Container (list_results) com a lista de unidades filtrada
        list_results.visible = False

    list_results.update()


# FUNÇÃO QUE PASSA O FOCO AUTOMÁTICO
def set_focus_end_date(_) -> None:
    # Se o número de caracteres digitados for igual a 7
    if len(start_date_field.value) == 7:
        # Passa o foco para o controle (end_date_field)
        end_date_field.focus()


# FUNÇÃO CHAMADA NO CLICK DO LISTVIEW
def selected_item(item: dict[str, str]) -> None:
    # Atribui ao valor do controle (unit_field) o valor da chave (code)
    unit_field.value = item.get('code')

    # Esconde o Container (list_results) com a lista
    # de unidades filtrada e atualiza o controle
    list_results.visible = False
    list_results.update()

    # Torna o controle (unit_field) somente leitura,
    # retira o ícone da lula e atualiza o controle
    unit_field.read_only = True
    unit_field.prefix_icon = ''
    unit_field.text_align = 'right'
    unit_field.update()

    # Passa o foco para o controle (start_date_field)
    start_date_field.focus()


# -------------------- CONTROLES DOS FOMULÁRIOS --------------------

# Instância uma ListView e atribui à variável (results)
results = ft.ListView(
    divider_thickness=1,
    cache_extent=10,
    spacing=1,
    expand=False,  # Para não ocupar toda a página
    auto_scroll=False,  # Desativa o auto-scroll ao adicionar itens
)

# Instancia um Container que vai exibir a ListView (results)
list_results = ft.Container(
    content=results,
    bgcolor='#21252b',
    visible=False,
    height=200,
    width=565,
    top=260,
    left=110,
    border_radius=5,
    border=ft.border.all(1, '#5a90fc')
)

# Controle que recebe o número do CPF
cpf_field = ft.TextField(
    label='CPF',
    col={'md': 6},
    hint_text='Digite um CPF',
    border_color='#5a90fc',
    autofocus=True,
    text_align=ft.TextAlign.RIGHT,
    expand=True,
)

# Controle que recebe o número da unidade de lotação
unit_field = ft.TextField(
    on_change=lambda e: search_description(e),
    read_only=False,
    col={'md': 6},
    label='Cód. Unidade',
    hint_text='Busca pelo nome da unidade',
    border_color='#5a90fc',
    prefix_icon=ft.icons.SEARCH,
    text_align=ft.TextAlign.LEFT,
    expand=True,
)

# Controle que recebe o período inicial
start_date_field = ft.TextField(
    label='Período Inicial',
    hint_text='Mês/Ano',
    border_color='#5a90fc',
    col={'md': 3},
    text_align=ft.TextAlign.RIGHT,
    expand=True,
    on_change=set_focus_end_date
)

# Controle que recebe o período final
end_date_field = ft.TextField(
    label='Período final',
    hint_text='Mês/Ano',
    border_color='#5a90fc',
    col={'md': 3},
    text_align=ft.TextAlign.RIGHT,
    expand=True
)
