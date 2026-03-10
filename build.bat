@echo off
echo Installing dependencies...
pip install pywebview feedparser requests beautifulsoup4 pyinstaller

echo.
echo Building ChewFeed.exe...
python -m PyInstaller --onefile --noconsole --name ChewFeed --icon assets\logo.ico --add-data "assets\logo.png;assets" --collect-all webview app.py

echo.
echo ========================================
echo   Build complete!
echo   EXE is at: dist\ChewFeed.exe
echo ========================================
pause

