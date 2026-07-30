# 🏭 SemiSense — 반도체 공정 시뮬레이터 & 이상 탐지 AI

[![tests](https://github.com/heeannw/semiconductor-fault-detection/actions/workflows/tests.yml/badge.svg)](https://github.com/heeannw/semiconductor-fault-detection/actions/workflows/tests.yml)

*[English version](README.en.md)*

Semiconductor Process Simulator & Fault Detection AI

- **기간:** 6주
- **배포:** Docker (로컬 실행 + CI 빌드 검증) — Hugging Face Space는 Docker SDK 유료 제약으로 보류
- **데이터:** SECOM (UCI)

## 📌 프로젝트 개요

반도체 8대 공정을 시뮬레이션하고, AI로 공정 이상을 실시간 탐지하는 포트폴리오 프로젝트.

### 구조 명확화 (⚠️ 원안에서 수정된 핵심 사항)

| 구성 요소 | 역할 | 비고 |
|---|---|---|
| SECOM 데이터셋 | AI 모델 학습 & 평가용 | UCI 공개 데이터, 실제 반도체 공정 센서 |
| 공정 시뮬레이터 | 실시간 추론용 데이터 생성 | 8대 공정 파라미터 기반 합성 데이터 |

SECOM은 어느 공정에서 나온 데이터인지 라벨이 없음. 따라서 두 모듈을 명확히 분리하여 설계하고, 이 사실을 명시한다. 면접에서 질문받을 포인트이므로 답변 준비 필수.

### AMHS 확장 (SK하이닉스 AMHS 직무 지원용)

SECOM/공정 시뮬레이터 파트가 **"웨이퍼가 불량인가"(FDC)**를 다룬다면, `amhs/`와 `notebooks/07~09`는 **"웨이퍼가 공정 장비까지 제때 도착하는가"(AMHS 물류)**를 다룬다. OHT 반송 시뮬레이션, 디스패칭 알고리즘 비교, 반송 지연 예측, 차량 예지보전에 더해 대시보드의 "AMHS 물류" 화면에서 실시간 실행까지 — 개념 정리는 [docs/AMHS.md](docs/AMHS.md) 참고.

### 수율→비용 정량화 프레임워크 (`notebooks/11_cost_sensitive_threshold.ipynb`)

F1/AUROC는 엔지니어링 지표일 뿐, 공정 매니저나 품질 임원은 "이 모델을 쓰면 얼마를 아끼는가"로 판단한다. 이 노트북은 SECOM 이상 탐지 모델(3주차)의 confusion matrix를 비용 항목(오탐=재검사 비용, 미탐=유출 비용)으로 재해석해서 F1-최적 임계값과 **비용-최적 임계값이 다르다**는 걸 실제로 계산해 보여준다.

**전제**: 웨이퍼당 재검사 비용/유출 비용은 실제 삼성·SK하이닉스 원가가 아니라 예시로 가정한 수치(FN:FP = 50:1, 제조 품질관리의 "10배 법칙"에서 방향성만 차용)다. 이 프레임워크가 실제로 보여주는 건 정확한 금액이 아니라 **재사용 가능한 구조**다:

1. 처음에 임계값을 등간격 그리드(0.01~0.99)로 스윕했더니 "최적값"이 그리드 하한에 걸려 있었다 — 관측된 확률값 전체를 후보로 넓히자 진짜 최적은 그보다 훨씬 아래(약 0.0014)였고, 그 지점은 test set 웨이퍼의 **90%를 재검사로 보내는** 비현실적인 정책이었다.
2. 그래서 "재검사 캐파는 유한하다"는 운영 제약을 추가했다 — 캐파 상한 10%일 때 임계값 0.1115, 캐파-비용 트레이드오프 곡선은 10% 부근부터 수확체감을 보인다.
3. 정직하게 남겨둔 결과: 캐파 10% 제약 버전이 test set(양성 21개뿐)에서는 오히려 F1-최적보다 비용이 더 높게 나온다 — 표본이 작아 정책 간 우열이 뒤집힐 수 있다는 걸 감추지 않았다. 이 프레임워크의 결론은 "우리 방법이 이긴다"가 아니라, **F1 최적화·비용 최적화·운영 제약(캐파)이 서로 다른 질문이고 순서대로 답을 바꾼다는 구조** 그 자체다.

## 📚 참고 논문 & 데이터셋

### 핵심 논문

| # | 제목 | 출처 | 핵심 기법 |
|---|---|---|---|
| ① | 반도체 공정 모니터링 데이터를 이용한 이상탐지 및 분류 | KISTI | 퍼지모델 + 뎀프스터-쉐이퍼 이론, OES 센서 |
| ② | 이상 탐지 모델을 위한 교차 다중작업 학습 방법 | 서울대 SNU | CNN + 셀프 어텐션, 다변량 시계열 |
| ③ | 상관관계 분석 및 데이터 증강을 활용한 설비 고장 감지 | DBpia | Grad-CAM, 특징 행렬, 데이터 증강 |
| ④ | 이상 탐지와 분류를 위한 특징 기반 의사결정 트리 | KISTI | Decision Tree, 피처 선택 방법론 |
| ⑤ | Smart Factory 빅데이터를 활용한 공정 이상 탐지 | KISTI | FDA, 머신러닝 정확도 비교 |

PDF는 `docs/papers/`에 저장.

### 공개 데이터셋

1. **SECOM Dataset (메인)** — [archive.ics.uci.edu/dataset/179/secom](https://archive.ics.uci.edu/dataset/179/secom)
   - 실제 반도체 제조 공정 센서 데이터
   - 590개 피처, 1,567개 샘플
   - 정상 ~93% / 불량 ~7% (심한 클래스 불균형 → 반드시 처리)
   - 결측값 주의: 피처 일부는 결측률 50% 초과
2. **WM-811K Wafer Map** — [kaggle.com/datasets/qingyi/wm811k-wafer-map](https://www.kaggle.com/datasets/qingyi/wm811k-wafer-map) (선택적 활용)
3. **MIMII Dataset** — [zenodo.org/record/3384388](https://zenodo.org/record/3384388) (선택적 확장)

### 참고 GitHub

- [hoya012/awesome-anomaly-detection](https://github.com/hoya012/awesome-anomaly-detection)
- [yzhao062/pyod](https://github.com/yzhao062/pyod)

## 🏗️ 시스템 아키텍처

```
[React 프론트엔드]
    ↕ REST API
[FastAPI 백엔드]
    ↕                        ↕
[AI 모델 서버]           [SQLite DB]
 Isolation Forest          공정 로그
 XGBoost                   이상 기록
 (LSTM — 6주차 이후)       센서 데이터
    ↕
[공정 시뮬레이터]
 8대 공정 합성 데이터 생성
 → 학습된 모델로 실시간 추론
```

## 🛠️ 기술 스택

| 영역 | 기술 |
|---|---|
| 백엔드 | FastAPI + Uvicorn |
| AI/ML | scikit-learn, XGBoost, PyOD, (PyTorch — 선택) |
| 프론트엔드 | React + Recharts + Chart.js |
| DB | SQLite |
| 시각화 | Plotly, Matplotlib |
| 배포 | Hugging Face Space (Docker) |
| 버전관리 | GitHub |

## 📁 프로젝트 구조

```
semiconductor-fault-detection/
├── data/
│   ├── raw/            # SECOM 원본 데이터 (git 미추적)
│   └── processed/      # 전처리 완료 데이터
├── docs/
│   ├── papers/         # 참고 논문 PDF
│   └── AMHS.md          # AMHS 개념 정리 (SK하이닉스 AMHS 직무 지원용)
├── notebooks/          # EDA, 실험용 Jupyter Notebook
├── simulator/           # 8대 공정 합성 데이터 생성기
├── amhs/                # OHT 반송 시뮬레이션, 디스패칭, 예지보전 (AMHS 확장)
├── models/              # 학습된 모델 아티팩트
├── backend/
│   ├── app/              # FastAPI 서버
│   ├── requirements.txt   # 런타임 전용 슬림 의존성 (Docker 이미지용)
│   └── Dockerfile
├── frontend/            # React 대시보드
│   └── Dockerfile
└── docker-compose.yml   # 백엔드+프론트엔드 로컬 실행
```

## 📅 6주 로드맵

### 1주차: 환경 설정 + 데이터 전처리

- GitHub 레포 생성, SECOM 데이터 다운로드 및 EDA
- 결측값 패턴 시각화(`seaborn.heatmap`), 결측률 50% 초과 피처 제거
- 나머지 결측값은 중앙값 대체, 분산 0/저분산 피처 제거, `StandardScaler` 정규화
- 클래스 불균형 처리: SMOTE 또는 `class_weight='balanced'`, 평가지표는 F1-score/AUROC 사용

### 2주차: 공정 시뮬레이터 구현

8대 공정 파라미터 기반 합성 데이터 생성기. SECOM과 직접 연결되지 않으며, 학습된 모델에 실시간 입력을 공급하는 역할.

| 공정 | 주요 파라미터 | 정상 범위 |
|---|---|---|
| ① 웨이퍼 제조 | 온도, 산소 농도, 저항률 | 1400~1500°C, 0~10ppb, 1~100Ω·cm |
| ② 산화 | 온도, 시간, 산화막 두께 | 900~1200°C, 10~120min, 10~1000nm |
| ③ 포토 | 노광 에너지, 초점 거리, 온도 | 10~50mJ/cm², ±0.1μm, 90~130°C |
| ④ 식각 | 압력, 가스 유량, 파워 | 5~100mTorr, 10~200sccm, 100~2000W |
| ⑤ 증착 | 온도, 압력, 증착 속도 | 300~900°C, 0.1~10Torr, 1~100nm/min |
| ⑥ 금속 배선 | 전류 밀도, 온도, 도금 시간 | 1~10mA/cm², 20~80°C, 1~30min |
| ⑦ EDS | 테스트 전압, 전류 | 1~5V, 1~100μA |
| ⑧ 패키징 | 다이싱 속도, 본딩 강도, 온도 | 10~100mm/s, 5~15g, 150~180°C |

정상 범위 이탈 시 이상 데이터 생성 (이상 비율 10% 내외).

### 3주차: AI 모델 구현

- **[필수] Isolation Forest** (비지도): `contamination=0.07`, 이상 스코어 임계값 분류
- **[필수] XGBoost** (지도): 이진 분류, `scale_pos_weight` 설정, 피처 중요도 상위 20개, SHAP(선택)
- **[필수] 앙상블**: 두 모델 투표(민감도 우선) 또는 스코어 가중 평균
- **[선택, 6주차 이후] LSTM Autoencoder**: 재구성 오류 기반 이상 탐지

> ⚠️ LSTM은 튜닝 시간이 길어 6주 내 완성 리스크 높음. IF + XGBoost만으로도 포트폴리오 충분히 강함.

#### 실측 결과 (`notebooks/03_modeling.ipynb`, test set 314개, 최초 1회 평가)

| 모델 | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|
| Isolation Forest | 0.214 | 0.143 | 0.171 | 0.541 |
| XGBoost | 0.155 | 0.429 | 0.228 | 0.692 |
| Ensemble (투표, 민감도 우선) | 0.156 | 0.476 | 0.235 | 0.612 |

- XGBoost 분류 임계값은 test가 아닌 5-fold 교차검증 OOF(out-of-fold) 예측으로 튜닝 (데이터 누출 방지).
- SECOM은 노이즈가 많고 라벨-피처 상관성이 약한 것으로 알려진 벤치마크라, 이 정도의 F1/AUROC 범위가 선행 연구들과도 유사한 수준.
- 앙상블은 재현율(불량 검출률) 우선 설계 — 실제 불량 21건 중 10건(47.6%)을 탐지.

#### SHAP 설명가능성 (6주차 확장)

`shap.TreeExplainer`로 XGBoost의 전역/국소 설명을 추가했다.

- 전역: `shap.summary_plot`(bar + beeswarm)으로 상위 20개 피처의 평균 기여도, `models/shap_importance.joblib`에 저장.
- 국소: 개별 샘플에 대해 어떤 피처가 이상/정상 어느 쪽으로 얼마나 밀었는지(부호 포함) 확인 가능. 백엔드 `POST /api/ai/explain`으로 실시간 제공, `TreeExplainer`가 예측에 사용한 것과 동일한 트리 구조를 그대로 쓰므로 노트북 결과와 API 응답이 정확히 일치한다.
- 대시보드 이상 탐지 결과 화면에 색상 막대(빨강=이상 쪽 기여, 초록=정상 쪽 기여)로 시각화.

#### Cpk/Ppk & SPC 관리도 (6주차 확장, `notebooks/10_spc_process_capability.ipynb`)

ML 기반 이상 탐지(SECOM)와는 별개로, **fab 품질관리의 가장 기본 도구**인 SPC(관리도, 공정능력지수, Western Electric 룰)를 다룬다. SECOM은 피처가 익명화돼 있어 단위·규격이 없으므로 Cpk 계산이 무의미하다 — 대신 실제 단위/규격이 정의된 공정 시뮬레이터(`simulator/`)에 적용했다. 함수는 재사용을 위해 `simulator/spc.py`로 분리하고 단위 테스트를 붙였다.

- **Cpk 분포**: 21개 파라미터 중 15개 "부적합"(Cpk<1.0), 8개 "양호(관리 필요)", 평균 Cpk 0.991 — 시뮬레이터가 `(high-low)/6`을 표준편차로 써서 데이터를 생성하므로 이론상 그대로 나오는 결과. 시뮬레이터가 "여유 없는 공정"을 의도적으로 흉내 내고 있다는 뜻이다.
- **Western Electric 룰 탐지** (식각 압력, baseline과 분리된 데이터로 평가): precision 0.684, **recall 1.0**, F1 0.813 — 시뮬레이터 이상치가 규칙상 정상 범위를 확실히 벗어나게 만들어지므로 3시그마 관리도로도 거의 다 잡힌다.
- SECOM ML(F1 0.228)과 숫자로 직접 비교할 수는 없지만(다른 데이터), **SPC는 설명 가능한 단순 규칙, ML은 다변량 패턴 학습**이라는 관점 차이를 보여준다. 실무에서도 새 공정엔 먼저 SPC를 걸고 데이터가 쌓이면 ML로 고도화하는 순서를 밟는 경우가 많다.

#### 핵심 에러 문구 + 원인/영향/조치 제안 (규칙 기반, `simulator/diagnosis.py`)

"이상 탐지 → 왜 이상인지 → 방치하면 뭐가 문제인지 → 어떻게 고치는지"까지 이어지는 게 이 프로젝트의 원래 목표였다. SHAP(위)은 SECOM 판정에서 "어떤 피처가 기여했는지"는 보여주지만, SECOM 피처 자체가 익명화돼 있어(`feature_1`, `feature_2`, ...) 사람이 읽을 수 있는 진단 문구로 바꿀 수 없다 — 이는 이 프로젝트가 해결할 수 없는 데이터셋 자체의 한계다. 반면 공정 시뮬레이터의 파라미터는 실제 이름·단위·정상 범위가 있으므로, "이 파라미터가 이 방향으로 규격을 벗어났다"는 사실만으로 반도체 공정 도메인 지식 기반의 원인/영향/조치를 규칙으로 제안할 수 있다.

- **LLM API를 전혀 호출하지 않는다** — 8개 공정 24개 파라미터 × 상한/하한 2방향, 총 48개 조합을 정적 템플릿으로 미리 써뒀다. 완전히 결정적(deterministic)이고 비용이 전혀 발생하지 않는다.
- `simulator/tests/test_diagnosis.py`에 "24개 파라미터 × 2방향 전체가 매핑됐는지" 검증하는 완결성 테스트를 포함 — 템플릿 하나라도 빠지면 "이상"이라고만 뜨고 원인/조치 없는 사각지대가 생기는 걸 방지한다.
- `POST /api/process/simulate`/`/api/process/status`/`/api/process/history` 응답의 `diagnoses` 필드로 노출되고, 프론트엔드 `ProcessCard`에서 이상 발생 시 파라미터별로 "핵심 에러 문구 / 원인 후보 / 영향 / 조치 제안"을 바로 보여준다.

#### AI 원인 분류 모델 (규칙이 아니라 데이터에서 학습, `notebooks/12_fault_scenario_classification.ipynb`)

위 규칙 기반 진단은 파라미터를 하나씩 독립적으로 검사할 뿐, "압력도 이상하고 가스 유량도 이상한데 사실 같은 원인 때문"이라는 연결은 모른다. 이 노트북은 `simulator/fault_scenarios.py`가 "숨은 원인(예: MFC 캘리브레이션 드리프트) → 여러 파라미터가 상관되게 움직이는 패턴"을 레이블과 함께 합성 생성하고, XGBoost가 그 패턴만 보고 원인을 맞히도록 공정별로 학습한다 — 하드코딩된 조건문이 아니라 데이터로부터 학습된 판단이라는 게 핵심이다.

- **8개 공정 전부 81~87% 정확도** (3-클래스: 정상 + 시나리오 2개). SECOM(F1 0.235)과 직접 비교할 수 없는 이유는 지금까지와 같다 — 여긴 규칙으로 생성한 합성 데이터, SECOM은 실측 노이즈 데이터.
- **정직하게 발견한 사실**: 이 모델을 대시보드의 기본 "데이터 생성" 버튼(파라미터를 독립적으로 무작위 이탈시키는 방식)에 그대로 연결했더니, 학습된 상관 패턴과 안 맞아서 값이 명백히 규격을 벗어나도 대부분 "정상"으로 오판했다. 규칙 기반 진단과 AI 분류기가 **서로 다른 질문**에 답하기 때문이다 — 규칙은 "이 파라미터 하나가 규격을 벗어났나", AI는 "이 다중 파라미터 패턴이 내가 학습한 고장 신호와 닮았나". 그래서 실제로 학습된 상관 패턴을 주입해 AI가 무엇을 잘 잡아내는지 직접 보여주는 별도 데모(`POST /api/process/fault-demo`, 대시보드 "AI 원인 분류 데모" 카드)를 추가했다 — 30개 표본으로 처음 검증했다가 60%가 나와 당황했는데, 200개로 다시 재보니 83.5%로 정상이었다(작은 표본의 우연이었다는 걸 확인하고 테스트도 n=150/임계값 0.65로 고쳤다).
- `POST /api/process/simulate` 등에도 `predicted_fault` 필드로 연결해, 규칙 기반 진단과 AI 예측을 나란히 보여준다(대시보드 `ProcessCard`).

#### 피처 선택 실험 (6주차 확장, `notebooks/04_feature_selection.ipynb`)

상관관계 필터(|corr|>0.95 제거, 440→267개) + XGBoost 중요도 기반 피처 선택으로 F1을 더 끌어올릴 수 있는지 실험했다. K 후보(30/50/100/200/267)마다 03과 동일한 5-fold OOF로 임계값과 OOF F1을 구하고, **OOF 기준 최고(k=30)를 test에 최초 1회만** 적용했다.

| | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|
| 베이스라인 (k=440, 03_modeling) | 0.155 | 0.429 | **0.228** | 0.692 |
| 피처 선택 (k=30) | 0.129 | 0.190 | 0.154 | **0.741** |

**결론: 프로덕션 모델은 baseline(k=440)을 그대로 유지.** AUROC는 뚜렷이 개선됐지만(랭킹 품질은 더 좋아짐) F1은 오히려 떨어졌다 — dev의 양성 샘플이 83개뿐이라 OOF로 고른 임계값이 fold 노이즈에 민감했고, test 재현율로 잘 전이되지 않았기 때문으로 보인다. 즉 병목은 피처 개수가 아니라 임계값 보정 쪽. 다음에 시도할 것: F1 argmax 대신 target-recall 기반 임계값, 또는 fold 간 임계값 평균화. 실험 결과는 `models/feature_selection_grid.csv`/`feature_selection_comparison.csv`에 남겨뒀다.

#### LSTM Autoencoder (6주차 확장, 선택 항목, `notebooks/05_lstm_autoencoder.ipynb`)

로드맵에 "시간 여유가 있을 때"로 남겨뒀던 항목. SECOM과는 완전히 별개로, **공정 시뮬레이터가 만드는 시계열**에 대해 정상 패턴만으로 학습한 LSTM Autoencoder의 재구성 오류로 이상을 탐지한다(길이 10 윈도우, 공정별 개별 모델).

- **1차 시도(윈도우 전체 평균 재구성 오류)는 성능이 낮았다** — 공정별 F1 0.18~0.22. 원인: 윈도우 10칸 중 이상은 마지막 1칸뿐인데 나머지 9칸(정상)의 낮은 오류가 평균에 섞여 신호가 희석됨.
- 라벨이 "마지막 시점이 이상인가"이므로 점수도 **마지막 시점의 재구성 오류만** 보도록 바꾸자 8개 공정 평균 F1이 0.20 → **0.955**로, AUROC가 0.72 → **~1.0**으로 뛰었다.
- 다만 시뮬레이터 이상치는 규칙(정상 범위 이탈)으로 만들어지므로 SECOM(실측 노이즈 데이터)보다 구분이 훨씬 쉽다는 점은 감안해야 한다. 이 실험에서 얻은 진짜 교훈은 결과 수치보다 **"시계열 이상 탐지에서 윈도우 집계 방식이 성능을 좌우한다"**는 것.
- `backend/`/`frontend/`에는 연동하지 않음 — 로드맵상 노트북 수준 실험으로 범위를 한정.

#### WM-811K 웨이퍼맵 결함 분류 CNN (6주차 확장, 선택 항목, `notebooks/06_wafer_map_cnn.ipynb`)

로드맵에서 "선택적 활용"으로 남겨뒀던 두 번째 공개 데이터셋. SECOM(표 데이터)·시뮬레이터(시계열)에 이어 **이미지 데이터**를 다루는 세 번째 모델리티다.

- **데이터 파이프라인 이슈**: 원본 `LSWMD.pkl`(2019년, pandas 0.2x대로 피클링)은 메인 pandas(3.x)로는 `pandas.indexes` 모듈을 못 찾아 읽지 못한다. `scripts/convert_wm811k.py`를 별도 레거시 venv(pandas==1.5.3)로 1회 실행해, 결함 라벨이 있는 25,519개 웨이퍼만 32×32(최근접 이웃 리사이즈)로 변환해 `data/processed/wafer_map_defects.npz`(3MB)로 저장 — 이 파일은 git에 커밋해뒀으므로 클론 후 바로 노트북 06을 돌릴 수 있다(2GB 원본/레거시 venv 없이도).
- 결함 패턴 8종(Center/Donut/Edge-Loc/Edge-Ring/Loc/Random/Scratch/Near-full) 분류, 'none'(정상)은 제외. 데이터셋에 포함된 Training/Test 분할을 그대로 사용(17,625 / 7,894).
- 클래스 불균형(Near-full 149개 vs Edge-Ring 9,680개, 최대 65배)은 SMOTE 대신 `CrossEntropyLoss`의 클래스 가중치로 처리 — 이미지 오버샘플링보다 간단하고 이 정도 불균형엔 충분했다.
- 3-conv-block CNN(16→32→64 채널), 15 epoch, CPU로 수 분 내 학습.
- **test 결과: accuracy 0.605, macro F1 0.664.** Near-full(F1 0.88)·Edge-Ring(F1 0.83)은 잘 잡지만 Scratch(precision 0.22)는 다른 클래스와 많이 혼동됨 — 흠집 패턴이 시각적으로 Random/Loc과 겹치는 경우가 많아서로 보인다. 공개 벤치마크의 정교한 모델들보다는 낮지만, 단순한 CNN + 클래스 가중치만으로도 합리적인 베이스라인.
- `backend/`/`frontend/`에는 연동하지 않음 — LSTM과 동일하게 노트북 수준 실험으로 범위를 한정.

### 4주차: FastAPI 서버 구현

```
POST   /api/process/simulate   공정 시뮬레이터 데이터 생성
POST   /api/ai/detect          이상 탐지 실행 (앙상블)
GET    /api/process/status     현재 공정 상태
GET    /api/process/history    공정 이력
GET    /api/fault/list         이상 발생 목록
GET    /api/fault/{id}         이상 상세 정보
POST   /api/alert/send         이상 알림 발송
GET    /api/stats/summary      전체 통계
GET    /api/stats/yield        수율 통계
POST   /api/model/retrain      모델 재학습
GET    /api/health             서버 상태 확인
```

추가 (원래 11개 목록에는 없었으나, 5주차 대시보드의 "모델별 비교"/"피처 중요도" 화면을 위해 필요해 추가):

```
GET    /api/model/metrics             모델 성능 이력 (model_metrics 테이블)
GET    /api/model/feature-importance  XGBoost 피처 중요도 상위 N개
POST   /api/ai/explain                SHAP 기반 개별 판정 설명 (국소 설명)
GET    /api/amhs/stations             AMHS 반송 네트워크 스테이션 목록
POST   /api/amhs/simulate             OHT 반송 시뮬레이션 즉시 실행 (< 1초)
```

SQLite 스키마: `process_logs`, `fault_records`, `model_metrics`

#### 구현 메모

- `POST /api/process/simulate`와 `POST /api/ai/detect`는 완전히 분리되어 있다. 전자는 `simulator/`가 만든 물리 파라미터(3개 내외)와 시뮬레이터 자체의 정상/이상 판정을 `process_logs`에 기록할 뿐, SECOM 학습 모델을 전혀 거치지 않는다. 후자만 SECOM과 동일한 피처 형식(`models/feature_columns.joblib`, 440개(전처리 후 최종 피처 수))을 입력받아 실제 학습된 Isolation Forest + XGBoost 앙상블로 추론하고 `fault_records`에 기록한다. 두 피처 공간은 차원이 달라 직접 연결할 수 없다는 게 "구조 명확화" 절의 핵심이며, 이 분리가 그 설계를 코드 수준까지 반영한 것이다.
- `POST /api/model/retrain`은 `notebooks/03_modeling.ipynb`의 5-fold OOF 임계값 튜닝은 재사용하고(오프라인에서 이미 확정된 값), 최신 `data/processed` 데이터로 두 모델만 다시 학습해 `models/`에 덮어쓴다.
- 로컬 실행: `.venv/Scripts/python -m uvicorn backend.app.main:app --port 8000` (프로젝트 루트에서), Swagger UI는 `/docs`.
- 11개 엔드포인트 전부 실제 SECOM 테스트 샘플/시뮬레이터 데이터로 curl 스모크 테스트 완료.
- 자동화 테스트: `.venv/Scripts/python -m pytest` (프로젝트 루트에서). `SEMISENSE_DATABASE_URL` 환경변수로 테스트 전용 SQLite 파일을 써서 실 서비스 DB(`backend/semisense.db`)를 건드리지 않는다. `models/`가 없는 상태에서 실행하면 ML 의존 테스트만 스킵되고 시뮬레이터/기본 엔드포인트 테스트는 그대로 통과한다.

### 5주차: React 대시보드 구현

1. 메인 대시보드 (공정 상태 카드, 이상 현황, 수율 트렌드)
2. 공정 시뮬레이터 화면 (8대 공정 파이프라인 시각화)
3. 이상 탐지 결과 화면 (피처 중요도, 모델별 비교)
4. 이력 관리 화면 (이상 이력, 수율 트렌드, 모델 성능 지표)
5. AMHS 물류 화면 (6주차 확장 — 디스패칭 정책 비교/차량 대수 민감도를 버튼 클릭으로 실시간 실행)

#### 구현 메모

- Vite + React + `react-router-dom` + `recharts`. (원안의 Chart.js는 생략 — 하나의 차팅 라이브러리로 요구되는 차트를 전부 커버할 수 있어 굳이 두 개를 함께 쓰지 않았다.)
- `src/api/client.js`가 백엔드(`http://localhost:8000`)를 호출하는 유일한 지점. CORS는 Vite 기본 포트(5173)와 원안 기준 CRA 포트(3000)를 모두 허용하도록 백엔드에 설정.
- 이상 탐지 결과 화면은 `X_test.csv`에서 뽑은 실제 SECOM 샘플 3종(정상 / 모델이 탐지한 불량 / 모델이 놓친 불량)을 `src/data/secomSamples.js`에 고정 fixture로 내장해 데모 — 440차원 피처를 사람이 직접 입력할 수 없기 때문.
- AMHS 물류 화면은 `POST /api/amhs/simulate`를 그때그때 호출해 정책 비교/차량 대수 민감도를 실시간으로 그린다(시뮬레이션이 1초 미만이라 가능). 반송 지연 예측(노트북 08)·차량 예지보전(노트북 09)은 XGBoost/IsolationForest 재학습이 무거워 대시보드에서 실시간으로 돌리지 않고 노트북 실행 결과를 참고용 고정 표로만 보여준다.
- 같은 화면에 `POST /api/amhs/simulate/replay`로 받은 개별 반송 이벤트를 canvas에 재생하는 2D 애니메이션(`AmhsAnimation.jsx`)을 추가했다 — 8개 스테이션을 원형 트랙으로 배치하고 OHT 차량을 실제 이동 경로대로 움직인다. 캔버스 표시 크기가 마운트 직후엔 아직 확정 안 된 상태라 `ResizeObserver`로 실제 크기가 잡힌 뒤 다시 내부 해상도를 맞추는 처리가 들어가 있다.
- 로컬 실행: `cd frontend && npm install && npm run dev` (백엔드가 8000번 포트에 떠 있어야 함).
- 브라우저에서 5개 화면 전부 수동 테스트 완료: 시뮬레이션 실행 → 대시보드/시뮬레이터 화면 갱신, 탐지 실행 → 모델별 비교 카드, 알림 발송 → 상태 변경, 재학습 → 이력 테이블에 새 행 추가, AMHS 정책 비교/민감도 버튼 → 실시간 차트 갱신.

### 6주차: 마무리 + 배포

- 성능 평가: F1-score, Precision, Recall, AUROC, Confusion Matrix, IF vs XGBoost 비교표
- Hugging Face Space 배포 (Docker, `.env` 설정, 데모 데이터로 즉시 실행 가능하게 구성)
- README 정리 (아키텍처 다이어그램, 데이터 구조, 모델 성능표, 논문 목록)
- 포트폴리오 정리 (시연 영상, 핵심 수치)
- 시간 남으면 LSTM Autoencoder 추가

#### Docker

로컬에서 백엔드+프론트엔드를 한 번에 띄우기:

```bash
docker compose up --build
```

- 백엔드: `http://localhost:8000` (Swagger `/docs`)
- 프론트엔드: `http://localhost:5173`

`backend/Dockerfile`은 **프로젝트 루트를 빌드 컨텍스트로 쓴다** — `backend/app/main.py`가 루트의 `simulator/`, `amhs/`를 import하기 때문에, `docker build -f backend/Dockerfile .`처럼 루트에서 빌드해야 한다(`docker-compose.yml`이 이미 그렇게 설정돼 있다). 백엔드 이미지는 `backend/requirements.txt`(런타임에 필요한 패키지만 추린 슬림 버전 — torch/matplotlib/jupyter 등 노트북 전용 패키지는 제외)를 쓴다.

**알아둘 것**:
- `models/`, `data/processed/`에 joblib/csv 아티팩트가 이미 로컬에 있으면(노트북을 먼저 돌렸다면) 이미지에 그대로 포함된다. 없는 상태로 빌드해도 컨테이너는 정상적으로 뜨고, ML 의존 엔드포인트만 503을 반환한다(로컬 실행과 동일한 동작).
- SQLite DB(`backend/semisense.db`)는 컨테이너 안에 생기므로 컨테이너를 지우면 함께 사라진다(포트폴리오 데모 용도로는 충분하지만, 데이터를 유지하려면 볼륨 마운트가 필요하다).
- 로컬 개발 환경에는 WSL2/Hyper-V가 없어 `docker compose up`을 직접 실행해보지는 못했다. 대신 `.github/workflows/tests.yml`의 `docker-build` job이 GitHub Actions의 ubuntu 러너(Docker 기본 내장)에서 매 push마다 실제로 `docker compose up --build`를 실행하고, 백엔드 헬스체크(`/api/health`)와 프론트엔드 응답까지 확인한다 — 로컬 1회성 확인보다 오히려 지속적으로 검증되는 셈이다.

## ⚠️ 주요 리스크 & 대응

| 리스크 | 대응 방안 |
|---|---|
| SECOM 결측값 과다 | 결측률 50% 초과 피처 제거 후 진행 |
| 클래스 불균형 (93:7) | SMOTE + class_weight + F1/AUROC 평가 |
| LSTM 일정 초과 | IF + XGBoost 앙상블로 먼저 완성 후 추가 |
| 시뮬레이터-SECOM 연결 질문 | 역할 분리 명확히 문서화, 면접 답변 준비 |

## 💡 면접 핵심 답변 메모

> 반도체 공정을 이해하기 위해 SECOM 실제 센서 데이터와 서울대·KISTI 논문을 참고했습니다.
> 데이터 특성상 결측값이 많고 클래스 불균형이 심해 피처 선택과 SMOTE 기반 데이터 증강을 먼저 적용했습니다.
> Isolation Forest(비지도)와 XGBoost(지도)를 앙상블해 이상 탐지 모델을 설계했고, XGBoost 기준 F1 Score 0.228 / AUROC 0.692, 재현율 우선 앙상블 기준 F1 0.235 / 재현율 47.6%를 달성했습니다.
> SECOM은 학습·평가용, 공정 시뮬레이터는 실시간 추론용으로 역할을 분리 설계해 실제 운영 환경을 고려한 아키텍처를 구성했습니다.
> FastAPI + React 대시보드로 실시간 모니터링까지 구현했으며 Hugging Face Space에서 직접 데모 확인 가능합니다.

## 🚀 진행 상황

- [x] GitHub 레포 생성
- [x] SECOM 데이터 다운로드 (`data/raw/`, git 미추적)
- [ ] 논문 PDF 저장
- [x] EDA 시작 (`notebooks/01_eda.ipynb`)
- [x] 결측값 패턴 확인, 결측률 50% 초과 피처 목록화 — 590개 중 28개 피처가 결측률 50% 초과
- [x] 클래스 분포 확인 — 정상(Pass) 1463 / 불량(Fail) 104 (93.36% / 6.64%)
- [x] 전처리 완료 (`notebooks/02_preprocessing.ipynb`) — 결측률 50% 초과 피처 제거, 중앙값 대체, 저분산 피처 제거, StandardScaler, SMOTE(train만) → `data/processed/`
- [x] 공정 시뮬레이터 구현 (`simulator/process_simulator.py`) — 8대 공정 파라미터 정상 범위 기반 합성 데이터 생성, 이상 비율 10%로 정상 범위 이탈 값 생성
- [x] AI 모델 구현 (`notebooks/03_modeling.ipynb`) — Isolation Forest + XGBoost 앙상블, 5-fold OOF로 분류 임계값 튜닝, `models/`에 저장 (F1/AUROC는 위 로드맵 3주차 표 참고)
- [x] FastAPI 서버 구현 (`backend/`) — 11개 엔드포인트 + 추가 4개(`/api/model/metrics`, `/api/model/feature-importance`, `/api/ai/explain`, `/api/amhs/*`), `process_logs`/`fault_records`/`model_metrics` SQLite 스키마, 전 엔드포인트 curl 스모크 테스트 완료
- [x] React 대시보드 구현 (`frontend/`) — 5개 화면(메인/시뮬레이터/탐지/이력/AMHS 물류), 브라우저에서 전 화면 수동 테스트 완료
- [x] SHAP 설명가능성 추가 — `notebooks/03_modeling.ipynb`에 전역/국소 설명, `POST /api/ai/explain`, 이상 탐지 결과 화면에 SHAP 막대 시각화
- [x] pytest 테스트 스위트 추가 — `backend/tests`(엔드포인트 13개) + `simulator/tests`(시뮬레이터 단위 테스트), 총 48개 테스트 통과. 모델/전처리 데이터가 없는 클론 상태에서도 ML 의존 테스트는 스킵되고 나머지는 통과하도록 설계
- [x] 피처 선택 실험 (`notebooks/04_feature_selection.ipynb`) — 상관관계 필터 + 중요도 기반 선택 시도, AUROC는 개선(0.692→0.741)됐으나 F1은 악화(0.228→0.154)되어 베이스라인 유지로 결론
- [x] LSTM Autoencoder 추가 (`notebooks/05_lstm_autoencoder.ipynb`) — 공정 시뮬레이터 시계열 대상, 공정별 개별 모델, 마지막 시점 재구성 오류 방식으로 평균 F1 0.955 달성
- [x] WM-811K 웨이퍼맵 CNN 분류기 추가 (`notebooks/06_wafer_map_cnn.ipynb`) — 결함 패턴 8종 분류, test accuracy 0.605 / macro F1 0.664
- [x] AMHS 개념 정리 (`docs/AMHS.md`) — OHT/스토커/디스패칭 등 핵심 용어, 프로젝트 매핑, 면접 답변 메모
- [x] OHT/스토커 물류 시뮬레이션 (`amhs/`, `notebooks/07_amhs_dispatch_simulation.ipynb`) — SimPy 이산사건 시뮬레이션, 설비 대기열 길이를 스토커 점유량으로 쓰는 back-pressure, 디스패칭 정책 4종 비교(최근접 91.4초 < 구역기반 115.7초 < FCFS 175.1초, 예측 기반은 저부하에서 최근접과 동일하게 판단), 차량 대수 민감도(6~8대에서 한계효용 체감), 스토커 용량이 작을수록 평균 반송 시간이 짧아지는 WIP 효과, 예지보전 피드백 적용 시 평균 반송 시간 6.7%↑ (15시드 평균)
- [x] 반송 지연 예측 (`notebooks/08_amhs_delay_prediction.ipynb`) — run-level split, R² 0.933 / 지연 분류 F1 0.947, 실시간 시스템 부하가 정적 거리보다 압도적으로 중요
- [x] OHT 차량 예지보전 (`amhs/vehicle_health_simulator.py`, `notebooks/09_amhs_predictive_maintenance.ipynb`) — SECOM 파이프라인(IF+XGBoost+SHAP)을 차량 센서 도메인에 재적용
- [x] 대시보드 AMHS 화면 추가 — `POST /api/amhs/simulate`로 디스패칭 정책 비교/차량 대수 민감도를 실시간 실행, 브라우저에서 동작 확인
- [x] AMHS 2D 반송 애니메이션 (`POST /api/amhs/simulate/replay`, `frontend/src/components/AmhsAnimation.jsx`) — OHT 차량이 8개 스테이션 원형 트랙을 실제로 이동하는 모습을 canvas로 재생(재생/일시정지/배속/시간 탐색), Hot Lot 차량은 색으로 구분
- [x] 예측 기반 디스패칭 + 예지보전 시뮬레이션 피드백 — 노트북 08/09의 모델을 `amhs/predictive.py`·`amhs/maintenance.py`로 실제 시뮬레이션/대시보드에 연결(평가만 하고 끝나지 않게)
- [x] GitHub Actions CI 추가 (`.github/workflows/tests.yml`) — push/PR마다 backend pytest + frontend Vitest/build + Docker 빌드/헬스체크 자동 실행, README 배지
- [x] 프론트엔드 테스트 추가 (Vitest + React Testing Library) — 13개 테스트, 컴포넌트/페이지/API 실패 시 부분 결과 표시 로직까지 커버
- [x] Docker화 (`backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`) — `docker compose up --build`로 로컬 실행. 로컬 개발 환경엔 WSL2/Hyper-V가 없어 직접 빌드는 못 해봤지만, CI(`docker-build` job, GitHub Actions ubuntu 러너)에서 실제 빌드 + 헬스체크 + 프론트엔드 응답 확인까지 매 push마다 검증
- [x] Cpk/Ppk + SPC 관리도 추가 (`simulator/spc.py`, `notebooks/10_spc_process_capability.ipynb`) — I-MR 관리도, Western Electric 룰, 21개 파라미터 공정능력지수, SPC 탐지 F1 0.813
- [x] Hot Lot(긴급 로트) 우선순위 반송 (`amhs/simulation.py`) — 경쟁 없으면 효과 없음(84.0초=83.4초), 경쟁 있으면 hot lot이 31% 빠름(190.5초 vs 276.5초, 15시드 평균) — 우선순위는 자원 경쟁이 있을 때만 의미 있다는 걸 확인
- [x] AMHS 실제 문헌 근거 보강 (`docs/AMHS.md` §8 참고 문헌) — 실제 논문 6건(Agrawal & Heragu 2006 서베이, Liao & Wang 2005 hot-lot DPD, Wang et al. 2017, Im et al. 헝가리안 알고리즘, 다변수 OHT 스케줄링, 2025 멀티에이전트 RL) 인용, 각각이 구현의 어느 부분과 겹치고 어디서 갈리는지 명시 + 솔직한 한계 서술
- [x] 수율→비용 정량화 프레임워크 (`notebooks/11_cost_sensitive_threshold.ipynb`) — confusion matrix를 비용 항목으로 매핑, F1-최적/비용-최적 임계값 비교, 재검사 캐파 제약 추가(무제약 최적값이 웨이퍼 90%를 재검사로 보내는 비현실적 정책이었던 문제를 캐파 상한으로 해결), test set에서 정책별 우열이 뒤집힐 수 있다는 한계까지 정직하게 기록
- [x] Hugging Face Space 배포 준비 (`Dockerfile.space`, `backend/app/main.py`의 정적 파일 서빙, CI `space-build` job으로 빌드+헬스체크 검증 완료) — 단, 실제 배포는 보류. 이 계정에서 Docker SDK Space가 유료로 막혀 있어(Static/Gradio만 무료), 비용을 들이지 않는다는 원칙에 따라 실제 배포 대신 로컬 실행(`docker compose up`)과 CI 검증으로 대체
- [x] 핵심 에러 문구 + 원인/영향/조치 제안 (`simulator/diagnosis.py`) — 공정 파라미터가 규격을 벗어나면 반도체 공정 도메인 지식 기반의 원인 후보/영향/조치를 정적 규칙(LLM 미사용, 비용 없음)으로 즉시 제안. 8개 공정 24개 파라미터 × 2방향 전체 매핑을 테스트로 검증, `POST /api/process/simulate` 등의 `diagnoses` 필드로 노출, 대시보드에 표시
- [x] AI 원인 분류 모델 (`simulator/fault_scenarios.py`, `notebooks/12_fault_scenario_classification.ipynb`) — 규칙이 아니라 다중 파라미터 상관 패턴에서 XGBoost가 원인을 추론(8개 공정 81~87% 정확도). 기본 데모 데이터(독립 무작위 이탈)와는 패턴이 안 맞아 대부분 "정상"으로 오판한다는 걸 발견해 `POST /api/process/fault-demo`(실제 학습 패턴 주입 데모, 200표본 재검증 83.5%)를 추가로 연결
