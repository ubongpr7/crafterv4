// const box1 = document.getElementById('box-1');
// const circle11 = document.getElementById('circle-11');
// const circle12 = document.getElementById('circle-12');


// const box2 = document.getElementById('box-2');
// const circle21 = document.getElementById('circle-21');
// const circle22 = document.getElementById('circle-22');
// function selectOption(resolution) {
//     // Reset styles for both options
//     document.getElementById('box-1').style.border = '1px solid #88888877';
//     document.getElementById('circle-11').style.border = '3px solid #D9D9D9';
//     document.getElementById('circle-12').style.background = '#D9D9D9';
    
//     document.getElementById('box-2').style.border = '1px solid #88888877';
//     document.getElementById('circle-21').style.border = '3px solid #D9D9D9';
//     document.getElementById('circle-22').style.background = '#D9D9D9';

//     // Highlight the selected option
//     if (resolution === '1:1') {
//         document.getElementById('box-1').style.border = '1px solid #864AF9';
//         document.getElementById('circle-11').style.border = '3px solid #864AF9';
//         document.getElementById('circle-12').style.background = '#864AF9';
//         document.getElementById('option1').checked = true;
//         document.getElementById('option2').checked = false;
//     } else if (resolution === '16:9') {
//         document.getElementById('box-2').style.border = '1px solid #864AF9';
//         document.getElementById('circle-21').style.border = '3px solid #864AF9';
//         document.getElementById('circle-22').style.background = '#864AF9';
//         document.getElementById('option2').checked = true;
//         document.getElementById('option1').checked = false;
//     }
// }

// function activateBox(selectedBox, selectedCircle1, selectedCircle2) {
//     // Remove styles from all boxes and circles
//     box1.style.border = '1px solid #88888877';
//     circle11.style.border = '3px solid #D9D9D9';
//     circle12.style.backgroundColor = '#D9D9D9';

//     box2.style.border = '1px solid #88888877';
//     circle21.style.border = '3px solid #D9D9D9';
//     circle22.style.backgroundColor = '#D9D9D9';

//     // Add styles to the selected box and circles
//     selectedBox.style.border = '1px solid #864AF9';  // Example style for box-border
//     selectedCircle1.style.border = '3px solid #864AF9';  // Example style for circle-outer
//     selectedCircle2.style.backgroundColor = '#864AF9';  // Example style for circle-inner
// }

// // Event listener for box1
// box1.addEventListener('click', function () {
//     activateBox(box1, circle11, circle12);
//     console.log('box1 clicked');
// });

// // Event listener for box2
// box2.addEventListener('click', function () {
//     activateBox(box2, circle21, circle22);
//     console.log('box2 clicked');
// });
function resetAllOptions() {
    const allBoxes = document.querySelectorAll('.box');
    const allCirclesOuter = document.querySelectorAll('.circle-outer');
    const allCirclesInner = document.querySelectorAll('.circle-inner');
    
    allBoxes.forEach(box => {
        box.style.border = '1px solid #88888877'; // Reset box border
    });
    
    allCirclesOuter.forEach(circleOuter => {
        circleOuter.style.border = '3px solid #D9D9D9'; // Reset outer circle
    });
    
    allCirclesInner.forEach(circleInner => {
        circleInner.style.backgroundColor = '#D9D9D9'; // Reset inner circle
    });
}

function selectOption(resolution) {
    resetAllOptions(); // Reset all styles

    const selectedBox = document.querySelector(`.box[data-resolution="${resolution}"]`);
    const selectedCircleOuter = selectedBox.querySelector('.circle-outer');
    const selectedCircleInner = selectedBox.querySelector('.circle-inner');
    
    // Highlight the selected option
    selectedBox.style.border = '1px solid #864AF9';
    selectedCircleOuter.style.border = '3px solid #864AF9';
    selectedCircleInner.style.backgroundColor = '#864AF9';
    
    // Set the selected radio button
    document.querySelector(`input[value="${resolution}"]`).checked = true;
}

// Attach event listeners to all boxes
document.querySelectorAll('.box').forEach(box => {
    box.addEventListener('click', function() {
        const resolution = this.getAttribute('data-resolution');
        selectOption(resolution)
        // adjustPreviewBox(resolution);  // Function to adjust preview box size based on resolution
    });
});






const slider = document.getElementById("mySlider");
const sliderValue = document.getElementById("SliderValue");
const previewText= document.getElementById("previewText");
slider.addEventListener('input', function() {
    sliderValue.textContent = slider.value;
    console.log(slider.value)
    previewText.style.fontSize = `${slider.value*0.8}px`;
    document.getElementById('font_size').value=slider.value*2
    console.log(document.getElementById('font_size').value)
    
});
const font_select = document.getElementById('font_select');

font_select.addEventListener('change', (event) => {
    font= event.target.value;
    previewText.style.fontFamily=font

    
});



slider.addEventListener('input', function() {
    const value = (slider.value - slider.min) / (slider.max - slider.min) * 100;
    slider.style.background = `linear-gradient(to right, #864AF9 0%, #864AF9 ${value}%, #D9D9D9 ${value}%, #D9D9D9 100%)`;
    slider.style.background.border = ``;
});

// Initialize the background on page load
slider.dispatchEvent(new Event('input'));

const color1 = document.getElementById('color1');
const colorPicker1 = document.getElementById('colorPicker1');
const colortext1 = document.getElementById('colortext1');
let colorvalue1 = '#FFFFFF';

    colorPicker1.addEventListener('input', function() {
         // Update the background color of the div in real-time
        color1.style.background = colorPicker1.value;
        colortext1.value = colorPicker1.value;
        previewText.style.color = colortext1.value;

        if(color1.style.border === '1px solid red') {
            color1.style.border = '1px solid #000000B2';
            colortext1.style.border = '1px solid #000000B2';
            color1.style.background = colortext1.value;
        }
    });
    colortext1.addEventListener('input', function() {
    colorvalue1 = colortext1.value;

    if(colorvalue1.charAt(0) === '#'){
        color1.style.border = '1px solid #000000B2';
        colortext1.style.border = '1px solid #000000B2';
        color1.style.background = colortext1.value;
    }
    else{
        color1.style.border = '1px solid red';
        colortext1.style.border = '1px solid red';
        color1.style.background = '#FFFFFF';
    }
});


const color2 = document.getElementById('color2');
const colorPicker2 = document.getElementById('colorPicker2');
const colortext2 = document.getElementById('colortext2');
const previewBackground = document.getElementById('previewBackground');
let colorvalue2 = '#FFFFFF';

    colorPicker2.addEventListener('input', function() {
         // Update the background color of the div in real-time
        color2.style.background = colorPicker2.value;
        colortext2.value = colorPicker2.value;
        previewBackground.style.background = colortext2.value;
        if(color2.style.border === '1px solid red') {
            color2.style.border = '1px solid #000000B2';
            colortext2.style.border = '1px solid #000000B2';
            color2.style.background = colortext1.value;
        }
    });
    colortext2.addEventListener('input', function() {
    colorvalue2 = colortext2.value;

    if(colorvalue2.charAt(0) === '#'){
        color2.style.border = '1px solid #000000B2';
        colortext2.style.border = '1px solid #000000B2';
        color2.style.background = colortext2.value;
    }
    else{
        color2.style.border = '1px solid red';
        colortext2.style.border = '1px solid red';
        color2.style.background = '#FFFFFF';
    }
});



// const pfp = document.getElementById('pfp');
// const dropdown = document.getElementById('pfpdropdown');

//     pfp.addEventListener('click', function() {
//         dropdown.classList.toggle('not-present');
//         dropdown.classList.toggle('present');
//     });

//     document.addEventListener('click', function(event) {
//         if (!dropdown.contains(event.target) && !pfp.contains(event.target)) {
//             dropdown.classList.remove('present');
//             dropdown.classList.add('not-present');
//         }
//     });

