# Diskly

A high-performance disk analysis tool for Windows, providing visual insights into storage distribution and file system structure.

## Description
Diskly is a powerful Python-based utility designed to help users understand how their disk space is being utilized. Inspired by tools like WinDirStat, it offers a combination of fast scanning algorithms (including MFT parsing) and a dynamic TreeMap visualization to identify large files and folders at a glance.

## Detailed Overview
Managing disk space effectively is a common challenge. Diskly addresses this by providing a comprehensive overview of the file system. It features a custom-built TreeMap implementation that represents files and folders as nested rectangles, where the area corresponds to the file size. The tool also includes a fast scanner that can directly read the NTFS Master File Table (MFT) for near-instant results on large volumes when run with appropriate privileges.

## Features
- Fast NTFS MFT scanning for rapid disk analysis
- Interactive TreeMap visualization of file and folder sizes
- Real-time file categorization and filtering
- Detailed folder exploration and file attribute viewing
- Support for multiple volumes and directories
- Professional UI with custom styling (QSS)

## Technologies Used
- Python 3.x
- PyQt / PySide (GUI Framework)
- Squarify (TreeMap algorithm)
- NTFS system integration (for MFT scanning)

## Installation Instructions
1. Clone the repository:
   ```bash
   git clone https://github.com/Santiprz27/Diskly.git
   ```
2. Navigate to the project directory:
   ```bash
   cd Diskly
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python main.py
   ```

## Usage Examples
1. Launch Diskly as Administrator (required for MFT scanning).
2. Select the drive or folder you wish to analyze.
3. Click "Scan" to start the process.
4. Interact with the TreeMap to navigate through your file system and identify space-consuming files.

## Project Structure
- `main.py`: Entry point for the application.
- `main_window.py`: Primary GUI logic and window management.
- `treemap_view.py`: Implementation of the interactive TreeMap visualization.
- `scanner_thread.py`: Background processing for file system scanning.
- `app.qss`: Stylesheet for the application interface.
- `ui/`: Directory for UI components and layouts.
- `utils/`: Common utilities and helper functions.

## Configuration
Diskly can be configured via environment variables or settings within the application for custom scan depths and visualization preferences.

## API Documentation
Internal modules are documented using standard docstrings. For developer-focused information, refer to the `utils` and `scanner` directories.

## Screenshots or Examples
![Diskly TreeMap Visualization](Diskly.lnk) *(Placeholder for actual visualization screenshot)*

## Roadmap / Future Improvements
- Cross-platform support for Linux and macOS
- Advanced file search and deletion capabilities
- Exporting scan results to various formats (JSON, CSV)
- Integration with cloud storage providers

## Contributing Guidelines
We welcome contributions through pull requests. Please follow PEP 8 style guidelines for Python code.

## License
MIT License

---

# Diskly (Español)

Una herramienta de análisis de disco de alto rendimiento para Windows, que proporciona información visual sobre la distribución del almacenamiento y la estructura del sistema de archivos.

## Descripción
Diskly es una potente utilidad basada en Python diseñada para ayudar a los usuarios a comprender cómo se está utilizando su espacio en disco. Inspirado en herramientas como WinDirStat, ofrece una combinación de algoritmos de escaneo rápido (incluyendo el análisis de MFT) y una visualización dinámica de tipo TreeMap.

## Resumen Detallado
Gestionar el espacio en disco de manera efectiva es un desafío común. Diskly aborda esto proporcionando una visión general completa del sistema de archivos. Cuenta con una implementación personalizada de TreeMap que representa archivos y carpetas como rectángulos anidados, donde el área corresponde al tamaño del archivo.

## Características
- Escaneo rápido de NTFS MFT para un análisis veloz
- Visualización interactiva mediante TreeMap de los tamaños de archivos y carpetas
- Categorización y filtrado de archivos en tiempo real
- Exploración detallada de carpetas y visualización de atributos de archivos
- Soporte para múltiples volúmenes y directorios
- Interfaz profesional con estilos personalizados (QSS)

## Tecnologías Utilizadas
- Python 3.x
- PyQt / PySide (Framework de GUI)
- Squarify (Algoritmo de TreeMap)
- Integración con el sistema NTFS

## Instrucciones de Instalación
1. Clonar el repositorio:
   ```bash
   git clone https://github.com/Santiprz27/Diskly.git
   ```
2. Navegar al directorio del proyecto:
   ```bash
   cd Diskly
   ```
3. Instalar las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecutar la aplicación:
   ```python
   python main.py
   ```

## Ejemplos de Uso
1. Iniciar Diskly como Administrador (requerido para el escaneo de MFT).
2. Seleccionar la unidad o carpeta que deseas analizar.
3. Haz clic en "Escanear" para comenzar el proceso.
4. Interactúa con el TreeMap para navegar por tu sistema de archivos e identificar archivos voluminosos.

## Estructura del Proyecto
- `main.py`: Punto de entrada de la aplicación.
- `main_window.py`: Lógica principal de la GUI y gestión de ventanas.
- `treemap_view.py`: Implementación de la visualización interactiva TreeMap.
- `scanner_thread.py`: Procesamiento en segundo plano para el escaneo del sistema.
- `app.qss`: Hoja de estilos para la interfaz de la aplicación.
- `ui/`: Directorio para componentes de interfaz y diseños.
- `utils/`: Utilidades comunes y funciones auxiliares.

## Configuración
Diskly puede configurarse a través de variables de entorno o ajustes dentro de la aplicación para profundidades de escaneo personalizadas.

## Documentación de la API
Los módulos internos están documentados utilizando docstrings estándar.

## Capturas de Pantalla o Ejemplos
![Visualización de Diskly](Diskly.lnk)

## Hoja de Ruta / Mejoras Futuras
- Soporte multiplataforma para Linux y macOS
- Capacidades avanzadas de búsqueda y eliminación de archivos
- Exportación de resultados a varios formatos (JSON, CSV)
- Integración con proveedores de almacenamiento en la nube

## Guía para Contribuir
¡Las contribuciones son bienvenidas! Por favor, sigue las guías de estilo PEP 8 para el código Python.

## Licencia
Licencia MIT
