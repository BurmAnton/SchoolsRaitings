document.addEventListener('DOMContentLoaded', function() {
    $('.toast').toast('show')
    document.querySelector('.active').classList.remove('active')
    document.querySelector('.questions-link').classList.add('active')
})

function toggleAnswer(questionId) {
    const answer = document.getElementById(`answer-${questionId}`)
    answer.style.display = answer.style.display === 'none' ? 'block' : 'none'
    const plusMinus = document.querySelector(`.plus-minus[data-question-id="${questionId}"]`)
    plusMinus.textContent = plusMinus.textContent === '+' ? '-' : '+'
}   