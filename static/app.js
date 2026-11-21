(function () {
  const data = window.OPENCOPACK_LISTINGS;
  if (!data) return;
  const q = document.getElementById("q");
  const state = document.getElementById("state");
  const category = document.getElementById("category");
  const cert = document.getElementById("cert");
  const moq = document.getElementById("moq");
  const startup = document.getElementById("startup");
  const grid = document.getElementById("results");
  const count = document.getElementById("count");
  const cards = Array.from(grid.querySelectorAll("[data-card]"));

  function val(el) { return (el && el.value || "").trim().toLowerCase(); }

  function match(card) {
    const hay = (card.getAttribute("data-hay") || "");
    const st = card.getAttribute("data-state") || "";
    const cats = (card.getAttribute("data-cats") || "").split(" ");
    const certs = (card.getAttribute("data-certs") || "").split("|");
    const hasMoq = card.getAttribute("data-moq") === "1";
    const isStart = card.getAttribute("data-start") === "1";
    const query = val(q);
    if (query && !hay.includes(query)) return false;
    if (val(state) && st !== val(state)) return false;
    if (val(category) && !cats.includes(val(category))) return false;
    if (val(cert) && !certs.includes(cert.value)) return false;
    if (moq && moq.checked && !hasMoq) return false;
    if (startup && startup.checked && !isStart) return false;
    return true;
  }

  function run() {
    let n = 0;
    cards.forEach((card) => {
      const ok = match(card);
      card.classList.toggle("hidden", !ok);
      if (ok) n += 1;
    });
    if (count) {
      count.textContent = n === data.total
        ? n + " plants in the directory"
        : n + " of " + data.total + " plants match";
    }
  }

  ["input", "change"].forEach((ev) => {
    [q, state, category, cert, moq, startup].forEach((el) => {
      if (el) el.addEventListener(ev, run);
    });
  });
  run();
})();
