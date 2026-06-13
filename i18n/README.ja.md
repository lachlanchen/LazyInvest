[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# LazyInvest

*米国株、セクター、まだ注目度の低い成長企業を扱う、日付付きの多言語公開リサーチワークスペースです。*

[![Website](https://img.shields.io/badge/Website-earn.lazying.art-0EA5E9?style=for-the-badge)](https://earn.lazying.art)
[![Research](https://img.shields.io/badge/Research-Markdown-111827?style=for-the-badge&logo=markdown&logoColor=white)](../US_Sector_Investment_Matrix_2026-06-13.md)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-lachlanchen-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)

LazyInvest は、現在強いセクター、すでに人気化したテーマ、まだ見落とされている成長候補、高リスクのムーンショット、避けるべき企業を整理するための調査ノート集です。各ノートには日付、出典リンク、Markdown 形式の本文があります。

これは調査ノートであり、個別の金融助言ではありません。市場データ、企業ガイダンス、法律、金利、ニュースは急速に変わるため、利用前に一次情報を確認してください。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

## 現在の内容

| ファイル | 目的 |
|---|---|
| [US_Sector_Investment_Matrix_2026-06-13.md](../US_Sector_Investment_Matrix_2026-06-13.md) | セクター別に「今よい候補」「熱いが混雑」「注目度が低い候補」「高リスク」「避ける候補」を整理した管理表です。 |
| [US_Underfollowed_Growth_Stocks_2026-06-13.md](../US_Underfollowed_Growth_Stocks_2026-06-13.md) | 注目度の低い米国成長企業を、カタリストとリスク付きでまとめたウォッチリストです。 |
| [AGENTS.md](../AGENTS.md) | 今後のリサーチ更新に使うローカル作業ルールです。 |

## クイックスタート

```bash
git clone https://github.com/lachlanchen/LazyInvest.git
cd LazyInvest
ls
```

Markdown ファイルは GitHub 上で直接開くか、任意の Markdown ビューアで読めます。

## 更新フロー

1. 更新する日付付きノートを選びます。
2. 企業 IR、SEC 提出書類、決算説明会の書き起こし、取引所データ、信頼できる市場データを更新します。
3. GAAP と non-GAAP の違いを明確に保ちます。
4. 仮定、出典リンク、調査日を更新します。

## 検証

```bash
rg -n "CITATION\\.cff|Source:|not personal financial advice" ../README.md . ../*.md
git diff --check
```

## 引用

研究で LazyInvest を使用する場合は、このリポジトリを引用してください。GitHub は [CITATION.cff](../CITATION.cff) を読み取り、リポジトリページに **Cite this repository** パネルを表示します。

```bibtex
@software{chen_lazyinvest_2026,
  author = {Chen, Lachlan},
  title = {LazyInvest: Dated U.S. Sector and Stock Research Notes},
  year = {2026},
  url = {https://github.com/lachlanchen/LazyInvest}
}
```

## ステータス

初回公開リリース: 2026-06-13。最初のノートでは、米国セクター、注目度の低い成長企業、人気テーマ、投機的候補、避ける候補を扱っています。
