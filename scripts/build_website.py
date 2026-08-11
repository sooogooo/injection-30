#!/usr/bin/env python3
"""Build the self-contained static website for Injection Beauty 30."""

from __future__ import annotations

import html
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIR = ROOT / "articles"
VISUAL_DIR = ROOT / "visuals"
SITE_DIR = ROOT / "website"
SITE_ARTICLES = SITE_DIR / "articles"
SITE_VISUALS = SITE_DIR / "assets" / "visuals"

PROFESSIONAL_IDS = {11, 18, 24, 28, 29, 30}

MODULES = [
    {
        "id": 1,
        "range": range(1, 6),
        "number": "01",
        "title": "基础认知",
        "long_title": "认知地基",
        "range_label": "01 至 05",
        "tone": "sky",
        "description": "先把“打一针”还原成医疗行为，再核验产品、人和场所。",
    },
    {
        "id": 2,
        "range": range(6, 12),
        "number": "02",
        "title": "肉毒毒素",
        "long_title": "肉毒毒素",
        "range_label": "06 至 11",
        "tone": "green",
        "description": "理解作用机制、适应证边界、真实风险与无应答。",
    },
    {
        "id": 3,
        "range": range(12, 19),
        "number": "03",
        "title": "填充与再生",
        "long_title": "填充与再生材料",
        "range_label": "12 至 18",
        "tone": "navy",
        "description": "从玻尿酸到再生材料，重点看可逆性与血管风险。",
    },
    {
        "id": 4,
        "range": range(19, 25),
        "number": "04",
        "title": "水光与灰区",
        "long_title": "水光、溶脂与灰色地带",
        "range_label": "19 至 24",
        "tone": "amber",
        "description": "识别营销名、注册状态和不该出现的灰色产品。",
    },
    {
        "id": 5,
        "range": range(25, 31),
        "number": "05",
        "title": "决策与自保",
        "long_title": "决策与责任闭环",
        "range_label": "25 至 30",
        "tone": "rose",
        "description": "从面诊、术后观察到证据保全，完成责任闭环。",
    },
]

POSTERS = [
    ("poster-01-系列总览.svg", "系列总览", "五个模块，一套写给普通消费者的注射安全说明书"),
    ("poster-02-责任链条.svg", "责任链条", "药械、人、场所、应急与责任，缺一不可"),
    ("poster-03-四道门.svg", "四道门", "能核验、能撤销、能急救、能追责"),
    ("poster-04-急症信号.svg", "急症信号", "需要立即停止注射并就医的红旗信号"),
    ("poster-05-当场核验五步.svg", "核验五步", "把模糊的信任变成可以当场完成的动作"),
    ("poster-06-面诊双向核验.svg", "双向核验", "面诊不是被动听方案，你也在面试对方"),
]

GATES = [
    ("01", "能核验", "产品有注册身份，机构、人员与场所都有资质。", "查证"),
    ("02", "能撤销", "材料可逆性与退出机制被如实告知，边界讲清。", "退路"),
    ("03", "能急救", "风险被完整告知，识别、处置与转诊体系真实存在。", "预案"),
    ("04", "能追责", "病历与记录完整，责任主体明确、找得到。", "记录"),
]

INLINE_TOKEN = re.compile(r"(\*\*.+?\*\*|\[[^\]]+\]\([^)]+\))")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def module_for(number: int) -> dict:
    return next(module for module in MODULES if number in module["range"])


def inline_markup(text: str) -> str:
    """Render the limited inline Markdown used by the source articles."""
    rendered: list[str] = []
    for token in INLINE_TOKEN.split(text):
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            rendered.append(f"<strong>{html.escape(token[2:-2])}</strong>")
            continue
        link = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
        if link:
            label, url = link.groups()
            attrs = ""
            if url.startswith(("http://", "https://")):
                attrs = ' target="_blank" rel="noopener noreferrer"'
            rendered.append(
                f'<a href="{html.escape(url, quote=True)}"{attrs}>'
                f"{html.escape(label)}"
                '<span class="external-mark" aria-hidden="true">↗</span></a>'
            )
            continue
        rendered.append(html.escape(token))
    return "".join(rendered)


def display_title(text: str) -> str:
    """Keep short Chinese title phrases intact while allowing semantic wraps."""
    phrases = re.findall(r"[^：，。；？！、—]+[：，。；？！、—]*", text)
    if not phrases:
        return html.escape(text)
    output: list[str] = []
    for phrase in phrases:
        escaped = html.escape(phrase)
        if len(phrase) <= 8:
            output.append(f'<span class="title-phrase">{escaped}</span><wbr>')
        else:
            output.append(escaped)
    return "".join(output)


def parse_article(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    number = int(path.name[:2])
    module = module_for(number)

    headline = next(line[2:].strip() for line in lines if line.startswith("# "))
    title = headline.split("｜", 1)[-1].strip()

    quote = next((line[1:].strip() for line in lines if line.startswith(">")), "")
    quote_match = re.match(r"\*\*(.+?)\*\*\s*(.*)", quote)
    if quote_match:
        perspective = quote_match.group(1).replace("视角｜", "").strip()
        deck = quote_match.group(2).strip()
    else:
        perspective = "公共教育"
        deck = quote

    first_image = ""
    first_image_alt = ""
    for line in lines:
        match = IMAGE_RE.fullmatch(line.strip())
        if match:
            first_image_alt, source = match.groups()
            first_image = Path(source).name
            break

    body_html, toc = render_markdown(lines)
    text_only = re.sub(r"[#>*_`\[\]()!:/.\-\s|]+", "", "\n".join(lines))
    char_count = len(text_only)

    return {
        "number": number,
        "nn": f"{number:02d}",
        "headline": headline,
        "title": title,
        "perspective": perspective,
        "deck": deck,
        "module": module,
        "audience": "专业篇" if number in PROFESSIONAL_IDS else "消费者篇",
        "audience_key": "professional" if number in PROFESSIONAL_IDS else "consumer",
        "first_image": first_image,
        "first_image_alt": first_image_alt,
        "body_html": body_html,
        "toc": toc,
        "char_count": char_count,
        "read_minutes": max(3, math.ceil(char_count / 420)),
    }


def render_markdown(lines: list[str]) -> tuple[str, list[dict[str, str]]]:
    output: list[str] = []
    toc: list[dict[str, str]] = []
    list_open = False
    reference_mode = False
    figure_number = 0

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            output.append("</ul>")
            list_open = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            close_list()
            continue
        if line.startswith("# ") or line.startswith(">"):
            continue

        if line.startswith("## "):
            close_list()
            heading = line[3:].strip()
            anchor = f"section-{len(toc) + 1}"
            toc.append({"anchor": anchor, "title": heading})
            reference_mode = heading == "延伸阅读"
            classes = ["section-heading"]
            if heading == "证据边界":
                classes.append("evidence-heading")
            output.append(
                f'<h2 id="{anchor}" class="{" ".join(classes)}">'
                f'<span class="heading-index">{len(toc):02d}</span>'
                f"{html.escape(heading)}</h2>"
            )
            continue

        if line == "延伸阅读":
            close_list()
            heading = line
            anchor = f"section-{len(toc) + 1}"
            toc.append({"anchor": anchor, "title": heading})
            reference_mode = True
            output.append(
                f'<h2 id="{anchor}" class="section-heading references-heading">'
                f'<span class="heading-index">{len(toc):02d}</span>{heading}</h2>'
            )
            continue

        image = IMAGE_RE.fullmatch(line)
        if image:
            close_list()
            alt, source = image.groups()
            figure_number += 1
            filename = Path(source).name
            output.append(
                '<figure class="article-figure">'
                '<div class="figure-frame">'
                f'<img src="../assets/visuals/{html.escape(filename, quote=True)}" '
                f'alt="{html.escape(alt, quote=True)}" width="900" height="620" loading="lazy">'
                "</div>"
                f"<figcaption><span>FIG. {figure_number:02d}</span>{html.escape(alt)}</figcaption>"
                "</figure>"
            )
            continue

        if line.startswith("- "):
            if not list_open:
                css_class = "reference-list" if reference_mode else "article-list"
                output.append(f'<ul class="{css_class}">')
                list_open = True
            output.append(f"<li>{inline_markup(line[2:].strip())}</li>")
            continue

        close_list()
        if line.startswith("**") and line.endswith("**") and line.count("**") == 2:
            output.append(
                f'<p class="closing-statement">{inline_markup(line)}</p>'
            )
        else:
            output.append(f"<p>{inline_markup(line)}</p>")

    close_list()
    return "\n".join(output), toc


def document_head(
    title: str,
    description: str,
    prefix: str = "",
    page_class: str = "",
) -> str:
    image = f"{prefix}assets/visuals/poster-01-系列总览.svg"
    return f"""<!doctype html>
<html lang="zh-CN" class="no-js">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f7f8f5">
  <meta name="description" content="{html.escape(description, quote=True)}">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="zh_CN">
  <meta property="og:title" content="{html.escape(title, quote=True)}">
  <meta property="og:description" content="{html.escape(description, quote=True)}">
  <meta property="og:image" content="{html.escape(image, quote=True)}">
  <title>{html.escape(title)}</title>
  <link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{prefix}assets/site.css">
  <script>document.documentElement.classList.replace('no-js', 'js');</script>
</head>
<body class="{page_class}">
<a class="skip-link" href="#main-content">跳到正文</a>"""


def site_header(prefix: str = "", current: str = "") -> str:
    home = f"{prefix}index.html"
    return f"""
<header class="site-header" data-header>
  <div class="header-inner">
    <a class="brand" href="{home}" aria-label="注射美容 30 讲首页">
      <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
      <span class="brand-type"><b>INJECTION</b><small>医学科普 · 30 讲</small></span>
    </a>
    <nav class="desktop-nav" aria-label="主导航">
      <a href="{home}"{" aria-current=\"page\"" if current == "home" else ""}>首页</a>
      <a href="{home}#gates">四道门</a>
      <a href="{home}#library">文章库</a>
      <a href="{home}#atlas">视觉图谱</a>
    </nav>
    <a class="header-cta" href="{home}#library">开始阅读<span aria-hidden="true">↗</span></a>
    <button class="menu-button" type="button" aria-label="打开导航" aria-expanded="false" data-menu-button>
      <span></span><span></span>
    </button>
  </div>
  <nav class="mobile-nav" aria-label="移动端导航" data-mobile-nav>
    <a href="{home}">首页</a>
    <a href="{home}#gates">四道门</a>
    <a href="{home}#library">文章库</a>
    <a href="{home}#atlas">视觉图谱</a>
  </nav>
</header>"""


def site_footer(prefix: str = "") -> str:
    return f"""
<footer class="site-footer">
  <div class="footer-main">
    <div>
      <a class="brand footer-brand" href="{prefix}index.html">
        <span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span class="brand-type"><b>INJECTION</b><small>医学科普 · 30 讲</small></span>
      </a>
      <p>把“打一针”还原成一次需要核验、判断与负责的医疗决策。</p>
    </div>
    <div class="footer-links">
      <div><span>阅读</span><a href="{prefix}index.html#library">全部文章</a><a href="{prefix}articles/01.html">从第一篇开始</a></div>
      <div><span>工具</span><a href="{prefix}articles/23.html">核验一支针剂</a><a href="{prefix}articles/26.html">识别危险信号</a></div>
      <div><span>总纲</span><a href="{prefix}articles/30.html">四道门与一条链</a><a href="{prefix}index.html#atlas">视觉图谱</a></div>
    </div>
  </div>
  <div class="footer-legal">
    <p>公众教育内容，不构成个体诊疗建议。监管信息以主管部门当前公示为准。</p>
    <p>注射美容 30 讲 · 静态数字出版物</p>
  </div>
</footer>
<button class="back-to-top" type="button" aria-label="返回页面顶部" data-back-to-top>↑</button>
<script src="{prefix}assets/site.js" defer></script>
</body>
</html>"""


def article_card(article: dict) -> str:
    module = article["module"]
    search_text = " ".join(
        [
            article["nn"],
            article["title"],
            article["deck"],
            module["title"],
            article["audience"],
        ]
    )
    return f"""
<a class="article-card reveal" href="articles/{article['nn']}.html"
   data-module="{module['id']}" data-audience="{article['audience_key']}"
   data-search="{html.escape(search_text, quote=True)}">
  <div class="card-visual">
    <img src="assets/visuals/{html.escape(article['first_image'], quote=True)}"
         alt="" width="900" height="620" loading="lazy">
    <span class="card-number">{article['nn']}</span>
  </div>
  <div class="card-body">
    <div class="card-meta"><span>模块 {module['number']} · {module['title']}</span><span>{article['audience']}</span></div>
    <h3>{html.escape(article['title'])}</h3>
    <p>{html.escape(article['deck'])}</p>
    <div class="card-action"><span>阅读约 {article['read_minutes']} 分钟</span><b aria-hidden="true">↗</b></div>
  </div>
</a>"""


def render_home(articles: list[dict]) -> str:
    module_cards = "\n".join(
        f"""
<a class="module-card module-{module['tone']} reveal" href="#library" data-module-jump="{module['id']}">
  <div class="module-card-top"><span>MODULE {module['number']}</span><b>{module['range_label']}</b></div>
  <h3>{module['long_title']}</h3>
  <p>{module['description']}</p>
  <span class="text-link">查看本模块 <i aria-hidden="true">→</i></span>
</a>"""
        for module in MODULES
    )

    gate_cards = "\n".join(
        f"""
<article class="gate-card reveal">
  <div class="gate-number">{number}</div>
  <div><span class="gate-key">{key}</span><h3>{title}</h3><p>{copy}</p></div>
</article>"""
        for number, title, copy, key in GATES
    )

    filter_buttons = [
        '<button class="filter-button is-active" type="button" data-filter="all" aria-pressed="true">全部 30 篇</button>'
    ]
    filter_buttons.extend(
        f'<button class="filter-button" type="button" data-filter="module:{module["id"]}" aria-pressed="false">{module["title"]}</button>'
        for module in MODULES
    )
    filter_buttons.append(
        '<button class="filter-button" type="button" data-filter="audience:professional" aria-pressed="false">专业篇 · 6</button>'
    )

    article_cards = "\n".join(article_card(article) for article in articles)
    poster_cards = "\n".join(
        f"""
<a class="poster-card reveal" href="assets/visuals/{filename}" target="_blank" rel="noopener">
  <div class="poster-frame"><img src="assets/visuals/{filename}" alt="{title}海报，{description}" width="900" height="1200" loading="lazy"></div>
  <div><span>POSTER {index:02d}</span><h3>{title}</h3><p>{description}</p></div>
</a>"""
        for index, (filename, title, description) in enumerate(POSTERS, 1)
    )

    return (
        document_head(
            "注射美容 30 讲｜写给普通消费者的注射安全说明书",
            "30 篇注射美容医学科普，内容覆盖产品、资质、风险、面诊、术后与责任闭环。",
            page_class="home-page",
        )
        + site_header(current="home")
        + f"""
<main id="main-content">
  <section class="hero">
    <div class="hero-orb hero-orb-one" aria-hidden="true"></div>
    <div class="hero-orb hero-orb-two" aria-hidden="true"></div>
    <div class="container hero-grid">
      <div class="hero-copy">
        <p class="eyebrow reveal">MEDICAL AESTHETICS · PUBLIC EDUCATION</p>
        <h1 class="reveal">把“打一针”<br>还原成一次<br><em>医疗决策</em></h1>
        <p class="hero-lead reveal">一套面向普通消费者的注射安全说明书。我们不替你选项目，只帮助你看清产品、人员、场所、风险与责任。</p>
        <div class="hero-actions reveal">
          <a class="button button-primary" href="articles/01.html">从第一篇开始<span aria-hidden="true">↗</span></a>
          <a class="button button-quiet" href="#gates">先看四道门<span aria-hidden="true">↓</span></a>
        </div>
        <div class="hero-note reveal"><span></span>不提供剂量、点位、品牌推荐与个体诊疗建议</div>
      </div>
      <div class="hero-visual reveal">
        <div class="poster-main">
          <img src="assets/visuals/poster-01-系列总览.svg" alt="注射美容 30 讲系列总览海报" width="900" height="1200">
        </div>
        <div class="floating-figure floating-figure-a" aria-hidden="true">
          <img src="assets/visuals/fig-30-2-四道门.svg" alt="" width="900" height="620">
        </div>
        <div class="floating-figure floating-figure-b" aria-hidden="true">
          <img src="assets/visuals/fig-23-1-当场核验五步.svg" alt="" width="900" height="620">
        </div>
        <div class="hero-seal" aria-hidden="true"><b>30</b><span>CHAPTERS</span></div>
      </div>
    </div>
    <div class="container fact-strip reveal" aria-label="系列数据">
      <div><strong>30</strong><span>完整文章</span></div>
      <div><strong>5</strong><span>主题模块</span></div>
      <div><strong>66</strong><span>原创图解与海报</span></div>
      <div><strong>4</strong><span>最终检查门</span></div>
    </div>
  </section>

  <section class="manifesto section">
    <div class="container manifesto-grid">
      <div class="section-heading-block reveal">
        <p class="eyebrow">THE PREMISE</p>
        <h2>你买到的，从来<br>不只是一支针剂。</h2>
      </div>
      <div class="manifesto-copy reveal">
        <p>一次可以被信任的注射，需要合法药械、有资质的操作者、有资质的场所、真实存在的应急能力，以及事后可追溯的责任主体。</p>
        <blockquote>“消费感”越强的场景，越要主动找回医疗行为应有的判断与责任。</blockquote>
      </div>
    </div>
  </section>

  <section class="gates section" id="gates">
    <div class="container">
      <div class="section-intro reveal">
        <div><p class="eyebrow">THE FOUR GATES</p><h2>四道门，<br>一道都不能省。</h2></div>
        <p>它们是“与”的关系，不是“或”。任何一道门不通过，其他三道再完美，这一针都不该打。</p>
      </div>
      <div class="gates-layout">
        <div class="gates-visual reveal">
          <img src="assets/visuals/poster-03-四道门.svg" alt="注射美容最终检查的四道门海报" width="900" height="1200" loading="lazy">
        </div>
        <div class="gate-list">{gate_cards}</div>
      </div>
      <div class="gates-cta reveal"><span>这不是行业标准术语，而是一套帮助你稳定决策的认知工具。</span><a href="articles/30.html">阅读终章 <b aria-hidden="true">↗</b></a></div>
    </div>
  </section>

  <section class="routes section">
    <div class="container">
      <div class="section-intro compact reveal">
        <div><p class="eyebrow">READING ROUTES</p><h2>不必从头硬读。<br>先从你的问题进入。</h2></div>
      </div>
      <div class="route-grid">
        <article class="route-card route-featured reveal">
          <span class="route-label">第一次接触注射美容</span>
          <h3>先建立一套不会过期的判断框架</h3>
          <p>从医疗属性、资质核验、重风险、产品核验到四道门，完成一条最短但完整的安全路径。</p>
          <div class="route-chapters"><a href="articles/01.html">01</a><a href="articles/05.html">05</a><a href="articles/14.html">14</a><a href="articles/23.html">23</a><a href="articles/30.html">30</a></div>
          <a class="route-action" href="articles/01.html">开始这条路线 <span aria-hidden="true">↗</span></a>
        </article>
        <article class="route-card reveal">
          <span class="route-label">风险优先</span>
          <h3>我最想知道，什么情况不能等？</h3>
          <p>理解血管栓塞、迟发反应、非法溶脂与术后危险信号。</p>
          <div class="route-chapters"><a href="articles/14.html">14</a><a href="articles/17.html">17</a><a href="articles/20.html">20</a><a href="articles/26.html">26</a></div>
          <a class="route-action" href="articles/14.html">从最重风险开始 <span aria-hidden="true">↗</span></a>
        </article>
        <article class="route-card reveal">
          <span class="route-label">专业从业者 · 6 篇</span>
          <h3>把个体技术放回机构系统里看</h3>
          <p>免疫原性、急救体系、灰色产品、患者筛查、联合时序与行业边界。</p>
          <div class="route-chapters"><a href="articles/11.html">11</a><a href="articles/18.html">18</a><a href="articles/24.html">24</a><a href="articles/28.html">28</a><a href="articles/29.html">29</a><a href="articles/30.html">30</a></div>
          <a class="route-action" href="articles/11.html">进入专业路径 <span aria-hidden="true">↗</span></a>
        </article>
      </div>
    </div>
  </section>

  <section class="modules section">
    <div class="container">
      <div class="section-intro compact reveal">
        <div><p class="eyebrow">FIVE MODULES</p><h2>五个模块，<br>建立完整责任链。</h2></div>
      </div>
      <div class="module-grid">{module_cards}</div>
    </div>
  </section>

  <section class="library section" id="library">
    <div class="container">
      <div class="library-head">
        <div class="section-heading-block reveal"><p class="eyebrow">THE LIBRARY</p><h2>30 篇完整正文</h2><p>消费者篇 24 篇，专业篇 6 篇。</p></div>
        <div class="search-wrap reveal">
          <label for="article-search">搜索文章</label>
          <div class="search-field"><span aria-hidden="true">⌕</span><input id="article-search" type="search" placeholder="搜索主题、风险或关键词…" autocomplete="off" data-article-search><kbd>/</kbd></div>
        </div>
      </div>
      <div class="filter-bar reveal" aria-label="文章筛选">{"".join(filter_buttons)}</div>
      <div class="library-status" aria-live="polite"><span data-result-count>显示 30 篇</span><button type="button" data-clear-search hidden>清除筛选</button></div>
      <div class="article-grid" data-article-grid>{article_cards}</div>
      <div class="empty-state" data-empty-state hidden><span>00</span><h3>没有找到匹配文章</h3><p>换一个关键词，或清除当前筛选。</p></div>
    </div>
  </section>

  <section class="atlas section" id="atlas">
    <div class="container">
      <div class="section-intro reveal">
        <div><p class="eyebrow">VISUAL ATLAS</p><h2>把关键判断，<br>变成一眼可见的图。</h2></div>
        <p>六张竖版海报浓缩全系列核心工具。点击任意海报可查看原始高清 SVG。</p>
      </div>
      <div class="poster-grid">{poster_cards}</div>
    </div>
  </section>

  <section class="closing section">
    <div class="container closing-card reveal">
      <div><p class="eyebrow">THE FINAL PRINCIPLE</p><h2>可以等，可以再问一个医生，<br>也可以永远不做。</h2></div>
      <div><p>注射美容是择期项目。“不打”不是损失，而是当核验没有通过时，这套系统正常工作的结果。</p><a class="button button-light" href="articles/30.html">阅读终章｜四道门与一条链 <span aria-hidden="true">↗</span></a></div>
    </div>
  </section>
</main>"""
        + site_footer()
    )


def article_navigation(article: dict, articles: list[dict]) -> str:
    module_articles = [
        item for item in articles if item["module"]["id"] == article["module"]["id"]
    ]
    module_position = module_articles.index(article) + 1
    module_progress = module_position / len(module_articles) * 100
    links = "\n".join(
        f'<a href="{item["nn"]}.html"{" aria-current=\"page\"" if item["number"] == article["number"] else ""}>'
        f'<span>{item["nn"]}</span><b>{html.escape(item["title"])}</b></a>'
        for item in module_articles
    )
    return f"""<aside class="series-rail">
  <p class="rail-kicker">MODULE {article['module']['number']}</p>
  <h2>{article['module']['long_title']}</h2>
  <div class="module-progress"><span style="--progress:{module_progress:.2f}%"></span></div>
  <nav aria-label="本模块文章">{links}</nav>
</aside>"""


def article_toc(article: dict) -> str:
    links = "\n".join(
        f'<a href="#{item["anchor"]}"><span>{index:02d}</span>{html.escape(item["title"])}</a>'
        for index, item in enumerate(article["toc"], 1)
    )
    return f"""<aside class="toc-rail">
  <div class="toc-sticky">
    <p class="rail-kicker">IN THIS ARTICLE</p>
    <nav aria-label="本文目录" data-toc>{links}</nav>
    <div class="reader-tools">
      <button type="button" data-font-size aria-label="调整正文字号"><span>Aa</span> 字号</button>
      <button type="button" data-focus-mode aria-pressed="false"><span>◫</span><b data-focus-label>专注阅读</b></button>
    </div>
  </div>
</aside>"""


def render_article(article: dict, articles: list[dict]) -> str:
    index = articles.index(article)
    previous_article = articles[index - 1] if index > 0 else None
    next_article = articles[index + 1] if index < len(articles) - 1 else None

    previous_link = (
        f'<a class="page-link page-previous" href="{previous_article["nn"]}.html"><span>上一篇 · {previous_article["nn"]}</span><b>{html.escape(previous_article["title"])}</b></a>'
        if previous_article
        else '<span class="page-link page-disabled"></span>'
    )
    next_link = (
        f'<a class="page-link page-next" href="{next_article["nn"]}.html"><span>下一篇 · {next_article["nn"]}</span><b>{html.escape(next_article["title"])}</b></a>'
        if next_article
        else '<a class="page-link page-next" href="../index.html"><span>已经读完</span><b>返回全系列首页</b></a>'
    )

    mobile_module_links = "\n".join(
        f'<a href="{item["nn"]}.html"{" aria-current=\"page\"" if item["number"] == article["number"] else ""}><span>{item["nn"]}</span>{html.escape(item["title"])}</a>'
        for item in articles
        if item["module"]["id"] == article["module"]["id"]
    )
    mobile_toc_links = "\n".join(
        f'<a href="#{item["anchor"]}"><span>{i:02d}</span>{html.escape(item["title"])}</a>'
        for i, item in enumerate(article["toc"], 1)
    )

    return (
        document_head(
            f"{article['headline']}｜注射美容 30 讲",
            article["deck"],
            prefix="../",
            page_class=f"article-page tone-{article['module']['tone']}",
        )
        + '<div class="reading-progress" aria-hidden="true"><span data-reading-progress></span></div>'
        + site_header(prefix="../")
        + f"""
<main id="main-content">
  <section class="article-hero">
    <div class="article-hero-pattern" aria-hidden="true"></div>
    <div class="container">
      <a class="article-breadcrumb" href="../index.html#library"><span aria-hidden="true">←</span> 返回 30 篇文章库</a>
      <div class="article-hero-grid">
        <div class="article-index" aria-hidden="true">{article['nn']}</div>
        <div class="article-title-block">
          <div class="article-labels"><span>模块 {article['module']['number']} · {article['module']['long_title']}</span><span>{article['audience']}</span></div>
          <h1>{display_title(article['title'])}</h1>
          <p>{html.escape(article['deck'])}</p>
          <div class="article-meta"><span>{article['perspective']}</span><span>约 {article['char_count']} 字</span><span>阅读约 {article['read_minutes']} 分钟</span></div>
        </div>
      </div>
    </div>
  </section>

  <div class="mobile-reader-nav container">
    <details>
      <summary>本模块与本文目录 <span aria-hidden="true">＋</span></summary>
      <div class="mobile-reader-columns">
        <nav aria-label="本模块文章"><p>本模块</p>{mobile_module_links}</nav>
        <nav aria-label="本文目录"><p>本文目录</p>{mobile_toc_links}</nav>
      </div>
    </details>
    <div class="mobile-reader-tools" aria-label="阅读工具">
      <button type="button" data-font-size aria-label="调整正文字号"><span>Aa</span> 字号</button>
      <button type="button" data-focus-mode aria-pressed="false"><span>◫</span><b data-focus-label>专注阅读</b></button>
    </div>
  </div>

  <div class="article-layout container">
    {article_navigation(article, articles)}
    <article class="prose" data-article-body>
      <div class="perspective-note"><span>阅读视角</span><p>{html.escape(article['perspective'])}</p></div>
      {article['body_html']}
      <div class="article-disclaimer">
        <span aria-hidden="true">i</span>
        <p><strong>内容边界</strong>本文用于公众教育，不构成个体诊疗建议；具体适应证、风险与处置请由合格医生面诊判断。</p>
      </div>
    </article>
    {article_toc(article)}
  </div>

  <nav class="article-pagination container" aria-label="文章翻页">{previous_link}{next_link}</nav>

  <section class="article-series-cta">
    <div class="container">
      <div><span>INJECTION · 30</span><h2>安全不是某一环的属性，<br>而是一条链的完整性。</h2></div>
      <a class="button button-light" href="../index.html#library">查看全部 30 篇 <span aria-hidden="true">↗</span></a>
    </div>
  </section>
</main>"""
        + site_footer(prefix="../")
    )


def copy_visuals() -> None:
    SITE_VISUALS.mkdir(parents=True, exist_ok=True)
    for stale in SITE_VISUALS.glob("*.svg"):
        stale.unlink()
    for source in sorted(VISUAL_DIR.glob("*.svg")):
        shutil.copy2(source, SITE_VISUALS / source.name)


def validate_sources(articles: list[dict]) -> None:
    if len(articles) != 30:
        raise RuntimeError(f"Expected 30 articles, found {len(articles)}")
    numbers = [article["number"] for article in articles]
    if numbers != list(range(1, 31)):
        raise RuntimeError(f"Article numbering is incomplete: {numbers}")
    visual_count = len(list(VISUAL_DIR.glob("*.svg")))
    if visual_count != 66:
        raise RuntimeError(f"Expected 66 SVG visuals, found {visual_count}")
    for article in articles:
        if not article["first_image"]:
            raise RuntimeError(f"Article {article['nn']} has no lead visual")


def build() -> None:
    article_paths = sorted(ARTICLE_DIR.glob("*.md"))
    articles = [parse_article(path) for path in article_paths]
    validate_sources(articles)

    SITE_ARTICLES.mkdir(parents=True, exist_ok=True)
    copy_visuals()

    for stale in SITE_ARTICLES.glob("*.html"):
        stale.unlink()

    (SITE_DIR / "index.html").write_text(render_home(articles), encoding="utf-8")
    for article in articles:
        (SITE_ARTICLES / f"{article['nn']}.html").write_text(
            render_article(article, articles), encoding="utf-8"
        )

    print(
        f"Built {1 + len(articles)} HTML pages and copied "
        f"{len(list(SITE_VISUALS.glob('*.svg')))} SVG assets to {SITE_DIR}"
    )


if __name__ == "__main__":
    build()
