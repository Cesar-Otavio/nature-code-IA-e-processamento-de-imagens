const canvas = document.getElementById("particles");
const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

window.addEventListener("resize", () => {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
});

const PARTICLE_COUNT = 70;
const particles = [];

const colors = [
  "rgba(29, 209, 161, 0.6)",  // ciano/turquesa — cor do quiz
  "rgba(76, 175, 80, 0.5)",   // verde médio
  "rgba(74, 144, 226, 0.5)",  // azul médio
  "rgba(0, 255, 136, 0.4)",   // verde neon suave
  "rgba(100, 160, 255, 0.4)", // azul claro
];

class Particle {
  constructor() {
    this.reset();
  }

  reset() {
    this.x = Math.random() * canvas.width;
    this.y = Math.random() * canvas.height;
    this.size = Math.random() * 2.5 + 0.5;
    this.speedX = (Math.random() - 0.5) * 0.5;
    this.speedY = (Math.random() - 0.5) * 0.5;
    this.color = colors[Math.floor(Math.random() * colors.length)];
    this.pulse = Math.random() * Math.PI * 2;
  }

  update() {
    this.x += this.speedX;
    this.y += this.speedY;
    this.pulse += 0.02;
    this.opacity = 0.15 + Math.abs(Math.sin(this.pulse)) * 0.45;

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

for (let i = 0; i < PARTICLE_COUNT; i++) {
  particles.push(new Particle());
}

function drawConnections() {
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x;
      const dy = particles[i].y - particles[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < 100) {
        ctx.beginPath();
        ctx.moveTo(particles[i].x, particles[i].y);
        ctx.lineTo(particles[j].x, particles[j].y);

        // linha azul ou verde dependendo das partículas
        const isBlue = particles[i].color.includes("144") || particles[j].color.includes("144");
        ctx.strokeStyle = isBlue
          ? `rgba(74, 144, 226, ${0.12 * (1 - dist / 100)})`
          : `rgba(29, 209, 161, ${0.12 * (1 - dist / 100)})`;
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }
    }
  }
}

function animate() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Fundo gradiente radial azul escuro
  const gradient = ctx.createRadialGradient(
    canvas.width / 2, canvas.height / 2, 0,
    canvas.width / 2, canvas.height / 2, canvas.width * 0.8
  );
  gradient.addColorStop(0, "#1e2d45");
  gradient.addColorStop(0.5, "#151e2e");
  gradient.addColorStop(1, "#0a0f1a");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  drawConnections();
  particles.forEach((p) => { p.update(); p.draw(); });

  requestAnimationFrame(animate);
}

animate();