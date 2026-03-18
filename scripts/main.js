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

  document.body.classList.add("has-auth-rail");

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

  document.body.prepend(rail);

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

  const setBoxStatus = (box, message, kind = "success") => {
    if (!box) {
      return;
    }
    box.textContent = message;
    box.className = `registration-status is-visible is-${kind}`;
  };

  const fillProfileForm = (profile) => {
    profileForm.elements.namedItem("firstName").value = profile.firstName || "";
    profileForm.elements.namedItem("email").value = profile.email || "";
    profileForm.elements.namedItem("phone").value = profile.phone || "";
  };
  const reservationsStatus = document.querySelector("[data-profile-reservations-status]");
  const reservationsTarget = document.querySelector("[data-profile-reservations]");

  const renderProfileReservations = (reservations) => {
    if (!reservationsTarget) {
      return;
    }

    if (!reservations.length) {
      reservationsTarget.innerHTML = '<div class="profile-empty">Noch keine Reservierungen mit diesem Gastprofil verknüpft.</div>';
      return;
    }

    reservationsTarget.innerHTML = reservations
      .map((reservation) => {
        const isCancelled = reservation.status === "cancelled";
        const cancelAction = !isCancelled && reservation.cancelUrl
          ? `<a class="button button-primary" href="${escapeHtml(reservation.cancelUrl)}" target="_blank" rel="noreferrer">Reservierung verwalten</a>`
          : "";

        return `
          <article class="profile-reservation-card">
            <div class="profile-reservation-head">
              <div>
                <p class="card-kicker">${escapeHtml(reservation.roomName)}</p>
                <h3>${escapeHtml(reservation.scheduledLabel)}</h3>
              </div>
              <span class="profile-reservation-status${isCancelled ? " is-cancelled" : ""}">${escapeHtml(reservation.status)}</span>
            </div>
            <div class="profile-reservation-meta">
              <p><strong>Code</strong><br /><span>${escapeHtml(reservation.reservationCode)}</span></p>
              <p><strong>Tisch</strong><br /><span>${escapeHtml(reservation.tableLabel)}</span></p>
              <p><strong>Personen</strong><br /><span>${escapeHtml(String(reservation.guests))}</span></p>
              <p><strong>Anlass</strong><br /><span>${escapeHtml(reservation.occasion || "Kein Anlass hinterlegt")}</span></p>
            </div>
            <p class="profile-reservation-copy">${escapeHtml(reservation.notes || "Keine Zusatznotizen hinterlegt.")}</p>
            <div class="profile-reservation-actions">
              <a class="button button-secondary" href="${escapeHtml(reservation.qrCodeUrl)}" target="_blank" rel="noreferrer">QR öffnen</a>
              ${cancelAction}
            </div>
          </article>
        `;
      })
      .join("");
  };

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
