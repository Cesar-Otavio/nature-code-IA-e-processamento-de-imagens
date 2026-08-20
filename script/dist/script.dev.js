"use strict";

document.addEventListener("DOMContentLoaded", function () {
  var carousel = document.querySelector('#cardsCarousel');
  var background = document.querySelector('#carouselBackground');

  function updateBackground() {
    var activeItem = carousel.querySelector('.carousel-item.active');
    var bgImage = activeItem.getAttribute('data-bg');
    background.style.backgroundImage = "url('".concat(bgImage, "')");
  } // Atualiza o fundo ao iniciar


  updateBackground(); // Escuta evento de mudança de slide do Bootstrap

  carousel.addEventListener('slid.bs.carousel', updateBackground);
});