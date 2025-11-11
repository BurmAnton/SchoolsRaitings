function sortTable(n, table_id='table-overall', minus=1) {
    let table = document.getElementById(table_id)
    let switching = true;
    let direction = "asc";
    let shouldSwitch;
    let switchcount = 0;

    // Remove any existing sort indicators
    let headers = table.getElementsByTagName("TH");
    for (let header of headers) {
        header.classList.remove("asc", "desc");
    }

    // Add sort indicator to current column header
    headers[n].classList.add(direction);

    while (switching) {
        switching = false;
        let rows = table.rows;
        let i = 1
        for (i; i < (rows.length - minus); i++) {
            shouldSwitch = false;
            let x = rows[i].getElementsByTagName("TD")[n];
            let y = rows[i + 1].getElementsByTagName("TD")[n];

            // Get numeric values if they exist, otherwise use text content
            let xValue = parseFloat(x.textContent) || x.textContent.toLowerCase();
            let yValue = parseFloat(y.textContent) || y.textContent.toLowerCase();

            if (direction === "asc") {
                if (xValue > yValue) {
                    shouldSwitch = true;
                    break;
                }
            } else if (direction === "desc") {
                if (xValue < yValue) {
                    shouldSwitch = true;
                    break;
                }
            }
            console.log(direction)
        }

        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
            switchcount++;
        } else {
            if (switchcount === 0 && direction === "asc") {
                direction = "desc";
                switching = true;
                
            } 
        }
    }
    // Hide all sort icons
    let ascIcons = table.querySelectorAll('.asc-icon');
    let descIcons = table.querySelectorAll('.desc-icon');
    ascIcons.forEach(icon => icon.style.display = 'none');
    descIcons.forEach(icon => icon.style.display = 'none');
    if (direction === "asc" && switchcount != 0 ) {
        headers[n].querySelector('.asc-icon').style.display = 'block'
        headers[n].querySelector('.desc-icon').style.display = 'none'
    } else if (direction === "desc" && switchcount != 0) {
        headers[n].querySelector('.asc-icon').style.display = 'none'
        headers[n].querySelector('.desc-icon').style.display = 'block'
    }
}