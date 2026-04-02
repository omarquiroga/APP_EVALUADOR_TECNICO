# Evaluador Tecnico

## Objetivo del proyecto

Aplicacion web interna para apoyar la evaluacion tecnica de ofertas en procesos de contratacion publica en Colombia.

Objetivos no funcionales confirmados:

- trazabilidad
- auditabilidad
- explicabilidad
- seguridad juridico-operativa
- revision humana obligatoria en puntos sensibles

El sistema no reemplaza el juicio profesional ni automatiza decisiones juridicas complejas.

## Stack real

- Python
- Django 6.0.3
- PostgreSQL 16
- Django templates
- HTMX
- Bootstrap por CDN
- Playwright para validacion local de UI

## Modulos principales

- `common`
- `procurement`
- `normative`
- `rules`
- `bidders`
- `documents`
- `rup`
- `experience`
- `finance`
- `external_checks`
- `evaluation`
- `causals`
- `consolidation`
- `audit`
- `review`

## Estado funcional resumido

- Dominio base modelado y migrado.
- Admin endurecido con politicas de lectura, add-only o no-delete segun el modelo.
- `review` implementado como consola operativa fuera del admin.
- Finance implementado como primer flujo de escritura controlada fuera del admin.
- Permisos finos iniciales aplicados solo a Finance en `review`.

## Comandos de arranque y validacion

Variables tipicas en PowerShell:

```powershell
$env:POSTGRES_DB="evaluador_test"
$env:POSTGRES_TEST_DB="test_evaluador_test"
$env:POSTGRES_USER="postgres"
$env:POSTGRES_PASSWORD="postgres"
$env:POSTGRES_HOST="localhost"
$env:POSTGRES_PORT="5432"
```

Entorno:

```powershell
Set-Location "C:\PROYECTOS\Evaluador Tecnico LFVU"
C:\Python314\python.exe -m venv .\venv
& '.\venv\Scripts\python.exe' -m pip install -r requirements.txt
```

Base de datos:

```powershell
docker start postgres-evaluador
```

Validacion:

```powershell
$env:DJANGO_SETTINGS_MODULE="settings_test"
& '.\venv\Scripts\python.exe' manage.py check
& '.\venv\Scripts\python.exe' manage.py makemigrations --check --dry-run
& '.\venv\Scripts\python.exe' manage.py test
```

Servidor local:

```powershell
$env:DJANGO_SETTINGS_MODULE="settings_admin"
& '.\venv\Scripts\python.exe' manage.py runserver
```

Playwright local:

```powershell
& '.\node_modules\.bin\playwright.cmd' --version
& '.\node_modules\.bin\playwright.cmd' install chromium
```

## Reglas de intervencion minima

- Confirmar primero el estado real del repo antes de cambios grandes.
- Preferir cambios pequenos, locales y reversibles.
- No cambiar dominio salvo ajuste minimo imprescindible.
- No abrir nuevos flujos sin plan corto previo.
- Mantener `review` como lugar de lectura/escritura controlada fuera del admin.
- Validar con `check`, `makemigrations --check --dry-run` y `test` despues de cambios funcionales.
- Si hay UI impactada, validar tambien en navegador con Playwright cuando sea viable.

## Que no tocar sin permiso

- otros modulos fuera del alcance pedido
- arquitectura base Django templates + HTMX
- decisiones de negocio juridico-operativas
- modelos sensibles del dominio si no es estrictamente necesario
- borrado de historicos/versiones como solucion rapida
- migraciones o refactors amplios no solicitados
- cambios globales de roles/permisos fuera del modulo objetivo

## Criterio de hecho

Una tarea se considera hecha cuando:

- el cambio esta implementado con superficie controlada
- el comportamiento queda cubierto por tests o validacion equivalente
- `manage.py check` pasa
- `manage.py makemigrations --check --dry-run` pasa
- `manage.py test` pasa
- cualquier decision nueva queda documentada si afecta continuidad
