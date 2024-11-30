# TNOM - The Nibiru Oracle Monitor

The Nibiru Oracle Monitor is a monitoring tool for the Nibiru Oracle. It monitors if
the price feeder signed and wallet balances of the Nibiru Oracle, and alerts if 
any of these values are out of expected range. TNOM is written in Python, and the
script can be compiled using Nuitka.

To remember later: patchelf

# Installation

There are two ways to run TNOM:
1. Run the script directly
2. Build the script using Nuitka 
3. Or download the compiled version

The script was made with Poetry. You can use poetry to install and run the script, 
use python directly and run it like that, build the script using Nuitka, or download
the compiled version.

## Requirements

- Python 3.11 or higher 
- Poetry (optional)
- All ot the requirements in the requirements.txt file
- patchelf # only if you plan to compile the code
- clang # only if you plan to compile the code

The script was made using Python 3.11 it should work with any version >= 3.11, but it
has only been tested with 3.11. 

Python Poetry was used to manage the dependencies. You can install it and use it to 
run the script, but it is not vital to run the script. It just simplifies the 
process. 
If you want to use Python Poetry, you can install it using the following command:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

If you plan to compile the code you will need to install patchelf, clang and some
essential tools. To install it you can use the following command:

For Debian based systems (Debian, Ubuntu, etc.):
```bash
sudo apt-get update -y \
sudo apt-get install build-essential -y \
sudo apt-get install clang -y \
sudo apt-get install patchelf -y
```

For RHEL based systems (Fedora, Rocky Linux, etc.):
```bash
sudo dnf update -y \ 
sudo dnf groupinstall "Development Tools" -y \
sudo dnf install clang -y \
sudo dnf install patchelf -y
```

## Option 1 - Running the script directly

Run the script using Poetry:

```bash
git clone https://github.com/Cogwheel_Validator/tnom.git # correct this later if needed
cd tnom
# install dependencies
poetry install
poetry run python tnom/main.py --working-dir /path/to/working/dir
```

Run the script using Python directly:

```bash
git clone https://github.com/Cogwheel_Validator/tnom.git # correct this later if needed
cd tnom
# create and activate a virtual environment
python -m venv v-tnom
source v-tnom/bin/activate
pip install -r requirements.txt
# run the script
python tnom/main.py --working-dir /path/to/working/dir
```

## Option 2 - Building the TNOM binary

Building the binary might take time. The code is compiled to C then it is compiled
into an executable binary. Depending on your system, it can up to an hour to build.

Build using Poetry:

```bash
poetry install
poetry run nuitka_builder.py
```

Build using Python directly:

```bash
python -m venv v-tnom
source v-tnom/bin/activate
pip install -r requirements.txt
python nuitka_builder.py
```