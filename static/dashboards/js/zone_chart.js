// Функция для создания графика зон
function createZoneChart() {
    // Ждем полной загрузки DOM
    setTimeout(function() {
        // Получаем canvas элемент
        var canvas = document.getElementById('test-chart');
        if (!canvas) {
            console.error('Canvas элемент не найден');
            return;
        }
        
        // Проверяем, загружена ли библиотека Chart.js
        if (typeof Chart === 'undefined') {
            console.error('Chart.js не загружен');
            return;
        }
        
        // Тестовые данные для графика
        var data = {
            labels: ['ТУ 1', 'ТУ 2', 'ТУ 3', 'ТУ 4', 'ТУ 5'],
            datasets: [
                {
                    label: 'Красная зона',
                    data: [5, 3, 8, 2, 7],
                    backgroundColor: '#FFC7CE'
                },
                {
                    label: 'Жёлтая зона',
                    data: [2, 6, 3, 9, 4],
                    backgroundColor: '#FFEB9C'
                },
                {
                    label: 'Зелёная зона',
                    data: [7, 4, 5, 3, 6],
                    backgroundColor: '#C6EFCE'
                }
            ]
        };
        
        // Настройки графика
        var options = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true }
            }
        };
        
        // Создаем график
        try {
            new Chart(canvas, {
                type: 'bar',
                data: data,
                options: options
            });
            console.log('График создан успешно');
        } catch (error) {
            console.error('Ошибка при создании графика:', error);
        }
    }, 1000);
}

// Запускаем создание графика после загрузки страницы
document.addEventListener('DOMContentLoaded', function() {
    createZoneChart();
}); 