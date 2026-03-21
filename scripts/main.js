const AUTH_TOKEN_STORAGE_KEY = "bavarianRoboTasteAuthToken";

const revealItems = document.querySelectorAll(".reveal");

if ("IntersectionObserver" in window) {
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16 }
  );

  revealItems.forEach((item) => {
    revealObserver.observe(item);
  });
} else {
  revealItems.forEach((item) => {
    item.classList.add("is-visible");
  });
}

const getAuthToken = () => window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || "";
const setAuthToken = (token) => window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
const clearAuthToken = () => window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
const isProfilePage = window.location.pathname.endsWith("/profile.html") || window.location.pathname.endsWith("profile.html");

const apiFetch = async (url, options = {}) => {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (token && options.auth !== false) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, {
    method: options.method || "GET",
    headers,
    body: options.body,
  });

  const contentType = response.headers.get("Content-Type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : null;

  if (!response.ok) {
    const detail = payload?.detail || payload?.error || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return payload;
};

const profileLabel = (profile) => profile?.firstName || "Gast";

const renderAuthRail = (profile) => {
  const existingRail = document.querySelector(".auth-rail");
  if (existingRail) {
    existingRail.remove();
  }
  const authHost = document.querySelector("[data-site-header-auth]");

  const rail = document.createElement("div");
  rail.className = "auth-rail";

  if (profile) {
    rail.innerHTML = `
      <div class="auth-rail-card">
        <span class="auth-rail-name">Hallo, ${profileLabel(profile)}</span>
        <a class="auth-rail-link${isProfilePage ? " is-active" : ""}" href="/profile.html">Profil</a>
        <a class="auth-rail-link" href="/docs.html" target="_blank" rel="noopener noreferrer">Doku</a>
        <button class="auth-rail-button" type="button" data-auth-logout>Logout</button>
      </div>
    `;
  } else {
    rail.innerHTML = `
      <div class="auth-rail-card">
        <a class="auth-rail-link" href="/register.html">Registrierung</a>
        <a class="auth-rail-link is-primary" href="/login.html">Login</a>
        <a class="auth-rail-link" href="/docs.html" target="_blank" rel="noopener noreferrer">Doku</a>
      </div>
    `;
  }

  if (authHost) {
    authHost.replaceChildren(rail);
    document.body.classList.add("has-auth-rail");
  } else {
    document.body.prepend(rail);
    document.body.classList.add("has-auth-rail");
  }

  const logoutButton = rail.querySelector("[data-auth-logout]");
  logoutButton?.addEventListener("click", async () => {
    try {
      await apiFetch("/api/auth/logout", {
        method: "POST",
        body: JSON.stringify({}),
      });
    } catch (_) {
      // ignore logout API errors and clear client state anyway
    }

    clearAuthToken();
    renderAuthRail(null);
    if (isProfilePage) {
      window.location.href = "/login.html";
    }
  });
};

const loadCurrentProfile = async () => {
  const token = getAuthToken();
  if (!token) {
    renderAuthRail(null);
    return null;
  }

  try {
    const payload = await apiFetch("/api/auth/me");
    renderAuthRail(payload.guestProfile);
    return payload.guestProfile;
  } catch (_) {
    clearAuthToken();
    renderAuthRail(null);
    return null;
  }
};

const authReady = loadCurrentProfile();

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character] || character;
  });

const formatDrinkPrice = (price) => {
  const normalizedPrice = String(price ?? "").trim();
  const splitPrice = normalizedPrice.match(/^CHF\s*([^/]+?)\s*\/\s*([^/]+)$/i);

  if (!splitPrice) {
    return normalizedPrice;
  }

  const [, glassPrice, bottlePrice] = splitPrice;
  return `Glas CHF ${glassPrice.trim()} | Flasche CHF ${bottlePrice.trim()}`;
};

const productPageRoot = document.querySelector("[data-product-page]");

const buildProductCard = (product, page) => {
  const classes = ["menu-item"];
  if (page === "drinks") {
    classes.push("drink-item");
  }
  if (product.featured) {
    classes.push("menu-item-featured");
  }

  const imageMarkup = product.imagePath
    ? `<img class="menu-item-media" src="${escapeHtml(product.imagePath)}" alt="${escapeHtml(product.title)}" />`
    : "";

  if (page === "drinks") {
    return `
      <article
        class="${classes.join(" ")} dish-trigger"
        tabindex="0"
        role="button"
        data-erp-id="${escapeHtml(product.erpId || "")}"
        data-dish-category="${escapeHtml(product.category)}"
        data-dish-title="${escapeHtml(product.title)}"
        data-dish-price="${escapeHtml(product.price)}"
        data-dish-copy="${escapeHtml(product.ingredients)}"
        data-dish-image="${escapeHtml(product.imagePath)}"
        data-dish-quote="${escapeHtml(product.quote.text)}"
        data-dish-author="${escapeHtml(product.quote.author)}"
        data-dish-special-heading-1="${escapeHtml(product.specialSections[0]?.heading || "")}"
        data-dish-special-content-1="${escapeHtml(product.specialSections[0]?.content || "")}"
        data-dish-special-heading-2="${escapeHtml(product.specialSections[1]?.heading || "")}"
        data-dish-special-content-2="${escapeHtml(product.specialSections[1]?.content || "")}"
      >
        <h3 class="drink-name">${escapeHtml(product.title)}</h3>
        <div class="drink-meta">
          <p class="drink-description">${escapeHtml(product.teaser)}</p>
          <span class="price-tag drink-price">${escapeHtml(formatDrinkPrice(product.price))}</span>
        </div>
      </article>
    `;
  }

  return `
    <article
      class="${classes.join(" ")} dish-trigger"
      tabindex="0"
      role="button"
      data-erp-id="${escapeHtml(product.erpId || "")}"
      data-dish-category="${escapeHtml(product.category)}"
      data-dish-title="${escapeHtml(product.title)}"
      data-dish-price="${escapeHtml(product.price)}"
      data-dish-copy="${escapeHtml(product.ingredients)}"
      data-dish-image="${escapeHtml(product.imagePath)}"
      data-dish-quote="${escapeHtml(product.quote.text)}"
      data-dish-author="${escapeHtml(product.quote.author)}"
      data-dish-special-heading-1="${escapeHtml(product.specialSections[0]?.heading || "")}"
      data-dish-special-content-1="${escapeHtml(product.specialSections[0]?.content || "")}"
      data-dish-special-heading-2="${escapeHtml(product.specialSections[1]?.heading || "")}"
      data-dish-special-content-2="${escapeHtml(product.specialSections[1]?.content || "")}"
    >
      ${imageMarkup}
      <div>
        <h3>${escapeHtml(product.title)}</h3>
        <p>${escapeHtml(product.teaser)}</p>
      </div>
      <span class="price-tag">${escapeHtml(product.price)}</span>
    </article>
  `;
};

const renderProductPage = async () => {
  if (!productPageRoot) {
    return;
  }

  const page = productPageRoot.dataset.productPage || "";
  try {
    const payload = await apiFetch(`/api/products?page=${encodeURIComponent(page)}`, { auth: false });
    productPageRoot.innerHTML = payload.sections
      .map(
        (section) => `
          <section class="section menu-section reveal">
            <div class="section-heading">
              <p class="section-tag">${escapeHtml(section.tag)}</p>
              <h2>${escapeHtml(section.title)}</h2>
            </div>
            <div class="menu-list">
              ${section.products.map((product) => buildProductCard(product, payload.page)).join("")}
            </div>
          </section>
        `
      )
      .join("");

    const dynamicRevealItems = productPageRoot.querySelectorAll(".reveal");
    dynamicRevealItems.forEach((item) => item.classList.add("is-visible"));
    bindDishTriggers();
  } catch (error) {
    productPageRoot.innerHTML = `
      <section class="section menu-section reveal is-visible">
        <div class="section-heading">
          <p class="section-tag">Produktdaten</p>
          <h2>Die Produktdaten konnten gerade nicht geladen werden.</h2>
        </div>
        <p>${escapeHtml(error.message)}</p>
      </section>
    `;
  }
};

const dishModal = document.querySelector("#dish-modal");
let bindDishTriggers = () => {};

if (dishModal) {
  const modalCategory = dishModal.querySelector("#dish-modal-category");
  const modalTitle = dishModal.querySelector("#dish-modal-title");
  const modalPrice = dishModal.querySelector("#dish-modal-price");
  const modalCopy = dishModal.querySelector("#dish-modal-copy");
  const modalOrigin = dishModal.querySelector("#dish-modal-origin");
  const modalQuality = dishModal.querySelector("#dish-modal-quality");
  const modalSpecialHeading1 = dishModal.querySelector("#dish-modal-special-heading-1");
  const modalSpecialHeading2 = dishModal.querySelector("#dish-modal-special-heading-2");
  const modalQuote = dishModal.querySelector("#dish-modal-quote");
  const modalAuthor = dishModal.querySelector("#dish-modal-author");
  const modalImageWrap = dishModal.querySelector(".dish-modal-image-wrap");
  const modalImage = dishModal.querySelector("#dish-modal-image");
  const imageOpenButton = dishModal.querySelector("[data-dish-image-open]");
  const closeButtons = dishModal.querySelectorAll("[data-dish-close]");
  const imageLightbox = document.querySelector("#image-lightbox");
  const imageLightboxImage = imageLightbox?.querySelector("#image-lightbox-image");
  const imageCloseButtons = imageLightbox?.querySelectorAll("[data-image-close]");

  const openDishModal = (trigger) => {
    modalCategory.textContent = trigger.dataset.dishCategory || "Gericht";
    modalTitle.textContent = trigger.dataset.dishTitle || "Gericht";
    modalPrice.textContent = trigger.dataset.dishPrice || "";
    modalCopy.textContent = trigger.dataset.dishCopy || "";
    modalOrigin.textContent = trigger.dataset.dishSpecialContent1 || "";
    modalQuality.textContent = trigger.dataset.dishSpecialContent2 || "";
    if (modalSpecialHeading1) {
      modalSpecialHeading1.textContent = trigger.dataset.dishSpecialHeading1 || "Details";
    }
    if (modalSpecialHeading2) {
      modalSpecialHeading2.textContent = trigger.dataset.dishSpecialHeading2 || "Mehr";
    }
    modalQuote.textContent = `"${trigger.dataset.dishQuote || ""}"`;
    modalAuthor.textContent = trigger.dataset.dishAuthor || "";

    if (modalImageWrap && modalImage) {
      const dishImage = trigger.dataset.dishImage || "";
      if (dishImage) {
        modalImage.src = dishImage;
        modalImage.alt = trigger.dataset.dishTitle || "Gericht";
        modalImageWrap.hidden = false;
      } else {
        modalImage.removeAttribute("src");
        modalImage.alt = "";
        modalImageWrap.hidden = true;
      }
    }

    dishModal.hidden = false;
    document.body.style.overflow = "hidden";
  };

  const closeDishModal = () => {
    dishModal.hidden = true;
    document.body.style.overflow = "";
  };

  const openImageLightbox = () => {
    if (!imageLightbox || !imageLightboxImage || !modalImage?.getAttribute("src")) {
      return;
    }

    imageLightboxImage.src = modalImage.src;
    imageLightboxImage.alt = modalImage.alt;
    imageLightbox.hidden = false;
  };

  const closeImageLightbox = () => {
    if (!imageLightbox || !imageLightboxImage) {
      return;
    }

    imageLightbox.hidden = true;
    imageLightboxImage.removeAttribute("src");
    imageLightboxImage.alt = "";
  };

  bindDishTriggers = () => {
    const dishTriggers = document.querySelectorAll(".dish-trigger");
    dishTriggers.forEach((trigger) => {
      if (trigger.dataset.dishBound === "true") {
        return;
      }

      trigger.dataset.dishBound = "true";
      trigger.addEventListener("click", () => openDishModal(trigger));
      trigger.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openDishModal(trigger);
        }
      });
    });
  };

  bindDishTriggers();

  closeButtons.forEach((button) => {
    button.addEventListener("click", closeDishModal);
  });

  if (imageOpenButton) {
    imageOpenButton.addEventListener("click", (event) => {
      event.stopPropagation();
      openImageLightbox();
    });
  }

  imageCloseButtons?.forEach((button) => {
    button.addEventListener("click", closeImageLightbox);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && imageLightbox && !imageLightbox.hidden) {
      closeImageLightbox();
      return;
    }

    if (event.key === "Escape" && !dishModal.hidden) {
      closeDishModal();
    }
  });
}

renderProductPage();

const docsTabs = Array.from(document.querySelectorAll("[data-docs-tab]"));
const docsPanels = Array.from(document.querySelectorAll("[data-docs-panel]"));

if (docsTabs.length > 0 && docsPanels.length > 0) {
  const docsShell = document.querySelector(".docs-shell");

  const activateDocsSection = (sectionId, updateUrl = true) => {
    const nextId = sectionId || docsPanels[0]?.id || "";

    docsTabs.forEach((tab) => {
      const isActive = tab.getAttribute("aria-controls") === nextId;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });

    docsPanels.forEach((panel) => {
      const isActive = panel.id === nextId;
      panel.hidden = !isActive;
      panel.classList.toggle("is-active", isActive);
    });

    if (updateUrl && nextId) {
      window.history.replaceState(null, "", `#${nextId}`);
    }

    const topOffset = docsShell
      ? docsShell.getBoundingClientRect().top + window.scrollY - 96
      : 0;
    window.scrollTo({ top: Math.max(0, topOffset), behavior: "auto" });
  };

  docsTabs.forEach((tab) => {
    tab.addEventListener("click", (event) => {
      event.preventDefault();
      activateDocsSection(tab.getAttribute("aria-controls") || "");
    });
  });

  const initialId = window.location.hash.replace("#", "") || docsPanels[0]?.id || "";
  activateDocsSection(initialId, Boolean(window.location.hash));
}

const infrastructureApp = document.querySelector("[data-infra-app]");

if (infrastructureApp) {
  const infrastructureViews = {
    "hw-network": {
      title: "HW & Netzwerk",
      intro: "Interaktive Übersicht für Hardware, Netzwerk und angebundene Geräte.",
      hotspots: [
        {
          id: "vm-cas-bpoh",
          selectors: ['rect[x="657"][y="93"][width="166"][height="99"]'],
          title: "VM CAS BPOH",
          text: "Dummytext: Einstieg in die Cloud-nahe Infrastruktur mit Hosting, Zugriffspfad und Betriebsverantwortung.",
          meta: [
            { label: "Typ", value: "Cloud / VM" },
            { label: "Beispiel", value: "IP, Rolle, Security, Wartungsfenster" },
          ],
        },
        {
          id: "kassensystem",
          selectors: ['rect[x="974"][y="243"][width="167"][height="99"]'],
          title: "Kassensystem",
          text: "Dummytext: Operativer Integrationspunkt für Buchungen, Zahlungen und Datenfluss im Restaurant.",
          meta: [
            { label: "Typ", value: "POS / Business Device" },
            { label: "Schnittstellen", value: "ERP, Tablets, lokale Services" },
          ],
        },
        {
          id: "raspberry-pi",
          selectors: ['rect[x="366"][y="295"][width="166"][height="98"]'],
          title: "Raspberry Pi",
          text: "Dummytext: Lokaler Edge-Knoten für Adapter, Automationen oder Steuerlogik.",
          meta: [
            { label: "Typ", value: "On-Prem Edge Node" },
            { label: "Mögliche Inhalte", value: "Docker, Adapter, lokale Prozesse" },
          ],
        },
        {
          id: "unitree-g1",
          selectors: ['rect[x="106"][y="489"][width="167"][height="98"]'],
          title: "Unitree G1 Roboter",
          text: "Physischer Service-Roboter im On-Prem-Netz. Er wird über die G1 API angesteuert und ist aktuell mit Armbewegungen, LED-Signalen, deutscher Sprachausgabe und QR-gestützten Abläufen gekoppelt.",
          meta: [
            { label: "Typ", value: "Robotik / Device" },
            { label: "Anknüpfung", value: "G1 API, Steuerung, Aufgaben" },
            { label: "Funktionen", value: "Motion, LED, Speech, QR Flow" },
          ],
        },
        {
          id: "hue-hub",
          selectors: ['rect[x="593"][y="511"][width="166"][height="73"]'],
          title: "HUE IoT Hub",
          text: "Dummytext: Lichtzentrale für Räume, Szenen und Trigger im Restaurant.",
          meta: [
            { label: "Typ", value: "IoT Hub" },
            { label: "Verknüpfungen", value: "HUE API, Lampen, Light Strips" },
          ],
        },
        {
          id: "hue-light-strips",
          selectors: ['rect[x="498"][y="615"][width="102"][height="60"]'],
          title: "HUE Light Strips",
          text: "Dummytext: Physischer Licht-Aktor für Effekte, Zonen und Stimmungswechsel.",
          meta: [
            { label: "Typ", value: "Licht-Aktor" },
            { label: "Später denkbar", value: "Szenen, Events, Raumzuordnung" },
          ],
        },
        {
          id: "hue-lampe",
          selectors: ['rect[x="742"][y="614"][width="102"][height="60"]'],
          title: "HUE Lampe",
          text: "Dummytext: Einzelner Licht-Aktor zur feineren Dokumentation der Gerätekategorien.",
          meta: [
            { label: "Typ", value: "Licht-Aktor" },
            { label: "Hinweis", value: "Kann später gruppiert oder einzeln beschrieben werden" },
          ],
        },
        {
          id: "tablet-cluster",
          selectors: [
            'rect[x="1057"][y="383"][width="103"][height="60"]',
            'rect[x="1056"][y="451"][width="102"][height="60"]',
            'rect[x="1056"][y="518"][width="102"][height="60"]',
            'rect[x="1056"][y="587"][width="102"][height="60"]',
          ],
          title: "Tablet-Cluster",
          text: "Dummytext: Gruppe von Tisch-Tablets für Bedienung, Information oder Interaktion.",
          meta: [
            { label: "Typ", value: "Client Devices" },
            { label: "Strukturidee", value: "Ein Hotspot für Gruppe oder später je Tablet" },
          ],
        },
      ],
    },
    services: {
      title: "Services",
      intro: "Interaktive Übersicht für Cloud- und On-Premise-Services.",
      hotspots: [
        {
          id: "camunda",
          selectors: ['rect[x="169"][y="246"][width="164"][height="69"]'],
          title: "Camunda",
          text: "Dummytext: Workflow- und Orchestrierungsengine für Prozesse und BPMN-Flows.",
          meta: [
            { label: "Ebene", value: "Cloud" },
            { label: "Später sinnvoll", value: "Trigger, Inputs, Outputs, Owner" },
          ],
        },
        {
          id: "n8n",
          selectors: ['rect[x="353"][y="246"][width="164"][height="69"]'],
          title: "n8n",
          text: "Dummytext: Automation und Glue-Code für schnelle Integrationsstrecken.",
          meta: [
            { label: "Ebene", value: "Cloud" },
            { label: "Typ", value: "Automation / Integration" },
          ],
        },
        {
          id: "power-automate",
          selectors: ['rect[x="541"][y="246"][width="164"][height="69"]'],
          title: "Power Automate",
          text: "Dummytext: Microsoft-nahe Workflow-Schicht für Freigaben und Benachrichtigungen.",
          meta: [
            { label: "Ebene", value: "Cloud" },
            { label: "Anwendungsfall", value: "M365-Workflows und Notifications" },
          ],
        },
        {
          id: "crm",
          selectors: ['rect[x="169"][y="335"][width="164"][height="68"]'],
          title: "CRM",
          text: "Dummytext: Kundendaten, Historie und Kommunikationsbezug für Gäste.",
          meta: [
            { label: "Ebene", value: "Cloud" },
            { label: "Datenfokus", value: "Gastprofil, Historie, Touchpoints" },
          ],
        },
        {
          id: "erp-ready2order",
          selectors: ['rect[x="353"][y="333"][width="352"][height="69"]'],
          title: "ERP / Ready2Order API",
          text: "Dummytext: Zentrale Business-Schnittstelle für Artikel, Preise und operative Daten.",
          meta: [
            { label: "Ebene", value: "Cloud" },
            { label: "Schwerpunkt", value: "Artikel, Preise, Synchronisation" },
          ],
        },
        {
          id: "ngrok-traefik",
          selectors: ['rect[x="169"][y="515"][width="164"][height="69"]'],
          title: "NGROK / Traefik",
          text: "Dummytext: Routing- und Zugangsschicht für Exponierung, Domains und TLS.",
          meta: [
            { label: "Ebene", value: "On-Premise" },
            { label: "Typ", value: "Ingress / Routing" },
          ],
        },
        {
          id: "hue-rest-api",
          selectors: ['rect[x="357"][y="515"][width="164"][height="68"]'],
          title: "HUE Rest API",
          text: "Dummytext: API für die Steuerung der lokalen Lichtinfrastruktur.",
          meta: [
            { label: "Ebene", value: "On-Premise" },
            { label: "Typ", value: "Device API" },
          ],
        },
        {
          id: "g1-api",
          selectors: ['rect[x="543"][y="515"][width="165"][height="68"]'],
          title: "G1 API",
          text: "Lokale FastAPI für Unitree-G1-Steuerung. Die Schnittstelle deckt Arm-Aktionen, LED-Blinken, deutsche TTS-Ausgabe sowie Start, Status und Stop eines QR-Scan-Workers ab.",
          meta: [
            { label: "Ebene", value: "On-Premise" },
            { label: "Typ", value: "Robot API" },
            { label: "Scope", value: "Arm, LED, Speech, QR Scan" },
          ],
        },
      ],
    },
  };

  const infrastructureOverlayFiles = {
    "hw-network": "/assets/docs/infrastructure/hw-network-overlays.json",
    services: "/assets/docs/infrastructure/services-overlays.json",
  };

  const viewButtons = Array.from(infrastructureApp.querySelectorAll("[data-infra-view-button]"));
  const controlButtons = Array.from(document.querySelectorAll("[data-infra-action]"));
  const inlineViews = Array.from(infrastructureApp.querySelectorAll("[data-infra-view]"));
  const inlineObjects = Array.from(infrastructureApp.querySelectorAll("[data-infra-svg]"));
  const inlineOverlay = infrastructureApp.querySelector("[data-infra-overlay]");
  const inlineOverlayTitle = infrastructureApp.querySelector("[data-infra-title]");
  const inlineOverlayText = infrastructureApp.querySelector("[data-infra-text]");
  const inlineOverlayMeta = infrastructureApp.querySelector("[data-infra-meta]");
  const zoomButton = infrastructureApp.querySelector("[data-infra-zoom]");
  const lightbox = document.querySelector("[data-infra-lightbox]");
  const lightboxCloseButtons = Array.from(document.querySelectorAll("[data-infra-lightbox-close]"));
  const lightboxViews = Array.from(document.querySelectorAll("[data-infra-lightbox-view]"));
  const lightboxObjects = Array.from(document.querySelectorAll("[data-infra-lightbox-svg]"));
  const lightboxOverlay = document.querySelector("[data-infra-lightbox-overlay]");
  const lightboxOverlayTitle = document.querySelector("[data-infra-lightbox-title]");
  const lightboxOverlayText = document.querySelector("[data-infra-lightbox-text]");
  const lightboxOverlayMeta = document.querySelector("[data-infra-lightbox-meta]");
  const SVG_NS = "http://www.w3.org/2000/svg";

  const state = {
    view: "hw-network",
    activeHotspot: {},
  };

  const instances = [];
  const hotspotNodeState = new WeakMap();

  const mergeInfrastructureOverlayContent = (payload) => {
    const viewKey = payload?.view;
    const viewConfig = infrastructureViews[viewKey];
    if (!viewConfig || !Array.isArray(payload?.hotspots)) {
      return;
    }

    const overlayById = new Map(
      payload.hotspots
        .filter((item) => item && typeof item.id === "string")
        .map((item) => [item.id, item])
    );

    viewConfig.hotspots = viewConfig.hotspots.map((hotspot) => {
      const external = overlayById.get(hotspot.id);
      if (!external) {
        return hotspot;
      }

      return {
        ...hotspot,
        title: external.title || hotspot.title,
        text: external.text || hotspot.text,
        meta: Array.isArray(external.meta) ? external.meta : hotspot.meta,
      };
    });
  };

  const loadInfrastructureOverlays = async () => {
    const fileEntries = Object.entries(infrastructureOverlayFiles);
    await Promise.all(
      fileEntries.map(async ([viewKey, filePath]) => {
        try {
          const response = await fetch(filePath, { cache: "no-store" });
          if (!response.ok) {
            return;
          }
          const payload = await response.json();
          if (!payload.view) {
            payload.view = viewKey;
          }
          mergeInfrastructureOverlayContent(payload);
        } catch (_) {
          // Fallback remains the inline hotspot content when overlay files are unavailable.
        }
      })
    );
  };

  const renderMeta = (target, items) => {
    if (!target) {
      return;
    }

    target.innerHTML = items
      .map(
        (item) => `
          <div>
            <p class="card-kicker">${escapeHtml(item.label)}</p>
            <p>${escapeHtml(item.value)}</p>
          </div>
        `
      )
      .join("");
  };

  const findInstance = (mode, view) => instances.find((entry) => entry.mode === mode && entry.view === view) || null;

  const runtimeOverlays = new Map();

  const getOverlayParts = (mode) => {
    if (runtimeOverlays.has(mode)) {
      return runtimeOverlays.get(mode);
    }

    const overlay = document.createElement("div");
    overlay.style.display = "none";
    overlay.style.position = "fixed";
    overlay.style.left = mode === "lightbox" ? "32px" : "24px";
    overlay.style.top = mode === "lightbox" ? "88px" : "96px";
    overlay.style.zIndex = "99999";
    overlay.style.width = "320px";
    overlay.style.maxWidth = "calc(100vw - 48px)";
    overlay.style.padding = "16px 18px";
    overlay.style.borderRadius = "20px";
    overlay.style.background = "rgba(7, 19, 28, 0.96)";
    overlay.style.border = "1px solid rgba(255,255,255,0.08)";
    overlay.style.boxShadow = "0 20px 40px rgba(0,0,0,0.35)";
    overlay.style.color = "#f4f7fb";
    overlay.style.pointerEvents = "none";
    overlay.style.fontFamily = "Arial, sans-serif";
    overlay.style.gap = "10px";

    const kicker = document.createElement("p");
    kicker.textContent = mode === "lightbox" ? "VOLLBILD" : "HOTSPOT";
    kicker.style.margin = "0";
    kicker.style.fontSize = "12px";
    kicker.style.letterSpacing = "0.18em";
    kicker.style.textTransform = "uppercase";
    kicker.style.fontWeight = "700";
    kicker.style.color = "#77e5d8";

    const title = document.createElement("h3");
    title.style.margin = "6px 0 0";
    title.style.fontSize = "28px";
    title.style.lineHeight = "1.1";
    title.style.color = "#ffffff";

    const text = document.createElement("p");
    text.style.margin = "10px 0 0";
    text.style.fontSize = "16px";
    text.style.lineHeight = "1.5";
    text.style.color = "rgba(244,247,251,0.92)";

    const meta = document.createElement("div");
    meta.style.display = "grid";
    meta.style.gap = "10px";
    meta.style.marginTop = "10px";

    overlay.appendChild(kicker);
    overlay.appendChild(title);
    overlay.appendChild(text);
    overlay.appendChild(meta);

    document.body.appendChild(overlay);

    const parts = {
      overlay,
      title,
      text,
      meta,
    };

    runtimeOverlays.set(mode, parts);
    return parts;
  };

  const hideOverlay = (mode) => {
    const parts = getOverlayParts(mode);
    if (parts.overlay) {
      parts.overlay.style.display = "none";
    }
  };

  const showOverlay = (mode, hotspot, triggerRect, figureRect) => {
    const parts = getOverlayParts(mode);
    if (!parts.overlay || !parts.title || !parts.text || !parts.meta) {
      return;
    }

    parts.title.textContent = hotspot.title;
    parts.text.textContent = hotspot.text;
    renderMeta(parts.meta, hotspot.meta || []);
    parts.overlay.style.display = "grid";

    const overlayRect = parts.overlay.getBoundingClientRect();
    const margin = 16;
    let left = triggerRect.right + margin;
    let top = triggerRect.top;

    if (left + overlayRect.width > window.innerWidth - margin) {
      left = triggerRect.left - overlayRect.width - margin;
    }
    if (left < margin) {
      left = margin;
    }
    if (top + overlayRect.height > window.innerHeight - margin) {
      top = Math.max(margin, window.innerHeight - overlayRect.height - margin);
    }

    parts.overlay.style.left = `${Math.round(left)}px`;
    parts.overlay.style.top = `${Math.round(top)}px`;
  };

  const setActiveHotspot = (mode, view, hotspotId) => {
    state.activeHotspot[`${mode}:${view}`] = hotspotId || "";
    const instance = findInstance(mode, view);
    if (!instance) {
      hideOverlay(mode);
      return;
    }

    instance.hotspots.forEach((entry) => {
      entry.trigger.classList.toggle("is-active", entry.hotspot.id === hotspotId);
      entry.sourceNodes.forEach((node) => {
        const original =
          hotspotNodeState.get(node) || {
            fill: node.getAttribute("fill"),
            stroke: node.getAttribute("stroke"),
            strokeWidth: node.getAttribute("stroke-width"),
            filter: node.style.filter || "",
            opacity: node.style.opacity || "",
          };

        hotspotNodeState.set(node, original);

        if (entry.hotspot.id === hotspotId) {
          if (node.tagName.toLowerCase() === "rect") {
            node.setAttribute("fill", "#FFF36A");
            node.setAttribute("stroke", "#77E5D8");
            node.setAttribute("stroke-width", "4");
          } else if (node.tagName.toLowerCase() === "text") {
            node.style.filter = "drop-shadow(0 0 10px rgba(119, 229, 216, 0.45))";
            node.style.opacity = "1";
          }
        } else {
          if (node.tagName.toLowerCase() === "rect") {
            if (original.fill === null) {
              node.removeAttribute("fill");
            } else {
              node.setAttribute("fill", original.fill);
            }
            if (original.stroke === null) {
              node.removeAttribute("stroke");
            } else {
              node.setAttribute("stroke", original.stroke);
            }
            if (original.strokeWidth === null) {
              node.removeAttribute("stroke-width");
            } else {
              node.setAttribute("stroke-width", original.strokeWidth);
            }
          } else if (node.tagName.toLowerCase() === "text") {
            node.style.filter = original.filter;
            node.style.opacity = original.opacity;
          }
        }
      });
    });

    const activeEntry = instance.hotspots.find((entry) => entry.hotspot.id === hotspotId);
    if (!activeEntry) {
      hideOverlay(mode);
      return;
    }

    showOverlay(mode, activeEntry.hotspot, activeEntry.trigger.getBoundingClientRect(), instance.figure.getBoundingClientRect());
  };

  const fitSvgToFigure = (instance) => {
    const { svg, figure } = instance;
    const width = svg.viewBox.baseVal.width || Number(svg.getAttribute("width")) || 1280;
    const height = svg.viewBox.baseVal.height || Number(svg.getAttribute("height")) || 720;

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    instance.minScale = 1;
    if (!instance.scale || instance.scale < 1) {
      instance.scale = 1;
      instance.translateX = 0;
      instance.translateY = 0;
    }
  };

  const clampPan = (instance) => {
    const figureWidth = instance.figure.clientWidth || 0;
    const figureHeight = instance.figure.clientHeight || 0;
    const scaledWidth = figureWidth * instance.scale;
    const scaledHeight = figureHeight * instance.scale;
    const maxX = Math.max(0, (scaledWidth - figureWidth) / 2);
    const maxY = Math.max(0, (scaledHeight - figureHeight) / 2);

    instance.translateX = Math.max(-maxX, Math.min(maxX, instance.translateX));
    instance.translateY = Math.max(-maxY, Math.min(maxY, instance.translateY));
  };

  const syncPanState = (instance) => {
    const isDraggable = instance.scale > instance.minScale + 0.001;
    instance.figure.classList.toggle("is-draggable", isDraggable);
    if (!isDraggable) {
      instance.figure.classList.remove("is-panning");
    }
    instance.svg.style.cursor = isDraggable ? "grab" : "";
  };

  const applyTransform = (instance) => {
    instance.svg.style.transformOrigin = "50% 50%";
    instance.svg.style.transform = `translate(${instance.translateX}px, ${instance.translateY}px) scale(${instance.scale})`;
    syncPanState(instance);
    const hotspotId = state.activeHotspot[`${instance.mode}:${instance.view}`];
    if (hotspotId) {
      setActiveHotspot(instance.mode, instance.view, hotspotId);
    }
  };

  const resetViewTransform = (instance) => {
    fitSvgToFigure(instance);
    instance.translateX = 0;
    instance.translateY = 0;
    instance.scale = instance.minScale;
    applyTransform(instance);
  };

  const zoomInstance = (instance, delta) => {
    const nextScale = Math.max(instance.minScale, Math.min(instance.minScale * 4, instance.scale + delta));
    instance.scale = nextScale;
    clampPan(instance);
    applyTransform(instance);
  };

  const setView = (viewKey) => {
    state.view = infrastructureViews[viewKey] ? viewKey : "hw-network";

    viewButtons.forEach((button) => {
      const isActive = button.dataset.infraViewButton === state.view;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", String(isActive));
    });

    inlineViews.forEach((figure) => {
      const isActive = figure.dataset.infraView === state.view;
      figure.hidden = !isActive;
      figure.classList.toggle("is-active", isActive);
    });

    lightboxViews.forEach((figure) => {
      const isActive = figure.dataset.infraLightboxView === state.view;
      figure.hidden = !isActive;
      figure.classList.toggle("is-active", isActive);
    });

    hideOverlay("inline");
    hideOverlay("lightbox");
  };

  const getTextUnionBounds = (svg, baseBounds) => {
    const nearbyTexts = Array.from(svg.querySelectorAll("text")).filter((node) => {
      const box = node.getBBox();
      const horizontallyNear = box.x + box.width >= baseBounds.x - 24 && box.x <= baseBounds.x + baseBounds.width + 24;
      const verticallyNear = box.y + box.height >= baseBounds.y - 24 && box.y <= baseBounds.y + baseBounds.height + 24;
      return horizontallyNear && verticallyNear;
    });

    return nearbyTexts.reduce(
      (bounds, node) => {
        const box = node.getBBox();
        const minX = Math.min(bounds.x, box.x);
        const minY = Math.min(bounds.y, box.y);
        const maxX = Math.max(bounds.x + bounds.width, box.x + box.width);
        const maxY = Math.max(bounds.y + bounds.height, box.y + box.height);
        return {
          x: minX,
          y: minY,
          width: maxX - minX,
          height: maxY - minY,
        };
      },
      { ...baseBounds }
    );
  };

  const bindHotspots = (instance) => {
    const viewConfig = infrastructureViews[instance.view];
    if (!viewConfig) {
      return;
    }

    instance.hotspots = [];

    viewConfig.hotspots.forEach((hotspot) => {
      const rectNodes = hotspot.selectors.flatMap((selector) => Array.from(instance.svg.querySelectorAll(selector)));
      if (!rectNodes.length) {
        return;
      }

      const sourceNodes = [...rectNodes];
      const trigger = rectNodes[0];

      sourceNodes.forEach((node) => {
        node.setAttribute("data-infra-source", hotspot.id);
        node.style.cursor = "pointer";
        node.style.transition = "filter 160ms ease, opacity 160ms ease";
        node.style.userSelect = "none";
      });

      let clearTimer = null;
      const activate = () => setActiveHotspot(instance.mode, instance.view, hotspot.id);
      const scheduleClear = () => {
        window.clearTimeout(clearTimer);
        clearTimer = window.setTimeout(() => {
          setActiveHotspot(instance.mode, instance.view, "");
        }, 40);
      };
      const cancelClear = () => {
        window.clearTimeout(clearTimer);
      };

      sourceNodes.forEach((node) => {
        node.addEventListener("mouseenter", () => {
          cancelClear();
          activate();
        });
        node.addEventListener("mousemove", () => {
          cancelClear();
          activate();
        });
        node.addEventListener("mouseleave", scheduleClear);
        node.addEventListener("pointerenter", () => {
          cancelClear();
          activate();
        });
        node.addEventListener("pointermove", () => {
          cancelClear();
          activate();
        });
        node.addEventListener("pointerleave", scheduleClear);
        node.addEventListener("focus", activate);
        node.addEventListener("blur", scheduleClear);
        node.addEventListener("click", activate);
      });

      instance.hotspots.push({ hotspot, trigger, sourceNodes });
    });
  };

  const bindPanZoom = (instance) => {
    const startPan = { active: false, x: 0, y: 0, startX: 0, startY: 0 };
    const interactionTarget = instance.svg;

    interactionTarget.addEventListener("wheel", (event) => {
      event.preventDefault();
      zoomInstance(instance, event.deltaY < 0 ? instance.minScale * 0.16 : -instance.minScale * 0.16);
    }, { passive: false });

    interactionTarget.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || instance.scale <= instance.minScale + 0.001) {
        return;
      }

      if (event.target.closest?.("[data-infra-trigger]")) {
        return;
      }

      startPan.active = true;
      startPan.startX = event.clientX;
      startPan.startY = event.clientY;
      startPan.x = instance.translateX;
      startPan.y = instance.translateY;
      instance.figure.classList.add("is-panning");
      interactionTarget.setPointerCapture(event.pointerId);
    });

    interactionTarget.addEventListener("pointermove", (event) => {
      if (!startPan.active) {
        return;
      }
      instance.translateX = startPan.x + (event.clientX - startPan.startX);
      instance.translateY = startPan.y + (event.clientY - startPan.startY);
      clampPan(instance);
      applyTransform(instance);
    });

    const stopPan = (event) => {
      if (startPan.active && interactionTarget.hasPointerCapture(event.pointerId)) {
        interactionTarget.releasePointerCapture(event.pointerId);
      }
      startPan.active = false;
      instance.figure.classList.remove("is-panning");
      syncPanState(instance);
    };

    interactionTarget.addEventListener("pointerup", stopPan);
    interactionTarget.addEventListener("pointercancel", stopPan);
  };

  const decorateSvg = (mode, view, objectNode, figure) => {
    const sourceSvg = objectNode.contentDocument?.querySelector("svg");
    if (!sourceSvg) {
      return;
    }

    const existingInlineSvg = figure.querySelector("svg.docs-infra-svg");
    existingInlineSvg?.remove();

    const svg = sourceSvg.cloneNode(true);
    svg.classList.add("docs-infra-svg");
    svg.setAttribute("data-inline-infra-svg", view);
    objectNode.hidden = true;
    objectNode.style.display = "none";
    figure.appendChild(svg);

    svg.style.width = "100%";
    svg.style.height = "100%";
    svg.style.display = "block";
    svg.style.transformBox = "fill-box";
    svg.style.cursor = "";
    svg.style.userSelect = "none";
    svg.style.webkitUserSelect = "none";

    const existingLayer = svg.querySelector('[data-brt-trigger-layer="true"]');
    existingLayer?.remove();

    const instance = {
      mode,
      view,
      objectNode,
      figure,
      svg,
      hotspots: [],
      minScale: 1,
      scale: 1,
      translateX: 0,
      translateY: 0,
    };

    instances.push(instance);
    bindHotspots(instance);
    bindPanZoom(instance);
    resetViewTransform(instance);

    const activeHotspotId = state.activeHotspot[`${mode}:${view}`];
    if (activeHotspotId) {
      setActiveHotspot(mode, view, activeHotspotId);
    }
  };

  const setupObject = (mode, view, objectNode, figure) => {
    const load = () => decorateSvg(mode, view, objectNode, figure);
    if (objectNode.contentDocument?.querySelector("svg")) {
      load();
      return;
    }
    objectNode.addEventListener("load", load, { once: true });
  };

  const initInfrastructureApp = async () => {
    await loadInfrastructureOverlays();

    inlineObjects.forEach((objectNode) => {
      const view = objectNode.dataset.infraSvg || "";
      const figure = objectNode.closest("[data-infra-view]");
      if (view && figure) {
        setupObject("inline", view, objectNode, figure);
      }
    });

    lightboxObjects.forEach((objectNode) => {
      const view = objectNode.dataset.infraLightboxSvg || "";
      const figure = objectNode.closest("[data-infra-lightbox-view]");
      if (view && figure) {
        setupObject("lightbox", view, objectNode, figure);
      }
    });

    viewButtons.forEach((button) => {
      button.addEventListener("click", () => {
        setView(button.dataset.infraViewButton || "hw-network");
      });
    });

    controlButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const mode = button.dataset.infraMode || "inline";
        const instance = findInstance(mode, state.view);
        if (!instance) {
          return;
        }

        const action = button.dataset.infraAction;
        if (action === "zoom-in") {
          zoomInstance(instance, instance.minScale * 0.2);
        } else if (action === "zoom-out") {
          zoomInstance(instance, -instance.minScale * 0.2);
        } else if (action === "reset") {
          resetViewTransform(instance);
        }
      });
    });

    zoomButton?.addEventListener("click", () => {
      if (!lightbox) {
        return;
      }
      lightbox.hidden = false;
      document.body.classList.add("is-modal-open");
      setView(state.view);
      requestAnimationFrame(() => {
        const instance = findInstance("lightbox", state.view);
        if (instance) {
          resetViewTransform(instance);
        }
      });
    });

    lightboxCloseButtons.forEach((button) => {
      button.addEventListener("click", () => {
        if (!lightbox) {
          return;
        }
        lightbox.hidden = true;
        document.body.classList.remove("is-modal-open");
        hideOverlay("lightbox");
      });
    });

    window.addEventListener("resize", () => {
      instances.forEach((instance) => {
        resetViewTransform(instance);
      });
    });

    setView("hw-network");
  };

  initInfrastructureApp();
}

const registrationApp = document.querySelector("[data-registration-app]");

if (registrationApp) {
  const stages = registrationApp.querySelectorAll("[data-stage]");
  const statusBox = registrationApp.querySelector("[data-registration-status]");
  const indicators = registrationApp.querySelectorAll("[data-step-indicator]");
  const registrationForm = registrationApp.querySelector("[data-registration-form]");
  const verificationForm = registrationApp.querySelector("[data-verification-form]");
  const passwordForm = registrationApp.querySelector("[data-password-form]");
  const resendButton = registrationApp.querySelector("[data-resend-code]");
  const codePreview = registrationApp.querySelector("[data-code-preview]");
  const successSummary = registrationApp.querySelector("[data-success-summary]");

  const state = {
    step: 1,
    profile: null,
    verified: false,
  };

  const showStatus = (message, kind = "success") => {
    if (!statusBox) {
      return;
    }

    statusBox.textContent = message;
    statusBox.className = `registration-status is-visible is-${kind}`;
  };

  const clearStatus = () => {
    if (!statusBox) {
      return;
    }

    statusBox.textContent = "";
    statusBox.className = "registration-status";
  };

  const setStep = (step) => {
    state.step = step;

    stages.forEach((stage) => {
      const isVisible = Number(stage.dataset.stage) === step;
      stage.hidden = !isVisible;
      stage.classList.toggle("is-active", isVisible);
    });

    indicators.forEach((indicator) => {
      const indicatorStep = Number(indicator.dataset.stepIndicator);
      indicator.classList.toggle("is-active", indicatorStep === step);
    });
  };

  const getValue = (form, name) => form?.elements?.namedItem(name)?.value?.trim() || "";

  registrationForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearStatus();

    const firstName = getValue(registrationForm, "firstName");
    const email = getValue(registrationForm, "email");
    const phone = getValue(registrationForm, "phone");

    if (!firstName || !email) {
      showStatus("Bitte Vorname und E-Mail ausfüllen.", "error");
      return;
    }

    state.profile = { firstName, email, phone };
    state.verified = false;

    try {
      await apiFetch("/api/register/request-code", {
        method: "POST",
        body: JSON.stringify({
          firstName,
          email,
          phone,
        }),
        auth: false,
      });

      if (codePreview) {
        codePreview.hidden = false;
        codePreview.textContent = `Wir haben einen Bestätigungscode an ${email} gesendet.`;
      }

      setStep(2);
      showStatus("Der Bestätigungscode wurde per E-Mail versendet.", "success");
    } catch (error) {
      showStatus(`Der Bestätigungscode konnte nicht gesendet werden: ${error.message}`, "error");
    }
  });

  verificationForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearStatus();

    const code = getValue(verificationForm, "verificationCode").replace(/\s+/g, "");

    if (!code) {
      showStatus("Bitte den 6-stelligen Code eingeben.", "error");
      return;
    }

    if (!state.profile?.email) {
      showStatus("Bitte starte die Registrierung erneut.", "error");
      setStep(1);
      return;
    }

    try {
      await apiFetch("/api/register/verify-code", {
        method: "POST",
        body: JSON.stringify({
          email: state.profile.email,
          verificationCode: code,
        }),
        auth: false,
      });

      state.verified = true;
      setStep(3);
      showStatus("Code bestätigt. Jetzt kannst du dein Passwort setzen.", "success");
    } catch (error) {
      showStatus(`Die Code-Prüfung ist fehlgeschlagen: ${error.message}`, "error");
    }
  });

  resendButton?.addEventListener("click", async () => {
    clearStatus();

    if (!state.profile?.email) {
      showStatus("Bitte zuerst die Registrierungsdaten erfassen.", "error");
      setStep(1);
      return;
    }

    try {
      await apiFetch("/api/register/request-code", {
        method: "POST",
        body: JSON.stringify(state.profile),
        auth: false,
      });

      state.verified = false;
      if (codePreview) {
        codePreview.hidden = false;
        codePreview.textContent = `Wir haben einen neuen Bestätigungscode an ${state.profile.email} gesendet.`;
      }

      showStatus("Ein neuer Bestätigungscode wurde per E-Mail versendet.", "success");
    } catch (error) {
      showStatus(`Der neue Bestätigungscode konnte nicht gesendet werden: ${error.message}`, "error");
    }
  });

  passwordForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearStatus();

    const password = getValue(passwordForm, "password");
    const passwordConfirm = getValue(passwordForm, "passwordConfirm");

    if (password.length < 8) {
      showStatus("Das Passwort muss mindestens 8 Zeichen lang sein.", "error");
      return;
    }

    if (password !== passwordConfirm) {
      showStatus("Die Passwörter stimmen nicht überein.", "error");
      return;
    }

    if (!state.profile?.email || !state.verified) {
      showStatus("Bitte bestätige zuerst deinen E-Mail-Code.", "error");
      return;
    }

    try {
      const result = await apiFetch("/api/register/complete", {
        method: "POST",
        body: JSON.stringify({
          email: state.profile.email,
          password,
          passwordConfirm,
        }),
        auth: false,
      });

      setAuthToken(result.token);
      renderAuthRail(result.guestProfile);

      if (successSummary) {
        successSummary.innerHTML = `
          <p><strong>Vorname</strong><br />${result.guestProfile.firstName}</p>
          <p><strong>E-Mail</strong><br />${result.guestProfile.email}</p>
          <p><strong>Telefon</strong><br />${result.guestProfile.phone || "nicht angegeben"}</p>
        `;
      }

      stages.forEach((stage) => {
        const isFinal = Number(stage.dataset.stage) === 4;
        stage.hidden = !isFinal;
        stage.classList.toggle("is-active", isFinal);
      });

      indicators.forEach((indicator) => {
        indicator.classList.remove("is-active");
      });

      showStatus("Die Registrierung wurde erfolgreich abgeschlossen.", "success");
    } catch (error) {
      showStatus(`Die Registrierung konnte nicht abgeschlossen werden: ${error.message}`, "error");
    }
  });
}

const contactForm = document.querySelector("[data-contact-form]");

if (contactForm) {
  const submitButton = contactForm.querySelector("[data-contact-submit]");
  const feedbackBox = contactForm.querySelector("[data-contact-feedback]");
  const requiredFields = Array.from(contactForm.querySelectorAll("[required]"));

  const setContactFeedback = (message, kind = "success") => {
    if (!feedbackBox) {
      return;
    }

    feedbackBox.textContent = message;
    feedbackBox.className = `form-feedback field-span is-visible is-${kind}`;
  };

  const clearContactFeedback = () => {
    if (!feedbackBox) {
      return;
    }

    feedbackBox.textContent = "";
    feedbackBox.className = "form-feedback field-span";
  };

  const isContactFormComplete = () => requiredFields.every((field) => field.value.trim().length > 0);
  const getSelectedTopic = () => contactForm.querySelector('input[name="topic"]:checked')?.value?.trim() || "";

  const updateContactSubmitState = () => {
    if (submitButton) {
      submitButton.disabled = !(isContactFormComplete() && getSelectedTopic());
    }
  };

  requiredFields.forEach((field) => {
    field.addEventListener("input", () => {
      clearContactFeedback();
      updateContactSubmitState();
    });

    field.addEventListener("change", () => {
      clearContactFeedback();
      updateContactSubmitState();
    });
  });

  contactForm.querySelectorAll('input[name="topic"]').forEach((field) => {
    field.addEventListener("change", () => {
      clearContactFeedback();
      updateContactSubmitState();
    });
  });

  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearContactFeedback();

    if (!(isContactFormComplete() && getSelectedTopic())) {
      setContactFeedback("Bitte alle Pflichtfelder ausfüllen, bevor du die Nachricht sendest.", "error");
      updateContactSubmitState();
      return;
    }

    const payload = {
      name: contactForm.elements.namedItem("name")?.value.trim() || "",
      email: contactForm.elements.namedItem("email")?.value.trim() || "",
      topic: getSelectedTopic(),
      message: contactForm.elements.namedItem("message")?.value.trim() || "",
      createdAt: new Date().toISOString(),
    };

    if (submitButton) {
      submitButton.disabled = true;
    }

    try {
      await apiFetch("/api/contact", {
        method: "POST",
        body: JSON.stringify(payload),
        auth: false,
      });

      contactForm.reset();
      const defaultTopic = contactForm.querySelector('input[name="topic"][value="Allgemeine Anfrage"]');
      if (defaultTopic) {
        defaultTopic.checked = true;
      }

      setContactFeedback("Die Nachricht wurde erfolgreich versendet. Wir haben dir außerdem eine Bestätigung per E-Mail geschickt.", "success");
    } catch (error) {
      setContactFeedback(`Der Mailversand ist fehlgeschlagen: ${error.message}`, "error");
    } finally {
      updateContactSubmitState();
    }
  });

  updateContactSubmitState();
}

const loginForm = document.querySelector("[data-login-form]");

if (loginForm) {
  const statusBox = document.querySelector("[data-login-status]");

  const showLoginStatus = (message, kind = "success") => {
    if (!statusBox) {
      return;
    }
    statusBox.textContent = message;
    statusBox.className = `registration-status is-visible is-${kind}`;
  };

  authReady.then((profile) => {
    if (profile) {
      window.location.href = "/profile.html";
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = loginForm.elements.namedItem("email")?.value.trim() || "";
    const password = loginForm.elements.namedItem("password")?.value.trim() || "";

    if (!email || !password) {
      showLoginStatus("Bitte gib deine E-Mail-Adresse und dein Passwort ein.", "error");
      return;
    }

    try {
      const result = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
        auth: false,
      });

      setAuthToken(result.token);
      renderAuthRail(result.guestProfile);
      window.location.href = "/profile.html";
    } catch (error) {
      showLoginStatus(`Der Login ist fehlgeschlagen: ${error.message}`, "error");
    }
  });
}

const profileForm = document.querySelector("[data-profile-form]");
const changePasswordForm = document.querySelector("[data-change-password-form]");

if (profileForm && changePasswordForm) {
  const profileStatus = document.querySelector("[data-profile-status]");
  const passwordStatus = document.querySelector("[data-password-status]");
  const accountTabs = document.querySelectorAll("[data-account-tab]");
  const accountPanes = document.querySelectorAll("[data-account-pane]");
  const reservationModal = document.querySelector("[data-profile-reservation-modal]");
  const reservationModalCloseButtons = document.querySelectorAll("[data-profile-reservation-close]");
  const reservationModalTitle = document.querySelector("[data-profile-reservation-title]");
  const reservationModalSubtitle = document.querySelector("[data-profile-reservation-subtitle]");
  const reservationModalMeta = document.querySelector("[data-profile-reservation-meta]");
  const reservationModalQr = document.querySelector("[data-profile-reservation-qr]");
  const reservationModalQrOpen = document.querySelector("[data-profile-reservation-qr-open]");
  const reservationModalQrHint = document.querySelector("[data-profile-reservation-qr-hint]");
  const reservationModalNotes = document.querySelector("[data-profile-reservation-notes]");
  const reservationModalActions = document.querySelector("[data-profile-reservation-actions]");
  const profileQrModal = document.querySelector("[data-profile-qr-modal]");
  const profileQrImage = document.querySelector("[data-profile-qr-image]");
  const profileQrDownload = document.querySelector("[data-profile-qr-download]");
  const profileQrCloseButtons = document.querySelectorAll("[data-profile-qr-close]");
  const reservationsStatus = document.querySelector("[data-profile-reservations-status]");
  const reservationsTarget = document.querySelector("[data-profile-reservations]");
  const reservationStore = new Map();
  let activeReservationQr = null;

  const setBoxStatus = (box, message, kind = "success") => {
    if (!box) {
      return;
    }
    box.textContent = message;
    box.className = `registration-status is-visible is-${kind}`;
  };

  const reservationQrImageUrl = (reservation) => {
    if (reservation?.qrImageUrl) {
      return reservation.qrImageUrl;
    }

    const reservationId = reservation?.reservationId || reservation?.id || "";
    if (!reservationId) {
      return "";
    }

    return `${window.location.origin}/reservations/qr-image/${encodeURIComponent(reservationId)}.svg`;
  };

  const fillProfileForm = (profile) => {
    profileForm.elements.namedItem("firstName").value = profile.firstName || "";
    profileForm.elements.namedItem("email").value = profile.email || "";
    profileForm.elements.namedItem("phone").value = profile.phone || "";
  };

  const setActiveReservationQr = (reservation) => {
    const qrImageUrl = reservationQrImageUrl(reservation);
    activeReservationQr = qrImageUrl
      ? {
          imageUrl: qrImageUrl,
          code: reservation?.reservationCode || reservation?.reservationId || reservation?.id || "reservation",
        }
      : null;
    return qrImageUrl;
  };

  const renderProfileReservations = (reservations) => {
    if (!reservationsTarget) {
      return;
    }

    reservationStore.clear();

    if (!reservations.length) {
      reservationsTarget.innerHTML = '<div class="profile-empty">Noch keine Reservierungen mit diesem Gastprofil verknüpft.</div>';
      return;
    }

    const sortedReservations = [...reservations].sort((left, right) => {
      const leftValue = `${left.date || ""}-${left.slotKey || ""}`;
      const rightValue = `${right.date || ""}-${right.slotKey || ""}`;
      return rightValue.localeCompare(leftValue);
    });

    sortedReservations.forEach((reservation) => {
      const reservationId = reservation?.reservationId || reservation?.id || "";
      if (reservationId) {
        reservationStore.set(reservationId, reservation);
      }
    });

    reservationsTarget.innerHTML = sortedReservations
      .map((reservation) => {
        const isCancelled = reservation.status === "cancelled";
        const qrImageUrl = reservationQrImageUrl(reservation);
        const reservationId = reservation?.reservationId || reservation?.id || "";

        return `
          <article class="profile-reservation-card" tabindex="0" role="button" data-profile-reservation-id="${escapeHtml(reservationId)}">
            <div class="profile-reservation-head">
              <p class="card-kicker">${escapeHtml(reservation.roomName)}</p>
              <h3>${escapeHtml(reservation.scheduledLabel)}</h3>
              <p class="profile-reservation-note">${escapeHtml(reservation.tableLabel)} | ${escapeHtml(reservation.occasion || "Kein Anlass")}</p>
            </div>
            <button class="profile-reservation-qr-preview" type="button" data-profile-card-qr="${escapeHtml(reservationId)}" aria-label="QR-Code gross öffnen">
              ${
                qrImageUrl
                  ? `<img src="${escapeHtml(qrImageUrl)}" alt="QR-Code für Reservierung ${escapeHtml(
                      reservation.reservationCode || "",
                    )}" loading="lazy" decoding="async" />`
                  : `<span>QR nicht verfügbar</span>`
              }
            </button>
            <div class="profile-reservation-facts">
              <p><strong>Code</strong><br /><span>${escapeHtml(reservation.reservationCode)}</span></p>
              <p><strong>Gäste</strong><br /><span>${escapeHtml(String(reservation.guests))}</span></p>
            </div>
            <span class="profile-reservation-status${isCancelled ? " is-cancelled" : ""}">${escapeHtml(reservation.status)}</span>
          </article>
        `;
      })
      .join("");

    reservationsTarget.querySelectorAll("[data-profile-reservation-id]").forEach((entry) => {
      const openDetails = () => {
        const reservation = reservationStore.get(entry.dataset.profileReservationId || "");
        if (reservation) {
          openProfileReservationModal(reservation);
        }
      };

      entry.addEventListener("click", openDetails);
      entry.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openDetails();
        }
      });
    });

    reservationsTarget.querySelectorAll("[data-profile-card-qr]").forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const reservation = reservationStore.get(button.dataset.profileCardQr || "");
        if (!reservation) {
          return;
        }
        setActiveReservationQr(reservation);
        openProfileQrModal();
      });
    });
  };

  const switchAccountPane = (nextPane) => {
    accountTabs.forEach((tab) => {
      const isActive = tab.dataset.accountTab === nextPane;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", String(isActive));
    });

    accountPanes.forEach((pane) => {
      const isActive = pane.dataset.accountPane === nextPane;
      pane.hidden = !isActive;
      pane.classList.toggle("is-active", isActive);
    });
  };

  const openProfileQrModal = () => {
    if (!profileQrModal || !profileQrImage || !activeReservationQr?.imageUrl) {
      return;
    }

    profileQrImage.innerHTML = `<img src="${escapeHtml(activeReservationQr.imageUrl)}" alt="QR-Code für Reservierung ${escapeHtml(
      activeReservationQr.code || "",
    )}" decoding="async" />`;

    if (profileQrDownload) {
      profileQrDownload.href = activeReservationQr.imageUrl;
      profileQrDownload.download = `qr-${activeReservationQr.code || "reservation"}.svg`;
    }

    profileQrModal.hidden = false;
    document.body.classList.add("is-modal-open");
  };

  const closeProfileQrModal = () => {
    if (!profileQrModal) {
      return;
    }

    profileQrModal.hidden = true;
    if (profileQrImage) {
      profileQrImage.innerHTML = "";
    }
    document.body.classList.toggle("is-modal-open", Boolean(reservationModal && !reservationModal.hidden));
  };

  const openProfileReservationModal = (reservation) => {
    if (!reservationModal) {
      return;
    }

    const qrImageUrl = setActiveReservationQr(reservation);

    if (reservationModalTitle) {
      reservationModalTitle.textContent = reservation.roomName || "Reservierung";
    }
    if (reservationModalSubtitle) {
      reservationModalSubtitle.textContent = reservation.scheduledLabel || "";
    }
    if (reservationModalMeta) {
      reservationModalMeta.innerHTML = `
        <p><strong>Reservierungscode</strong><br />${escapeHtml(reservation.reservationCode || "-")}</p>
        <p><strong>Status</strong><br />${escapeHtml(reservation.status || "-")}</p>
        <p><strong>Tisch</strong><br />${escapeHtml(reservation.tableLabel || "-")}</p>
        <p><strong>Gäste</strong><br />${escapeHtml(String(reservation.guests || "-"))}</p>
        <p><strong>Anlass</strong><br />${escapeHtml(reservation.occasion || "Kein Anlass hinterlegt")}</p>
      `;
    }
    if (reservationModalQr) {
      reservationModalQr.innerHTML = qrImageUrl
        ? `<img src="${escapeHtml(qrImageUrl)}" alt="QR-Code für Reservierung ${escapeHtml(
            reservation.reservationCode || "",
          )}" decoding="async" />`
        : `<div class="profile-reservation-qr-empty">QR-Code nicht verfügbar.</div>`;
    }
    if (reservationModalQrOpen) {
      reservationModalQrOpen.disabled = !qrImageUrl;
    }
    if (reservationModalQrHint) {
      reservationModalQrHint.textContent = qrImageUrl
        ? "Klicke auf den kleinen QR-Code, um ihn gross zu öffnen."
        : "Für diese Reservierung steht gerade kein QR-Code bereit.";
    }
    if (reservationModalNotes) {
      reservationModalNotes.innerHTML = `
        <p><strong>Notizen</strong><br />${escapeHtml(reservation.notes || "Keine Zusatznotizen hinterlegt.")}</p>
        <p><strong>Storno-Frist</strong><br />${escapeHtml(reservation.cancellationDeadlineLabel || "-")}</p>
      `;
    }
    if (reservationModalActions) {
      const cancelAction =
        reservation.status !== "cancelled" && reservation.cancelUrl
          ? `<a class="button button-primary" href="${escapeHtml(reservation.cancelUrl)}" target="_blank" rel="noreferrer">Reservierung verwalten</a>`
          : "";
      reservationModalActions.innerHTML = `
        ${cancelAction}
      `;
    }

    reservationModal.hidden = false;
    document.body.classList.add("is-modal-open");
  };

  const closeProfileReservationModal = () => {
    if (!reservationModal) {
      return;
    }

    closeProfileQrModal();
    reservationModal.hidden = true;
    activeReservationQr = null;
    document.body.classList.remove("is-modal-open");
  };

  accountTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      switchAccountPane(tab.dataset.accountTab || "settings");
    });
  });

  reservationModalCloseButtons.forEach((button) => {
    button.addEventListener("click", () => {
      closeProfileReservationModal();
    });
  });

  reservationModalQrOpen?.addEventListener("click", (event) => {
    event.stopPropagation();
    openProfileQrModal();
  });

  profileQrCloseButtons.forEach((button) => {
    button.addEventListener("click", () => {
      closeProfileQrModal();
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && profileQrModal && !profileQrModal.hidden) {
      closeProfileQrModal();
      return;
    }

    if (event.key === "Escape" && reservationModal && !reservationModal.hidden) {
      closeProfileReservationModal();
    }
  });

  const loadProfileReservations = async () => {
    if (!reservationsTarget) {
      return;
    }

    if (reservationsStatus) {
      reservationsStatus.textContent = "";
      reservationsStatus.className = "registration-status";
    }

    try {
      const result = await apiFetch("/api/profile/reservations");
      renderProfileReservations(result.reservations || []);
    } catch (error) {
      if (reservationsStatus) {
        reservationsStatus.textContent = `Die Reservierungen konnten nicht geladen werden: ${error.message}`;
        reservationsStatus.className = "registration-status is-visible is-error";
      }
    }
  };

  authReady.then((profile) => {
    if (!profile) {
      window.location.href = "/login.html";
      return;
    }

    switchAccountPane("settings");
    fillProfileForm(profile);
    loadProfileReservations();
  });

  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const firstName = profileForm.elements.namedItem("firstName")?.value.trim() || "";
    const phone = profileForm.elements.namedItem("phone")?.value.trim() || "";

    if (!firstName) {
      setBoxStatus(profileStatus, "Bitte gib einen Vornamen an.", "error");
      return;
    }

    try {
      const result = await apiFetch("/api/profile", {
        method: "POST",
        body: JSON.stringify({ firstName, phone }),
      });

      fillProfileForm(result.guestProfile);
      renderAuthRail(result.guestProfile);
      setBoxStatus(profileStatus, "Dein Profil wurde erfolgreich gespeichert.", "success");
    } catch (error) {
      setBoxStatus(profileStatus, `Das Profil konnte nicht gespeichert werden: ${error.message}`, "error");
    }
  });

  changePasswordForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const currentPassword = changePasswordForm.elements.namedItem("currentPassword")?.value.trim() || "";
    const newPassword = changePasswordForm.elements.namedItem("newPassword")?.value.trim() || "";
    const newPasswordConfirm = changePasswordForm.elements.namedItem("newPasswordConfirm")?.value.trim() || "";

    if (!currentPassword || !newPassword || !newPasswordConfirm) {
      setBoxStatus(passwordStatus, "Bitte fülle alle Passwort-Felder aus.", "error");
      return;
    }

    try {
      await apiFetch("/api/profile/change-password", {
        method: "POST",
        body: JSON.stringify({
          currentPassword,
          newPassword,
          newPasswordConfirm,
        }),
      });

      changePasswordForm.reset();
      setBoxStatus(passwordStatus, "Dein Passwort wurde erfolgreich geändert.", "success");
    } catch (error) {
      setBoxStatus(passwordStatus, `Das Passwort konnte nicht geändert werden: ${error.message}`, "error");
    }
  });
}
const reservationApp = document.querySelector("[data-reservation-app]");

if (reservationApp) {
  const reservationForm = reservationApp.querySelector("[data-reservation-form]");
  const statusBox = reservationApp.querySelector("[data-reservation-status]");
  const roomsTarget = reservationApp.querySelector("[data-reservation-rooms]");
  const slotsTarget = reservationApp.querySelector("[data-reservation-slots]");
  const tablesTarget = reservationApp.querySelector("[data-reservation-tables]");
  const calendarTarget = document.querySelector("[data-reservation-calendar]");
  const calendarModal = document.querySelector("[data-reservation-calendar-modal]");
  const calendarOpenButton = reservationApp.querySelector("[data-calendar-open]");
  const calendarCloseButtons = document.querySelectorAll("[data-calendar-close]");
  const confirmationModal = document.querySelector("[data-reservation-confirmation-modal]");
  const confirmationCloseButtons = document.querySelectorAll("[data-confirmation-close]");
  const processingModal = document.querySelector("[data-reservation-processing-modal]");
  const selectedDateLabel = reservationApp.querySelector("[data-selected-date-label]");
  const selectedRoomLabel = reservationApp.querySelector("[data-selected-room]");
  const availabilitySummary = reservationApp.querySelector("[data-availability-summary]");
  const confirmationCode = document.querySelector("[data-confirmation-code]");
  const confirmationRoom = document.querySelector("[data-confirmation-room]");
  const confirmationTime = document.querySelector("[data-confirmation-time]");
  const confirmationTable = document.querySelector("[data-confirmation-table]");
  const confirmationMail = document.querySelector("[data-confirmation-mail]");
  const confirmationQr = document.querySelector("[data-confirmation-qr]");
  const confirmationCancel = document.querySelector("[data-confirmation-cancel]");

  let reservationConfig = null;
  let selectedRoomId = "";
  let selectedSlotKey = "";
  let selectedTableId = "";
  let calendarDays = [];

  const showReservationStatus = (message, kind = "success") => {
    if (!statusBox) {
      return;
    }
    statusBox.textContent = message;
    statusBox.className = `registration-status is-visible is-${kind}`;
  };

  const clearReservationStatus = () => {
    if (!statusBox) {
      return;
    }
    statusBox.textContent = "";
    statusBox.className = "registration-status";
  };

  const syncSelectedDateLabel = () => {
    if (!selectedDateLabel) {
      return;
    }
    const selectedDate = reservationForm.elements.namedItem("date")?.value || "";
    selectedDateLabel.textContent = selectedDate
      ? `Ausgewählt: ${selectedDate}`
      : "Bitte einen Tag auswählen.";
  };

  const openCalendarModal = () => {
    if (!calendarModal) {
      return;
    }
    calendarModal.hidden = false;
    document.body.classList.add("is-modal-open");
  };

  const closeCalendarModal = () => {
    if (!calendarModal) {
      return;
    }
    calendarModal.hidden = true;
    document.body.classList.remove("is-modal-open");
  };

  const openConfirmationModal = (reservation, room, mailStatus) => {
    if (!confirmationModal) {
      return;
    }
    if (confirmationCode) {
      confirmationCode.textContent = reservation.reservationCode || "–";
    }
    if (confirmationRoom) {
      confirmationRoom.textContent = room?.name || reservation.roomName || "–";
    }
    if (confirmationTime) {
      confirmationTime.textContent = reservation.scheduledLabel || `${reservation.date} · ${reservation.slotLabel || ""}`;
    }
    if (confirmationTable) {
      confirmationTable.textContent = reservation.tableLabel || reservation.tableId || "–";
    }
    if (confirmationMail) {
      confirmationMail.textContent =
        mailStatus === "failed"
          ? "Die Reservierung steht, aber die Bestätigungs-Mail konnte gerade nicht gesendet werden."
          : "Die Bestätigungs-Mail mit QR-Code ist unterwegs.";
    }
    if (confirmationQr) {
      confirmationQr.href = reservation.qrCodeUrl || "#";
    }
    if (confirmationCancel) {
      confirmationCancel.href = reservation.cancelUrl || "#";
    }
    confirmationModal.hidden = false;
    document.body.classList.add("is-modal-open");
  };

  const closeConfirmationModal = () => {
    if (!confirmationModal) {
      return;
    }
    confirmationModal.hidden = true;
    document.body.classList.remove("is-modal-open");
  };

  const openProcessingModal = () => {
    if (!processingModal) {
      return;
    }
    processingModal.hidden = false;
    document.body.classList.add("is-modal-open");
  };

  const closeProcessingModal = () => {
    if (!processingModal) {
      return;
    }
    processingModal.hidden = true;
    document.body.classList.remove("is-modal-open");
  };

  const currentRoom = () =>
    reservationConfig?.rooms?.find((room) => room.id === selectedRoomId) || null;

  const currentSlot = () =>
    reservationConfig?.slots?.find((slot) => slot.key === selectedSlotKey) || null;

  const renderRooms = () => {
    if (!roomsTarget || !reservationConfig) {
      return;
    }

    const orderedRooms = [...reservationConfig.rooms].sort((left, right) => {
      if (left.status === right.status) {
        return 0;
      }
      return left.status === "bookable" ? -1 : 1;
    });

    roomsTarget.innerHTML = orderedRooms
      .map((room) => {
        const isActive = room.id === selectedRoomId;
        const tags =
          room.status === "bookable"
            ? `<span class="reservation-room-pill">Buchbar</span>`
            : `<span class="reservation-room-pill is-muted">${escapeHtml(room.eventTableRange)}</span>`;

        return `
          <button
            class="reservation-room-card${isActive ? " is-active" : ""}"
            type="button"
            data-room-id="${escapeHtml(room.id)}"
          >
            <p class="card-kicker">${escapeHtml(room.name)}</p>
            <h3>${escapeHtml(room.tagline)}</h3>
            <p>${escapeHtml(room.theme)}</p>
            <div class="reservation-room-meta">
              ${tags}
              <span>${escapeHtml(room.defaultStatusNote)}</span>
            </div>
          </button>
        `;
      })
      .join("");

    roomsTarget.querySelectorAll("[data-room-id]").forEach((button) => {
      button.addEventListener("click", () => {
        selectedRoomId = button.dataset.roomId || "";
        selectedTableId = "";
        renderRooms();
        updateCalendar();
        updateAvailability();
      });
    });
  };

  const renderSlots = () => {
    if (!slotsTarget || !reservationConfig) {
      return;
    }

    slotsTarget.innerHTML = reservationConfig.slots
      .map(
        (slot) => `
          <button
            class="reservation-slot-button${slot.key === selectedSlotKey ? " is-active" : ""}"
            type="button"
            data-slot-key="${escapeHtml(slot.key)}"
          >
            ${escapeHtml(slot.label)}
          </button>
        `
      )
      .join("");

    slotsTarget.querySelectorAll("[data-slot-key]").forEach((button) => {
      button.addEventListener("click", () => {
        selectedSlotKey = button.dataset.slotKey || "";
        selectedTableId = "";
        renderSlots();
        updateCalendar();
        updateAvailability();
      });
    });
  };

  const renderTables = (tables, room) => {
    if (!tablesTarget) {
      return;
    }

    if (!room) {
      tablesTarget.innerHTML = `<p class="reservation-empty">Bitte zuerst einen Raum auswählen.</p>`;
      return;
    }

    if (room.status !== "bookable") {
      tablesTarget.innerHTML = `
        <div class="reservation-empty">
          <strong>${escapeHtml(room.name)}</strong><br />
          Dieser Raum ist aktuell für Veranstaltungen reserviert.
        </div>
      `;
      return;
    }

    if (!tables.length) {
      tablesTarget.innerHTML = `<p class="reservation-empty">Für diese Auswahl konnten keine Tische geladen werden.</p>`;
      return;
    }

    tablesTarget.innerHTML = tables
      .map((table) => {
        const isSelected = table.id === selectedTableId;
        const isDisabled = !table.isAvailable;
        const statusLabel =
          table.availability === "reserved"
            ? "Bereits reserviert"
            : table.availability === "capacity_mismatch"
              ? "Passt nicht zur Personenzahl"
              : "Frei";

        return `
          <button
            class="reservation-table-card${isSelected ? " is-active" : ""}"
            type="button"
            data-table-id="${escapeHtml(table.id)}"
            ${isDisabled ? "disabled" : ""}
          >
            <div class="reservation-table-head">
              <strong>${escapeHtml(table.label)}</strong>
              <span class="reservation-table-pill${table.isAvailable ? "" : " is-muted"}">${escapeHtml(statusLabel)}</span>
            </div>
            <p>${escapeHtml(table.kindLabel)} · ${escapeHtml(table.capacityMin)}-${escapeHtml(table.capacityMax)} Gäste</p>
            <p>${escapeHtml(table.description)}</p>
          </button>
        `;
      })
      .join("");

    tablesTarget.querySelectorAll("[data-table-id]").forEach((button) => {
      button.addEventListener("click", () => {
        selectedTableId = button.dataset.tableId || "";
        renderTables(tables, room);
      });
    });
  };

  const renderCalendar = () => {
    if (!calendarTarget || !calendarDays.length) {
      return;
    }

    const selectedDate = reservationForm.elements.namedItem("date")?.value || "";
    const weekdayLabels = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
    const firstCalendarDate = new Date(`${calendarDays[0].date}T00:00:00`);
    const leadingPadCount = (firstCalendarDate.getDay() + 6) % 7;
    const leadingPad = Array.from({ length: leadingPadCount }, () => `<span class="reservation-calendar-pad"></span>`).join("");

    calendarTarget.innerHTML = `
      <div class="reservation-calendar-weekdays">
        ${weekdayLabels.map((label) => `<span>${label}</span>`).join("")}
      </div>
      <div class="reservation-calendar-days">
        ${leadingPad}
        ${calendarDays
          .map((day) => {
            const [year, month, date] = day.date.split("-");
            const isActive = day.date === selectedDate;
            const isDisabled = !["available", "fully_booked"].includes(day.state);

            return `
              <button
                class="reservation-calendar-day is-${day.state}${isActive ? " is-active" : ""}"
                type="button"
                data-calendar-date="${escapeHtml(day.date)}"
                title="${escapeHtml(day.summary)}"
                ${isDisabled ? "disabled" : ""}
              >
                <strong>${escapeHtml(`${date}.${month}.`)}</strong>
                <span>${escapeHtml(day.summary)}</span>
                <small class="reservation-calendar-slots">
                  <span>1. Schicht: ${escapeHtml(String(day.slotCounts?.early ?? 0))}</span>
                  <span>2. Schicht: ${escapeHtml(String(day.slotCounts?.late ?? 0))}</span>
                </small>
              </button>
            `;
          })
          .join("")}
      </div>
    `;

    calendarTarget.querySelectorAll("[data-calendar-date]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextDate = button.dataset.calendarDate || "";
        reservationForm.elements.namedItem("date").value = nextDate;
        selectedTableId = "";
        syncSelectedDateLabel();
        renderCalendar();
        updateAvailability();
        closeCalendarModal();
      });
    });
  };

  const updateCalendar = async () => {
    if (!reservationConfig || !calendarTarget) {
      return;
    }

    try {
      const guests = reservationForm.elements.namedItem("guests")?.value || "";
      const result = await apiFetch(
        `/api/reservations/calendar?start=${encodeURIComponent(reservationConfig.minDate)}&days=28&slotKey=${encodeURIComponent(selectedSlotKey)}&roomId=${encodeURIComponent(selectedRoomId)}&guests=${encodeURIComponent(guests)}`,
        { auth: false }
      );
      calendarDays = result.days;
      syncSelectedDateLabel();
      renderCalendar();
    } catch (error) {
      calendarTarget.innerHTML = `<div class="reservation-empty">${escapeHtml(error.message)}</div>`;
    }
  };

  const updateAvailability = async () => {
    const room = currentRoom();
    const slot = currentSlot();
    const date = reservationForm.elements.namedItem("date")?.value || "";
    const guests = reservationForm.elements.namedItem("guests")?.value || "";

    selectedRoomLabel.textContent = room
      ? `${room.name} · ${room.status === "bookable" ? "individuell buchbar" : "für Events blockiert"}`
      : "Bitte einen Raum auswählen.";

    if (!room || !slot || !date || !guests) {
      availabilitySummary.textContent = "Bitte Datum, Personenanzahl, Slot und Raum auswählen.";
      renderTables([], room);
      return;
    }

    if (room.status !== "bookable") {
      availabilitySummary.textContent = `${room.name} ist standardmäßig durch Veranstaltungen blockiert.`;
      renderTables([], room);
      return;
    }

    try {
      const result = await apiFetch(
        `/api/reservations/availability?date=${encodeURIComponent(date)}&slotKey=${encodeURIComponent(selectedSlotKey)}&roomId=${encodeURIComponent(selectedRoomId)}&guests=${encodeURIComponent(guests)}`,
        { auth: false }
      );
      const freeCount = result.tables.filter((table) => table.isAvailable).length;
      availabilitySummary.textContent =
        freeCount > 0
          ? `${freeCount} Tisch(e) sind für ${date} im Slot ${slot.label} frei.`
          : `Für ${date} im Slot ${slot.label} ist kein passender Tisch mehr frei.`;
      renderTables(result.tables, room);
    } catch (error) {
      availabilitySummary.textContent = error.message;
      renderTables([], room);
    }
  };

  const applyReservationConfig = (config) => {
    reservationConfig = config;
    selectedRoomId = config.rooms.find((room) => room.status === "bookable")?.id || config.rooms[0]?.id || "";
    selectedSlotKey = config.slots[0]?.key || "";
    selectedTableId = "";

    const dateInput = reservationForm.elements.namedItem("date");
    if (dateInput) {
      dateInput.min = config.minDate;
      dateInput.max = config.maxDate;
      dateInput.value = config.minDate;
    }

    syncSelectedDateLabel();
    renderRooms();
    renderSlots();
    updateCalendar();
    updateAvailability();
  };

  ["date", "guests"].forEach((fieldName) => {
    reservationForm.elements.namedItem(fieldName)?.addEventListener("change", () => {
      selectedTableId = "";
      if (fieldName === "guests") {
        updateCalendar();
      } else {
        syncSelectedDateLabel();
        renderCalendar();
      }
      updateAvailability();
    });
  });

  calendarOpenButton?.addEventListener("click", () => {
    openCalendarModal();
  });

  calendarCloseButtons.forEach((button) => {
    button.addEventListener("click", () => {
      closeCalendarModal();
    });
  });

  confirmationCloseButtons.forEach((button) => {
    button.addEventListener("click", () => {
      closeConfirmationModal();
    });
  });

  reservationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearReservationStatus();
    openProcessingModal();

    const room = currentRoom();
    const slot = currentSlot();
    const payload = {
      name: reservationForm.elements.namedItem("name")?.value.trim() || "",
      email: reservationForm.elements.namedItem("email")?.value.trim() || "",
      phone: reservationForm.elements.namedItem("phone")?.value.trim() || "",
      date: reservationForm.elements.namedItem("date")?.value || "",
      guests: reservationForm.elements.namedItem("guests")?.value || "",
      occasion: reservationForm.elements.namedItem("occasion")?.value || "",
      notes: reservationForm.elements.namedItem("notes")?.value.trim() || "",
      roomId: selectedRoomId,
      slotKey: selectedSlotKey,
      tableId: selectedTableId,
    };

    if (!room || !slot) {
      closeProcessingModal();
      showReservationStatus("Bitte Raum und Zeitslot auswählen.", "error");
      return;
    }

    if (!selectedTableId) {
      closeProcessingModal();
      showReservationStatus("Bitte einen freien Tisch auswählen.", "error");
      return;
    }

    try {
      const result = await apiFetch("/api/reservations", {
        method: "POST",
        body: JSON.stringify(payload),
        auth: false,
      });

      const reservation = result.reservation;
      const mailHint =
        result.mailStatus === "failed"
          ? " Die Reservierung steht, aber die Bestätigungs-Mail konnte gerade nicht gesendet werden."
          : " Die Bestätigungs-Mail mit QR-Code ist unterwegs.";
      showReservationStatus(
        `Reservierung ${reservation.reservationCode} aufgenommen: ${room.name}, ${slot.label}, ${reservation.date}.${mailHint}`,
        "success"
      );
      closeProcessingModal();
      openConfirmationModal(reservation, room, result.mailStatus);
      reservationForm.reset();
      reservationForm.elements.namedItem("guests").value = "2";
      reservationForm.elements.namedItem("date").value = reservationConfig.minDate;
      selectedTableId = "";
      updateCalendar();
      updateAvailability();
    } catch (error) {
      closeProcessingModal();
      showReservationStatus(`Die Reservierung konnte nicht erstellt werden: ${error.message}`, "error");
    }
  });

  authReady.then((profile) => {
    if (!profile || !reservationForm) {
      return;
    }
    reservationForm.elements.namedItem("name").value = profile.firstName || "";
    reservationForm.elements.namedItem("email").value = profile.email || "";
    reservationForm.elements.namedItem("phone").value = profile.phone || "";
  });

  apiFetch("/api/reservations/config", { auth: false })
    .then((result) => applyReservationConfig(result.config))
    .catch((error) => {
      showReservationStatus(`Die Reservierungskonfiguration konnte nicht geladen werden: ${error.message}`, "error");
    });
}

