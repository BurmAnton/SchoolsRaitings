document.addEventListener('DOMContentLoaded', function() {
    $('.toast').toast('show')
    document.querySelector('.active').classList.remove('active')
    document.querySelector('.report-link').classList.add('active')


    document.querySelector('#CheckAll').addEventListener('click', (event) => {
        var checkbox = event.currentTarget.querySelector('.form-check-input');
        if (event.currentTarget.parentElement.classList.contains('selected-all-row')) {
            checkbox.checked = false;
        } else {
            checkbox.checked = true;
        }
        check_all_rows(checkbox);
    });
    document.querySelectorAll('.check-td').forEach(td =>{
        td.addEventListener('click', (event) =>{
            var checkbox = event.currentTarget.querySelector('.form-check-input');
            if (td.parentElement.classList.contains('selected-row')) {
                checkbox.checked = false;
            } else {
                checkbox.checked = true;
            }
            check_row(checkbox);
        })
    });
    
    // Добавляем обработчик для кнопки "Выбрать все отчёты"
    const selectAllReportsBtn = document.getElementById('SelectAllReportsBtn');
    if (selectAllReportsBtn) {
        selectAllReportsBtn.addEventListener('click', function() {
            const selectAllInput = document.getElementById('selectAllReportsInput');
            const wasSelected = selectAllInput.value === 'true';
            
            // Получаем общее количество отчетов из data-атрибута кнопки
            const totalCount = parseInt(selectAllReportsBtn.getAttribute('data-total-reports') || '0');
            
            // Меняем значение на противоположное
            selectAllInput.value = wasSelected ? 'false' : 'true';
            
            if (!wasSelected) {
                // Если выбираем все отчеты, активируем кнопку отправки
                document.querySelector('#SendReports').removeAttribute('disabled');
                
                // Также выбираем все чекбоксы на текущей странице
                document.querySelector('#CheckAll').querySelector('.form-check-input').checked = true;
                document.querySelector('#CheckAll').parentElement.classList.add('selected-all-row');
                document.querySelectorAll('.center-checkbox').forEach(checkbox => {
                    checkbox.checked = true;
                    checkbox.parentElement.parentElement.parentElement.classList.add('selected-row');
                });
                
                // Меняем текст ссылки
                selectAllReportsBtn.textContent = 'Снять выделение';
                
                // Обновляем счетчик общим количеством отчетов
                document.querySelector('.selected-row-count').innerHTML = totalCount;
            } else {
                // Отменяем выбор
                document.querySelector('#SendReports').setAttribute('disabled', 'disabled');
                
                // Снимаем выбор со всех чекбоксов на текущей странице
                document.querySelector('#CheckAll').querySelector('.form-check-input').checked = false;
                document.querySelector('#CheckAll').parentElement.classList.remove('selected-all-row');
                document.querySelectorAll('.center-checkbox').forEach(checkbox => {
                    checkbox.checked = false;
                    checkbox.parentElement.parentElement.parentElement.classList.remove('selected-row');
                });
                
                // Восстанавливаем текст ссылки
                selectAllReportsBtn.textContent = 'Выбрать все отчёты (' + totalCount + ')';
                
                // Скрываем ссылку, т.к. нет выбранных отчетов
                selectAllReportsBtn.style.display = 'none';
                
                // Обновляем счетчик
                document.querySelector('.selected-row-count').innerHTML = '0';
            }
        });
    }
})


function check_all_rows(checkbox){
    // Сбрасываем режим "выбрать все отчеты", если он был активен
    const selectAllInput = document.getElementById('selectAllReportsInput');
    if (selectAllInput && selectAllInput.value === 'true') {
        selectAllInput.value = 'false';
        const selectAllReportsBtn = document.getElementById('SelectAllReportsBtn');
        if (selectAllReportsBtn) {
            const countText = selectAllReportsBtn.textContent.match(/\d+/);
            const totalCount = countText ? parseInt(countText[0]) : 0;
            selectAllReportsBtn.textContent = 'Выбрать все отчёты (' + totalCount + ')';
            selectAllReportsBtn.classList.remove('btn-outline-danger');
            selectAllReportsBtn.classList.add('btn-outline-secondary');
        }
    }

    if (checkbox.checked) {
        checkbox.parentElement.parentElement.parentElement.classList.add('selected-all-row');
        document.querySelectorAll('.center-checkbox').forEach(checkbox =>{
            checkbox.checked = true;
            checkbox.parentElement.parentElement.parentElement.classList.add('selected-row');
        })
    } else {
        checkbox.parentElement.parentElement.parentElement.classList.remove('selected-all-row');
        document.querySelectorAll('.center-checkbox').forEach(checkbox =>{
            checkbox.checked = false;
            checkbox.parentElement.parentElement.parentElement.classList.remove('selected-row');
        })
    }
    count_selected_rows();
}

function check_row(checkbox){
    // Сбрасываем режим "выбрать все отчеты", если он был активен
    const selectAllInput = document.getElementById('selectAllReportsInput');
    if (selectAllInput && selectAllInput.value === 'true') {
        selectAllInput.value = 'false';
        const selectAllReportsBtn = document.getElementById('SelectAllReportsBtn');
        if (selectAllReportsBtn) {
            const countText = selectAllReportsBtn.textContent.match(/\d+/);
            const totalCount = countText ? parseInt(countText[0]) : 0;
            selectAllReportsBtn.textContent = 'Выбрать все отчёты (' + totalCount + ')';
        }
    }

    if (checkbox.checked) {
        checkbox.parentElement.parentElement.parentElement.classList.add('selected-row');
        var inputs = document.querySelectorAll('.center-checkbox');
        var is_checked = true;
        for(var x = 0; x < inputs.length; x++) {
            is_checked = inputs[x].checked;
            if(is_checked === false) break;
        }
        if(is_checked) {
            document.querySelector('#CheckAll').querySelector('.form-check-input').checked = true;
            document.querySelector('#CheckAll').parentElement.classList.add('selected-all-row');
        }
    } else {
        checkbox.parentElement.parentElement.parentElement.classList.remove('selected-row');
        document.querySelector('#CheckAll').querySelector('.form-check-input').checked = false;
        document.querySelector('#CheckAll').parentElement.classList.remove('selected-all-row');
    }
    count_selected_rows();
}

function count_selected_rows(){
    var inputs = document.querySelectorAll('.center-checkbox');
    var is_checked = true;
    var counter = 0;
    for(var x = 0; x < inputs.length; x++) {
        is_checked = inputs[x].checked;
        if(is_checked){
            counter += 1;
        };
    }
    
    // Управление кнопкой отправки
    if (counter > 0) {
        document.querySelector('#SendReports').removeAttribute('disabled');
    } else {
        document.querySelector('#SendReports').setAttribute('disabled', 'disabled');
    }
    
    // Управление ссылкой "Выбрать все"
    const selectAllBtn = document.getElementById('SelectAllReportsBtn');
    if (selectAllBtn) {
        if (counter > 0) {
            selectAllBtn.style.display = 'inline-block';
        } else {
            selectAllBtn.style.display = 'none';
            // Сбросим скрытое поле если все отчеты были сняты с выбора
            const selectAllInput = document.getElementById('selectAllReportsInput');
            if (selectAllInput) {
                selectAllInput.value = 'false';
            }
        }
    }
    
    document.querySelector('.selected-row-count').innerHTML = counter;
}