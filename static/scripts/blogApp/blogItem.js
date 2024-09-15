document.addEventListener("DOMContentLoaded", function () {
  const editBtn = document.getElementById("edit-btn");

  const type = document.getElementById("type");
  const typeInput = document.getElementById("type-input");
  const saveType = document.getElementById("save-type");

  const title = document.getElementById("title");
  const titleInput = document.getElementById("title-input");
  const saveTitle = document.getElementById("save-title");

  const imageOne = document.getElementById("nH-image-container");
  const imageOneInput = document.getElementById("news-header-input");
  const saveImageOne = document.getElementById("save-imageOne");

  const body = document.getElementById("blog-body");
  const bodyInput = document.getElementById("blog-body-input");
  const saveBody = document.getElementById("save-blog-body");

  const imageTwoAndThree = document.getElementById("images");
  const imageTwoInput = document.getElementById("imageTwo-input");
  const imageThreeInput = document.getElementById("imageThree-input");
  const saveImageTwo = document.getElementById("save-imageTwo");
  const saveImageThree = document.getElementById("save-imageThree");

  editBtn.addEventListener("click", function () {
    editBtn.style.display = "none";

    type.style.display = "none";
    typeInput.style.display = "block";
    saveType.style.display = "block";

    titleInput.value = title.textContent;
    title.style.display = "none";
    titleInput.style.display = "block";
    saveTitle.style.display = "block";

    imageOne.style.display = "none";
    imageOneInput.style.display = "block";
    saveImageOne.style.display = "block";

    bodyInput.value = body.textContent;
    body.style.display = "none";
    bodyInput.style.display = "block";
    saveBody.style.display = "block";

    imageTwoAndThree.style.display = "none";
    imageTwoInput.style.display = "block";
    imageThreeInput.style.display = "block";
    saveImageTwo.style.display = "block";
    saveImageThree.style.display = "block";
  });
});
