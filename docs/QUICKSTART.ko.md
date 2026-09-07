# Seedance 2.0 Skill OS 빠른 시작

> 버전 6.7.0 · 설치부터 첫 "연출된" 프롬프트까지 약 5분.
> 자세한 내용은 [README](../README.md)와 [한국어 가이드](README.ko.md)를 참고하세요.

## 한마디로

Seedance 2.0 Skill OS 는 형용사를 늘어놓는 대신 영화감독처럼 Seedance 2.0 을 연출하는 agent skill 입니다. 규칙은 하나뿐입니다——**모델을 연출하되, 프레임을 한 컷씩 붙들지 마세요.** 그 장면이 "무엇을 하고 있는지"만 말해 주면, 그 의도를 바로 쓸 수 있는 프롬프트로 컴파일합니다.

## 1. 루트 스킬 하나 설치하기

저장소를 다운로드해 압축을 풀거나 다음 명령을 실행하세요.

```sh
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
```

해당 폴더에서 설치 위치를 **하나** 선택하세요. 각 위치에 `seedance-20/` 폴더가 만들어집니다. 하위 스킬을 따로 설치할 필요는 없습니다.

```sh
# Codex: 현재 사용자용
python scripts/install_codex_skill.py --client codex --scope user

# Claude Code: 현재 사용자용
python scripts/install_codex_skill.py --client claude-code --scope user

# Codex: 기존 프로젝트 하나에 설치. 소스 폴더 밖의 프로젝트를 지정
python scripts/install_codex_skill.py --client codex --scope project --project-root "/path/to/project"
```

`/path/to/project`를 소스 폴더 밖에 있는 기존 프로젝트 경로로 바꾸세요. 공백이 있는 경로는 따옴표로 감싸세요. 명령은 소스 폴더에서 실행합니다.

이 절의 한국어 수정은 AI를 활용한 초안이며 독립적인 언어 검토는 대기 중입니다. [검토 상태](LANGUAGE_COVERAGE.md).

다른 클라이언트나 사용자 지정 설정에는 `--dest /path/to/client/skills`로 스킬의 상위 폴더를 지정하세요. 클라이언트·범위 옵션과 함께 사용하지 마세요. 설치 위치 옵션을 생략하면 기존의 `$CODEX_HOME/skills` 또는 `~/.codex/skills`를 사용합니다. 사용자 범위를 명시해도 이전 사본을 이동하거나 비활성화하지는 않습니다.

doctor에도 **같은 설치 위치**를 지정하세요. 예를 들어 첫 번째 옵션으로 설치했다면:

```sh
python scripts/install_doctor.py --client codex --scope user --json
```

`current`는 확인한 설치 파일이 이 소스 사본과 일치한다는 뜻입니다. 클라이언트를 다시 시작하거나 새로 고친 뒤, 인식된 스킬 경로를 별도로 확인하세요. doctor는 클라이언트가 어느 사본을 불러오는지까지 확인하지 않습니다. `--force`는 의도적으로 교체할 때만 사용하고, 먼저 로컬 수정 사항과 별도의 백업을 보관하세요. [설치 위치 선택](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_SCOPES.md) · [이전 설치와 중복 확인](https://github.com/Emily2040/seedance-2.0/blob/main/docs/INSTALL_MIGRATION.md).

수동으로 옮기려면 설치 프로그램의 `--dest /path/to/new-staging/skills`를 사용해 소스 폴더 밖의 새 위치에 파일을 준비하세요. 숨김 파일과 설치 완료 기록을 포함한 **생성된 `seedance-20/` 디렉터리만** 복사하세요. GitHub에서 직접 가져오는 경우 클라이언트가 다른 파일을 포함할 수 있습니다. 가져오는 내용을 확인하고, 이 설치 프로그램의 허용 목록이 적용된다고 가정하지 마세요. [수동 전송 안내](https://github.com/Emily2040/seedance-2.0/blob/main/docs/MANUAL_INSTALL.md).

<details>
<summary>교체 및 복구 상세 안내</summary>

교체 중에는 트랜잭션용 임시 백업을 보관합니다. 교체에 실패하고 필요한 기록이 유효하면 이전의 완전한 사본으로 롤백합니다. 교체에 성공하면 임시 백업을 격리한 뒤 삭제합니다. 따라서 별도로 보관하는 백업을 대신할 수는 없습니다. 자동 복구는 검증할 수 있는 트랜잭션 상태에만 적용됩니다. 검증할 수 없는 파일이나 기록은 삭제하지 않고 확인을 위해 보존합니다. [복구 조건 상세 안내](../README.md#install)를 참고하세요.

</details>

## 2. 상황에 맞춰 스킬 고르기

| 지금 상황 | 먼저 로드 |
|---|---|
| 아직 막연한 아이디어 | `seedance-interview` |
| 분명해진 장면 | `seedance-prompt` |
| 여러 클립으로 이어지는 이야기 | `seedance-sequence` |
| 확정된 클립의 다음 이어가기 | `seedance-continuation` |
| 결과가 나쁘거나 막혔을 때 | `seedance-troubleshoot` |
| 캐릭터·브랜드·유명인·실존 인물이 얽힐 때 | `seedance-copyright` |

## 3. 쓰기 전에 "연출"부터 —— 네 가지 질문

1. **이 장면은 무엇을 하고 있나요?** 전환인가, 폭로인가, 감정인가, 아니면 제시인가요.
2. **카메라는 그것을 어떻게 말하나요?** 고독은 와이드로, 표정은 클로즈업으로, 깨달음은 푸시인으로.
3. **빛은 무엇을 위해 일하나요?** 시간대, 강함과 부드러움, 따뜻함과 차가움 —— 모두 의도를 위해서.
4. **소리는 무엇을 하나요?** 거의 무음인가, 환경음 하나인가, 아니면 대사 한 줄인가요.

## 4. 한 가지 대비

**치장 위주 (약함)**

```
웅장한 시네마틱 샷, 편지를 읽는 여성, 감성적, 아름다운 조명, 4K
```

**연출 (강함)**

```
울 카디건을 입은 여자가 부엌 식탁에 앉아 편지지 한 장을 읽는다. 같은 줄을 두 번 훑은 뒤, 두 손이 편지지를 식탁에 내려놓고 완전히 멈춘다. 카메라는 눈높이 미디엄 클로즈업을 유지한 채 천천히 다가가, 손이 멈추는 지점에서 멈춘다. 왼쪽에서 들어오는 흐린 날 창빛이 얼굴을 평평하게 만들고, 보조광은 없다. 사운드: 룸톤, 의자 긁히는 소리 하나, 그다음 거의 무음.
```

단어만이 아니라 **순서**를 보세요. 피사체와 그가 하고 있는 일이 **맨 앞**에 오고, 카메라·빛·사운드가 그 뒤를 따릅니다. 프롬프트의 첫머리가 바로 모델이 "이 숏은 누구의 것인가"를 확정하는 자리이기 때문입니다. `미디엄 클로즈업, 눈높이`로 시작하면 그 자리를 프레이밍 정보에 써버리고, 피사체는 나중에 추론하게 됩니다. 같은 기술인데 위계가 약해집니다.

길이도 같은 원리입니다. 피사체·동작·카메라·빛·사운드를 전달할 수 있는 압축된 촬영 브리프로 쓰세요. 한국어는 단어 수가 아니라 **음절 수**로 셉니다(`vocab/ko` 참고). 너무 짧으면 모델이 빈칸을 채우고, 너무 길면 뒤쪽 문장이 화면에 닿지 않습니다.

## 5. 테이크를 아끼는 두 가지 원칙

- **참조 태그는 한 글자도 바꾸지 마세요.** `@Image1`, `@Video1`, `@Audio1`, `@图片1`, `@视频1` 를 번역하거나 형식을 손대지 않습니다.
- **이야기 전체를 한 번에 생성하려 하지 마세요.** 먼저 Clip 01 을 만들고, 그것이 "실제로" 어디서 끝났는지 본 다음, 그 진짜 결말에서 Clip 02 를 씁니다(`seedance-continuation`).

## 6. 안전

- **콘텐츠 안전:** 보호되는 캐릭터, 유명인, 브랜드, 로고, 노래, 또는 실존 인물의 얼굴과 목소리를 쓴다면 다른 언어로 숨기려 하지 마세요. `seedance-copyright` 로 오리지널·라이선스·후반작업 대체안처럼 안전한 형태로 바꿉니다.
- **agent 안전:** **설치된 페이로드**는 네트워크 통신이나 텔레메트리를 하지 않으며, 설치되는 스크립트는 외부 서비스에 접속하지 않고 로컬에서 동작합니다. 저장소 작업 사본에는 모델 제공자에 접속할 수 있는 개발 전용 `scripts/eval_run.py`도 있지만 설치 프로그램은 이를 제외합니다. API 키, 계정 쿠키, 비공개 소스를 믿을 수 없는 agent 에 붙여넣지 마세요. [SECURITY.md](../SECURITY.md) 참고.

## 7. 더 깊이

- `references/directing-engine.md` — 장면을 읽고 하나의 의도를 고르기(33개 장르 예제).
- `references/capability-map.md` — 모델의 강점을 살리고 알려진 약점을 피해 설계하기.
- `references/api-workflow.md` — API, 제공자, 가격, 모델 ID(모두 출처 날짜 표기).
- `references/examples-by-mode.md` — T2V, I2V, V2V, R2V, FLF2V, 편집, 확장 예시.

---

다른 언어: [English](QUICKSTART.md) · [中文](QUICKSTART.zh.md) · [日本語](QUICKSTART.ja.md) · [Español](QUICKSTART.es.md) · [Русский](QUICKSTART.ru.md)
