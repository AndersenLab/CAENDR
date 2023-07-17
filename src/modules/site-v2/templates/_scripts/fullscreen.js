// Open and Close Fullscreen Buttons
const closeButton = document.getElementById("closeButton");
const fullscreenButton = document.getElementById("fullscreenButton");
const fullScreenAvailable = document.fullscreenEnabled || 
                            document.mozFullscreenEnabled ||
                            document.webkitFullscreenEnabled ||
                            document.msFullscreenEnabled


/* Run any time fullscreen changes */
function onFullscreenChange() {

  // Check for an IGV variable and trigger browser(s) to resize
  if (typeof igv !== 'undefined') igv.visibilityChange();
}


if (fullScreenAvailable) {
  function openFullscreen() {
    if (fullscreenBrowser.requestFullscreen) {
      fullscreenBrowser.requestFullscreen().then(onFullscreenChange);
    } else if (fullscreenBrowser.webkitRequestFullscreen) { /* Safari */
      fullscreenBrowser.webkitRequestFullscreen().then(onFullscreenChange);
    } else if (fullscreenBrowser.msRequestFullscreen) { /* IE11 */
      fullscreenBrowser.msRequestFullscreen().then(onFullscreenChange);
    }
  }
} else {
  // fullscreen not supported
  fullscreenButton.classList.add("d-none");
}

  function closeFullscreen() {
    if (document.exitFullscreen) {
      document.exitFullscreen().then(onFullscreenChange);
    } else if (document.webkitExitFullscreen) { /* Safari */
      document.webkitExitFullscreen().then(onFullscreenChange);
    } else if (document.msExitFullscreen) { /* IE11 */
      document.msExitFullscreen().then(onFullscreenChange);
    }
  }

document.addEventListener("fullscreenchange", function() {
  if (closeButton.style.display === "block") {
    closeButton.style.display = "none";
  } else {
    closeButton.style.display = "block";
  }
});
document.addEventListener("mozfullscreenchange", function() {
  if (closeButton.style.display === "block") {
    closeButton.style.display = "none";
  } else {
    closeButton.style.display = "block";
  }
});
document.addEventListener("webkitfullscreenchange", function() {
  if (closeButton.style.display === "block") {
    closeButton.style.display = "none";
  } else {
    closeButton.style.display = "block";
  }
  if (window.matchMedia("(min-width: 1370px)").matches) {
         closeButton.classList.display = "none";
       }
});
document.addEventListener("msfullscreenchange", function() {
  if (closeButton.style.display === "block") {
    closeButton.style.display = "none";
  } else {
    closeButton.style.display = "block";
  }
});