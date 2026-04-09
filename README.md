<h1 align="center">
  <br>
  Diskly
  <br>
</h1>

<h4 align="center">Disk space analyzer for Windows.</h4>

<p align="center">
  <em>Read this in other languages: <a href="README.md">English</a>, <a href="README-es.md">Español</a></em>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-installation-and-usage">Installation & Usage</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-tech-stack">Tech Stack</a>
</p>

---

**Diskly** is a native Windows tool designed to visualize and analyze the space used on your hard drives at extreme speeds. Using low-level techniques to read the Master File Table (MFT) directly, it manages to scan millions of files in a matter of seconds, rivaling industry leaders like *WizTree* or *SpaceSniffer*.

All of this is presented in a modern, warm, and highly responsive graphical interface built with PyQt6.

## ✨ Features

- ⚡ **Lightning-fast scanning** through direct reading of the NTFS **USN Journal** (it only takes 2 to 5 seconds to process over 500,000 files).
- 🗺️ **Native Treemap Visualizer** built for high performance using QPainter with a *Squarified* layout algorithm.
- 🖱️ **Interactive Drill-down**, allowing fluid navigation through folders and subfolders with a single click.
- 🔍 **Instant Search** by name or extension that smartly guides you to the exact location of the file on the map.
- 📊 **Insights Panel** featuring the Top 10 heaviest files at the current directory level.
- 🎨 **Modern and Natural Design**, employing a warm palette and clean typography, without distractions.
- 🛡️ **Smart UAC Auto-elevation**: the app requests administrator permissions upon opening and includes a fallback mode in case privileges are denied.

---

## 🚀 How It Works

To achieve performance similar to industrial tools, Diskly does not rely on traditional Python searches (`os.walk` or `os.scandir`). Instead, it communicates at a low level with the Windows kernel.

### 1. The Scanning Engine (USN Journal)
When running Diskly as an Administrator on an **NTFS** partition, the application uses the native Windows API `DeviceIoControl` with the `FSCTL_ENUM_USN_DATA` flag. This literally "dumps" the entire disk table into memory in a single blocking hit of less than a second, returning the File Reference Numbers (FRNs) of each entry.
Then, it iteratively reconstructs the disk's family tree (without recursion) using strict 48-bit identifier masking. Calls to `os.stat` to obtain sizes are deferred and executed by taking full advantage of the OS RAM cache.

### 2. Base Data Structure (Trie)
All this raw information feeds a tree (`DirNode`) where the post-processing magic happens: post-order propagation to sum gigabytes up to the root folders `O(n)`, and fixed-size heap generation to calculate the Top 10 heaviest files in real-time `O(n log k)`.

### 3. Rendering and Layout (*Squarified*)
Rather than relying on heavy embedded web browsers, a 100% native rendering pipeline (`QPainter`) was built. It calculates the perfect aspect ratio (as close to 1:1 squares as possible) using a *Squarified* system, visually prioritizing the most massive directories.

---

## 💻 Installation and Usage

### Prerequisites
- Windows 10 or 11.
- Python 3.11 or higher.
- *Administrator permissions enabled on the user session.*

---

## 🏗️ Architecture

The project follows a clear separation of concerns between view and logic (without strictly being MVC).

```text
Diskly/
├── main.py                  # Entry point — UAC auto-elevation and QtWidgets initialization.
├── scanner/                 # (Backend) All low-level OS interaction.
│   ├── mft_scanner.py       # USN Journal engine and os.scandir fallback.
│   ├── scanner_thread.py    # QThread linking the blocking scanner with the UI.
│   └── dir_trie.py          # RAM Trie structure, path-aware searching.
├── ui/                      # (Frontend) PyQt6.
│   ├── main_window.py       # Interconnects dockable layout signals.
│   ├── control_panel.py     # Left-sidebar (Inputs, search results and Top10).
│   └── treemap_view.py      # Right-view (Raw Qt Canvas).
├── utils/                   
│   ├── elevation.py         # Kernel32 wrappers for elevation.
│   └── squarify.py          # Math for fractal map subdivision.
└── styles/
    └── app.qss              # System stylesheet.
```

---

## ⚙️ Tech Stack

- **[PyQt6](https://pypi.org/project/PyQt6/)** base UI and rendering framework.
- **[pywin32](https://pypi.org/project/pywin32/)** the necessary bridge to talk directly with Win32API (`win32file`).
- **[psutil](https://pypi.org/project/psutil/)** for initial state collection of mounted drives.
- **[PyInstaller](https://pyinstaller.org/en/stable/)** packaging and distribution.

---
> Project developed with a primary focus on I/O access speed to modern Microsoft file systems.
