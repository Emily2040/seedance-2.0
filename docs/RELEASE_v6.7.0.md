# Seedance 2.0 Skill OS — v6.7.0

A modular agent-skill operating system for directing ByteDance **Seedance 2.0** video. It turns vague ideas into production-ready prompts, **directs each scene like a filmmaker**, keeps platform facts source-dated, rewrites unsafe IP, and plans long-form stories across many clips — with localized reader paths for English, 中文, 日本語, and 한국어.

## Final hardening pass — 2026-08-05

The final audit after the main v6.7.0 work found four reproducible defects. Pull requests [#149](https://github.com/Emily2040/seedance-2.0/pull/149), [#150](https://github.com/Emily2040/seedance-2.0/pull/150), [#151](https://github.com/Emily2040/seedance-2.0/pull/151), and [#152](https://github.com/Emily2040/seedance-2.0/pull/152) are now merged. Together they close the following gaps without changing the active version or the documented Seedance 2.0 platform boundary.

### Frame tooling now spans current and legacy FFmpeg

FFmpeg 9 removed the `-vsync` option used by the frame helper, so first- and last-frame extraction failed before decoding on a current Windows runner. The helper now performs one bounded capability probe for the selected FFmpeg binary, prefers `-fps_mode passthrough`, and falls back to `-vsync 0` for older builds. The same real-frame extraction path was verified with FFmpeg 8.1.1 and 9.0; the publication and rollback contract remains unchanged.

### Copyable prompts now match the routing contract

Some repository-authored generic sequence examples used malformed `[Video 1]` and `@Image 1` spellings instead of the canonical tokens the examples intended to teach. They now use `@Video1` and `@Image1`; user- or interface-supplied tags such as `[Video 1]` and `@Image 1` remain byte-preserved by design. The continuation examples also now bind their opening to the accepted take's actual observed state instead of a planned ending, and carry the scene through specific behavior, props, timing, sound, and endpoints. Focused regressions inspect the inline prompt bodies rather than passing on nearby explanatory prose.

### New evaluator ledgers are bound to retained objects

A brand-new ledger previously depended on a mutable temporary pathname during publication and rollback. The repaired Linux path creates an unnamed `O_TMPFILE` and links the retained descriptor into the retained target directory with atomic no-replace semantics. The Windows path retains a zero-share source handle and the exact destination-directory handle, then performs a root-relative no-replace native rename. Rollback is armed before publication, concurrent late claimants and namespace substitutes are preserved, and unsupported hosts or filesystems fail closed instead of weakening the boundary.

This closes the confirmed first-publication, parent-redirection, and rollback race classes. It does not claim protection against a process that can rewrite the evaluator itself.

### Windows release validation follows CPython's real launchers

The masthead build trust check assumed every supported Windows Python copied `Lib/venv/scripts/nt/python.exe`. CPython 3.13 uses the `venvlauncher` family instead, with free-threaded and debug variants. The trust mapping now follows the exact launcher packaged or built for CPython 3.11, 3.12, and 3.13; missing, unsupported, and wrong-variant candidates are rejected. A real `venv.EnvBuilder(with_pip=False)` regression verifies the generated runner against the selected source, and the Windows CI matrix covers all three supported versions.

### What this final pass proves — and what it does not

The merged fixes are backed by repository validators, focused adversarial tests, real FFmpeg extraction, and hosted Linux and Windows matrices. They verify the checked-in prompt contracts and the tested local tooling. They do not guarantee the subjective quality of every generated clip, prove that every third-party agent host auto-loads the skill, or replace a blinded live Seedance generation benchmark.

## What's new in v6.7.0 — the outside world moved

v6.6.0 closed the sequence loop. v6.7.0 is about everything that drifted while the loop was being closed: reports of a newer model line surfaced, the front page's type was resolving differently on every reader's machine, and the path a first-time user walks was broken in four places.

### A newer model line exists, and the skill now knows it

ByteDance's [official Seedance 2.5 model page](https://seed.bytedance.com/en/seedance2_5) now confirms a separate, newer model line, and [Dreamina's official product page](https://dreamina.capcut.com/seedance/seedance-2-5) says it is live on Dreamina. Neither primary page gives an exact launch date; API and other-surface availability were unconfirmed in the 2026-08-01 review. The previous verification stamp was 2026-06-20 and did not signal that another line existed.

The fix is a boundary, not a rewrite:

- **`api-status` opens with the 2.5 source boundary.** It records what ByteDance's model page and Dreamina's product page establish, what they do not establish, and why no 2.5 platform number belongs in this 2.0 skill.
- **Dreamina availability is confirmed; the exact launch date and API or other-surface availability are not.** Technology press and provider pages report additional dates and access routes, but `source-registry` keeps those reports below the `confirmed` bar.
- **The root skill's source gate now establishes the model line, not just the surface.** A user can be on 2.5 without saying so.
- **`model-name-map` gains a 2.5 boundary entry** and a standing rule: never normalize "2.5" to "2.0". That normalization would silently apply this skill's 2.0 durations, reference ceilings, resolutions, and model IDs to an unverified model line — the highest-cost naming error the file exists to prevent. Reports of a 2.0 4K tier remain a source caveat, not a canonical model-name row.

The rule underneath all of it: **craft transfers across model lines; platform numbers never do.** Direction, shot contracts, reference roles, continuity, and anti-slop remain correct on any line. Durations, reference counts, resolutions, model IDs, and mode availability are 2.0 values and stay 2.0 values.

For sequence work, re-derive every duration and shot budget from the verified active surface. This release deliberately adds no 2.5 capability guidance.

### The masthead now renders the same for everyone

The design system specifies a "high-contrast editorial serif". The stack it used — `Didot, 'Bodoni MT', 'Hoefler Text', Baskerville, 'Palatino Linotype', Georgia, serif` — delivers Didot only on macOS. Windows fell through to Bodoni MT or Palatino Linotype. Linux, including the machine this repository is built and validated on, has **none of the six** and fell all the way to a default system serif.

This is precisely the failure the script wordmark was retired for in v6.6.0 ("a design that only resolves on the author's machine is not a design"). The serif stack had the same disease and outlasted the fix.

The wordmark and tagline are now **glyph outlines** — real vector geometry, shaped with HarfBuzz kerning from Bodoni Moda (SIL OFL; attribution, version, and instance axes recorded in `assets/masthead-outlines.json`). Optical size tracks rendered size, so the hairlines are drawn for the size they appear at. No font needs to be installed by anyone, and every reader sees identical type. Specification values moved to the monospace stack, so the only serif on the canvas is outlined and nothing can silently fall back.

### The first ten minutes work

Five defects on the path a first-time user actually walks, all found by checking the repository rather than the feedback:

- **There was no `git clone` anywhere in the documentation.** Every install path began at step two, inside a copy of the repository nothing told the reader to obtain.
- **The installer looked Codex-only.** It has always accepted `--dest`; Claude Code and every other listed client had a one-command install and were being sent to copy the folder by hand. It also told every user to "Restart Codex" regardless of destination.
- **A validator reported gitignored files as committed.** Running the tests before the validators — the order the README lists — produced a wall of "must not be committed" errors naming files that were gitignored and never committed. CI never saw it because the workflow sets `PYTHONDONTWRITEBYTECODE`.
- **An in-tree `--dest` copied the repository into itself** until the path length failed — 757 directories deep.
- **The beginner example taught against the doctrine.** The "Directed (strong)" prompt was 29 words, below the root skill's own 40–110 band, and opened on `Medium close-up, eye-level` — the exact inversion `seedance-prompt` warns against when it says to put the subject and primary action first.

### Prompt architecture is now a CI gate

`scripts/prompt_architecture_stress.py` scores a 102-prompt corpus over 34 briefs and every mode, written three ways: the Director Formula, the shape the old beginner example taught, and untrained/listicle style. The doctrine arm scores **3.92/4** against `eval-rubric`; the other two fail. It runs with `--strict` in CI, so a change that degrades the doctrine fails the build instead of arriving later as "the prompts feel average".

### CJK reaches parity

Japanese gained **Register (文体)** — 敬語 / です・ます体 / 普通体 with script-verified mora costs, and the first-person pronoun as a register axis — closing the asymmetry that left Chinese with Script Variant and Korean with Speech Level while Japanese had neither. All three languages gained dialogue-format lines, aesthetic-register sections mined from the legacy archive, and wrapper-level discoverability for features that previously existed only in reference files.

`references/sync-budget-protocol.md` makes the two remaining "not separately measured" cells fillable: fixed shot conditions, script-verified sentence ladders in morae and syllables, a Mandarin control ladder, a three-defect scoring rule, and write-back rules that keep the `[field]` label and per-surface scope.

## Upgrading

Nothing to migrate. Re-run the installer for your client:

```bash
git clone https://github.com/Emily2040/seedance-2.0.git
cd seedance-2.0
python scripts/install_codex_skill.py --dest ~/.claude/skills --force
```

## Verification

Run the documented validator suite and unit-test discovery rather than relying on a frozen count. The release checks include the masthead design-rule suite, the prompt-architecture gate, and `source_registry_check --enforce-freshness`.

At the final handoff, merged `main` commit `f084a54` passed both canonical archive-safe validation jobs and the Windows frame-publication and runner-trust jobs on CPython 3.11, 3.12, and 3.13. The privileged Linux workflow also passed, but the hosted runner lacked the complete descriptor-bound extended-attribute prerequisite, so its success-path metadata-preservation step was explicitly skipped while the prerequisite check proved the helper fails closed.

---

## 简体中文 — v6.7.0 发布摘要

以下内容是上方英文发布说明的本地化摘要，不增加新的功能声明。[Seedance 2.0 Skill OS v6.7.0](https://github.com/Emily2040/seedance-2.0/releases/tag/v6.7.0) 已公开发布，并标记为 GitHub **Latest** Release。

- 标签：`v6.7.0`
- 目标提交：`8802978eb17bea7b1fa4e8bd230d9edfbe58e0dd`

### 本版确认的改进

- **FFmpeg 帧工具兼容性：** 帧提取器对所选 FFmpeg 执行一次有界能力探测，优先使用 `-fps_mode passthrough`，旧版本则回退到 `-vsync 0`。真实帧提取路径已在 FFmpeg 8.1.1 和 9.0 上验证。
- **提示词契约：** 部分由仓库编写、用于讲解规范标签的通用连续镜头范例，已改为使用 `@Video1` 和 `@Image1`。用户或界面提供的 `[Video 1]`、`@Image 1` 等标签仍按原始字节保留。续拍范例从已接受片段的实际观测终态开始，不再把计划中的结尾当成既成事实。
- **首次发布竞态加固：** 新评估器账本的发布路径绑定到已保留的文件描述符或目录句柄，并使用原子 no-replace 语义。首次发布、父目录重定向和回滚竞态均已覆盖；不支持所需能力的主机或文件系统会默认拒绝（fail closed），不会静默削弱边界。
- **Windows 启动器信任：** 信任映射覆盖 CPython 3.11、3.12 和 3.13 的实际 `venv` 启动器，包括 `venvlauncher`、自由线程和调试变体；缺失、不受支持或变体不匹配的候选项会被拒绝。
- **Seedance 2.5 来源边界：** 文档只记录官方来源能够确认的 2.5 模型线与 Dreamina 可用性。准确发布日期、API 和其他平台的可用性仍未确认；Seedance 2.0 的时长、参考数量、分辨率、模型 ID 和模式能力不会移用到 2.5。
- **可复现的页首字标：** 字标和副标题改为由 Bodoni Moda 与 HarfBuzz 生成的矢量字形轮廓，并记录字体、许可、版本和实例轴；渲染结果不再依赖读者本机安装的字体或操作系统回退。
- **安装与前十分钟体验：** 补齐 `git clone` 和 ZIP 获取路径，明确 `--dest` 可用于不同客户端，修复验证器对已忽略文件的误报，拒绝把目标目录设在仓库内部，并重写首个提示词范例，使其遵循“主体与动作优先”的结构。
- **提示词架构与中日韩一致性：** `prompt_architecture_stress.py --strict` 已纳入 CI。中文、日文和韩文补齐对话格式、审美语域与功能入口；日文新增文体和第一人称代词轴。

### 验证范围

PR #153 的 **11 项检查全部通过**；合并后，目标提交上的 `validate-seedance-skill` 与 `validate-privileged-frame-publication` 两条 `main` 工作流也全部通过。受托管 Linux runner 缺少完整的描述符绑定扩展属性前置条件，因此特权工作流中的元数据保留成功路径步骤被明确跳过；前置条件检查验证了辅助工具会默认拒绝，而不是降低保护边界。

这些检查验证的是仓库内已提交的提示词契约、本地工具和受测运行环境。它们不保证每次生成结果的主观质量，不证明所有第三方 agent 都会自动加载该技能，不覆盖所有主机、文件系统、客户端或操作系统组合，也不抵抗能够改写评估器本身的攻击者。

## 日本語 — v6.7.0 リリース概要

以下は上記の英語版リリースノートを日本語で要約したもので、新しい機能主張を追加するものではありません。[Seedance 2.0 Skill OS v6.7.0](https://github.com/Emily2040/seedance-2.0/releases/tag/v6.7.0) は公開済みで、GitHub の **Latest** リリースです。

- タグ：`v6.7.0`
- 対象コミット：`8802978eb17bea7b1fa4e8bd230d9edfbe58e0dd`

### この版で確認した改善

- **FFmpeg 8.1.1 / 9.0 対応：** フレーム抽出は選択された FFmpeg の機能を一度だけ限定的に確認し、`-fps_mode passthrough` を優先します。旧版では `-vsync 0` にフォールバックし、両バージョンで実フレーム抽出を検証しました。
- **プロンプト契約：** リポジトリが作成した汎用シーケンス作例のうち、正規トークンを教える意図のものを `@Video1` / `@Image1` 表記へ修正しました。ユーザーやインターフェース由来の `[Video 1]`、`@Image 1` などのタグはバイト単位で保持します。連続クリップは、予定上の終点ではなく、採用済みテイクで実際に観測された状態から開始します。
- **初回公開時の競合対策：** evaluator ledger の公開処理を、Linux では保持済みファイル記述子、Windows では保持済みハンドルへ束縛しました。置換を許さない公開と事前に準備したロールバックにより、確認済みの初回公開・親ディレクトリ差し替え・ロールバック競合を防ぎます。必要な機能を利用できない環境では安全側に停止します。
- **Windows ランチャー信頼判定：** CPython 3.11、3.12、3.13 で実際に配布またはビルドされる `venv` ランチャーを追跡し、`venvlauncher` 系列、free-threaded 版、debug 版を区別します。欠落、未対応、または種類が一致しない候補は拒否します。
- **Seedance 2.5 の出典境界：** 2.5 という別モデル系列と Dreamina での提供のみを確認済み事実として扱います。正確な公開日、API、その他の提供先は未確認です。2.0 固有の時間、参照数上限、解像度、モデル ID、モード可用性を 2.5 へ流用しません。
- **再現可能なマストヘッド：** Bodoni Moda を HarfBuzz でシェーピングしたベクター字形アウトラインへ変更し、フォント、ライセンス、バージョン、インスタンス軸を記録しました。表示はローカルフォントや OS のフォールバックに依存しません。
- **インストールと最初の 10 分：** `git clone` / ZIP の取得手順、クライアント別 `--dest`、再起動案内、gitignore 判定、リポジトリ内への再帰コピー防止、初心者向けプロンプトの順序と長さを修正しました。
- **プロンプト品質と CJK 対応：** `prompt_architecture_stress.py --strict` を CI ゲートに追加しました。日本語の文体軸と一人称代名詞軸を追加し、中国語・日本語・韓国語の会話形式、表現レジスター、機能への導線も揃えました。

### 検証済み範囲と限界

PR #153 の **11 件のチェック**と、マージ後の対象コミットで実行された `main` の **2 件のワークフロー**（`validate-seedance-skill`、`validate-privileged-frame-publication`）はすべて成功しました。ただし、ホステッド Linux runner ではディスクリプタに結び付いた拡張属性の前提条件がすべて揃わなかったため、特権ワークフローのメタデータ保持成功パスは明示的にスキップされました。前提条件の検査では、保護を弱めず安全側に停止することを確認しています。

これらのテストが保証するのは、リポジトリ内のプロンプト契約、検証対象のローカルツール、テスト済みの実行環境です。生成映像ごとの主観的な品質、すべての第三者 agent ホストによる自動読み込み、あらゆる OS・ファイルシステム・クライアント・実行環境での動作、evaluator 自体を書き換えられる攻撃者への耐性は保証しません。

## 한국어 — v6.7.0 릴리스 요약

아래 내용은 위 영문 릴리스 노트를 한국어로 요약한 것이며 새로운 기능 주장을 추가하지 않습니다. [Seedance 2.0 Skill OS v6.7.0](https://github.com/Emily2040/seedance-2.0/releases/tag/v6.7.0)은 공개되었으며 GitHub **Latest** 릴리스로 지정되었습니다.

- 태그: `v6.7.0`
- 대상 커밋: `8802978eb17bea7b1fa4e8bd230d9edfbe58e0dd`

### 이 버전에서 확인한 개선 사항

- **FFmpeg 8.1.1과 9.0 프레임 호환성:** 선택된 FFmpeg 바이너리의 기능을 한 번만 제한적으로 확인하여 `-fps_mode passthrough`를 우선 사용하고, 구형 빌드에서는 `-vsync 0`으로 전환합니다. 첫 프레임과 마지막 프레임의 실제 추출 경로를 두 버전에서 검증했습니다.
- **복사 가능한 프롬프트 계약:** 저장소가 작성한 범용 연속 클립 예시 가운데 표준 토큰을 가르치려는 예시를 `@Video1`과 `@Image1` 형식으로 수정했습니다. 사용자나 인터페이스가 제공한 `[Video 1]`, `@Image 1` 같은 태그는 바이트 단위로 보존됩니다. 연속 클립 예시는 계획된 결말이 아니라 승인된 테이크에서 실제로 관찰된 마지막 상태에 시작점을 고정합니다.
- **첫 게시 경쟁 조건 방어:** 새 평가기 원장은 변경 가능한 임시 경로명이 아니라 계속 보유 중인 객체와 디렉터리 디스크립터 또는 핸들에 바인딩됩니다. 원자적 비대체 게시와 사전에 활성화된 롤백으로 확인된 첫 게시, 상위 디렉터리 전환, 롤백 경쟁 조건을 막습니다. 필요한 기능이 없는 호스트나 파일시스템에서는 보호 수준을 낮추지 않고 fail-closed로 중단합니다.
- **Windows CPython 런처 신뢰:** CPython 3.11, 3.12, 3.13에서 실제로 패키징되거나 빌드되는 `venv` 런처를 기준으로 신뢰 대상을 판별합니다. CPython 3.13의 `venvlauncher` 계열과 free-threaded·debug 변형을 구분하며, 누락되었거나 지원되지 않거나 변형이 맞지 않는 후보는 거부합니다.
- **Seedance 2.5 출처 경계:** 공식 출처가 확인하는 별도 2.5 모델 계열과 Dreamina 제공 상태만 확인된 사실로 기록합니다. 정확한 출시일과 API 또는 다른 표면의 제공 여부는 확인되지 않았습니다. Seedance 2.0의 길이, 참조 수, 해상도, 모델 ID, 모드 가용성은 2.5에 가져다 쓰지 않습니다.
- **재현 가능한 마스트헤드:** 워드마크와 태그라인을 Bodoni Moda에서 HarfBuzz로 셰이핑한 벡터 글리프 윤곽선으로 저장하고, 글꼴, 라이선스, 버전, 인스턴스 축을 기록했습니다. 독자의 로컬 글꼴이나 운영체제의 대체 글꼴 선택에 의존하지 않습니다.
- **설치 후 첫 10분 경로 복구:** `git clone`과 ZIP 설치 경로를 추가하고, `--dest`를 이용한 여러 클라이언트 설치와 클라이언트별 재시작 안내를 바로잡았습니다. 검증기가 Git에서 무시된 생성 파일을 커밋된 파일로 잘못 보고하지 않도록 수정했고, 저장소 내부를 가리키는 `--dest`는 재귀 복사를 막기 위해 거부합니다. 초보자 예시는 피사체와 주 동작을 먼저 배치하도록 고쳤습니다.
- **프롬프트 아키텍처 CI와 CJK 동등성:** `prompt_architecture_stress.py --strict`를 CI 게이트에 추가했습니다. 일본어에는 문체 축과 1인칭 대명사 축을 추가했고, 중국어·일본어·한국어 모두 대화 형식, 미학적 레지스터, 상위 래퍼에서의 기능 탐색 경로를 갖추었습니다.

### 검증 범위

PR #153의 **검사 11개**와 병합 후 대상 커밋에서 실행된 `main`의 **워크플로 2개**(`validate-seedance-skill`, `validate-privileged-frame-publication`)가 모두 통과했습니다. 다만 호스팅된 Linux runner에는 디스크립터 결합 확장 속성의 전체 전제 조건이 없어 특권 워크플로의 메타데이터 보존 성공 경로 단계가 명시적으로 건너뛰어졌습니다. 전제 조건 검사는 도우미가 보호 수준을 낮추지 않고 fail-closed로 중단한다는 점을 입증했습니다.

이 결과는 검사된 저장소 계약, 검증된 로컬 도구, 테스트한 실행 환경을 입증합니다. 모든 생성 영상의 주관적 품질, 모든 서드파티 agent 호스트의 자동 스킬 로드, 모든 운영체제·호스트·파일시스템·클라이언트 조합에서의 동작, 평가기 자체를 다시 쓸 수 있는 공격자에 대한 내성은 보장하지 않습니다.
