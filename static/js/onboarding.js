/**
 * FinLab - Onboarding Slides
 */
document.addEventListener('DOMContentLoaded', () => {
    const slides = document.querySelectorAll('.slide');
    const dots = document.querySelectorAll('.dot');
    const btnNext = document.getElementById('btn-next');
    const btnSkip = document.getElementById('btn-skip');
    let current = 0;
    const total = slides.length;

    function goTo(idx) {
        slides[current].classList.remove('active');
        slides[current].classList.add('exit-left');
        dots[current].classList.remove('active');

        current = idx;
        slides[current].classList.remove('exit-left');
        slides[current].classList.add('active');
        dots[current].classList.add('active');

        // Cleanup exit-left after animation
        slides.forEach((s, i) => {
            if (i !== current) {
                setTimeout(() => s.classList.remove('exit-left'), 450);
            }
        });

        // Update button on last slide
        if (current === total - 1) {
            btnNext.textContent = 'Bắt đầu';
        } else {
            btnNext.textContent = 'Tiếp tục';
        }
    }

    if (btnNext) {
        btnNext.addEventListener('click', () => {
            if (current < total - 1) {
                goTo(current + 1);
            } else {
                window.location.href = '/register';
            }
        });
    }

    if (btnSkip) {
        btnSkip.addEventListener('click', () => {
            window.location.href = '/login';
        });
    }

    // Initialize first slide
    if (slides.length > 0) {
        slides[0].classList.add('active');
        if (dots.length > 0) dots[0].classList.add('active');
    }
});
