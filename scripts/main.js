const revealItems = document.querySelectorAll(".hero-copy, .hero-card, .section");

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
      }
    });
  },
  { threshold: 0.18 }
);

revealItems.forEach((item) => {
  item.classList.add("reveal");
  revealObserver.observe(item);
});

