# 🚀 TryAkSys

> Retrofitting a Tronxy X5S 3D printer into a fasteners sorting machine
<p align="center">
  <img src="Images/imprimante.png" alt="Picture of our printer" width="500"/>
</p>

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Status](https://img.shields.io/badge/status-in%20progress-yellow)


## 📋 Project Overview
This project is intended for individuals, organizations, or small businesses in need of a low-cost sorting machine.  
This project is designed to be modular and reproducible, which is why all source files, as well as the STL and SolidWorks files needed to print the mods, are available.
The programm is written in Python, using mainly the libraries PyTorch, scikit-learn, scikit-image, open-cv.

## ✨ Features

- Automated fastener detection and sorting
- Computer vision pipeline for object recognition
- Modular hardware design (3D printable parts)
- Low-cost and reproducible system
- Real-time processing

## 🧠 How it works

1. A camera captures images of fasteners
2. Images are processed using computer vision techniques
3. A machine learning model classifies the objects
4. The system sends commands via serial communication to sort the parts

## 📁 Project Structure

```bash
.
├── 3DPrinting/          # STL and Solidworks files
├── dataset_edge         # Processed dataset used for training
├── Images/              # Illustrations images
├── notebooks/           # Post-Processing tets and experiments
├── src/                 # Source code
├── requirements.txt
└── main.py              # Entry point
```

## ⚙️ Installation & Setup

Follow these steps to set up the development environment on your local machine.

### 1. Clone the repository
```bash
git clone https://github.com/gtritzguden/PI01.git
cd project-name
```

### 2. Create a python virtual environment
```bash
python -m venv venv_name
```

### 3. Activate the virtual environment
#### Windows 
```bash
.\venv\Scripts\activate
```
#### macOS / Linux
```
source venv_name/bin/activate
```

### 4. Dependencies
> ⚠️ `torch` and `torchvision` are installed from the PyTorch CPU index to save storage:
> https://download.pytorch.org/whl/cpu

| Package        | Version        |
|----------------|---------------|
| joblib         | 1.5.3         |
| numpy          | 2.4.3         |
| Pillow         | 12.1.1        |
| pyserial       | 3.5           |
| scikit-learn   | 1.8.0         |
| scikit-image   | 0.26.0        |
| torch          | 2.10.0+cpu    |
| torchvision    | 0.25.0+cpu    |
| tqdm           | 4.67.3        |

```bash
pip install -r requirements.txt
```

### 5. Usage
#### Train the model
```bash
python src/train_classifier
```

#### Launch sorting 
- Turn on the printer by pressing the button next to the power cable
- Make sure the printer is connected to the Raspberry Pi5 : the RJ45 cable needs to be plugged in an USB port)
  
```bash
python main.py
```
<p align="center">
  <img src="Images/screenshot.png" alt="GUI" width="500"/>
</p>
Once the GUI has launched, click on "connecter". It allow the communication between the RPI5 and the printer via serial connection
Multiple options then : \ 
- **Home (G28)** Do a homing
- Move the printer's head by using pixel coordinates
- Launch a detection and a classification (whithout sorting) :
---

## 👥 Team Members

| Name | Email |
|------|-------|
| Mathieu Brasseur | [mathieu.brasseur@etu.unistra.fr](mailto:mathieu.brasseur@etu.unistra.fr)|
| Mohamed Hamza Choukaili | [choukaili@etu.unistra.fr](mailto:choukaili@etu.unistra.fr) |
| Nicola Di Pietro| [nicola.di-pietro@etu.unistra.fr](mailto:nicola.di-pietro@etu.unistra.fr) |
| Bilal Erraissi| [bilal.erraissi@etu.unistra.fr](mailto:bilal.erraissi@etu.unistra.fr) 
| Guillaume Tritz--Guden | [guillaume.tritz-guden@etu.unistra.fr](mailto:guillaume.tritz-guden@etu.unistra.fr) |
---

> 🚀 Feel free to contact any of us for questions or collaborations!





