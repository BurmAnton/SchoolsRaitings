document.addEventListener('DOMContentLoaded', function() {
    check_section()

    document.querySelector('#btn-forward').addEventListener('click', (btn) => {
        let current_section = document.querySelector('.current-section')
        current_section.classList.remove('current-section')
        current_section.nextElementSibling.classList.add('current-section')
        check_section()
        window.scrollTo({ top: 0, behavior: 'smooth' });
    })
    document.querySelector('#btn-back').addEventListener('click', (btn) => {
        let current_section = document.querySelector('.current-section')
        current_section.classList.remove('current-section')
        current_section.previousElementSibling.classList.add('current-section')
        check_section()
        window.scrollTo({ top: 0, behavior: 'smooth' });
    })
    document.querySelectorAll('.selectpicker').forEach(input => {
        input.addEventListener('change', () => {
            let points = document.querySelector(`option[value="${input.value}"]`).dataset.points
            change_question_value(input.id, input.value, points)
            
            document.querySelectorAll('.section-points').forEach(th => {set_points(th)})
        })
    })
    document.querySelectorAll('.number-input').forEach(input => {
        input.addEventListener('change', () => {
            let points = 0
            change_question_value(input.id, input.value, points)
            document.querySelectorAll('.section-points').forEach(th => {set_points(th)})
        })
    })
    document.querySelectorAll('.form-check-input:not(.mult-checkbox)').forEach(input => {
        input.addEventListener('change', () => {
            let points = "0"
            if(input.checked){
                points = input.dataset.points
            }
            change_question_value(input.id, input.checked, input)
            document.querySelectorAll('.section-points').forEach(th => {set_points(th)})
            
        })
    })
    document.querySelectorAll('.mult-checkbox').forEach(input => {
        input.addEventListener('change', () => {
            const fieldId = input.dataset.field;
            const checkedOptions = [];
            
            document.querySelectorAll(`.mult-checkbox[data-field="${fieldId}"]:checked`).forEach(checkbox => {
                checkedOptions.push(checkbox.value);
            });
            
            change_multiple_question_value(fieldId, checkedOptions);
            document.querySelectorAll('.section-points').forEach(th => {set_points(th)});
        });
    });
    document.querySelectorAll('.section-points-max').forEach(th => {set_max_points(th)})
    document.querySelectorAll('.section-points').forEach(th => {set_points(th)})

    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', () => {
            const allowedExtensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.jpeg', '.png', '.zip', '.rar', '.7z', '.bmp'];
            const hasValidExtension = allowedExtensions.some(ext => input.value.toLowerCase().endsWith(ext));
            console.log(input.value)
            if (!hasValidExtension) {
                    let alert_id = input.parentElement.parentElement.querySelector('.alert').id;
                    input.parentElement.parentElement.querySelector('.alert').innerHTML = "Недопустимый формат файла!";
                    alert_id = `#${alert_id}`;
                    $(alert_id).fadeTo(4000, 500).slideUp(500, function(){
                        $(".alert").slideUp(500);
                });
                console.log("Недопустимый формат файла!")
                input.value = ""
                return;
            } else {
                upload_file(input.files[0], input.name, input)
            }
            input.value = ""
        })
    })
    document.querySelectorAll('input[type="link"]').forEach(input => {
        input.addEventListener('change', () => {
            upload_link(input.value, input.name, input)
        })
    })
    document.querySelectorAll('.delete-file').forEach(btn => {
        btn.addEventListener('click', () => {
            fetch(window.location.href, {
                method: 'POST',
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "Accept": "application/json",
                    'Content-Type': 'application/json'
                    },
                body: JSON.stringify({
                    'file_id': btn.dataset.fileid,
                }),
            })
            .then(response => response.json())
            .then(result => {
                btn.parentElement.style.display = 'none';
            })
        })
    })
    document.querySelectorAll('.delete-link').forEach(btn => {
        btn.addEventListener('click', () => {
            fetch(window.location.href, {
                method: 'POST',
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "Accept": "application/json",
                    'Content-Type': 'application/json'
                    },
                body: JSON.stringify({
                    'link_id': btn.dataset.linkid,
                }),
            })
            .then(response => response.json())
            .then(result => {
                btn.parentElement.style.display = 'none';
            })
        })
    })
})


function set_max_points(th){
    let max_points = 0
    th.parentElement.parentElement.querySelectorAll('.question-points-max').forEach(td => {
        max_points += Number(td.innerHTML)
    })
    th.innerHTML = max_points
}


function set_points(th){
    let max_points = 0
    th.parentElement.parentElement.querySelectorAll('.question-points').forEach(td => {
        max_points += Number(td.innerHTML)
    })
    th.innerHTML = max_points
}


function change_question_value(id, value, input){
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
        document.querySelector(`#points_${id}`).innerHTML = result['points'].replace(",", ".").replace(".0", "")
        if (result['ready'] === true){
            document.querySelector('#send-button').classList.remove('disabled')
            document.querySelector('#send-button').classList.remove('btn-secondary')
            document.querySelector('#send-button').classList.add('btn-success')
        } else {
            document.querySelector('#send-button').classList.add('disabled')
            document.querySelector('#send-button').classList.add('btn-secondary')
            document.querySelector('#send-button').classList.remove('btn-success')
        }
        if (result['zone'] === 'Y'){
            document.querySelector('#report-zone').style.background = "#ffc600";
        } else if (result['zone'] === 'R'){
            document.querySelector('#report-zone').style.background = "red";
        } else if (result['zone'] === 'G'){
            document.querySelector('#report-zone').style.background = "green";
        } else {
            document.querySelector('#report-zone').style.background = "white";
        }
        let section = document.querySelector('.current-section')
        if (result['section_z']=== 'Y'){
            section.querySelector('.section-zone').style.background = "#ffc600";
        } else if (result['section_z'] === 'R'){
            section.querySelector('.section-zone').style.background = "red";
        } else if (result['section_z'] === 'G') {
            section.querySelector('.section-zone').style.background = "green";
        } else {
            
            section.querySelector('.section-zone').style.background = "white";
        }
        if (result['answer_z']=== 'Y'){
            section.querySelector(`.question-zone${id}`).style.background = "#ffc600";
        } else if (result['answer_z'] === 'R'){
            section.querySelector(`.question-zone${id}`).style.background = "red";
        } else if (result['answer_z'] === 'G') {
            section.querySelector(`.question-zone${id}`).style.background = "green";
        } else {
            section.querySelector(`.question-zone${id}`).style.background = "white";
            
        }
        document.querySelector('#report-points').innerHTML = result['report_points'].replace(",", ".").replace(".0", "")
        
    })
    .then(result => {
        document.querySelectorAll('.section-points').forEach(th => {set_points(th)})
        
    }

    )
}

function upload_link(value, name, input){
    
    fetch(window.location.href, {
        method: 'POST',
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Accept": "application/json",
            },
        body: JSON.stringify({
            'link': true,
            'value': value,
            'id': name,
        }),
    })
    .then(response => response.json())
    .then(result => {
        console.log(result)
        
        alink = result['link'] 
        question_id = result['question_id'] 
        let files = document.querySelector(`.files${question_id}`)
        const div = document.createElement("div")
        div.style = "display: flex; align-items: stretch; gap: 5px; justify-content: space-between;"
        const link = document.createElement("a")
        link.setAttribute('href', alink)
        link.classList.add(`attachment${question_id}`)
        link.style = "width: 100%;"
        const btn = document.createElement("button")
        btn.style = "width: 100%; height: 100%;"
        btn.innerHTML = alink
        btn.classList.add(`btn`)
        btn.classList.add(`btn-outline-success`)
        btn.classList.add(`btn-sm`)
        link.appendChild(btn)
        div.appendChild(link)
        const btn_delete = document.createElement("button")
        btn_delete.style = "width: 50px; height: 100%;"
        btn_delete.classList.add(`btn`)
        btn_delete.classList.add(`btn-danger`)
        btn_delete.classList.add(`delete-lin`)
        btn_delete.innerHTML = "—"
        btn_delete.dataset.linkid = result['link_id']
        btn_delete.addEventListener('click', () => {
            fetch(window.location.href, {
                method: 'POST',
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "Accept": "application/json",
                    'Content-Type': 'application/json'
                    },
                body: JSON.stringify({
                    'link_id': result['link_id'],
                }),
            })
            .then(response => response.json())
            .then(result => {
                btn_delete.parentElement.style.display = 'none';
            })
        })
        div.appendChild(btn_delete)
        files.appendChild(div)
        let alert_id = input.parentElement.parentElement.querySelector('.alert').id
        input.parentElement.parentElement.querySelector('.alert').innerHTML ="Ссылка прикреплена успешно!"
        alert_id = `#${alert_id}`
        $(alert_id).fadeTo(4000, 500).slideUp(500, function(){
            $(".alert").slideUp(500);
            input.value = "";
        });
    })
}


function upload_file(file, name, input){
    let formData = new FormData()
    formData.append('file', file)
    formData.append('id', name)
    console.log(name)
    
    fetch(window.location.href, {
        method: 'POST',
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Accept": "application/json",
            },
        body: formData
    })
    .then(response => response.json())
    .then(result => {

        file_link = result['file_link'] 
        file_name = result['filename']
        
        question_id = result['question_id'] 
        let files = document.querySelector(`.files${question_id}`)
        const div = document.createElement("div")
        div.style = "display: flex; align-items: stretch; gap: 5px; justify-content: space-between;"
        const link = document.createElement("a")
        link.setAttribute('href', file_link)
        link.classList.add(`attachment${question_id}`)
        link.style = "width: 100%;"
        const btn = document.createElement("button")
        btn.style = "width: 100%; height: 100%;"
        btn.innerHTML = file_name
        btn.classList.add(`btn`)
        btn.classList.add(`btn-outline-success`)
        btn.classList.add(`btn-sm`)
        link.appendChild(btn)
        div.appendChild(link)
        const btn_delete = document.createElement("button")
        btn_delete.style = "width: 50px; height: 100%;"
        btn_delete.classList.add(`btn`)
        btn_delete.classList.add(`btn-danger`)
        btn_delete.classList.add(`delete-file`)
        btn_delete.innerHTML = "—"
        btn_delete.dataset.fileid = result['file_id']
        btn_delete.addEventListener('click', () => {
            fetch(window.location.href, {
                method: 'POST',
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "Accept": "application/json",
                    'Content-Type': 'application/json'
                    },
                body: JSON.stringify({
                    'file_id': result['file_id'],
                }),
            })
            .then(response => response.json())
            .then(result => {
                btn_delete.parentElement.style.display = 'none';
            })
        })
        div.appendChild(btn_delete)
        files.appendChild(div)
        let alert_id = input.parentElement.parentElement.querySelector('.alert').id
        input.parentElement.parentElement.querySelector('.alert').innerHTML ="Документ загружен успешно!"
        alert_id = `#${alert_id}`
        $(alert_id).fadeTo(4000, 500).slideUp(500, function(){
            $(".alert").slideUp(500);
            input.value = "";
        });
    })
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

function change_multiple_question_value(fieldId, selectedOptions) {
    fetch(window.location.href, {
        method: 'POST',
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Accept": "application/json",
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            'id': fieldId,
            'multiple_values': selectedOptions,
        }),
    })
    .then(response => response.json())
    .then(result => {
        document.querySelector(`#points_${fieldId}`).innerHTML = result['points'].replace(",", ".").replace(".0", "");
        
        if (result['ready'] === true){
            document.querySelector('#send-button').classList.remove('disabled');
            document.querySelector('#send-button').classList.remove('btn-secondary');
            document.querySelector('#send-button').classList.add('btn-success');
        } else {
            document.querySelector('#send-button').classList.add('disabled');
            document.querySelector('#send-button').classList.add('btn-secondary');
            document.querySelector('#send-button').classList.remove('btn-success');
        }
        
        if (result['zone'] === 'Y'){
            document.querySelector('#report-zone').style.background = "#ffc600";
        } else if (result['zone'] === 'R'){
            document.querySelector('#report-zone').style.background = "red";
        } else if (result['zone'] === 'G'){
            document.querySelector('#report-zone').style.background = "green";
        } else {
            document.querySelector('#report-zone').style.background = "white";
        }
        
        let section = document.querySelector('.current-section');
        if (result['section_z'] === 'Y'){
            section.querySelector('.section-zone').style.background = "#ffc600";
        } else if (result['section_z'] === 'R'){
            section.querySelector('.section-zone').style.background = "red";
        } else if (result['section_z'] === 'G') {
            section.querySelector('.section-zone').style.background = "green";
        } else {
            section.querySelector('.section-zone').style.background = "white";
        }
        
        if (result['answer_z'] === 'Y'){
            section.querySelector(`.question-zone${fieldId}`).style.background = "#ffc600";
        } else if (result['answer_z'] === 'R'){
            section.querySelector(`.question-zone${fieldId}`).style.background = "red";
        } else if (result['answer_z'] === 'G') {
            section.querySelector(`.question-zone${fieldId}`).style.background = "green";
        } else {
            section.querySelector(`.question-zone${fieldId}`).style.background = "white";
        }
        
        document.querySelector('#report-points').innerHTML = result['report_points'].replace(",", ".").replace(".0", "");
    })
    .then(result => {
        document.querySelectorAll('.section-points').forEach(th => {set_points(th)});
    });
}