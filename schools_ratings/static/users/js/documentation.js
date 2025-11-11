document.addEventListener('DOMContentLoaded', function() {
    $('.toast').toast('show')
    document.querySelector('.active').classList.remove('active')
    document.querySelector('.doc-link').classList.add('active')
})