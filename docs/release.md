# 배포 절차 (유지 관리자용)

## 한 번만: PyPI Trusted Publishing 등록

API 토큰 없이 GitHub Actions가 PyPI에 올리도록 합니다(OIDC).

1. https://pypi.org 계정으로 로그인 → **Account settings → Publishing → Add a new pending publisher**
2. 다음 값을 넣습니다.

   | 항목 | 값 |
   |---|---|
   | PyPI project name | `sarangbang` |
   | Owner | `springwindteam` (조직으로 옮겼으면 조직 이름) |
   | Repository name | `sarangbang` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

3. GitHub 저장소 **Settings → Environments → New environment** 이름 `pypi` (선택: Required reviewers를 켜면 배포 전에 승인 단계가 생깁니다).
4. 저장소 **Settings → Secrets and variables → Actions → Variables**에 `PYPI_PUBLISH` = `true` 추가.
   이 변수가 없으면 릴리스 워크플로는 GitHub Release까지만 만들고 PyPI 단계를 건너뜁니다.

첫 배포가 성공하면 PyPI에 프로젝트가 생기고 pending publisher가 정식 publisher로 바뀝니다. 그 뒤에는 조직 이름이 바뀌지 않는 한 손댈 일이 없습니다.

## 매번: 버전 올리고 태그

```bash
# 1. 버전 — src/sarangbang/__init__.py 의 __version__ 하나만 고친다(pyproject는 여기서 읽는다)
# 2. CHANGELOG.md — "미공개" 아래 내용을 "## <버전> — <날짜>" 로 옮긴다. CITATION.cff 의 version/date-released 도 맞춘다
# 3. 확인
pytest -q && ruff check . && python -m build && twine check dist/*
# 4. 커밋·태그·푸시
git commit -am "release: v0.2.1"
git tag v0.2.1
git push origin main --tags
```

태그가 올라가면 `.github/workflows/release.yml`이

1. 태그와 `__version__`이 같은지 확인하고 sdist·휠을 빌드
2. GitHub Release를 만들고(CHANGELOG의 해당 절이 본문) 휠·sdist를 첨부
3. `PYPI_PUBLISH=true`면 `pypi` 환경에서 PyPI에 올립니다.

배포 뒤 확인:

```bash
pip install --upgrade sarangbang && sarangbang --version
```

## PyPI 없이 설치하는 법 (사용자 안내용)

```bash
pip install git+https://github.com/springwindteam/sarangbang.git@v0.2.0
pip install https://github.com/springwindteam/sarangbang/releases/download/v0.2.0/sarangbang-0.2.0-py3-none-any.whl
```

## TestPyPI로 먼저 시험하려면

TestPyPI는 계정·publisher 등록이 별개입니다(https://test.pypi.org, environment 이름 `testpypi`). 필요하면 `release.yml`의 `pypi` 작업을 복사해
`repository-url: https://test.pypi.org/legacy/`를 `with:`에 추가한 작업을 만듭니다.
