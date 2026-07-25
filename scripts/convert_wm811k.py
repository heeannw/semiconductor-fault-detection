"""WM-811K(LSWMD.pkl) 원본을 CNN 학습용 npz로 변환.

LSWMD.pkl은 2019년에 아주 오래된 pandas(0.2x대)로 피클링되어 있어서,
이 프로젝트의 메인 가상환경(pandas 3.x)에서는 `pandas.indexes` 모듈을
찾지 못해 그대로 읽을 수 없다. 그래서 이 스크립트는 별도의 레거시
가상환경(pandas==1.5.3)에서 한 번만 실행해 결함 8종 웨이퍼맵만 추출,
32x32로 리사이즈해 data/processed/wafer_map_defects.npz로 저장한다.
이후 노트북(06_wafer_map_cnn.ipynb)은 메인 venv에서 이 npz만 읽는다.

실행 방법:
    python -m venv .venv_legacy
    .venv_legacy/Scripts/pip install "pandas==1.5.3" "numpy<2" pillow
    .venv_legacy/Scripts/python scripts/convert_wm811k.py
    # 변환 끝나면 .venv_legacy는 지워도 된다 (메인 venv/노트북은 npz만 읽음)
"""
import numpy as np
import pandas as pd
from PIL import Image

RAW_PATH = "data/raw/wafer_map/LSWMD.pkl"
OUT_PATH = "data/processed/wafer_map_defects.npz"
IMAGE_SIZE = 32

DEFECT_CLASSES = [
    "Center", "Donut", "Edge-Loc", "Edge-Ring",
    "Loc", "Random", "Scratch", "Near-full",
]


def extract_label(cell) -> str | None:
    arr = np.array(cell)
    if arr.size == 0:
        return None
    return str(arr.flatten()[0])


def resize_wafer_map(wafer_map: np.ndarray, size: int) -> np.ndarray:
    img = Image.fromarray(wafer_map.astype(np.uint8))
    resized = img.resize((size, size), resample=Image.NEAREST)
    return np.array(resized, dtype=np.uint8)


def main():
    print("loading", RAW_PATH)
    df = pd.read_pickle(RAW_PATH)
    print("total rows:", len(df))

    df["failureType_flat"] = df["failureType"].apply(extract_label)
    df["trianTestLabel_flat"] = df["trianTestLabel"].apply(extract_label)

    defects = df[df["failureType_flat"].isin(DEFECT_CLASSES)].copy()
    print("labeled defect rows:", len(defects))
    print(defects["failureType_flat"].value_counts())

    images = np.stack([
        resize_wafer_map(np.array(wm), IMAGE_SIZE) for wm in defects["waferMap"]
    ])
    labels = defects["failureType_flat"].to_numpy()
    split = defects["trianTestLabel_flat"].fillna("Unknown").to_numpy()

    np.savez_compressed(OUT_PATH, images=images, labels=labels, split=split)
    print("saved:", OUT_PATH, "images shape:", images.shape)


if __name__ == "__main__":
    main()
