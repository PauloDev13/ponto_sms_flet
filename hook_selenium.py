from PyInstaller.utils.hooks import copy_metadata, collect_submodules

# Coleta todos os submódulos do selenium
hiddenimports = collect_submodules('selenium')

# Adiciona os metadados da biblioteca selenium
datas = copy_metadata('selenium')