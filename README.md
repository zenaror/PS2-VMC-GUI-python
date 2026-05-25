# PS2-VMC-GUI

A Python port of the PS2-VMC-GUI tool for managing PlayStation 2 virtual memory cards.

This project is based on the original GUI fork at https://github.com/MegaBitmap/PS2-VMC-GUI and keeps the same functionality for reading and managing PS2 VMC files.

## Features

- Read and manage PS2 virtual memory card files (`.bin`, `.vmc`, `.ps2`, `.mcd`)
- Import `.psu` / `.PSV` saves into a VMC file
- Export VMC files to `.psu`
- Designed for use with OPL and other PS2 memory card workflows

## Usage

1. Clone this repository or download it as a ZIP.
2. Extract the files into a folder.
3. Run:

```bash
python vmc_gui.py
```

On Linux, you can also use:

```bash
./run.sh
```

## Warning

Importing multiple saves from the same game can overwrite previous save data.

## Credits

- Original GUI fork: https://github.com/MegaBitmap/PS2-VMC-GUI
- PS2VMC Tool by Bucanero: https://github.com/bucanero/ps2vmc-tool
- ps2-covers: https://github.com/xlenore/ps2-covers
- Based on ps3mca-tool by jimmikaelkael

## License

This software is licensed under GNU GPLv3. See the `LICENSE` file for details.
