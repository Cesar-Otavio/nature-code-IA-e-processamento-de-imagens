document.addEventListener("DOMContentLoaded", function () {
  const carousel = document.querySelector("#cardsCarousel");
  const background = document.querySelector("#carouselBackground");

  // Só executa se os dois elementos existirem e o background estiver visível
  if (!carousel || !background || background.style.display === "none") return;

  function updateBackground() {
    const activeItem = carousel.querySelector(".carousel-item.active");
    const bgImage = activeItem.getAttribute("data-bg");
    background.style.backgroundImage = `url('${bgImage}')`;
  }

  updateBackground();
  carousel.addEventListener("slid.bs.carousel", updateBackground);
});