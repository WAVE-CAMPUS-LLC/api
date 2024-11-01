const startButton = document.getElementById("startScanningButton");

startButton.addEventListener('click', function() {
    startScanning();
});

function startScanning() {
    document.getElementById("scanner-container").style.display = "none";
    document.getElementById("scanner-display").style.display = "block";

    startQrScan();
}

function startQrScan() {
    const qrReader = new Html5Qrcode("qrReader");

    const config = { fps: 10, qrbox: 500 };

    qrReader.start(
        { facingMode: "environment" },
        config,
        (decodedText, decodedResult) => {
            alert("QR Code Content: " + decodedText);
        },
        (errorMessage) => {
            console.log(errorMessage);
        }
    ).catch((err) => {
        console.error("Camera initialization error:", err);
    });
}