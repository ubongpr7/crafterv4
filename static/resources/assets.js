document.addEventListener('DOMContentLoaded', function() {
    const menus = document.querySelectorAll('.menu');
    const dropdowns = document.querySelectorAll('.actions');
    let activeDropdown = null;

    // Function to hide all dropdowns
    function hideAllDropdowns() {
        dropdowns.forEach(dropdown => {
            dropdown.style.display = 'none';
        });
        activeDropdown = null;
    }

    // Event listener for each menu click
    menus.forEach((menu, index) => {
        menu.addEventListener('click', function(event) {
            event.stopPropagation();  // Prevent the event from bubbling up to the document click listener
            
            const currentDropdown = dropdowns[index];

            if (activeDropdown === currentDropdown) {
                // Toggle off if the same menu is clicked again
                currentDropdown.style.display = 'none';
                activeDropdown = null;
            } else {
                // Hide other dropdowns and show the clicked one
                hideAllDropdowns();
                currentDropdown.style.display = 'block';
                activeDropdown = currentDropdown;
            }
        });
    });

    // Hide dropdowns if clicked outside
    document.addEventListener('click', function() {
        hideAllDropdowns();
    });

    // Prevent dropdown from closing if clicking inside it
    dropdowns.forEach(dropdown => {
        dropdown.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    });
});

document.addEventListener('htmx:configRequest', function(evt) {
document.querySelector('.loader').style.display = 'block';
});

document.addEventListener('htmx:afterOnLoad', function(evt) {
document.querySelector('.loader').style.display = 'none';
});

document.addEventListener('htmx:afterSwap', function(evt) {
document.querySelector('.loader').style.display = 'none';
});