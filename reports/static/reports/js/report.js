document.addEventListener('DOMContentLoaded', function() {
    // Обработка удаления файлов
    document.querySelectorAll('.delete-file').forEach(button => {
        button.addEventListener('click', function() {
            const fileId = this.getAttribute('data-fileid');
            if (confirm('Вы уверены, что хотите удалить этот файл?')) {
                fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        file_id: fileId
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message === "File deleted successfully.") {
                        this.closest('div').remove();
                    }
                });
            }
        });
    });

    // Обработка удаления ссылок
    document.querySelectorAll('.delete-link').forEach(button => {
        button.addEventListener('click', function() {
            const linkId = this.getAttribute('data-linkid');
            if (confirm('Вы уверены, что хотите удалить эту ссылку?')) {
                fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        link_id: linkId
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message === "Link deleted successfully.") {
                        this.closest('div').remove();
                    }
                });
            }
        });
    });

    // Обработка добавления ссылок
    document.querySelectorAll('input[type="link"]').forEach(input => {
        input.addEventListener('change', function() {
            const link = this.value;
            if (link) {
                fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        id: this.name,
                        link: link
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message === "Link updated/saved successfully.") {
                        const filesDiv = this.previousElementSibling;
                        const newLinkDiv = document.createElement('div');
                        newLinkDiv.style.display = 'flex';
                        newLinkDiv.style.alignItems = 'stretch';
                        newLinkDiv.style.gap = '5px';
                        newLinkDiv.style.justifyContent = 'space-between';
                        newLinkDiv.innerHTML = `
                            <a class="btn btn-outline-success btn-sm lattachment${data.question_id}" href="${data.link}" style="width: 100%;" target="_blank" rel="noopener noreferrer">${data.link}</a>
                            <button style="width: 50px; height: 100%;" class="btn btn-danger delete-link" data-linkid="${data.link_id}" name="delete-link">—</button>
                        `;
                        filesDiv.appendChild(newLinkDiv);
                        this.value = '';
                    }
                });
            }
        });
    });

    // Обработка добавления файлов
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('id', this.name);

                fetch(window.location.href, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    if (data.message === "File updated/saved successfully.") {
                        const filesDiv = this.previousElementSibling;
                        const newFileDiv = document.createElement('div');
                        newFileDiv.style.display = 'flex';
                        newFileDiv.style.alignItems = 'stretch';
                        newFileDiv.style.gap = '5px';
                        newFileDiv.style.justifyContent = 'space-between';
                        newFileDiv.innerHTML = `
                            <a class='attachment${data.question_id}' href="${data.file_link}" style="width: 100%;" target="_blank">
                                <button class="btn btn-outline-success btn-sm" style="width: 100%; height: 100%; ">${data.filename}</button>
                            </a>
                            <button style="width: 50px; height: 100%;" class="btn btn-danger delete-file" data-fileid="${data.file_id}" name="delete-file">—</button>
                        `;
                        filesDiv.appendChild(newFileDiv);
                        this.value = '';
                    }
                });
            }
        });
    });

    // Функция для получения CSRF токена
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
}); 