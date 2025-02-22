function toggleColumns(li, shouldDisable) {
    let $row = $(li).closest("tr");
    let $nextCols = $row.find("td").slice(2, 4);

    $nextCols.each(function () {
        $(this).css({
            "background-color": shouldDisable ? "#d3d3d3" : ""
        });
    });

    $nextCols.find("a, button")
        .prop("disabled", shouldDisable)
        .css({
            "cursor": shouldDisable ? "wait" : "pointer",
            "pointer-events": shouldDisable ? "none" : "auto"
        });
}

//good
function deleteAllLi(cNumber) {

    const ul = document.getElementById(`list-of-tags_${cNumber}`); // Get the <ul> element by ID
    if (ul) {
        const liElements = ul.querySelectorAll("li");

        liElements.forEach(li => li.remove());
    } else {
        console.error("Element with ID 'list-of-tags' not found.");
    }
}
//good

 function handleEnterToHide(currentNumber,) {
    edit = false
    const textarea = document.getElementById(`slide_text_${currentNumber}`);

    const wrapper = document.getElementById(`wrapper_${currentNumber}`);
    const slide_span = document.getElementById(`slide_span_${currentNumber}`);
    const edit_ = document.getElementById(`edit_${currentNumber}`);
    const delete_ = document.getElementById(`delete_${currentNumber}`);
    const reset_ = document.getElementById(`reset_${currentNumber}`);
    const lisOfTags=document.getElementById(`list-of-tags_${currentNumber}`)
    let clip_id = slide_span.dataset.id
    let tableBody = document.querySelector("#leadsTable tbody");
    let rows = tableBody.getElementsByTagName("tr");

    textarea.addEventListener('keydown', function (event) {
    deleteAllLi(currentNumber)

        if (event.key === 'Enter') {
            event.preventDefault();
            textarea.style.display = 'none';
            wrapper.style.display = 'flex';
            edit_.style.display = 'flex';
            slide_span.textContent = textarea.value;
            // toggleColumns(textarea, true)

            // const check = await checkSubtitlesLength();

            if (true) {

                if (textarea.value) {

                    const payload = JSON.stringify({
                        text: textarea.value,
                        // position:rows.length+1
                    });

                    const xhr = new XMLHttpRequest();
                    xhr.addEventListener('load', function () {
                        if (xhr.status === 200) {
                            const response = JSON.parse(xhr.responseText);
                            if (!response.new) {
                                if (response.changed) {
                                    slide_span.textContent = textarea.value;
                                    deleteAllLi(currentNumber)

                                }
                                textarea.style.display = 'none';
                                wrapper.style.display = 'flex';
                                edit_.style.display = 'flex';
                            }
                            else {
                                textarea.style.display = 'none';
                                wrapper.style.display = 'flex';
                                edit_.style.display = 'flex';
                                slide_span.textContent = textarea.value;
                            }
                            if (response.success) {

                                const tr = slide_span.closest("tr");
                                if (tr) {
                                    tr.setAttribute("data-id", response.id);
                                }
                                slide_span.dataset.id = response.id
                                tr.dataset.id = response.id
                                clip_id = response.id
                                if (reset_) {
                                    reset_.onclick = function () {
                                        subclipReset(clip_id);
                                    };
                                    reset_.style.display = 'flex'
                                    delete_.onclick = function () {
                                        deleteSavedSlide(clip_id, delete_);

                                    };


                                };
                                updateBackendOrder()
                                toggleColumns(textarea, false)
                                showSuccessMessage(`Subtitle submitted successfully!`);

                            } else {
                                alert(response.error || 'Failed to submit the text.');
                            }
                        } else {
                            alert('An error occurred while submitting the text.');
                        }
                    });

                    xhr.addEventListener('error', function () {
                        alert('An error occurred during the request.');
                    });
                    if (clip_id) {

                        xhr.open('POST', `/text/edit_text_clip_line/${clip_id}/`);
                    } else {

                        xhr.open('POST', `/text/add_text_clip_line/${textFileID}/`);
                    }
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.setRequestHeader('X-CSRFToken', '{{ csrf_token }}');
                    xhr.send(payload);
                }

            }

        }
    });
}

function EditeSlide(currentNumber) {
    edit = true
    const textarea = document.getElementById(`slide_text_${currentNumber}`);
    const wrapper = document.getElementById(`wrapper_${currentNumber}`);
    const slide_span = document.getElementById(`slide_span_${currentNumber}`);
    const edit_ = document.getElementById(`edit_${currentNumber}`);
    const delete_ = document.getElementById(`edit_${currentNumber}`);
    textarea.style.display = 'flex';
    wrapper.style.display = 'flex'

    wrapper.style.display = 'none'
    toggleColumns(textarea, true)


};

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('no_of_slides').value == 0) {
        addSlide()
    } else {
        for (let index = 1; index <= document.getElementById('no_of_slides').value; index++) {
            handleEnterToHide(index);
            handleSelection(index);
        }
    }
})
function clearErrorMessages() {
    const errorElements = document.querySelectorAll('[id^="error"]');
    errorElements.forEach(element => {
        element.textContent = "";
    });
}



function startProcessingAnimation() {
    const buttonText = $('#button-text');
    const svgIcon = $('#proceed-svg'); // Reference to the SVG element
    let dots = 0;

    // Hide the SVG icon when processing starts
    svgIcon.css('display', 'none'); 

    // Fix the button text content and size before starting animation
    buttonText.css({
        'white-space': 'nowrap', // Prevent text wrapping
        'overflow': 'hidden',    // Hide any overflowed text if needed
        'text-overflow': 'ellipsis', // Ensure ellipsis is applied if text overflows
    });

    if (buttonText.data('intervalId')) {
        clearInterval(buttonText.data('intervalId'));
    }

    const intervalId = setInterval(function () {
        dots = (dots + 1) % 4;
        let loadingText = 'Processing' + '.'.repeat(dots);
        buttonText.text(loadingText);
    }, 500);

    buttonText.data('intervalId', intervalId);
}

function stopProcessingAnimation() {
    const buttonText = $('#button-text');
    const svgIcon = $('#proceed-svg');
    const intervalId = buttonText.data('intervalId');

    if (intervalId) {
        clearInterval(intervalId);
        buttonText.data('intervalId', null);
        buttonText.text('Proceed To Background Music Selection');
    }

    // Show the SVG icon again once processing stops
    svgIcon.css('display', 'inline-block');
}

function highlightNoSubclipIcons(button) {
    startProcessingAnimation();
    const tagBoxes = document.querySelectorAll('.tag-box');
    const spanIds = [];
    tagBoxes.forEach(tagBox => {
        const span = tagBox.querySelector('ul span');

        if (span && span.dataset.id) {
            spanIds.push(Number(span.dataset.id));
        }
    });

    console.log(spanIds)
    if (areAllTextareasHidden()) {
        fetchNoSubclipIds().then((ids) => {
            if (Array.isArray(ids) && ids.length > 0) {
                ids.forEach((id) => {
                    if (spanIds.includes(id)) {
                        console.log(`ID matched: ${id}`);
                        const matchingTagBox = Array.from(tagBoxes).find(tagBox =>
                            Number(tagBox.querySelector('ul span')?.dataset.id) === Number(id)
                        );
                        const matchingSpan = matchingTagBox.querySelector('ul span')
                        if (matchingSpan) {
                            // matchingSpan.style.color='red'
                            console.log(matchingSpan.id.split('_').pop())
                            const errorMessage = document.getElementById(`error-message_${matchingSpan.id.split('_').pop()}`);
                            if (errorMessage) {
                                console.log(errorMessage)
                                if (matchingSpan.textContent.trim() === '') {
                                    errorMessage.textContent = 'Please Wait For Clip To Process'

                                } else {
                                    errorMessage.textContent = 'Assign Clips To All Of The Subtitle Text'

                                }
                            }

                            stopProcessingAnimation();
                        }
                    }
                });
            } else {
                updateBackendOrder();
                const form = document.getElementById('processFile');
                if (form) {

                    form.submit();
                } else {
                    console.error("Form with ID 'processFile' not found.");
                }
            }
        }).catch((error) => {
            console.error("Error fetching no subclip IDs:", error);
        });
    } else {
        alert('You Need To Save or Delete The Current Text')
    }

}

function areAllTextareasHidden() {
    const textareas = document.querySelectorAll('textarea');

    for (const textarea of textareas) {
        const style = window.getComputedStyle(textarea);

        if (style.display !== 'none') {
            return false;
        }
    }

    return true;
}

if (areAllTextareasHidden()) {
    console.log("All textareas are hidden.");
} else {
    console.log("At least one textarea is visible.");
}


function handleSelection(cNumber) {
    const wrapper = document.querySelector(`#wrapper_${cNumber}`);
    const span = wrapper.querySelector("span");
    const ul = wrapper.querySelector(`#list-of-tags_${cNumber}`);
    const remainingInput = wrapper.querySelector(`#remaining_${cNumber}`);
    const errorMessage = document.querySelector(`#error-message_${cNumber}`);

    document.getElementById(`highlightable_${cNumber}`).addEventListener("mouseup", function () {
        const selection = window.getSelection();
        clip_Id = span.dataset.id
        
        if (document.getElementById(`slide_text_${cNumber}`).style.display === 'none') {

            if (selection && selection.toString().trim()) {
                const selectedText = selection.toString().trim();
                const fullText = span.innerText.trim();
                const words = fullText.split(/\s+/);
                const selectedWords = selectedText.split(/\s+/);
                
                const startsCorrectly = fullText.startsWith(selectedText);
                const isWordAligned = selectedWords.every(word => words.includes(word));

                if (startsCorrectly && isWordAligned) {
                    errorMessage.innerText = "";
                    if (typeof clip_Id === "undefined") {
                        alert('Please Select Text Again')
                        return
                    }
                    console.log('clipid: ', clip_Id)

                    const li = document.createElement("li");
                    li.innerText = selectedText;
                    li.dataset.id = cNumber;
                    li.disabled = true
                    li.style.fontSize = "1.2rem";
                    li.style.borderColor = "#864AF9";
                    li.onclick = function () {
                        editCurrentLi(li);
                    };
                    num = span.dataset.num
                    li.id = `current_li_${cNumber}`
                    sessionStorage.setItem('cNumber', cNumber)
                    console.log('li: ', li, 'number: ', sessionStorage.getItem('cNumber', cNumber))

                    ul.insertBefore(li, span);

                    const remainingText = fullText.slice(selectedText.length).trim();
                    remainingInput.value = remainingText;
                    span.innerText = remainingText;
                    openPopup(clip_Id, selectedText, remainingText, cNumber, li);
                    li.style.cursor = 'wait'




                } else {
                    errorMessage.innerText = "Highlighting Must Start From The First Unassigned Word Of The Sentence.";
                }
            }

            selection.removeAllRanges();
        } else {

        }
    });
}


function clearFileInput() {
    document.getElementById('slide_file').value = ''
    document.getElementById('clear-file').style.display = 'none'
    document.getElementById('upload-text').textContent = 'Choose File'


}
function clearCurrentFile() {
    document.getElementById('currentFile').innerHTML = ''
}





const proceedBtn = document.querySelector(".proceed-btn")
const instructionDiv = document.getElementById("instruction")

function showInstruction() {
    const instructionContainer = document.getElementById("instruction")
    const arrow = document.getElementById("arrow")
    instructionContainer.classList.toggle('hidden')
    arrow.classList.toggle('rotate')
}


function savedInputChangeFunc(id) {
    const inputFile = document.getElementById(`saved_slide_file_${id}`)
    const fileName = inputFile.files.length > 0 ? inputFile.files[0].name.slice(20) : 'Choose file';
    const element = document.getElementById(`current_${id}`);
    if (element) {
        element.style.display = 'none';
        document.getElementById(`saved_span_${id}`).textContent = fileName;
    } else {
        console.error(`Element with ID current_${id} not found.`);
    }
}
function showSuccessMessage(message) {
    const successMessage = document.createElement('div');
    successMessage.textContent = message;
    successMessage.style.position = 'fixed';
    successMessage.style.top = '95px';
    successMessage.style.right = '20px';
    successMessage.style.padding = '10px 15px';
    successMessage.style.backgroundColor = '#4CAF50';
    successMessage.style.color = 'white';
    successMessage.style.borderRadius = '5px';
    successMessage.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
    successMessage.style.zIndex = '1000';

    clearErrorMessages();

    document.body.appendChild(successMessage);

    setTimeout(() => {
        document.body.removeChild(successMessage);
    }, 2000);
}

let currentNumber = document.getElementById('no_of_slides').value


function deleteSlide(btn) {
    const row = btn.closest('tr');

    row.parentNode.removeChild(row);
    edit = false

    updateSubtitleNumbers(document.getElementById('leadsTable').getElementsByTagName('tbody')[0])
}


function checkRowCount(tableBody) {
    var rowCount = tableBody.rows.length;
    const unlimitedPlans = ['premium', 'admin','pro']; 
    console.log(userPlan);
    // if (rowCount > 10 && !unlimitedPlans.includes(userPlan)) {
    if (userPlan ==='free' & rowCount>= 10){
        console.log("Row count exceeded 10!");
        alert("Your Current Package Only Allows You To Add 10 Slides Please Upgrade To Unlock Unlimited Slides");
        // showPopup()
        return false;
    } else {
        return true;
    }
}
function updateSubtitleNumbers(tableBody) {
    for (let i = 0; i < tableBody.rows.length; i++) {
        tableBody.rows[i].cells[0].textContent = `Subtitle ${i + 1}`;
    }
}



function subclipReset(mainId) {

    
    const url = `/text/reset_subclip/${mainId}/`;

    if (confirm("Are You Sure You Want To Reset This Sentence?")) {
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({ textfile_id: textFileID })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert("Failed to reset the clip. Please try again.");
                }
            })
            .catch(error => {
                console.error("Error resetting clip:", error);
                alert("An error occurred. Please try again later.");
            });
    }
}

function fetchClipIds() {
    fetch(`/text/get_clips_id/${textFileID}/`)
        .then(response => response.json())
        .then(clipIds => {
            console.log('Fetched clip IDs:', clipIds);
            // handleClips(clipIds);
        })
        .catch(error => console.error('Error fetching clip IDs:', error));
}

function clearFileInput() {
    document.getElementById('slide_file').value = ''
    document.getElementById('clear-file').style.display = 'none'
    document.getElementById('upload-text').textContent = 'Choose File'


}


async function fetchNoSubclipIds() {
    try {
        textfileId = textFileID
        const url = `/text/check_text_clip/${textfileId}/`;

        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const idsOfNoSubclip = await response.json();

        console.log('IDs of clips with no subclips:', idsOfNoSubclip);

        return idsOfNoSubclip;
    } catch (error) {
        console.error('Error fetching no subclip IDs:', error);
    }
}

function clearErrorMessages() {
    const errorElements = document.querySelectorAll('[id^="error"]');
    errorElements.forEach(element => {
        element.textContent = "";
    });
    const slide_span_s = document.querySelectorAll('[id^="slide_span_"]');
    slide_span_s.forEach(element => {
        element.style.border = "none";
    });
}
function closeModal() {
    clearErrorMessages();

    document.getElementById('add-subclip-popup').style.display = 'none';

    const formClipID = document.getElementById('clipId').value;
    const ulElement = document.getElementById(`list-of-tags_${formClipID}`);
    const spanElement = document.getElementById(`slide_span_${formClipID}`);
    const liItem = document.getElementById(`saved_li_${formClipID}`);
    const current_li = document.getElementById(`current_li_${sessionStorage.getItem('cNumber')}`);
    console.log(sessionStorage.getItem('cNumber',current_li))
    if (liItem) {
        liItem.disabled = false
        liItem.style.cursor = 'pointer'

    } else if (current_li) {
        const text = current_li.textContent.trim();
        const ul = current_li.closest("ul");

        if (ul) {
            const span = ul.querySelector("span");
            if (span) {
                span.textContent = text + " " + span.textContent;
            }
        }

        current_li.remove();
    }
    else {
        console.log("No <li> items found to remove.");
    }
}
function getVideoDimensions(file, callback) {
    const video = document.createElement("video");
    video.preload = "metadata";

    video.onloadedmetadata = function () {
        window.URL.revokeObjectURL(video.src);
        callback({ width: video.videoWidth, height: video.videoHeight });
    };

    video.onerror = function () {
        callback({ error: "Invalid video file" });
    };

    video.src = URL.createObjectURL(file);
}
function saveInput(inputElement) {
    const uploadElement = document.getElementById('upload-text');

    if (inputElement.type === 'file') {
        console.log(inputElement.value);

        if (inputElement.value) {
    
            document.getElementById('upload-text').style.color = 'black'

            document.getElementById('error-slide').textContent = '';

            const fileName = inputElement.files.length > 0 ? inputElement.files[0].name : "Choode File";
            uploadElement.textContent = fileName.slice(0, 13)
            document.getElementById('currentFile').textContent = ''
            document.getElementById('clear-file').style.display = 'flex'

            document.getElementById(`videoSelect`).value = ""
            document.getElementById(`videoSelect`).innerHTML = "<option value='' selected disabled>Select Video</option>"
            document.getElementById(`selected_topic`).value = ""
            saveInput(document.getElementById(`videoSelect`))
            saveInput(document.getElementById(`selected_topic`))
            getVideoDimensions(inputElement.files[0], function (dimensions) {
                if (dimensions.error) {
                    console.error(dimensions.error);
                } else {
                    console.log("Video Width:", dimensions.width);
                    console.log("Video Height:", dimensions.height);
            
                    let aspectRatio = dimensions.width / dimensions.height;
                    if (Math.abs(aspectRatio - (9 / 16)) < 0.05) { // Allowing a small tolerance
                        document.getElementById('is_tiktok').value = 1;
                    } else {
                        document.getElementById('is_tiktok').value = 0;
                    }
                }
            });
            
            
        }

    } else {

        console.log(inputElement.value);

        if (inputElement.value !== '') {
            document.getElementById('error-slide').textContent = '';
            document.getElementById('is_tiktok').value = 0;

            console.log('first line is true')
            document.getElementById('currentFile').textContent = '';
            console.log('currentfile')
            document.getElementById("slide_file").value = '';
            console.log('slide_file')
            uploadElement.textContent = 'Choose File'
            console.log('uploadElement:', uploadElement)
            saveInput(document.getElementById("slide_file"))
            document.getElementById('clear-file').style.display = 'none'


        };

    }

};

async function fetchVideoClips(selected) {
    id = selected.value;
    let video_id = `videoSelect`
    // saveInput(selected)
    if (id) {
        saveInput(selected)
        populateVideoCategories(video_id, `/video/get_clip/${id}`)

    } else {
        document.getElementById(video_id).innerHTML = `<option selected disabled value="">Select A Video Clip</option>`
    }
}

function populateVideoCategories(selectElementId, apiUrl) {
    const selectElement = document.getElementById(selectElementId);
    selectElement.innerHTML = ''
    if (!selectElement) {
        console.error(`Select element with ID "${selectElementId}" not found.`);
        return;
    }


    // Fetch categories from the API
    fetch(apiUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(videos => {
            // const defaultOption = document.createElement("option");
            // defaultOption.value = "";
            // defaultOption.textContent = "Select A Video Clip";
            // defaultOption.disabled = true;
            // defaultOption.selected = true;
            // selectElement.appendChild(defaultOption);

            videos.forEach(video => {
                const option = document.createElement("option");
                option.value = video.id;
                option.textContent = video.title;
                selectElement.appendChild(option);

         

            })

        })
        .catch(error => {
            console.error("Failed to fetch video categories:", error);
        });
}


function attachValidation(formId, clipId, cNumber, li) {


    const form = document.getElementById(formId);

    if (form) {
        const fileInput = document.getElementById('slide_file');
        const videoSelect = document.getElementById('videoSelect');

        if ((!fileInput.value || fileInput.value.trim() === "") &&
            (!videoSelect || !videoSelect.value || videoSelect.value.trim() === "")) {
            if (videoSelect.disabled) {
                document.getElementById('upload-text').style.color = 'red'
            } else {

                document.getElementById('error-slide').textContent = 'Select A Clip';
            }

            videoSelect.focus();
        } else {
            document.getElementById('upload-text').style.color = 'inherit'

            document.getElementById('error-slide').textContent = ''; // Clear error message
            
            if (li) {
                li.disabled = true;
                li.style.cursor = 'wait';
                li.id = 'processing_' + cNumber
                console.log(li, ' has been disabled');
            }
            const popup = document.getElementById('add-subclip-popup');
            if (popup) popup.style.display = 'none';
            const formData = new FormData(form);
            const xhr = new XMLHttpRequest();

            xhr.addEventListener('load', function () {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);

                    if (response.success) {
                        const newId = response.id;


                        if (li) {
                            li.id = `saved_li_${newId}`;
                            li.dataset.id = newId;
                            if (response.video_clip) {
                                li.dataset.name = response.video_clip.name
                                li.dataset.clipid = response.video_clip.id
                                li.dataset.cat_id = response.video_clip.cat_id
                                sessionStorage.setItem(`${li.dataset.id}` ,response.video_clip.id)



                            }else {
                                li.dataset.current_file = response.current_file
                                if (!response.exists_in_s3){
                                    li.disabled = false;
                                    li.style.cursor = 'pointer';
                                    li.style.border='1px solid red';
                                    alert('Please Reupload File For The Subclip With Red Border')
                                }
                            }
                            li.disabled = false;
                            li.style.cursor = 'pointer';
                        }
                        sessionStorage.setItem(`${newId}`, videoSelect.value)


                        // Show success message
                        const successMessage = document.createElement('div');
                        successMessage.textContent = 'Clip Added Successfully!';
                        successMessage.style.position = 'fixed';
                        successMessage.style.top = '20px';
                        successMessage.style.right = '20px';
                        successMessage.style.padding = '10px 15px';
                        successMessage.style.backgroundColor = '#4CAF50';
                        successMessage.style.color = 'white';
                        successMessage.style.borderRadius = '5px';
                        successMessage.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
                        successMessage.style.zIndex = '1000';
                        clearErrorMessages();
                        document.body.appendChild(successMessage);

                        // Remove the success message after 2 seconds
                        setTimeout(() => {
                            document.body.removeChild(successMessage);
                        }, 2000);

                    } else {
                        alert(response.error || 'Failed to add clip.');
                    }
                } else {
                    alert('An error occurred while saving the clip.');
                }

                if (li) {
                    li.disabled = false;
                    li.style.cursor = 'pointer';
                }
            });

            // Handle errors
            xhr.addEventListener('error', function () {
                alert('An error occurred during the request.');
                if (li) {
                    li.disabled = false;
                    li.style.cursor = 'pointer';
                }
            });

            // Open and send the request
            xhr.open('POST', `/text/add_subcliphtmx/${clipId}/`);
            xhr.setRequestHeader('X-CSRFToken', '{{ csrf_token }}');
            xhr.send(formData);
        }
    }
}


function editAttachValidation(formId, clipId, getUrl, li) {

    if (li) {
        li.disabled = true;
        console.log(li.dataset.id, ' has been disabled');
    }

    const form = document.getElementById(formId);

    if (form) {
        const fileInput = document.getElementById('slide_file');
        const videoSelect = document.getElementById('videoSelect');

        if ((!fileInput.value || fileInput.value.trim() === "") &&
            (!videoSelect || !videoSelect.value || videoSelect.value.trim() === "")) {
            if (videoSelect.disabled) {
                document.getElementById('upload-text').style.color = 'red'
            } else {

                document.getElementById('error-slide').textContent = 'Select A Clip';
            }
            videoSelect.focus();
        } else {
            document.getElementById('upload-text').style.color = 'black'
            if (videoSelect.value){
                sessionStorage.setItem(`${li.dataset.id}` ,videoSelect.value)

            }

            document.getElementById('error-slide').textContent = ''; 
            const popup = document.getElementById('add-subclip-popup');
            if (popup) popup.style.display = 'none';
            const formData = new FormData(form);
            const xhr = new XMLHttpRequest();

            xhr.addEventListener('load', function () {
                if (xhr.status === 200) {
                    const response = JSON.parse(xhr.responseText);

                    if (response.success) {
                        const newId = response.id;

                        // Update the li element
                        if (li) {

                            li.dataset.id = newId;
                            li.dataset.name = ''
                                li.dataset.clipid =''
                                li.dataset.cat_id = ''
                                li.dataset.current_file=''

                            if (response.video_clip) {
                                li.dataset.name = response.video_clip.name
                                li.dataset.clipid = response.video_clip.id
                                li.dataset.cat_id = response.video_clip.cat_id
                                sessionStorage.setItem(`${li.dataset.id}` ,response.video_clip.id)



                            }else {
                                li.dataset.current_file = response.current_file
                                if (!response.exists_in_s3){
                                    li.disabled = false;
                                    li.style.cursor = 'pointer';
                                    li.style.border='1px solid red'
                                    alert('Please Reupload File For The Subclip With Red Border')
                                }

                            }
                            li.disabled = false;
                            li.style.cursor = 'pointer';

                        }
                        sessionStorage.setItem(`${newId}`, videoSelect.value)

                        // Show success message
                        const successMessage = document.createElement('div');
                        successMessage.textContent = 'Clip Updated Successfully!';
                        successMessage.style.position = 'fixed';
                        successMessage.style.top = '20px';
                        successMessage.style.right = '20px';
                        successMessage.style.padding = '10px 15px';
                        successMessage.style.backgroundColor = '#4CAF50';
                        successMessage.style.color = 'white';
                        successMessage.style.borderRadius = '5px';
                        successMessage.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.2)';
                        successMessage.style.zIndex = '1000';
                        clearErrorMessages();
                        document.body.appendChild(successMessage);

                        // Remove the success message after 2 seconds
                        setTimeout(() => {
                            document.body.removeChild(successMessage);
                        }, 2000);

                    } else {
                        alert(response.error || 'Failed to add clip.');
                    }
                } else {
                    alert('An error occurred while saving the clip.');
                }

                if (li) {
                    li.disabled = false;
                    li.style.cursor = 'pointer';
                }
            });

            // Handle errors
            xhr.addEventListener('error', function () {
                alert('An error occurred during the request.');
                if (li) {
                    li.disabled = false;
                    li.style.cursor = 'pointer';
                }
            });

            xhr.open('POST', getUrl);
            xhr.setRequestHeader('X-CSRFToken', '{{ csrf_token }}');
            xhr.send(formData);
        }
    }
}


function disableForFree() {
    const disabledDiv = document.getElementById('disabled-div');
    if (disabledDiv) {
        disabledDiv.style.cursor = "not-allowed";
        disabledDiv.disabled = true

        const children = disabledDiv.querySelectorAll('*');
        children.forEach(child => {
            child.style.cursor = "not-allowed";
            child.disabled = true

        });
    }

}


async function restoreSelectFields(liItem) {
const topic = document.getElementById('selected_topic');
const videoClip = document.getElementById('videoSelect');

if (liItem.dataset.cat_id) {
    topic.value = liItem.dataset.cat_id;


    await fetchVideoClips(topic);
    
    const savedValue = sessionStorage.getItem(`${liItem.dataset.id}`);
    if (savedValue) {
        videoClip.value = savedValue;
    }
} else if (liItem.dataset.current_file) {
    topic.value = '';
    videoClip.value = '';

    document.getElementById('currentFile').innerHTML = `Current File: ${liItem.dataset.current_file} 
        <i id="clearCurrentFile" style="font-size:large;"  onclick="clearCurrentFile()" class="ri-close-circle-line"></i>
    `;
}

}

function clearCurrentFile() {
    document.getElementById('currentFile').innerHTML = ''
}

document.addEventListener("htmx:afterRequest", function (event) {
    const xhr = event.detail.xhr;
    if (xhr && xhr.responseURL.includes("add_subcliphtmx") && xhr.method === "POST") {
        try {
            // Parse the JSON response
            const jsonResponse = JSON.parse(xhr.responseText);

            if (jsonResponse.success) {
                const subclipId = jsonResponse.id;

                // Perform additional tasks with the subclip ID
                console.log("Subclip created with ID:", subclipId);

                // Example: Add the subclip ID to a list or update the UI
                const subclipList = document.getElementById("subclip-list");
                if (subclipList) {
                    const newItem = document.createElement("li");
                    newItem.textContent = `Subclip ID: ${subclipId}`;
                    subclipList.appendChild(newItem);
                }

                alert(`Subclip created successfully with ID: ${subclipId}`);
            } else {
                console.error("Error creating subclip:", jsonResponse.error);
                alert(`Failed to create subclip: ${jsonResponse.error}`);
            }
        } catch (error) {
            console.error("Failed to parse response JSON:", error);
        }
    }
});




document.querySelectorAll('.subtitle_clip').forEach(item => {
    item.addEventListener('dragstart', handleDragStart);
    item.addEventListener('dragover', handleDragOver);
    item.addEventListener('drop', handleDrop);
    item.addEventListener('dragend', handleDragEnd);
});

let draggedElement = null;

function handleDragStart(event) {
    draggedElement = event.target;
    draggedElement.classList.add('dragging');
    const dragBox = document.createElement('div');
    dragBox.classList.add('drag-box');
    dragBox.textContent = draggedElement.querySelector('.drag-container').textContent;
    document.body.appendChild(dragBox);
    draggedElement.style.visibility = 'hidden';
}

function handleDragOver(event) {
    event.preventDefault();
}

function handleDrop(event) {
    event.preventDefault();
    if (draggedElement) {
        const draggedText = draggedElement.querySelector('.drag-container').textContent;
        const dragBox = document.querySelector('.drag-box');
        dragBox.textContent = draggedText;
    }
}

function handleDragEnd() {
    draggedElement.style.visibility = 'visible';
    draggedElement.classList.remove('dragging');
    const dragBox = document.querySelector('.drag-box');
    if (dragBox) {
        dragBox.remove();
    }
}
