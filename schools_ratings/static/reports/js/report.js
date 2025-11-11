document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing report page...');
    
    // Проверяем наличие секций и автоматически устанавливаем первую как текущую
    const sections = document.querySelectorAll('.section');
    const currentSection = document.querySelector('.current-section');
    
    if (sections.length > 0 && !currentSection) {
        console.warn('No current section found! Adding current-section class to first section.');
        sections[0].classList.add('current-section');
    }
    
    // Добавляем обработчики для навигационных ссылок
    document.querySelectorAll('.pagination .page-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault(); // Предотвращаем обычный переход по ссылке
            
            const url = new URL(this.href);
            const targetSectionId = url.searchParams.get('current_section');
            
            if (targetSectionId) {
                // Скрываем текущую секцию
                const currentSection = document.querySelector('.current-section');
                if (currentSection) {
                    currentSection.classList.remove('current-section');
                }
                
                // Показываем новую секцию
                const targetSection = document.querySelector(`[data-section-id="${targetSectionId}"]`);
                if (targetSection) {
                    targetSection.classList.add('current-section');
                    
                    // Обновляем навигацию
                    check_section();
                    
                    // Прокручиваем страницу вверх
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                } else {
                    console.error('Target section not found:', targetSectionId);
                }
            }
        });
    });
    
    check_section()

    // document.querySelector('#btn-forward').addEventListener('click', (btn) => {
    //     let current_section = document.querySelector('.current-section')
    //     current_section.classList.remove('current-section')
    //     current_section.nextElementSibling.classList.add('current-section')
    //     check_section()
    //     window.scrollTo({ top: 0, behavior: 'smooth' });
    // })
    // document.querySelector('#btn-back').addEventListener('click', (btn) => {
    //     let current_section = document.querySelector('.current-section')
    //     current_section.classList.remove('current-section')
    //     current_section.previousElementSibling.classList.add('current-section')
    //     check_section()
    //     window.scrollTo({ top: 0, behavior: 'smooth' });
    // })
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
    document.querySelectorAll('.form-check-input:not(.mult-checkbox):not(.check-answer)').forEach(input => {
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
    
    // Обработчик для кнопок отправки ссылок
    document.querySelectorAll('.send-link-btn').forEach(button => {
        button.addEventListener('click', () => {
            const linkInput = button.parentElement.querySelector('input[type="link"]');
            const urlPattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
            
            // Очищаем предыдущие состояния
            linkInput.classList.remove('is-invalid');
            button.classList.remove('sending');
            
            if (linkInput.value) {
                // Добавляем анимацию загрузки
                button.classList.add('sending');
                button.disabled = true;
                
                // Показываем индикатор загрузки
                const originalIcon = button.innerHTML;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
                
                upload_link(linkInput.value, linkInput.name, linkInput)
                    .then(() => {
                        // Успешная отправка
                        button.innerHTML = '<i class="fas fa-check"></i>';
                        
                        // Возвращаем исходный вид через 2 секунды
                        setTimeout(() => {
                            button.innerHTML = originalIcon;
                            button.classList.remove('sending');
                            button.disabled = false;
                        }, 2000);
                    })
                    .catch(() => {
                        // Ошибка отправки
                        button.innerHTML = '<i class="fas fa-times"></i>';
                        button.classList.add('btn-danger');
                        button.classList.remove('btn-success');
                        
                        // Возвращаем исходный вид через 3 секунды
                        setTimeout(() => {
                            button.innerHTML = originalIcon;
                            button.classList.remove('sending', 'btn-danger');
                            button.classList.add('btn-success');
                            button.disabled = false;
                        }, 3000);
                    });
            } else {
                // Показываем ошибку валидации
                linkInput.classList.add('is-invalid');
                let alert_element = linkInput.closest('.col, .field, .mb-3').querySelector('.alert');
                if (alert_element) {
                    alert_element.innerHTML = linkInput.value ? "Введите корректную ссылку!" : "Поле не может быть пустым!";
                    alert_element.classList.remove('alert-success');
                    alert_element.classList.add('alert-danger');
                    let alert_id = `#${alert_element.id}`;
                    $(alert_id).fadeTo(4000, 500).slideUp(500, function(){
                        $(".alert").slideUp(500);
                        alert_element.classList.remove('alert-danger');
                        alert_element.classList.add('alert-success');
                    });
                }
                
                // Добавляем эффект тряски для кнопки
                // button.classList.add('shake');
                // setTimeout(() => {
                //     button.classList.remove('shake');
                // }, 500);
            }
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
            .then(response => {
                if (response.status === 403) {
                    return response.json().then(data => {
                        showBlockedFieldMessage(data.error);
                        throw new Error(data.error);
                    });
                }
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(result => {
                btn.parentElement.style.display = 'none';
            })
            .catch(error => {
                console.error('Error deleting file:', error);
            });
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
            .then(response => {
                if (response.status === 403) {
                    return response.json().then(data => {
                        showBlockedFieldMessage(data.error);
                        throw new Error(data.error);
                    });
                }
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(result => {
                btn.parentElement.style.display = 'none';
            })
            .catch(error => {
                console.error('Error deleting link:', error);
            });
        })
    })
    document.querySelectorAll('.check-answer').forEach(input => {
        input.addEventListener('change', () => {
            const answerId = input.dataset.answerId;
            const isChecked = input.checked;
            
            fetch(window.location.href, {
                method: 'POST',
                headers: {
                    "X-CSRFToken": getCookie("csrftoken"),
                    "Accept": "application/json",
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    check_answer: true,
                    answer_id: answerId,
                    is_checked: isChecked
                }),
            })
            .then(response => {
                if (response.status === 403) {
                    return response.json().then(data => {
                        // Возвращаем чекбокс в предыдущее состояние
                        input.checked = !isChecked;
                        showBlockedFieldMessage(data.error);
                        throw new Error(data.error);
                    });
                }
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(result => {
                const checkInfo = document.getElementById(`check-info-${answerId}`);
                if (isChecked) {
                    checkInfo.innerHTML = `${result.checked_by}<br>Дата: ${result.checked_at}`;
                } else {
                    checkInfo.innerHTML = '';
                }
            })
            .catch(error => {
                console.error('Error updating check status:', error);
            });
        });
    });
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
    th.parentElement.parentElement.parentElement.querySelectorAll('.question-points').forEach(td => {
        let pointValue = td.innerHTML.trim().replace(',', '.');
        let pointNumber = parseFloat(pointValue) || 0;
        max_points += pointNumber;
    });
    
    th.innerHTML = max_points.toString().replace('.', ',').replace(/,0$/, '');
    
    let totalPoints = 0;
    document.querySelectorAll('.section-points').forEach(sectionTotal => {
        let sectionValue = parseFloat(sectionTotal.innerHTML.trim().replace(',', '.')) || 0;
        totalPoints += sectionValue;
    });
    
    if (document.getElementById('report-points')) {
        document.getElementById('report-points').innerHTML = totalPoints.toString().replace('.', ',').replace(/,0$/, '');
    }
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
    .then(response => {
        if (response.status === 403) {
            return response.json().then(data => {
                showBlockedFieldMessage(data.error);
                throw new Error(data.error);
            });
        }
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
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
        
    })
    .catch(error => {
        console.error('Error updating field:', error);
        // Сообщение об ошибке уже показано в showBlockedFieldMessage
    });
}

function upload_link(value, name, input){
    
    return fetch(window.location.href, {
        method: 'POST',
        headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Accept": "application/json",
            'Content-Type': 'application/json'
            },
        body: JSON.stringify({
            'link': true,
            'value': value,
            'id': name,
        }),
    })
    .then(response => {
        console.log('Response status:', response.status);
        console.log('Response headers:', response.headers.get('content-type'));
        
        if (response.status === 403) {
            return response.json().then(data => {
                showBlockedFieldMessage(data.error);
                throw new Error(data.error);
            });
        }
        
        if (!response.ok) {
            return response.text().then(text => {
                console.error('Server error response:', text);
                throw new Error(`HTTP ${response.status}: ${text}`);
            });
        }
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            return response.text().then(text => {
                console.error('Non-JSON response:', text);
                throw new Error('Сервер вернул не JSON ответ');
            });
        }
        
        return response.json();
    })
    .then(result => {
        console.log('Upload success:', result);
        
        if (!result || !result.question_id) {
            console.error('Invalid response format:', result);
            throw new Error('Неверный формат ответа сервера');
        }
        
        alink = result['link'] 
        question_id = result['question_id'] 
        let files = document.querySelector(`.files${question_id}`)
        
        if (!files) {
            console.error('Files container not found for question_id:', question_id);
            throw new Error('Не найден контейнер для файлов');
        }
        
        // Проверяем, что ссылка получена корректно
        if (!alink) {
            console.error('Empty link in response:', result);
            throw new Error('Сервер вернул пустую ссылку');
        }
        
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
            .then(response => {
                if (response.status === 403) {
                    return response.json().then(data => {
                        showBlockedFieldMessage(data.error);
                        throw new Error(data.error);
                    });
                }
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(result => {
                btn_delete.parentElement.style.display = 'none';
            })
            .catch(error => {
                console.error('Error deleting link:', error);
            });
        })
        div.appendChild(btn_delete)
        files.appendChild(div)
        
        // Показываем сообщение об успехе
        let alert_element = input.parentElement.parentElement.querySelector('.alert');
        if (alert_element) {
            alert_element.innerHTML = "Ссылка прикреплена успешно!";
            alert_element.classList.remove('alert-danger');
            alert_element.classList.add('alert-success');
            let alert_id = `#${alert_element.id}`;
            $(alert_id).fadeTo(4000, 500).slideUp(500, function(){
                $(".alert").slideUp(500);
            });
        }
        
        // Очищаем поле ввода после успешной отправки с небольшой задержкой
        setTimeout(() => {
            input.value = "";
        }, 1000);
        
        return result; // Возвращаем результат для цепочки промисов
    })
    .catch(error => {
        console.error('Error uploading link:', error);
        // Показываем ошибку пользователю
        let alert_element = input.parentElement.parentElement.querySelector('.alert');
        if (alert_element) {
            alert_element.innerHTML = `Ошибка при отправке ссылки: ${error.message}`;
            alert_element.classList.remove('alert-success');
            alert_element.classList.add('alert-danger');
            let alert_id = `#${alert_element.id}`;
            $(alert_id).fadeTo(4000, 500).slideUp(500, function(){
                $(".alert").slideUp(500);
                alert_element.classList.remove('alert-danger');
                alert_element.classList.add('alert-success');
            });
        }
        throw error; // Перебрасываем ошибку для обработки в вызывающем коде
    });
}

// Функция для отображения сообщения о блокировке поля
function showBlockedFieldMessage(message) {
    // Создаем модальное окно или уведомление
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-warning alert-dismissible fade show';
    alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alertDiv.innerHTML = `
        <strong>Редактирование запрещено!</strong><br>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
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
    .then(response => {
        if (response.status === 403) {
            return response.json().then(data => {
                showBlockedFieldMessage(data.error);
                throw new Error(data.error);
            });
        }
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
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
            .then(response => {
                if (response.status === 403) {
                    return response.json().then(data => {
                        showBlockedFieldMessage(data.error);
                        throw new Error(data.error);
                    });
                }
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                return response.json();
            })
            .then(result => {
                btn_delete.parentElement.style.display = 'none';
            })
            .catch(error => {
                console.error('Error deleting file:', error);
            });
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
    .catch(error => {
        console.error('Error uploading file:', error);
        // Сообщение об ошибке уже показано в showBlockedFieldMessage
    });
}


function check_section(){
    let current_section = document.querySelector('.current-section');
    let backButton = document.querySelector('#btn-back');
    let forwardButton = document.querySelector('#btn-forward');
    
    if (!current_section) {
        console.error('No current section found in check_section!');
        return;
    }
    
    if (backButton) {
        if (current_section.classList.contains('first')){
            backButton.style.display = 'none';
        } else {
            backButton.style.display = 'block';
        }
    }
    
    if (forwardButton) {
        if (current_section.classList.contains('last')){
            forwardButton.style.display = 'none';
        } else {
            forwardButton.style.display = 'block';
        }
    }
    
    // Сброс активных элементов навигации
    document.querySelectorAll('.page-item').forEach(item => {
        item.classList.remove('active');
    });
    
    let currentSectionId = current_section.dataset.sectionId;
    
    if (currentSectionId) {
        const navSelector = `.page-item a[href*="current_section=${currentSectionId}"]`;
        const navLink = document.querySelector(navSelector);
        const activePageItem = navLink?.parentElement;
        
        if (activePageItem) {
            activePageItem.classList.add('active');
        } else {
            console.warn('Navigation item not found for section ID:', currentSectionId);
        }
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
    .then(response => {
        if (response.status === 403) {
            return response.json().then(data => {
                showBlockedFieldMessage(data.error);
                throw new Error(data.error);
            });
        }
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
    })
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
    })
    .catch(error => {
        console.error('Error updating multiple choice field:', error);
        // Сообщение об ошибке уже показано в showBlockedFieldMessage
    });
}