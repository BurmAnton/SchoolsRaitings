document.addEventListener('DOMContentLoaded', function() {
    console.log(document.querySelector('.active'))
    document.querySelector('.active').classList.remove('active')
    document.querySelector('.dashboard-link').classList.add('active')

    const terAdminSelect = document.getElementById('TerAdminFilter');
    const schoolSelect = document.getElementById('SchoolFilter');

    terAdminSelect.addEventListener('change', function() {
        const selectedTerAdminId = this.value;
        console.log(selectedTerAdminId)
        // Hide all options in the school select
        Array.from(schoolSelect.options).forEach(option => {
            if (option.dataset.terAdminId !== selectedTerAdminId) {
                option.style.display = 'none';
            } else {
                option.style.display = '';
            }
        });

        // Reset the school select
        schoolSelect.value = '';
        $(schoolSelect).selectpicker('refresh');
    });
})