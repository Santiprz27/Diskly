<h1 align="center">
  <br>
  💿 Diskly
  <br>
</h1>

<h4 align="center">Analizador de espacio en disco de alto rendimiento para Windows.</h4>

<p align="center">
  <a href="#-características">Características</a> •
  <a href="#-cómo-funciona">Cómo Funciona</a> •
  <a href="#-instalación-y-uso">Instalación y Uso</a> •
  <a href="#-arquitectura">Arquitectura</a> •
  <a href="#-stack-tecnológico">Stack</a>
</p>

---

**Diskly** es una herramienta nativa para Windows diseñada para visualizar y analizar el uso del espacio en tus discos duros a una velocidad extrema. Empleando técnicas de bajo nivel para leer la Master File Table (MFT) directamente, logra escanear millones de archivos en cuestión de segundos, compitiendo con líderes del sector como *WizTree* o *SpaceSniffer*.

Todo ello presentado en una interfaz gráfica moderna, cálida y altamente responsiva construida con PyQt6.

## ✨ Características

- ⚡ **Escaneo ultrarrápido** a través de la lectura directa del **USN Journal** de NTFS (solo toma de 2 a 5 segundos procesar más de 500.000 archivos).
- 🗺️ **Visualizador Treemap nativo** de alto rendimiento implementado en QPainter con un algoritmo de distribución *Squarified*.
- 🖱️ **Drill-down interactivo**, permitiendo la navegación fluida a través de carpetas y subcarpetas con un clic.
- 🔍 **Búsqueda instantánea** inteligente por nombre o extensión que te guía a la ubicación exacta del archivo en el mapa.
- 📊 **Panel de Insights** con el Top 10 de los archivos más pesados en el nivel actual.
- 🎨 **Diseño Moderno y Natural**, utilizando una paleta cálida y tipografía limpia, sin distracciones.
- 🛡️ **Auto-elevación UAC** inteligente: la app solicita los permisos de administrador al abrirse y posee un modo "*fallback*" por si el usuario rechaza los privilegios.

---

## 🚀 Cómo Funciona

Para lograr un rendimiento similar a las herramientas industriales, Diskly no usa las búsquedas tradicionales de Python (`os.walk` u `os.scandir`), sino que se comunica en bajo nivel con el kernel de Windows.

### 1. El Motor de Escaneo (USN Journal)
Cuando ejecutas Diskly como Administrador sobre una partición **NTFS**, la aplicación usa la API nativa de Windows `DeviceIoControl` con la bandera `FSCTL_ENUM_USN_DATA`. Esto "vuelca" literalmente toda la tabla del disco en memoria en un solo golpe bloqueante de menos de un segundo, devolviendo los File Reference Numbers (FRNs) de cada entrada. 
Luego, reconstruye el árbol genealógico del disco iterativamente (sin recursión) mediante el enmascaramiento estricto a 48 bits de los identificadores. Las llamadas a `os.stat` para obtener tamaños se postergan y se ejecutan aprovechando al máximo la caché en RAM del sistema operativo.

### 2. Estructura de Datos Base (Trie)
Toda esta información en bruto alimenta un árbol (`DirNode`) donde ocurre la magia post-procesal: propagación en post-orden para sumar los gigabytes a las carpetas raíz `O(n)`, y generación de montículos de tamaño fijo para calcular el Top 10 de archivos pesados en tiempo real `O(n log k)`.

### 3. Renderizado y Layout (*Squarified*)
En lugar de depender de pesados navegadores web embebidos, se construyó un pipeline de renderizado 100% nativo (`QPainter`). Calcula el aspect-ratio perfecto (lo más cercano a cuadros de 1:1) usando un sistema *Squarified*, priorizando los directorios más masivos visualmente.

---

## 💻 Instalación y Uso

### Pre-requisitos
- Windows 10 u 11.
- Python 3.11 superior.
- *Permisos de administrador habilitados en la sesión de usuario.*

### Construyendo desde el código fuente

```bash
# 1. Clona este repositorio
git clone <tu-url-del-repo-github>
cd Diskly

# 2. Instala las dependencias necesarias
pip install -r requirements.txt

# 3. Ejecuta la aplicación 
python main.py
```
*(Nota: Al ejecutar `main.py`, la aplicación forzará un relanzamiento mostrándo el Prompt de Administrador de Windows).*

### Compilación a ejecutable (EXE)

Si deseas tener un programa portable sin necesidad de tener la consola detrás:

```bash
# Simplemente ejecuta el batch:
build_exe.bat
```
Esto creará una carpeta `/dist` en donde estará `Diskly.exe` autocontenido y listo para usar en cualquier PC de Windows.

---

## 🏗️ Arquitectura

El proyecto sigue una separación clara entre vista y lógica (sin llegar a ser un estricto MVC).

```text
Diskly/
├── main.py                  # Entry point — UAC auto-elevation e inicio de QtWidgets.
├── scanner/                 # (Backend) Toda la interacción a bajo nivel con el SO.
│   ├── mft_scanner.py       # Motor USN Journal y os.scandir fallback.
│   ├── scanner_thread.py    # QThread que comunica el scanner bloqueante con la UI.
│   └── dir_trie.py          # Estructura del Trie en RAM, búsquedas path-aware.
├── ui/                      # (Frontend) PyQt6.
│   ├── main_window.py       # Interconecta las señales del layout dockeable.
│   ├── control_panel.py     # Left-sidebar (Inputs, listas de búsquedas y Top10).
│   └── treemap_view.py      # Right-view (Canvas en crudo de Qt).
├── utils/                   
│   ├── elevation.py         # Wrappers de Kernel32 para elevación.
│   └── squarify.py          # Matemáticas para la subdivisión fractal del mapa.
└── styles/
    └── app.qss              # Hoja de estilos del sistema.
```

---

## ⚙️ Stack Tecnológico

- **[PyQt6](https://pypi.org/project/PyQt6/)** framework base de renderizado y UI.
- **[pywin32](https://pypi.org/project/pywin32/)** el enlace necesario para hablar directamente con el Win32API (`win32file`).
- **[psutil](https://pypi.org/project/psutil/)** para la recolección inicial del estado de discos montados.
- **[PyInstaller](https://pyinstaller.org/en/stable/)** empaquetado y distribución.

---
> Proyecto desarrollado con enfoque primario en la velocidad de acceso I/O a sistemas de archivos modernos de Microsoft.
