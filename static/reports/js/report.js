document.addEventListener('DOMContentLoaded', function() {
    check_section()
    document.querySelector('#btn-forward').addEventListener('click', (btn) => {
        let current_section = document.querySelector('.current-section')
        current_section.classList.remove('current-section')
        current_section.nextElementSibling.classList.add('current-section')
        check_section()
    })
    document.querySelector('#btn-back').addEventListener('click', (btn) => {
        let current_section = document.querySelector('.current-section')
        current_section.classList.remove('current-section')
        current_section.previousElementSibling.classList.add('current-section')
        check_section()
    })
    document.querySelectorAll('.selectpicker').forEach(input => {
        input.addEventListener('change', () => {
            let points = document.querySelector(`option[value="${input.value}"]`).dataset.points
            change_question_value(input.id, input.value, points)
        })
    })
    document.querySelectorAll('.form-check-input').forEach(input => {
        input.addEventListener('change', () => {
            let points = "0"
            if(input.checked){
                points = input.dataset.points
            }
            change_question_value(input.id, input.checked, points)
        })
    })
})


function change_question_value(id, value, points){
    fetch(window.location.href, {
        method: 'POST',
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Accept": "application/json",
            'Content-Type': 'application/json'
            },
        body: JSON.stringify({
            'id': id,
            'value': value,
        }),
    })
    .then(response => response.json())
    .then(result => {
        console.log(result);
    })

    document.querySelector(`#points_${id}`).innerHTML = points.replace(",", ".").replace(".0", "")
}



function check_section(){
    let current_section = document.querySelector('.current-section')
    if (current_section.classList.contains('first')){
        document.querySelector('#btn-back').style.display = 'none'
    } else {
        document.querySelector('#btn-back').style.display = 'block'
    }
    if (current_section.classList.contains('last')){
        document.querySelector('#btn-forward').style.display = 'none'
    } else {
        document.querySelector('#btn-forward').style.display = 'block'
    }
}


function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}