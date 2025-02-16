document.addEventListener('DOMContentLoaded', () => {
    // Select all file inputs and corresponding elements
    const fileInputs = document.querySelectorAll('.uploaded_file');
    const uploadTexts = document.querySelectorAll('.uploadText');
    const svgs = document.querySelectorAll('.uploadFileIcon');
    const selected_clips = document.querySelectorAll('.selected_clip');

    fileInputs.forEach((input, index) => {
        input.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                uploadTexts[index].textContent = `${file.name.slice(0,15)}`;
                svgs[index].style.position = 'absolute';
                svgs[index].style.opacity = '0';
                selected_clips[index].value= ""
            } else {
                uploadTexts[index].textContent = 'Choose File';
                svgs[index].style.position = 'static';
                svgs[index].style.opacity = '1';
            }
        });
    });
});


// function fetchVideos(topic, index) {
//     fetch(`/get_videos/${topic}`)
//     .then(response => response.json())
//     .then(data => {
//         let videoSelect = document.getElementById(`videoSelect_${index}`);
//         videoSelect.innerHTML = '';
//         data.videos.forEach(video => {
//             let option = document.createElement('option');
//             option.value = video;
//             option.textContent = video;

//             videoSelect.appendChild(option);
//         //     const videoPreview = document.getElementById('videoPreview');
//         // const videoPreviewContainer = document.getElementById('videoPreviewContainer');

//         // videoPreview.src =`data/${topic}/${video}`
//         // videoPreviewContainer.style.display = 'block'; // Show the preview container
//         // videoPreview.load();

//         });

//         document.getElementById(`topicFolder_${index}`).value = topic;
//     });
// }


function toggleForms() {
    const subtitleForm = document.getElementById('second-section');
    const formSection = document.getElementById('first-section');


    subtitleForm.style.display = 'block';
    formSection.style.display = 'none';
}
