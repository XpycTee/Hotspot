// Get the modal
const modalElement = document.getElementById('myModal');

// Get the button that opens the modal
const openModalButton = document.getElementById("modal_trigger");

// Get the <span> element that closes the modal
const closeModalSpan = document.getElementsByClassName("close")[0];

// Function to close the modal
function closeModal() {
    modalElement.style.display = "none";
}

// When the user clicks the button, open the modal
openModalButton.onclick = () => {
    modalElement.style.display = "block";
};
// When the user clicks on <span> (x), close the modal
closeModalSpan.onclick = closeModal();
// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
    if (event.target === modalElement) {
        closeModal();
    }
}
