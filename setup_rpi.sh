#!/usr/bin/env bash
set -euo pipefail

# Raspberry Pi setup for OpenCV + GStreamer in a Python venv.
# - Installs OpenCV from APT (has GStreamer enabled on Raspberry Pi OS)
# - Creates a venv with --system-site-packages so cv2 comes from APT, not pip
# - Installs pip deps from requirements.txt
# - Verifies that OpenCV reports GStreamer: YES

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${PROJECT_DIR}/venv"
REQ_FILE="${PROJECT_DIR}/requirements.txt"

echo "== PI01 RPi Setup =="
echo "Project: ${PROJECT_DIR}"
echo "Venv:    ${VENV_DIR}"
echo

echo "[1/6] Installing system packages (APT)..."
sudo apt update
sudo apt install -y \
  python3-venv python3-dev python3-numpy \
  python3-opencv \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev

echo
echo "[2/6] Creating venv with --system-site-packages..."
rm -rf "${VENV_DIR}"
python3 -m venv "${VENV_DIR}" --system-site-packages

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

echo
echo "[3/6] Upgrading pip tooling..."
python -m pip install -U pip setuptools wheel

echo
echo "[4/6] Ensuring pip OpenCV wheels are NOT installed in the venv..."
python -m pip uninstall -y opencv-python opencv-contrib-python opencv-python-headless >/dev/null 2>&1 || true

echo
echo "[5/6] Installing Python requirements..."
if [[ ! -f "${REQ_FILE}" ]]; then
  echo "ERROR: requirements.txt not found at: ${REQ_FILE}"
  exit 1
fi
python -m pip install -r "${REQ_FILE}"

echo
echo "[6/6] Verifying OpenCV GStreamer support..."
python - <<'PY'
import cv2

print("cv2 path:", cv2.__file__)
print("OpenCV:", cv2.__version__)

info = cv2.getBuildInformation()
gst_lines = [l for l in info.splitlines() if "GStreamer" in l]
print("\n".join(gst_lines[:10]) if gst_lines else "GStreamer line not found in build info")

if not any("YES" in l for l in gst_lines):
    raise SystemExit(
        "\nERROR: OpenCV was built without GStreamer support.\n"
        "- Make sure you did NOT install opencv-python via pip.\n"
        "- Make sure python3-opencv is installed via apt.\n"
        "- Make sure the venv was created with --system-site-packages.\n"
    )

print("\nOK: OpenCV has GStreamer support.")
PY

echo
echo "Done."
echo "Activate your environment with:"
echo "  source venv/bin/activate"
