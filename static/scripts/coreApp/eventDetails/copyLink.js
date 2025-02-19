document.addEventListener("DOMContentLoaded", function () {
    const shareButton = document.getElementById("shareLinkCopyButton");
    const copyLinkSuccess = document.getElementById("copyLinkSuccessUrl").value;
  
    const copyShareLink = () => {
      const shareLink = document.getElementById("shareLink");
  
      navigator.clipboard
        .writeText(shareLink.value)
        .then(() => {
          // Use the value property to get the URL string
          fetch(copyLinkSuccess, { method: "GET" }).then((response) => {
            if (response.ok) {
              window.location.reload();
            } else {
              throw new Error("Failed to fetch");
            }
          });
        })
        .catch((error) => {
          console.error("Error fetching success Link", error);
        });
    };
  
    shareButton.addEventListener("click", copyShareLink);
  });
  