import sys

from cx_Freeze import setup, Executable

# Configurações do cx_Freeze
build_exe_options = {
    "packages": [
        "flet",
        "selenium",
        "xlsxwriter",
        "dotenv",
        "bs4",
        "lxml",
        "psutil",
        "numpy",
        "pandas",
        "os",
        "sys",
    ],
    "includes": [
        "controls.components",
        "services.authenticate_service",
        "services.generate_service",
        "utils.excel",
        "utils.extractor_data",
        "utils.format_dataframe",
        "utils.format_excel",
        "utils.share_model",
        "utils.validators",
        "dotenv",
    ],
    "include_files": ["assets/", "controls/", "services/", "utils/", ".env", "main.py"],
    # "include_msvcr": True,
}

# Define o executável, com base em Win32GUI para ocultar o console
executables = [
    Executable(
        script="main.py",
        base=None,
        # base="Win32GUI" if sys.platform == "win32" else None,
        target_name="app_sms.exe"
    )
]

setup(
    name="PontoSMSApp",
    version="0.1",
    description="Aplicativo com Flet",
    options={"build_exe": build_exe_options},
    executables=executables
)