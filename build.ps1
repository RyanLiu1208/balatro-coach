$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name BalatroCoach --add-data 'data;data' --add-data 'bridge;bridge' app.py
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Write-Host 'Built dist/BalatroCoach.exe'
