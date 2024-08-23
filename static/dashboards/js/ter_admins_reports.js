document.addEventListener('DOMContentLoaded', function() {
    console.log(document.querySelector('.active'))
    document.querySelector('.active').classList.remove('active')
    document.querySelector('.dashboard-link').classList.add('active')
})