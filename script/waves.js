const canvas = document.getElementById("waves");
const ctx = canvas.getContext("2d");

canvas.width = window.innerWidth;
canvas.height = window.innerHeight;

window.addEventListener("resize", () => {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  initStars();
});

const STAR_COUNT = 180;
const CONSTELLATION_DISTANCE = 120;
const stars = [];

class Star {
  constructor() {
    this.reset(true);
  }

  reset(randomPos = false) {
    this.x = randomPos ? Math.random() * canvas.width : Math.random() * canvas.width;
    this.y = randomPos ? Math.random() * canvas.height : -10;
    this.size = Math.random() * 2 + 0.5;
    this.speedX = (Math.random() - 0.5) * 0.3;
    this.speedY = (Math.random() - 0.5) * 0.3;
    this.pulse = Math.random() * Math.PI * 2;
    this.pulseSpeed = 0.01 + Math.random() * 0.02;
    this.isBright = Math.random() < 0.08;

    const colors = [
      [29, 209, 161],
      [76, 175, 80],
      [74, 144, 226],
      [200, 220, 255],
      [150, 255, 200],
    ];
    this.color = colors[Math.floor(Math.random() * colors.length)];
  }

  update() {
    this.pulse += this.pulseSpeed;
    this.x += this.speedX;
    this.y += this.speedY;

    // Rebate nas bordas suavemente
    if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
    if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
  }

  draw() {
    const alpha = 0.4 + Math.sin(this.pulse) * 0.3;
    const [r, g, b] = this.color;

    if (this.isBright) {
      const size = this.size * 3;
      ctx.save();
      ctx.translate(this.x, this.y);

      const glow = ctx.createRadialGradient(0, 0, 0, 0, 0, size * 4);
      glow.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${alpha * 0.6})`);
      glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(0, 0, size * 4, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
      ctx.lineWidth = 0.8;
      for (let i = 0; i < 4; i++) {
        ctx.beginPath();
        ctx.moveTo(0, 0);
        const angle = (i * Math.PI) / 2;
        ctx.lineTo(Math.cos(angle) * size * 2.5, Math.sin(angle) * size * 2.5);
        ctx.stroke();
      }

      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
      ctx.beginPath();
      ctx.arc(0, 0, size * 0.8, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    } else {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
      ctx.fill();
    }
  }
}

function initStars() {
  stars.length = 0;
  for (let i = 0; i < STAR_COUNT; i++) {
    stars.push(new Star());
  }
}

function drawConstellationLines() {
  for (let i = 0; i < stars.length; i++) {
    for (let j = i + 1; j < stars.length; j++) {
      const dx = stars[i].x - stars[j].x;
      const dy = stars[i].y - stars[j].y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist < CONSTELLATION_DISTANCE) {
        const alpha = (1 - dist / CONSTELLATION_DISTANCE) * 0.3;
        const [r, g, b] = stars[i].color;
        ctx.beginPath();
        ctx.moveTo(stars[i].x, stars[i].y);
        ctx.lineTo(stars[j].x, stars[j].y);
        ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
        ctx.lineWidth = 0.6;
        ctx.stroke();
      }
    }
  }
}

let time = 0;

function drawBackground() {
  time += 0.005;

  // Fundo base mais claro e dinâmico
  const gradient = ctx.createRadialGradient(
    canvas.width * (0.4 + Math.sin(time) * 0.1),
    canvas.height * (0.4 + Math.cos(time * 0.7) * 0.1),
    0,
    canvas.width * 0.5,
    canvas.height * 0.5,
    canvas.width * 0.9
  );
  gradient.addColorStop(0, "#152535");   // azul mais claro no centro
  gradient.addColorStop(0.4, "#0e1e2a"); // transição
  gradient.addColorStop(1, "#060f14");   // escuro nas bordas
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Névoa verde pulsando
  const nebula1 = ctx.createRadialGradient(
    canvas.width * (0.6 + Math.sin(time * 0.8) * 0.15),
    canvas.height * (0.3 + Math.cos(time * 0.6) * 0.15),
    0,
    canvas.width * 0.6,
    canvas.height * 0.3,
    canvas.width * 0.45
  );
  nebula1.addColorStop(0, `rgba(20, 80, 50, ${0.2 + Math.sin(time) * 0.08})`);
  nebula1.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = nebula1;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Névoa azul pulsando
  const nebula2 = ctx.createRadialGradient(
    canvas.width * (0.2 + Math.cos(time * 0.5) * 0.12),
    canvas.height * (0.7 + Math.sin(time * 0.4) * 0.12),
    0,
    canvas.width * 0.2,
    canvas.height * 0.7,
    canvas.width * 0.4
  );
  nebula2.addColorStop(0, `rgba(15, 50, 90, ${0.25 + Math.cos(time * 1.2) * 0.08})`);
  nebula2.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = nebula2;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

function animate() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawBackground();
  drawConstellationLines();
  stars.forEach((s) => { s.update(); s.draw(); });
  requestAnimationFrame(animate);
}

initStars();
animate();