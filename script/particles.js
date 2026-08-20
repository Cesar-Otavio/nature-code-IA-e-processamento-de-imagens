const canvas = document.getElementById("particles");
const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

window.addEventListener("resize", () => {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
});

const PARTICLE_COUNT = 80;
const particles = [];

const colors = [
  "rgba(76, 175, 80, 0.6)", // verde médio
  "rgba(29, 209, 161, 0.5)", // verde água
  "rgba(102, 187, 106, 0.4)", // verde claro
  "rgba(27, 67, 50, 0.8)", // verde escuro
];

class Particle {
  constructor() {
    this.reset();
  }

  reset() {
    this.x = Math.random() * canvas.width;
    this.y = Math.random() * canvas.height;
    this.size = Math.random() * 3 + 1;
    this.speedX = (Math.random() - 0.5) * 0.6;
    this.speedY = (Math.random() - 0.5) * 0.6;
    this.color = colors[Math.floor(Math.random() * colors.length)];
    this.opacity = Math.random() * 0.5 + 0.2;
    this.pulse = Math.random() * Math.PI * 2; // fase aleatória do pulso
  }

  update() {
    this.x += this.speedX;
    this.y += this.speedY;
    this.pulse += 0.02;
    this.opacity = 0.2 + Math.abs(Math.sin(this.pulse)) * 0.5;

    // Rebate nas bordas
    if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
    if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
  }

  draw() {
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
    ctx.fillStyle = this.color;
    ctx.globalAlpha = this.opacity;
    ctx.fill();
    ctx.globalAlpha = 1;
  }
}

// Cria partículas
for (let i = 0; i < PARTICLE_COUNT; i++) {
  particles.push(new Particle());
}

// Desenha linhas entre partículas próximas
function drawConnections() {
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x;
      const dy = particles[i].y - particles[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < 120) {
        ctx.beginPath();
        ctx.moveTo(particles[i].x, particles[i].y);
        ctx.lineTo(particles[j].x, particles[j].y);
        ctx.strokeStyle = `rgba(76, 175, 80, ${0.15 * (1 - dist / 120)})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }
    }
  }
}

function animate() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Fundo gradiente escuro
  // Troca o gradiente linear por um radial
  const gradient = ctx.createRadialGradient(
    canvas.width / 2,
    canvas.height / 2,
    0, // centro
    canvas.width / 2,
    canvas.height / 2,
    canvas.width * 0.8, // borda
  );
  gradient.addColorStop(0, "#1a3a2a"); // verde escuro no centro
  gradient.addColorStop(0.5, "#0f2419"); // verde mais escuro no meio
  gradient.addColorStop(1, "#060e0a"); // quase preto nas bordas
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  drawConnections();

  particles.forEach((p) => {
    p.update();
    p.draw();
  });

  requestAnimationFrame(animate);
}

animate();
