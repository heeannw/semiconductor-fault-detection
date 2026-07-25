# 🏭 SemiSense — 반도체 공정 시뮬레이터 & 이상 탐지 AI

Semiconductor Process Simulator & Fault Detection AI

- **기간:** 6주
- **배포:** Hugging Face Space
- **데이터:** SECOM (UCI)

## 📌 프로젝트 개요

반도체 8대 공정을 시뮬레이션하고, AI로 공정 이상을 실시간 탐지하는 포트폴리오 프로젝트.

### 구조 명확화 (⚠️ 원안에서 수정된 핵심 사항)

| 구성 요소 | 역할 | 비고 |
|---|---|---|
| SECOM 데이터셋 | AI 모델 학습 & 평가용 | UCI 공개 데이터, 실제 반도체 공정 센서 |
| 공정 시뮬레이터 | 실시간 추론용 데이터 생성 | 8대 공정 파라미터 기반 합성 데이터 |

SECOM은 어느 공정에서 나온 데이터인지 라벨이 없음. 따라서 두 모듈을 명확히 분리하여 설계하고, 이 사실을 명시한다. 면접에서 질문받을 포인트이므로 답변 준비 필수.

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
│   └── papers/         # 참고 논문 PDF
├── notebooks/          # EDA, 실험용 Jupyter Notebook
├── simulator/           # 8대 공정 합성 데이터 생성기
├── models/              # 학습된 모델 아티팩트
├── backend/
│   └── app/             # FastAPI 서버
└── frontend/            # React 대시보드
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

#### 실측 결과 (`notebooks/03_modeling.ipynb`, test set 313개, 최초 1회 평가)

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

#### 피처 선택 실험 (6주차 확장, `notebooks/04_feature_selection.ipynb`)

상관관계 필터(|corr|>0.95 제거, 440→267개) + XGBoost 중요도 기반 피처 선택으로 F1을 더 끌어올릴 수 있는지 실험했다. K 후보(30/50/100/200/267)마다 03과 동일한 5-fold OOF로 임계값과 OOF F1을 구하고, **OOF 기준 최고(k=30)를 test에 최초 1회만** 적용했다.

| | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|
| 베이스라인 (k=440, 03_modeling) | 0.155 | 0.429 | **0.228** | 0.692 |
| 피처 선택 (k=30) | 0.129 | 0.190 | 0.154 | **0.741** |

**결론: 프로덕션 모델은 baseline(k=440)을 그대로 유지.** AUROC는 뚜렷이 개선됐지만(랭킹 품질은 더 좋아짐) F1은 오히려 떨어졌다 — dev의 양성 샘플이 83개뿐이라 OOF로 고른 임계값이 fold 노이즈에 민감했고, test 재현율로 잘 전이되지 않았기 때문으로 보인다. 즉 병목은 피처 개수가 아니라 임계값 보정 쪽. 다음에 시도할 것: F1 argmax 대신 target-recall 기반 임계값, 또는 fold 간 임계값 평균화. 실험 결과는 `models/feature_selection_grid.csv`/`feature_selection_comparison.csv`에 남겨뒀다.

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

#### 구현 메모

- Vite + React + `react-router-dom` + `recharts`. (원안의 Chart.js는 생략 — 하나의 차팅 라이브러리로 요구되는 차트를 전부 커버할 수 있어 굳이 두 개를 함께 쓰지 않았다.)
- `src/api/client.js`가 백엔드(`http://localhost:8000`)를 호출하는 유일한 지점. CORS는 Vite 기본 포트(5173)와 원안 기준 CRA 포트(3000)를 모두 허용하도록 백엔드에 설정.
- 이상 탐지 결과 화면은 `X_test.csv`에서 뽑은 실제 SECOM 샘플 3종(정상 / 모델이 탐지한 불량 / 모델이 놓친 불량)을 `src/data/secomSamples.js`에 고정 fixture로 내장해 데모 — 440차원 피처를 사람이 직접 입력할 수 없기 때문.
- 로컬 실행: `cd frontend && npm install && npm run dev` (백엔드가 8000번 포트에 떠 있어야 함).
- 브라우저에서 4개 화면 전부 수동 테스트 완료: 시뮬레이션 실행 → 대시보드/시뮬레이터 화면 갱신, 탐지 실행 → 모델별 비교 카드, 알림 발송 → 상태 변경, 재학습 → 이력 테이블에 새 행 추가.

### 6주차: 마무리 + 배포

- 성능 평가: F1-score, Precision, Recall, AUROC, Confusion Matrix, IF vs XGBoost 비교표
- Hugging Face Space 배포 (Docker, `.env` 설정, 데모 데이터로 즉시 실행 가능하게 구성)
- README 정리 (아키텍처 다이어그램, 데이터 구조, 모델 성능표, 논문 목록)
- 포트폴리오 정리 (시연 영상, 핵심 수치)
- 시간 남으면 LSTM Autoencoder 추가

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
- [x] FastAPI 서버 구현 (`backend/`) — 11개 엔드포인트 + 추가 2개(`/api/model/metrics`, `/api/model/feature-importance`), `process_logs`/`fault_records`/`model_metrics` SQLite 스키마, 전 엔드포인트 curl 스모크 테스트 완료
- [x] React 대시보드 구현 (`frontend/`) — 4개 화면(메인/시뮬레이터/탐지/이력), 브라우저에서 전 화면 수동 테스트 완료
- [x] SHAP 설명가능성 추가 — `notebooks/03_modeling.ipynb`에 전역/국소 설명, `POST /api/ai/explain`, 이상 탐지 결과 화면에 SHAP 막대 시각화
- [x] pytest 테스트 스위트 추가 — `backend/tests`(엔드포인트 13개) + `simulator/tests`(시뮬레이터 단위 테스트), 총 48개 테스트 통과. 모델/전처리 데이터가 없는 클론 상태에서도 ML 의존 테스트는 스킵되고 나머지는 통과하도록 설계
- [x] 피처 선택 실험 (`notebooks/04_feature_selection.ipynb`) — 상관관계 필터 + 중요도 기반 선택 시도, AUROC는 개선(0.692→0.741)됐으나 F1은 악화(0.228→0.154)되어 베이스라인 유지로 결론
