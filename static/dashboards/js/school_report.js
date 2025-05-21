document.addEventListener('DOMContentLoaded', function() {
    console.log(document.querySelector('.active'))
    document.querySelector('.active').classList.remove('active')
    document.querySelector('.dashboard-link').classList.add('active')

    const terAdminSelect = document.getElementById('TerAdminFilter');
    const schoolSelect = document.getElementById('SchoolFilter');

    terAdminSelect.addEventListener('change', function() {
        const selectedTerAdminId = this.value;
        
        // Сначала скрываем все опции
        $(schoolSelect).find('option').each(function() {
            const $option = $(this);
            const terAdminId = $option.attr('data-ter-admin-id');
            
            if (terAdminId !== selectedTerAdminId) {
                $option.prop('hidden', true);
                $option.prop('disabled', true);
            } else {
                $option.prop('hidden', false);
                $option.prop('disabled', false);
            }
        });

        // Сбросить выбор и обновить Bootstrap-select
        schoolSelect.value = '';
        $(schoolSelect).selectpicker('refresh');
    });
})