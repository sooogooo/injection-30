(() => {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const header = document.querySelector("[data-header]");
  const menuButton = document.querySelector("[data-menu-button]");
  const mobileNav = document.querySelector("[data-mobile-nav]");
  const backToTop = document.querySelector("[data-back-to-top]");

  const closeMenu = () => {
    if (!menuButton || !mobileNav) return;
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", "打开导航");
    mobileNav.classList.remove("is-open");
    body.classList.remove("menu-open");
  };

  if (menuButton && mobileNav) {
    menuButton.addEventListener("click", () => {
      const isOpen = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!isOpen));
      menuButton.setAttribute("aria-label", isOpen ? "打开导航" : "关闭导航");
      mobileNav.classList.toggle("is-open", !isOpen);
      body.classList.toggle("menu-open", !isOpen);
    });
    mobileNav.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeMenu();
    });
  }

  let scrollTicking = false;
  const updatePageChrome = () => {
    const y = window.scrollY;
    if (header) header.classList.toggle("is-scrolled", y > 18);
    if (backToTop) backToTop.classList.toggle("is-visible", y > 720);
    scrollTicking = false;
  };

  window.addEventListener(
    "scroll",
    () => {
      if (!scrollTicking) {
        window.requestAnimationFrame(updatePageChrome);
        scrollTicking = true;
      }
    },
    { passive: true }
  );
  updatePageChrome();

  if (backToTop) {
    backToTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  }

  const revealItems = [...document.querySelectorAll(".reveal")];
  if ("IntersectionObserver" in window) {
    const revealObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      { rootMargin: "0px 0px -7% 0px", threshold: 0.08 }
    );
    revealItems.forEach((item, index) => {
      item.style.transitionDelay = `${Math.min(index % 4, 3) * 55}ms`;
      revealObserver.observe(item);
    });
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  const searchInput = document.querySelector("[data-article-search]");
  const articleGrid = document.querySelector("[data-article-grid]");
  const articleCards = articleGrid ? [...articleGrid.querySelectorAll(".article-card")] : [];
  const filterButtons = [...document.querySelectorAll("[data-filter]")];
  const resultCount = document.querySelector("[data-result-count]");
  const emptyState = document.querySelector("[data-empty-state]");
  const clearSearch = document.querySelector("[data-clear-search]");
  let activeFilter = "all";

  const normalize = (value) => value.normalize("NFKC").toLocaleLowerCase("zh-CN").trim();

  const applyArticleFilters = () => {
    if (!articleCards.length) return;
    const query = normalize(searchInput?.value || "");
    let visible = 0;

    articleCards.forEach((card) => {
      const [filterType, filterValue] = activeFilter.split(":");
      const filterMatch =
        activeFilter === "all" ||
        (filterType === "module" && card.dataset.module === filterValue) ||
        (filterType === "audience" && card.dataset.audience === filterValue);
      const textMatch = !query || normalize(card.dataset.search || "").includes(query);
      const show = filterMatch && textMatch;
      card.hidden = !show;
      if (show) visible += 1;
    });

    if (resultCount) resultCount.textContent = `显示 ${visible} 篇`;
    if (emptyState) emptyState.hidden = visible !== 0;
    if (clearSearch) clearSearch.hidden = activeFilter === "all" && !query;
  };

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.filter || "all";
      filterButtons.forEach((item) => {
        const active = item === button;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      applyArticleFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener("input", applyArticleFilters);
    document.addEventListener("keydown", (event) => {
      const target = event.target;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;
      if (event.key === "/" && !isTyping) {
        event.preventDefault();
        searchInput.focus();
      }
    });
  }

  if (clearSearch) {
    clearSearch.addEventListener("click", () => {
      activeFilter = "all";
      if (searchInput) searchInput.value = "";
      filterButtons.forEach((button) => {
        const active = button.dataset.filter === "all";
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-pressed", String(active));
      });
      applyArticleFilters();
      searchInput?.focus();
    });
  }

  document.querySelectorAll("[data-module-jump]").forEach((link) => {
    link.addEventListener("click", () => {
      const target = document.querySelector(`[data-filter="module:${link.dataset.moduleJump}"]`);
      window.setTimeout(() => target?.click(), 50);
    });
  });

  const progressBar = document.querySelector("[data-reading-progress]");
  const articleBody = document.querySelector("[data-article-body]");
  if (progressBar && articleBody) {
    let progressTicking = false;
    const updateProgress = () => {
      const start = articleBody.offsetTop;
      const end = start + articleBody.offsetHeight - window.innerHeight;
      const progress = Math.max(0, Math.min(1, (window.scrollY - start) / Math.max(end - start, 1)));
      progressBar.style.width = `${progress * 100}%`;
      progressTicking = false;
    };
    window.addEventListener(
      "scroll",
      () => {
        if (!progressTicking) {
          window.requestAnimationFrame(updateProgress);
          progressTicking = true;
        }
      },
      { passive: true }
    );
    window.addEventListener("resize", updateProgress);
    updateProgress();
  }

  const toc = document.querySelector("[data-toc]");
  if (toc) {
    const tocLinks = [...toc.querySelectorAll("a")];
    const headings = tocLinks
      .map((link) => document.querySelector(link.getAttribute("href")))
      .filter(Boolean);
    let tocTicking = false;
    const updateToc = () => {
      let current = headings[0];
      headings.forEach((heading) => {
        if (heading.getBoundingClientRect().top <= 180) current = heading;
      });
      tocLinks.forEach((link) => {
        link.classList.toggle("is-current", link.getAttribute("href") === `#${current?.id}`);
      });
      tocTicking = false;
    };
    window.addEventListener(
      "scroll",
      () => {
        if (!tocTicking) {
          window.requestAnimationFrame(updateToc);
          tocTicking = true;
        }
      },
      { passive: true }
    );
    updateToc();
  }

  const fontButtons = [...document.querySelectorAll("[data-font-size]")];
  if (fontButtons.length) {
    const classNames = ["", "font-large", "font-larger"];
    let fontStep = Number.parseInt(window.localStorage.getItem("injection30-font-step") || "0", 10);
    if (!Number.isInteger(fontStep) || fontStep < 0 || fontStep > 2) fontStep = 0;

    const applyFontStep = () => {
      body.classList.remove("font-large", "font-larger");
      if (classNames[fontStep]) body.classList.add(classNames[fontStep]);
      fontButtons.forEach((button) => {
        button.setAttribute("aria-label", `调整正文字号，当前第 ${fontStep + 1} 档`);
      });
    };

    fontButtons.forEach((button) => {
      button.addEventListener("click", () => {
        fontStep = (fontStep + 1) % classNames.length;
        window.localStorage.setItem("injection30-font-step", String(fontStep));
        applyFontStep();
      });
    });
    applyFontStep();
  }

  const focusButtons = [...document.querySelectorAll("[data-focus-mode]")];
  if (focusButtons.length) {
    const applyFocusState = (enabled) => {
      focusButtons.forEach((button) => {
        button.setAttribute("aria-pressed", String(enabled));
        const label = button.querySelector("[data-focus-label]");
        if (label) label.textContent = enabled ? "退出专注" : "专注阅读";
      });
    };
    focusButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const enabled = body.classList.toggle("focus-mode");
        applyFocusState(enabled);
      });
    });
    applyFocusState(body.classList.contains("focus-mode"));
  }

  document.querySelectorAll(".mobile-reader-nav a").forEach((link) => {
    link.addEventListener("click", () => {
      const details = link.closest("details");
      if (details && link.hash) details.open = false;
    });
  });

  root.style.setProperty("--vh", `${window.innerHeight * 0.01}px`);
})();
