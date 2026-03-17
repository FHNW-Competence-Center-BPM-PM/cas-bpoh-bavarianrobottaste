const currentPagePath = window.location.pathname.split("/").pop() || "index.html";
const isHomePage = currentPagePath === "index.html" || currentPagePath === "";

const headerTarget = document.querySelector("[data-site-header]");
const footerTarget = document.querySelector("[data-site-footer]");

const navigationItems = [
  { href: "index.html", label: "Start" },
  { href: "menu.html", label: "Menü" },
  { href: "drinks.html", label: "Getränke" },
  { href: "stories.html", label: "Stories" },
  { href: "reservation.html", label: "Reservierung" },
  { href: "contact.html", label: "Kontakt" },
  { href: "impressum.html", label: "Impressum" },
];

if (headerTarget) {
  const navMarkup = navigationItems
    .map(({ href, label }) => {
      const isActive = currentPagePath === href;
      return `<a${isActive ? ' class="is-active"' : ""} href="${href}">${label}</a>`;
    })
    .join("");

  headerTarget.innerHTML = `
    <a class="brand" href="index.html">
      <img
        class="brand-mark${isHomePage ? " brand-mark-large" : ""}"
        src="assets/logo/bavarian-robotaste-logo.svg"
        alt="Logo von Bavarian RoboTaste"
      />
    </a>
    <nav class="site-nav" aria-label="Hauptnavigation">
      ${navMarkup}
    </nav>
  `;
}

if (footerTarget) {
  footerTarget.innerHTML = `
    <div>
      <strong>Bavarian RoboTaste</strong>
      <p>Future Bavarian Dining für Kontakt und rechtliche Informationen.</p>
    </div>
    <div class="footer-links">
      <a href="contact.html">Kontakt</a>
      <a href="impressum.html">Impressum</a>
    </div>
  `;
}
