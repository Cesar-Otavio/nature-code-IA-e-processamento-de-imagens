const infoIcon = document.getElementById("infoIcon");
const modalOverlay = document.getElementById("modalOverlay");
const modalContent = document.getElementById("modalContent");
const closeBtn = document.getElementById("closeBtn");

// Abrir modal
infoIcon.addEventListener("click", () => {
  modalOverlay.classList.add("active");
});

// Fechar modal ao clicar no botão X
closeBtn.addEventListener("click", () => {
  modalOverlay.classList.remove("active");
});

// Fechar modal ao clicar fora do conteúdo
modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) {
    modalOverlay.classList.remove("active");
  }
});

// Fechar modal com a tecla ESC
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && modalOverlay.classList.contains("active")) {
    modalOverlay.classList.remove("active");
  }
});

// Prevenir fechamento ao clicar dentro do modal
modalContent.addEventListener("click", (e) => {
  e.stopPropagation();
});
