
function highlightNoSubclipIcons() {
    fetchNoSubclipIds().then((ids)=>{
        if (ids){
            ids.forEach((id) => {
                const elementId = `icon_${id}`;
    
                const element = document.getElementById(elementId);
    
                if (element) {
                    element.style.border = '2px solid red';
                } else {
                    console.warn(`Element with ID ${elementId} not found.`);
                }
            });
       
        }

    })
}

async function fetchNoSubclipIds() {
    try {
        // Define the URL endpoint
        textfileId=textfile_id
        const url = `/text/check_text_clip/${textfileId}/`;

        // Make the AJAX request
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest', // This identifies the request as AJAX
            },
        });

        // Check if the response is okay
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        // Parse the JSON response
        const idsOfNoSubclip = await response.json();

        console.log('IDs of clips with no subclips:', idsOfNoSubclip);

        return idsOfNoSubclip;
    } catch (error) {
        console.error('Error fetching no subclip IDs:', error);
    }
}

function subclipAdd(id,slideNumber,slide,){
    const popupModal=document.getElementById('popup-modal');
    const modalCont=document.getElementById('modal-cont');
    popupModal.style.display='block';
    modalCont.style.display='flex';
    document.getElementById('no_of_slides').value=slideNumber
    document.getElementById('words').value=document.getElementById(`slide_${slide}`).value
    initialValue=document.getElementById(`slide_${slide}`).value
    // document.getElementById('lead-form').action=`/text/add_subclip/${id}/`
    document.getElementById('lead-form').action = `/text/add_subclip/${id}/`;

    document.getElementById('main_clip_id').value=id
    document.getElementById('id').value=id;
    if (slideNumber >1){
        document.getElementById('done-btn').textContent=`Proceed To add ${slideNumber} clips`
        
    }else{
        
        document.getElementById('done-btn').textContent=`Proceed To add ${slideNumber} clip`
    }
}

document.addEventListener("keydown", function (event) {
if (event.key === "Esc") {
    const popupModal = document.getElementById("popup-modal");
    if (popupModal && !popupModal.classList.contains("hidden")) {
        popupModal.classList.add("hidden");
    }
}
});
