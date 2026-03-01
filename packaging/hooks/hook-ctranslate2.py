from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

binaries = collect_dynamic_libs("ctranslate2")
datas = collect_data_files("ctranslate2")
