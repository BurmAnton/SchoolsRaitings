document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('#notif-btn').addEventListener('click', () => {
        document.querySelector('.notifcation-bar').classList.toggle('show')
        document.querySelector('#notif-btn').classList.toggle('show')
    })
})