document.addEventListener("DOMContentLoaded", function () {
  // Get the elements
  const title = document.getElementById("title");
  const titleInput = document.getElementById("title-input");
  const editBtn = document.getElementById("edit-btn");
  const saveBtn = document.getElementById("save-btn");

  // Function to switch to edit mode (show input field)
  editBtn.addEventListener("click", function () {
    titleInput.value = title.textContent;
    title.style.display = "none"; // Hide the <h2>
    titleInput.style.display = "block"; // Show the input field
    editBtn.style.display = "none"; // Hide the Edit button
    saveBtn.style.display = "block"; // Show the Save button
  });

  // Function to handle saving the updated title
  saveBtn.addEventListener("click", function () {
    const form = titleInput.closest("form");
    form.submit(); // Submit the form when Save button is clicked
  });

  // // Function to save the updated title
  // saveBtn.addEventListener("click", function () {
  //   title.textContent = titleInput.value; // Update <h2> text with input value
  //   title.style.display = "block"; // Show the <h2> again
  //   titleInput.style.display = "none"; // Hide the input field
  //   editBtn.style.display = "flex"; // Show the Edit button again
  //   saveBtn.style.display = "none"; // Hide the Save button
  // });
});
