// =====================
// QUIZ ENGINE
// =====================

// =====================
// MODAIS CUSTOMIZADOS
// =====================
function showModal({
  icon = "✅",
  title,
  message,
  confirmText = "OK",
  cancelText = null,
  onConfirm,
  onCancel,
}) {
  const overlay = document.createElement("div");
  overlay.className = "confirm-modal-overlay";
  overlay.innerHTML = `
    <div class="confirm-modal-box">
      <div class="confirm-modal-icon">${icon}</div>
      <div class="confirm-modal-title">${title}</div>
      <div class="confirm-modal-message">${message}</div>
      <div class="confirm-modal-buttons">
        ${cancelText ? `<button class="confirm-modal-btn confirm-modal-btn-cancel">${cancelText}</button>` : ""}
        <button class="confirm-modal-btn confirm-modal-btn-confirm">${confirmText}</button>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector(".confirm-modal-btn-confirm").addEventListener("click", () => {
    overlay.remove();
    if (onConfirm) onConfirm();
  });

  if (cancelText) {
    overlay.querySelector(".confirm-modal-btn-cancel").addEventListener("click", () => {
      overlay.remove();
      if (onCancel) onCancel();
    });
  }
}

let currentQuestion = 0;
let userAnswers = {};
let quizSubmitted = false;

function loadProgress() {
  try {
    const saved = localStorage.getItem("quizProgress");
    return saved ? JSON.parse(saved) : { topics: {} };
  } catch (e) {
    return { topics: {} };
  }
}

function saveProgress(topicId, answers, submitted = false) {
  try {
    const progress = loadProgress();
    progress.topics[topicId] = {
      topicName: quizData[0].title,
      totalQuestions: quizData.length,
      answers,
      submitted,
      completedAt: submitted ? new Date().toISOString() : null,
      progress: (Object.keys(answers).length / quizData.length) * 100,
    };
    localStorage.setItem("quizProgress", JSON.stringify(progress));
  } catch (e) {
    console.error("Erro ao salvar:", e);
  }
}

function loadSavedAnswers() {
  try {
    const topicId = getTopicId();
    const saved = loadProgress().topics[topicId];
    if (saved) {
      userAnswers = saved.answers || {};
      quizSubmitted = saved.submitted || false;
    }
  } catch (e) {
    console.error("Erro ao carregar:", e);
  }
}

function getTopicId() {
  return quizData[0].title.toLowerCase().replace(/\s+/g, "_");
}

function scrollQuizToTop() {
  const container = document.querySelector(".div2 .quiz-container");
  if (container) container.scrollTo(0, 0);
}

function renderQuestion() {
  const question = quizData[currentQuestion];
  const questionTypeEl = document.getElementById("questionTypeText");
  const questionTitleEl = document.getElementById("questionTitle");
  const explanationEl = document.getElementById("explanation");
  const explanationTextEl = document.getElementById("explanationText");
  const optionsContainerEl = document.getElementById("optionsContainer");
  const trueFalseContainerEl = document.getElementById("trueFalseContainer");
  const progressInfoEl = document.getElementById("progressInfo");
  const progressFillEl = document.getElementById("progressFill");
  const nextBtnEl = document.getElementById("nextBtn");
  const prevBtnEl = document.getElementById("prevBtn");
  const nextNavBtnEl = document.getElementById("nextNavBtn");
  const quizTitleEl = document.getElementById("quizTitle");
  const scoreEl = document.getElementById("score");

  quizTitleEl.textContent = question.title;
  scoreEl.textContent = `${currentQuestion + 1}/${quizData.length}`;
  progressInfoEl.textContent = `Questão ${currentQuestion + 1} de ${quizData.length}`;
  progressFillEl.style.width =
    ((currentQuestion + 1) / quizData.length) * 100 + "%";
  questionTitleEl.textContent = question.question;
  explanationTextEl.textContent = question.explanation;
  explanationEl.classList.remove("show");
  prevBtnEl.disabled = currentQuestion === 0;
  nextNavBtnEl.disabled = currentQuestion === quizData.length - 1;

  if (quizSubmitted) {
    explanationEl.classList.add("show");
    nextBtnEl.textContent = "Próximo";
    nextBtnEl.disabled = currentQuestion === quizData.length - 1;
  } else if (currentQuestion === quizData.length - 1) {
    nextBtnEl.textContent = "Enviar Respostas";
    nextBtnEl.disabled = Object.keys(userAnswers).length < quizData.length;
  } else {
    nextBtnEl.textContent = "Próximo";
    nextBtnEl.disabled = false;
  }

  if (question.type === "multiple") {
    questionTypeEl.textContent = "Escolha múltipla";
    renderMultipleChoice(question);
    trueFalseContainerEl.style.display = "none";
    optionsContainerEl.style.display = "flex";
  } else {
    questionTypeEl.textContent = "Verdadeiro ou Falso";
    renderTrueFalse(question);
    optionsContainerEl.style.display = "none";
    trueFalseContainerEl.style.display = "flex";
  }
}

function renderMultipleChoice(question) {
  const optionsContainerEl = document.getElementById("optionsContainer");
  const nextBtnEl = document.getElementById("nextBtn");
  optionsContainerEl.innerHTML = "";
  const savedAnswer = userAnswers[currentQuestion];

  question.options.forEach((option, index) => {
    const optionEl = document.createElement("div");
    optionEl.className = "option";

    if (quizSubmitted) {
      if (option.correct) {
        optionEl.classList.add("correct");
        optionEl.innerHTML = `
          <div class="option-letter">${String.fromCharCode(65 + index)}</div>
          <div class="option-text">${option.text}</div>
          <span class="check-icon" style="display:block;">✓</span>
        `;
      } else if (savedAnswer === index) {
        optionEl.classList.add("incorrect");
        optionEl.innerHTML = `
          <div class="option-letter">${String.fromCharCode(65 + index)}</div>
          <div class="option-text">${option.text}</div>
          <span class="check-icon" style="display:block; color:#ff6b6b;">✗</span>
        `;
      } else {
        optionEl.innerHTML = `
          <div class="option-letter">${String.fromCharCode(65 + index)}</div>
          <div class="option-text">${option.text}</div>
          <span class="check-icon"></span>
        `;
      }
    } else {
      if (savedAnswer === index) optionEl.classList.add("selected");
      optionEl.innerHTML = `
        <div class="option-letter">${String.fromCharCode(65 + index)}</div>
        <div class="option-text">${option.text}</div>
        <span class="check-icon">✓</span>
      `;
      optionEl.addEventListener("click", () => {
        document
          .querySelectorAll("#optionsContainer .option")
          .forEach((o) => o.classList.remove("selected"));
        optionEl.classList.add("selected");
        userAnswers[currentQuestion] = index;
        saveProgress(getTopicId(), userAnswers, false);
        if (currentQuestion === quizData.length - 1)
          nextBtnEl.disabled =
            Object.keys(userAnswers).length < quizData.length;
      });
    }

    optionsContainerEl.appendChild(optionEl);
  });
} // <-- fecha renderMultipleChoice

function renderTrueFalse(question) {
  const trueFalseContainerEl = document.getElementById("trueFalseContainer");
  const nextBtnEl = document.getElementById("nextBtn");
  trueFalseContainerEl.innerHTML = "";
  const savedAnswer = userAnswers[currentQuestion];

  const trueBtn = document.createElement("button");
  trueBtn.type = "button";
  trueBtn.className = "true-false-btn";
  trueBtn.innerHTML = `<span class="true-false-btn-icon">✓</span><span>Verdadeiro</span>`;

  const falseBtn = document.createElement("button");
  falseBtn.type = "button";
  falseBtn.className = "true-false-btn";
  falseBtn.innerHTML = `<span class="true-false-btn-icon">✕</span><span>Falso</span>`;

  if (quizSubmitted) {
    if (question.correct === true) {
      trueBtn.classList.add("correct-true");
      trueBtn.innerHTML = `
      <span class="true-false-btn-icon">✓</span>
      <span>Verdadeiro</span>
      <span class="check-icon" style="display:block; color:#00ff88;">✓</span>
    `;
      if (savedAnswer === false) {
        falseBtn.classList.add("incorrect-false");
        falseBtn.innerHTML = `
        <span class="true-false-btn-icon">✕</span>
        <span>Falso</span>
        <span class="check-icon" style="display:block; color:#ff6b6b;">✗</span>
      `;
      }
    } else {
      falseBtn.classList.add("correct-false");
      falseBtn.innerHTML = `
      <span class="true-false-btn-icon">✕</span>
      <span>Falso</span>
      <span class="check-icon" style="display:block; color:#00ff88;">✓</span>
    `;
      if (savedAnswer === true) {
        trueBtn.classList.add("incorrect-true");
        trueBtn.innerHTML = `
        <span class="true-false-btn-icon">✓</span>
        <span>Verdadeiro</span>
        <span class="check-icon" style="display:block; color:#ff6b6b;">✗</span>
      `;
      }
    }
  } else {
    if (savedAnswer === true) trueBtn.classList.add("selected-true");
    else if (savedAnswer === false) falseBtn.classList.add("selected-false");

    trueBtn.addEventListener("click", () => {
      falseBtn.classList.remove("selected-false");
      trueBtn.classList.add("selected-true");
      userAnswers[currentQuestion] = true;
      saveProgress(getTopicId(), userAnswers, false);
      if (currentQuestion === quizData.length - 1)
        nextBtnEl.disabled = Object.keys(userAnswers).length < quizData.length;
    });

    falseBtn.addEventListener("click", () => {
      trueBtn.classList.remove("selected-true");
      falseBtn.classList.add("selected-false");
      userAnswers[currentQuestion] = false;
      saveProgress(getTopicId(), userAnswers, false);
      if (currentQuestion === quizData.length - 1)
        nextBtnEl.disabled = Object.keys(userAnswers).length < quizData.length;
    });
  }

  trueFalseContainerEl.appendChild(trueBtn);
  trueFalseContainerEl.appendChild(falseBtn);
}

function submitQuiz() {
  quizSubmitted = true;
  saveProgress(getTopicId(), userAnswers, true);
  let correct = 0;
  quizData.forEach((question, index) => {
    const userAnswer = userAnswers[index];
    if (question.type === "multiple") {
      if (question.options[userAnswer]?.correct) correct++;
    } else {
      if (userAnswer === question.correct) correct++;
    }
  });

  showModal({
    icon: correct === quizData.length ? "🏆" : correct === 0 ? "😅" : "📊",
    title: "Quiz finalizado!",
    message: `Você acertou <span>${correct} de ${quizData.length}</span> questões.<br>Agora você pode revisar suas respostas.`,
    confirmText: "Ver respostas",
    onConfirm: () => {
      currentQuestion = 0;
      renderQuestion();
    },
  });
}

// =====================
// EVENT LISTENERS
// =====================
document.getElementById("nextBtn").addEventListener("click", () => {
  if (currentQuestion === quizData.length - 1 && !quizSubmitted) {
    submitQuiz();
  } else if (currentQuestion < quizData.length - 1) {
    currentQuestion++;
    renderQuestion();
    scrollQuizToTop();
  }
});

document.getElementById("prevBtn").addEventListener("click", () => {
  if (currentQuestion > 0) {
    currentQuestion--;
    renderQuestion();
    scrollQuizToTop();
  }
});

document.getElementById("nextNavBtn").addEventListener("click", () => {
  if (currentQuestion < quizData.length - 1) {
    currentQuestion++;
    renderQuestion();
    scrollQuizToTop();
  }
});

document.querySelector(".quiz-back-btn").addEventListener("click", () => {
  alert("Voltar ao tópico");
});

document.getElementById("resetBtn").addEventListener("click", () => {
  showModal({
    icon: "⚠️",
    title: "Resetar quiz?",
    message: "Seu progresso será perdido e você começará do zero.",
    confirmText: "Sim, resetar",
    cancelText: "Cancelar",
    onConfirm: () => {
      localStorage.removeItem("quizProgress");
      currentQuestion = 0;
      userAnswers = {};
      quizSubmitted = false;
      renderQuestion();
      scrollQuizToTop();
    }
  });
});

// Iniciar
loadSavedAnswers();
renderQuestion();
