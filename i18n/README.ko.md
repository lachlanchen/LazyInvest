[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*미국 주식, 섹터, 아직 덜 주목받는 성장 기업을 다루는 날짜 기반 다국어 공개 리서치 작업 공간입니다.*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

LazyInvest는 현재 강한 섹터, 이미 과열된 인기 테마, 덜 알려진 성장 후보, 고위험 문샷, 피해야 할 기업을 구분해 정리하는 리서치 노트 모음입니다. 각 노트는 날짜, 출처 링크, Markdown 형식을 갖추어 나중에 쉽게 갱신할 수 있습니다.

이 저장소는 리서치 노트북이며 개인 금융 자문이 아닙니다. 시장 데이터, 기업 가이던스, 법률, 금리, 뉴스는 빠르게 바뀌므로 어떤 노트든 사용하기 전에 1차 출처를 확인해야 합니다.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 현재 내용

| 파일 | 목적 |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | 섹터별로 현재 유망, 인기 테마, 덜 알려진 후보, 고위험 후보, 회피 후보를 정리한 관리형 표입니다. |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | 덜 주목받는 미국 성장 기업을 촉매와 리스크와 함께 정리한 워치리스트입니다. |
| [AGENTS.md](../AGENTS.md) | 향후 리서치 업데이트를 위한 로컬 작업 규칙입니다. |

## 빠른 시작

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

Markdown 파일은 GitHub에서 직접 열거나 원하는 Markdown 뷰어로 읽을 수 있습니다.

## 업데이트 흐름

1. 업데이트할 날짜가 있는 노트를 선택합니다.
2. 기업 IR, SEC 제출 자료, 실적 발표 녹취, 거래소 데이터, 신뢰할 수 있는 시장 데이터를 갱신합니다.
3. GAAP 지표와 non-GAAP 지표를 명확히 구분합니다.
4. 가정, 출처 링크, 리서치 날짜를 갱신합니다.

## 검증

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## 인용

연구에서 LazyInvest를 사용한다면 이 저장소를 인용해 주세요. GitHub는 [CITATION.cff](../CITATION.cff)를 읽고 저장소 페이지에 **Cite this repository** 패널을 표시합니다.

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## 상태

첫 공개 릴리스: 2026-06-13. 첫 노트는 미국 섹터, 덜 알려진 성장 기업, 인기 테마, 투기적 후보, 회피 후보를 다룹니다.
