#! /bin/sh
pyinstaller --onefile pyautosrt.pyw --additional-hooks-dir=./ --noconsole --windowed
