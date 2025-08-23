function createConfetti() {
    const confettiContainer = document.getElementById('celebration-popup');
    if (!confettiContainer) return;
    const colors = ['#FFD700', '#C0C0C0', '#CD7F32', '#4A90E2', '#fff'];
    for (let i = 0; i < 100; i++) { // Create 100 pieces of confetti
        const confetti = document.createElement('div');
        confetti.classList.add('confetti');
        confetti.style.left = `${Math.random() * 100}vw`;
        confetti.style.top = `${Math.random() * -100}vh`; // Start above the screen
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        confetti.style.animationDelay = `${Math.random() * 2}s`;
        confettiContainer.appendChild(confetti);

        // Remove confetti from DOM after animation
        setTimeout(() => {
            confetti.remove();
        }, 3500);
    }
}
