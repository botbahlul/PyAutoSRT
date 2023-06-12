@echo off
setlocal

set "folderToDelete1=.\build"
set "folderToDelete2=.\dist"
set "folderToDelete3=.\vosk_autosrt.egg-info"

if exist "%folderToDelete1%" (
    rmdir /s /q "%folderToDelete1%"
    if errorlevel 1 (
        echo Error occurred while deleting the folder.
    )
)

if exist "%folderToDelete2%" (
    rmdir /s /q "%folderToDelete2%"
    if errorlevel 1 (
        echo Error occurred while deleting the folder.
    )
)

if exist "%folderToDelete3%" (
    rmdir /s /q "%folderToDelete3%"
    if errorlevel 1 (
        echo Error occurred while deleting the folder.
    )
)

python setup.py sdist
rem python setup.py bdist_wheel --plat-name win_amd64
python setup.py bdist_wheel

endlocal
