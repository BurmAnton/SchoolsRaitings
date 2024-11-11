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
    })
})


function check_all_rows(checkbox){
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
    if (counter > 0) {
        document.querySelector('#SendReports').removeAttribute('disabled');
    } else {
        document.querySelector('#SendReports').setAttribute('disabled', 'disabled');
    }
    document.querySelector('.selected-row-count').innerHTML = counter;
}