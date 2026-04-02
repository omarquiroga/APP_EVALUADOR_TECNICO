# Validacion local

## Variables de entorno recomendadas

PowerShell:

```powershell
$env:POSTGRES_DB="evaluador_test"
$env:POSTGRES_TEST_DB="test_evaluador_test"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
$env:DJANGO_SETTINGS_MODULE="settings_test"
```

## Entorno Python

```powershell
Set-Location "C:\PROYECTOS\Evaluador Tecnico LFVU"
C:\Python314\python.exe -m venv .\venv
& '.\venv\Scripts\python.exe' -m pip install -r requirements.txt
```

## Docker / PostgreSQL

Crear el contenedor local:

```powershell
docker run --name postgres-evaluador `
  -e POSTGRES_DB=evaluador_test `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -p 5432:5432 `
  -d postgres:16
```

Si ya existe:

```powershell
docker start postgres-evaluador
```

## Validaciones tecnicas

```powershell
& '.\venv\Scripts\python.exe' manage.py check
& '.\venv\Scripts\python.exe' manage.py makemigrations --check --dry-run
& '.\venv\Scripts\python.exe' manage.py test
```

## Servidor local

Para admin y review:

```powershell
$env:DJANGO_SETTINGS_MODULE="settings_admin"
& '.\venv\Scripts\python.exe' manage.py runserver
```

## Nota sobre Playwright

- La dependencia JavaScript vive en `package.json`.
- En PowerShell conviene usar el binario local para evitar bloqueos de `npx.ps1`:

```powershell
& '.\node_modules\.bin\playwright.cmd' --version
& '.\node_modules\.bin\playwright.cmd' install chromium
```

- Si no hay MCP de navegador disponible en la sesion de Codex, puede hacerse validacion runtime local con ese binario.
