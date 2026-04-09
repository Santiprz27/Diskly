# Diskly — Analizador de Espacio en Disco de Alto Rendimiento

**Diskly** es una herramienta de análisis de disco para Windows inspirada en WizTree. Usa técnicas de lectura directa del sistema de archivos NTFS para ofrecer una indexación extremadamente rápida, presentada en una interfaz moderna con un visualizador Treemap nativo.

---

## ✨ Características

- **Escaneo ultrarrápido** vía USN Journal (modo administrador) — ~2–5s para 500 K+ archivos
- **Visualizador Treemap** nativo con QPainter y layout Squarified
- **Drill-down interactivo** — navega dentro de cualquier carpeta haciendo clic
- **Top 10 archivos más pesados** por subcarpeta en tiempo real
- **Modo fallback** con `os.scandir` si no hay privilegios de administrador
- **UAC auto-elevation** — la app solicita permisos automáticamente al iniciar

---

## 🚀 Cómo Funciona

### 1. Escaneo — Motor de Doble Modo

Al presionar **Analizar**, `ScannerThread` ejecuta el escaneo en segundo plano (sin bloquear la UI) usando uno de dos modos:

#### Modo Primario — USN Journal (Admin requerido)

Cuando corre como Administrador sobre una partición NTFS, Diskly usa las APIs de bajo nivel de Windows en **tres fases**:

| Fase | API | Descripción |
|:-----|:----|:------------|
| **1. Enumeración** | `FSCTL_ENUM_USN_DATA` | Lista todos los FRNs, nombres, padres y atributos de un solo golpe (~100 ms para 500 K archivos) |
| **2. Resolución de paths** | — | Reconstruye la ruta completa de cada archivo recorriendo la cadena de FRNs padres de forma iterativa (sin recursión, sin límite de profundidad) |
| **3. Tamaños** | `os.stat()` | Obtiene el tamaño de cada archivo tras resolver su ruta — una sola syscall por archivo, cacheada por el OS |

> **Por qué FRN masking importa:** cada File Reference Number de NTFS tiene 48 bits de número de registro MFT + 16 bits de número de secuencia. Ambos (clave y padre) deben ser maskeados consistentemente a 48 bits (`& 0x0000_FFFF_FFFF_FFFF`) para que la resolución de rutas funcione correctamente.

#### Modo Fallback — `os.scandir`

Si no hay privilegios de admin o la partición no es NTFS, Diskly realiza un recorrido recursivo iterativo con `os.scandir`. Evita symlinks, archivos de 0 bytes y errores de permisos silenciosamente.

### 2. Estructura de Datos — DirNode Trie

Los datos del escaneo se insertan en un **Trie** donde cada nodo es una carpeta o archivo (`DirNode`). Al finalizar:

- `accumulate()` propaga tamaños en post-orden hacia la raíz — O(n)
- `top_files()` encuentra los N archivos más pesados con un heap de tamaño fijo — O(n log k)
- `get_node()` navega directamente a cualquier subcarpeta por ruta

### 3. Visualización — Treemap Squarified (QPainter nativo)

El visualizador Treemap es 100% nativo (sin WebEngine ni Plotly):

- **Layout Squarified** — aspecto ratio óptimo en cada rectángulo
- **Renderizado QPainter** — sin overhead de DOM ni JavaScript
- **Drill-down y navegación** — clic para entrar a una carpeta, botón Atrás para subir
- **Filtro por tamaño** — nodos < 0.5% del padre se agrupan en `+N más` para mantener la UI rápida

---

## 🏗️ Arquitectura del Proyecto

```
Diskly/
├── main.py                  # Entry point — UAC elevation, QApplication, MainWindow
├── scanner/
│   ├── mft_scanner.py       # Motor de escaneo (USN Journal + os.scandir fallback)
│   ├── scanner_thread.py    # QThread no-bloqueante — wrappea scan_drive()
│   └── dir_trie.py          # DirNode Trie — acumulación, búsqueda, exportación
├── ui/
│   ├── main_window.py       # Ventana principal — layout y señales
│   ├── control_panel.py     # Panel lateral — selector de unidad, búsqueda, top files
│   └── treemap_view.py      # Visualizador Treemap QPainter + layout Squarified
├── utils/
│   ├── elevation.py         # is_admin() + request_elevation() vía UAC
│   └── format_bytes.py      # Formateador human-readable de bytes
└── styles/
    └── app.qss              # Dark theme "Neon Coral on Space Black"
```

---

## 🛠️ Stack Tecnológico

| Librería | Versión mínima | Propósito |
|:---------|:--------------|:----------|
| **PyQt6** | 6.6.0 | Framework UI de escritorio — widgets, QThread, QPainter |
| **psutil** | 5.9.0 | Detección de unidades, particiones y estadísticas de uso |
| **pywin32** | 306 | APIs Win32 para acceso directo al USN Journal vía `DeviceIoControl` |
| **send2trash** | 1.8.3 | Integración con la Papelera de Reciclaje de Windows |
| **pandas** | 2.0.0 | Procesamiento de datos para exportación del árbol |
| **PyInstaller** | 6.0.0 | Compilación a ejecutable `.exe` portable |

---

## 🎨 Guía de Diseño — "Neon Coral on Space Black"

El sistema de diseño se carga desde `styles/app.qss`:

| Token | Valor | Uso |
|:------|:------|:----|
| `Space Black` | `#121313` | Fondo principal |
| `Neon Coral` | `#ff6044` | Botón Analizar, breadcrumbs activos, resaltado |
| `Surface` | `#1e1f1f` | Paneles y cards |
| `Typography` | Segoe UI 10pt | Legibilidad en Windows |

---

## 📦 Instrucciones para Desarrolladores

### Requisitos

- Windows 10/11
- Python 3.11+
- Cuenta de Administrador (para el modo rápido)

### Instalación

```bash
git clone <repo>
cd Diskly
pip install -r requirements.txt
```

### Ejecución

```bash
# Opción 1 — directo
python main.py

# Opción 2 — script batch (recomendado, activa logging)
run.bat
```

> La app detecta automáticamente si no tiene privilegios de Administrador y muestra el prompt UAC para re-lanzarse con los permisos necesarios.

### Compilación a EXE

```bash
build_exe.bat
```

El archivo `diskly.spec` empaqueta los estilos QSS y los assets necesarios. El ejecutable resultante solicita privilegios de admin automáticamente mediante un manifiesto UAC embebido.

### Test del Scanner

Para verificar el motor de escaneo de forma aislada (requiere correr como admin para el modo rápido):

```bash
python temp_test_scan_mft.py C
```

Imprime métricas detalladas: cantidad de archivos, tamaño total, tiempo por fase y resultado PASS/FAIL.

---

## ⚠️ Notas Técnicas

- **Privilegios de Admin**: necesarios para acceder al USN Journal vía `DeviceIoControl`. Sin admin, el modo scandir es el fallback automático.
- **Solo NTFS**: el modo USN solo funciona en particiones NTFS. FAT32/exFAT usan el fallback scandir.
- **FRN Masking**: los File Reference Numbers del USN Journal deben maskearse a 48 bits para que la resolución de rutas sea consistente.
- **Codificación**: todos los recursos se cargan en UTF-8 para evitar errores en sistemas con localización distinta al inglés.
- **Sin recursión**: la resolución de rutas y la traversal del árbol son iterativas, sin riesgo de `RecursionError` en discos con miles de niveles de anidamiento.
